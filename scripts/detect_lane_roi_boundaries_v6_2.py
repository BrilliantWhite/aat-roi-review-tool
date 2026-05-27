#!/usr/bin/env python3
"""Detect standalone v6_2 horizontal-ROI-aware lane boundary candidates."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from scipy.signal import find_peaks, peak_prominences

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import load_grayscale, load_inventory  # noqa: E402

PROFILES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_profiles.csv"
PROJECTION_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_manifest.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "lane_roi_boundary_detection_v6_2.yaml"
LANE_COUNT_REVIEW_PATH = PROJECT_ROOT / "dataset" / "metadata" / "lane_count_review.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6_2"
CANDIDATES_PATH = OUTPUT_DIR / "lane_boundary_candidates_v6_2.csv"
MANIFEST_PATH = OUTPUT_DIR / "lane_boundary_manifest_v6_2.csv"
COMPARISON_PATH = OUTPUT_DIR / "lane_boundary_v6_1_v6_2_comparison.csv"
ROI_MANIFEST_PATH = OUTPUT_DIR / "horizontal_roi_manifest_v6_2.csv"
PLOTS_DIR = OUTPUT_DIR / "diagnostics"
V6_1_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6_1" / "lane_boundary_manifest_v6_1.csv"

CANDIDATE_FIELDNAMES = [
    "image_id",
    "candidate_index",
    "center_x",
    "left_x",
    "right_x",
    "estimated_width",
    "y_start",
    "y_end",
    "roi_height",
    "roi_confidence",
    "roi_reason",
    "roi_quality_flag",
    "left_boundary_source",
    "right_boundary_source",
    "smoothed_projection_value",
    "raw_normalized_projection_value",
    "band_region_projection_value",
    "prominence",
    "method",
    "source",
    "confidence",
    "status",
]
MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "issues",
    "width",
    "height",
    "y_start",
    "y_end",
    "roi_height",
    "roi_confidence",
    "roi_reason",
    "roi_quality_flag",
    "band_region_y_ranges_px",
    "method_notes",
    "expected_lane_count_override",
    "detected_boundary_count",
    "accepted_boundary_count",
    "direct_strong_count",
    "weak_peak_count",
    "conditional_fallback_count",
    "accepted_fallback_count",
    "accepted_count",
    "tentative_count",
    "review_only_count",
    "median_center_spacing_px",
    "median_estimated_width_px",
    "min_estimated_width_px",
    "max_estimated_width_px",
    "detection_quality_flag",
    "candidate_output_path",
    "diagnostic_plot_path",
    "method",
    "fallback_allowed",
    "fallback_reason",
    "manual_review_required",
]
ROI_FIELDNAMES = [
    "image_id",
    "source_filename",
    "width",
    "height",
    "y_start",
    "y_end",
    "roi_height",
    "roi_confidence",
    "roi_reason",
    "roi_quality_flag",
    "roi_profile_peak_value",
    "roi_profile_threshold",
    "method",
]
COMPARISON_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "v6_1_boundary_count",
    "v6_2_boundary_count",
    "boundary_count_delta",
    "v6_1_detection_quality_flag",
    "v6_2_detection_quality_flag",
    "v6_2_median_estimated_width_px",
    "fallback_allowed_v6_2",
    "fallback_reason_v6_2",
]


def load_config() -> dict[str, object]:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def odd_window_size_for_length(length: int, config: dict[str, object], fraction_key: str, min_key: str, max_key: str) -> int:
    raw_size = round(length * float(config[fraction_key]))
    size = max(int(config[min_key]), raw_size)
    size = min(int(config[max_key]), size)
    if size % 2 == 0:
        size += 1
    return max(1, min(size, length if length % 2 == 1 else length - 1))


def odd_window_size(width: int, config: dict[str, object]) -> int:
    return odd_window_size_for_length(width, config, "smoothing_window_fraction", "minimum_smoothing_window_px", "maximum_smoothing_window_px")


def smooth_profile(values: np.ndarray, window_size: int) -> np.ndarray:
    if window_size <= 1:
        return values.copy()
    pad = window_size // 2
    padded = np.pad(values, pad_width=pad, mode="edge")
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    return np.convolve(padded, kernel, mode="valid")


def normalize(values: np.ndarray) -> np.ndarray:
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if maximum <= minimum:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - minimum) / (maximum - minimum)).astype(np.float32)


def load_profiles() -> dict[str, np.ndarray]:
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with PROFILES_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            grouped[row["image_id"]].append((int(row["x"]), float(row["normalized_projection_value"])))
    profiles = {}
    for image_id, rows in grouped.items():
        rows.sort(key=lambda item: item[0])
        profiles[image_id] = np.array([value for _, value in rows], dtype=np.float32)
    return profiles


def load_csv_by_image_id(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def load_lane_count_review() -> dict[str, dict[str, str]]:
    if not LANE_COUNT_REVIEW_PATH.exists():
        return {}
    return load_csv_by_image_id(LANE_COUNT_REVIEW_PATH)


def contiguous_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    if not np.any(mask):
        return []
    indices = np.where(mask)[0]
    splits = np.where(np.diff(indices) > 1)[0] + 1
    return [(int(segment[0]), int(segment[-1]) + 1) for segment in np.split(indices, splits)]


def close_small_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    if max_gap <= 0 or not np.any(mask):
        return mask.copy()
    closed = mask.copy()
    false_segments = contiguous_segments(~mask)
    for start, end in false_segments:
        if start == 0 or end == len(mask):
            continue
        if end - start <= max_gap:
            closed[start:end] = True
    return closed


def estimate_broad_roi(image_id: str, config: dict[str, object]) -> tuple[dict[str, object], np.ndarray, np.ndarray, np.ndarray]:
    grayscale = load_grayscale(image_id).astype(np.float32)
    inverted = 255.0 - grayscale
    height, width = inverted.shape
    x_margin = round(width * float(config["roi_profile_x_margin_fraction"]))
    content = inverted[:, x_margin : max(x_margin + 1, width - x_margin)]
    row_profile = normalize(content.mean(axis=1))
    smoothed = smooth_profile(
        row_profile,
        odd_window_size_for_length(height, config, "roi_smoothing_window_fraction", "roi_minimum_smoothing_window_px", "roi_maximum_smoothing_window_px"),
    )
    allowed_start = round(height * float(config["roi_allowed_y_min_fraction"]))
    allowed_end = round(height * float(config["roi_allowed_y_max_fraction"]))
    allowed_end = max(allowed_start + 1, min(height, allowed_end))
    allowed = smoothed[allowed_start:allowed_end]
    peak_value = float(np.max(allowed)) if len(allowed) else 0.0
    threshold = max(float(np.quantile(allowed, float(config["roi_threshold_quantile"]))) if len(allowed) else 0.0, peak_value * float(config["roi_threshold_floor_fraction"]))
    mask = allowed >= threshold
    min_height = round(height * float(config["roi_min_height_fraction"]))
    max_height = round(height * float(config["roi_max_height_fraction"]))
    if np.any(mask):
        indices = np.where(mask)[0]
        y_start = allowed_start + int(indices[0])
        y_end = allowed_start + int(indices[-1]) + 1
        reason = "v6_row_signal_threshold_band"
    else:
        center = allowed_start + int(np.argmax(allowed)) if len(allowed) else height // 2
        y_start = center - min_height // 2
        y_end = y_start + min_height
        reason = "v6_fallback_centered_minimum_height"
    pad = round(height * float(config["roi_padding_fraction"]))
    y_start = max(allowed_start, y_start - pad)
    y_end = min(allowed_end, y_end + pad)
    if y_end - y_start < min_height:
        center = (y_start + y_end) // 2
        y_start = max(allowed_start, center - min_height // 2)
        y_end = min(allowed_end, y_start + min_height)
        y_start = max(allowed_start, y_end - min_height)
        reason = f"{reason};expanded_to_min_height"
    elif y_end - y_start > max_height:
        center = (y_start + y_end) // 2
        y_start = max(allowed_start, center - max_height // 2)
        y_end = min(allowed_end, y_start + max_height)
        y_start = max(allowed_start, y_end - max_height)
        reason = f"{reason};clamped_to_max_height"
    broad_roi = {
        "y_start": int(y_start),
        "y_end": int(y_end),
        "roi_height": int(max(1, y_end - y_start)),
        "roi_confidence": "medium",
        "roi_reason": reason,
        "roi_quality_flag": "review",
        "roi_profile_peak_value": f"{peak_value:.6f}",
        "roi_profile_threshold": f"{threshold:.6f}",
    }
    return broad_roi, grayscale, inverted, smoothed


def band_region_profiles(image_id: str, config: dict[str, object], roi: dict[str, object]) -> tuple[np.ndarray, list[np.ndarray], str]:
    grayscale = load_grayscale(image_id).astype(np.float32)
    inverted = 255.0 - grayscale
    height, width = inverted.shape
    roi_start = int(roi["y_start"])
    roi_end = int(roi["y_end"])
    roi_height = max(1, roi_end - roi_start)
    profiles = []
    ranges = []
    for start_frac, end_frac in config["band_region_y_ranges"]:
        start = max(roi_start, min(roi_end - 1, roi_start + round(roi_height * float(start_frac))))
        end = max(start + 1, min(roi_end, roi_start + round(roi_height * float(end_frac))))
        region = inverted[start:end, :]
        profile = normalize(region.mean(axis=0))
        profiles.append(profile)
        ranges.append(f"{start}-{end}")
    return np.max(np.vstack(profiles), axis=0), profiles, ";".join(ranges)


def preliminary_lane_centers_for_roi(image_id: str, config: dict[str, object], roi: dict[str, object]) -> np.ndarray:
    band_profile, band_profiles, _ = band_region_profiles(image_id, config, roi)
    combined_raw = normalize(float(config["band_projection_weight"]) * band_profile)
    width = len(combined_raw)
    smoothed = smooth_profile(combined_raw, odd_window_size(width, config))
    band_smoothed_profiles = [smooth_profile(profile, odd_window_size(width, config)) for profile in band_profiles]
    edge_margin = round(width * float(config["edge_margin_fraction"]))
    min_distance = max(1, round(width * float(config["minimum_peak_distance_fraction"])))
    strong_height = float(np.quantile(smoothed, float(config["strong_peak_height_quantile"])))
    weak_height = float(np.quantile(smoothed, float(config["weak_peak_height_quantile"])))
    strong_peaks, _ = find_peaks(smoothed, distance=min_distance, prominence=float(config["strong_peak_prominence"]), height=strong_height)
    weak_peaks, _ = find_peaks(smoothed, distance=min_distance, prominence=float(config["weak_peak_prominence"]), height=weak_height)
    strong_peaks = strong_peaks[(strong_peaks >= edge_margin) & (strong_peaks <= width - edge_margin - 1)]
    weak_peaks = weak_peaks[(weak_peaks >= edge_margin) & (weak_peaks <= width - edge_margin - 1)]
    support_thresholds = [float(np.quantile(profile, float(config["weak_peak_min_combined_value_quantile"]))) for profile in band_smoothed_profiles]
    strong_set = {int(peak) for peak in strong_peaks}
    weak_only = []
    for peak in weak_peaks:
        if int(peak) in strong_set:
            continue
        support = sum(1 for profile, threshold in zip(band_smoothed_profiles, support_thresholds) if float(profile[peak]) >= threshold)
        if support >= int(config["weak_peak_min_band_support"]):
            weak_only.append(int(peak))
    centers, _ = merge_close_centers(
        [int(peak) for peak in strong_peaks] + weak_only,
        {**{int(peak): "band_region_strong_peak" for peak in strong_peaks}, **{int(peak): "band_region_weak_peak" for peak in weak_only}},
        min_distance,
        smoothed,
    )
    return centers


def nonwhite_row_support_from_lane_columns(
    grayscale: np.ndarray,
    lane_centers: np.ndarray,
    broad_roi: dict[str, object],
    config: dict[str, object],
) -> tuple[np.ndarray, np.ndarray, float, float, int, int, int]:
    height, width = grayscale.shape
    if len(lane_centers):
        spacing = float(np.median(np.diff(np.sort(lane_centers)))) if len(lane_centers) > 1 else width / max(2, int(config["coverage_target_lane_count"]))
    else:
        spacing = width / max(2, int(config["coverage_target_lane_count"]))
    half_width = max(int(config["roi_lane_sample_min_half_width_px"]), round(spacing * float(config["roi_lane_sample_half_width_fraction"])))
    broad_start = int(broad_roi["y_start"])
    broad_end = int(broad_roi["y_end"])
    lane_support_profiles = []
    lane_nonwhite_counts = []
    for center_x in lane_centers:
        left = max(0, int(center_x) - half_width)
        right = min(width, int(center_x) + half_width + 1)
        if right <= left:
            continue
        lane_region = grayscale[:, left:right]
        white_level = float(np.quantile(lane_region, float(config["roi_nonwhite_background_high_quantile"])))
        dark_level = float(np.quantile(lane_region[broad_start:broad_end, :], float(config["roi_nonwhite_signal_low_quantile"]))) if broad_end > broad_start else float(np.quantile(lane_region, float(config["roi_nonwhite_signal_low_quantile"])))
        delta = max(float(config["roi_nonwhite_min_delta_intensity"]), white_level - dark_level)
        threshold = white_level - delta * float(config["roi_nonwhite_threshold_fraction"])
        nonwhite = lane_region <= threshold
        lane_nonwhite_counts.append(nonwhite.sum(axis=1).astype(np.float32) / max(1, lane_region.shape[1]))
        lane_support_profiles.append((255.0 - lane_region).mean(axis=1).astype(np.float32))
    if not lane_support_profiles:
        zeros = np.zeros(height, dtype=np.float32)
        return zeros, zeros, 0.0, 0.0, half_width, broad_start, broad_end
    nonwhite_stack = np.vstack(lane_nonwhite_counts)
    signal_stack = np.vstack([normalize(profile) for profile in lane_support_profiles])
    nonwhite_support = np.median(nonwhite_stack, axis=0).astype(np.float32)
    signal_support = np.quantile(signal_stack, float(config["roi_lane_profile_quantile"]), axis=0).astype(np.float32)
    combined = normalize(0.75 * normalize(nonwhite_support) + 0.25 * normalize(signal_support))
    smoothed = smooth_profile(
        combined,
        odd_window_size_for_length(height, config, "roi_nonwhite_smoothing_window_fraction", "roi_nonwhite_minimum_smoothing_window_px", "roi_nonwhite_maximum_smoothing_window_px"),
    )
    local = smoothed[broad_start:broad_end] if broad_end > broad_start else smoothed
    threshold = max(
        float(config["roi_nonwhite_row_support_floor"]),
        float(np.quantile(local, float(config["roi_nonwhite_row_support_quantile"]))) if len(local) else 0.0,
    )
    return smoothed, nonwhite_support, threshold, float(np.max(local)) if len(local) else 0.0, half_width, broad_start, broad_end


def estimate_horizontal_roi(image_id: str, whole_profile: np.ndarray, config: dict[str, object]) -> dict[str, object]:
    del whole_profile
    broad_roi, grayscale, inverted, broad_smoothed = estimate_broad_roi(image_id, config)
    height, width = inverted.shape
    lane_centers = preliminary_lane_centers_for_roi(image_id, config, broad_roi)
    support_profile, raw_nonwhite_support, support_threshold, support_peak, half_width, broad_start, broad_end = nonwhite_row_support_from_lane_columns(
        grayscale,
        lane_centers,
        broad_roi,
        config,
    )
    broad_height = max(1, broad_end - broad_start)
    broad_reason = str(broad_roi["roi_reason"])
    if len(lane_centers) == 0:
        y_start = broad_start
        y_end = broad_end
        lane_reason = "lane_support_unavailable_fallback_to_broad_roi"
    else:
        support_mask = support_profile >= max(support_threshold, float(config["roi_nonwhite_row_support_min_fraction"]))
        gap_px = max(int(config["roi_nonwhite_close_gap_min_px"]), round(height * float(config["roi_nonwhite_close_gap_fraction"])))
        support_mask = close_small_gaps(support_mask, gap_px)
        components = contiguous_segments(support_mask)
        min_component_height = max(2, round(height * float(config["roi_nonwhite_component_min_height_fraction"])))
        lane_rows = [segment for segment in components if segment[1] - segment[0] >= min_component_height and segment[1] > broad_start and segment[0] < broad_end]
        if lane_rows:
            top = min(start for start, _ in lane_rows)
            bottom = max(end for _, end in lane_rows)
            top = max(round(height * float(config["roi_allowed_y_min_fraction"])), top - round(height * float(config["roi_nonwhite_top_extension_fraction"])))
            bottom = min(round(height * float(config["roi_allowed_y_max_fraction"])), bottom + round(height * float(config["roi_nonwhite_bottom_extension_fraction"])))
            candidate_height = bottom - top
            min_height = round(height * float(config["roi_nonwhite_min_height_fraction"]))
            if candidate_height < min_height:
                pad_needed = min_height - candidate_height
                top = max(round(height * float(config["roi_allowed_y_min_fraction"])), top - pad_needed // 2)
                bottom = min(round(height * float(config["roi_allowed_y_max_fraction"])), bottom + (pad_needed - pad_needed // 2))
                top = max(round(height * float(config["roi_allowed_y_min_fraction"])), bottom - min_height)
                bottom = min(round(height * float(config["roi_allowed_y_max_fraction"])), top + min_height)
            y_start = int(top)
            y_end = int(bottom)
            lane_reason = f"lane_nonwhite_support_rows={len(lane_rows)}"
        else:
            y_start = broad_start
            y_end = broad_end
            lane_reason = "lane_support_empty_fallback_to_broad_roi"
    bottom_guard = round(height * float(config["roi_bottom_guard_fraction"]))
    if y_end > bottom_guard:
        y_end = bottom_guard
        lane_reason = f"{lane_reason};bottom_guard_applied"
    if y_end - y_start < round(height * float(config["roi_fallback_min_height_fraction"])):
        y_start, y_end = broad_start, broad_end
        lane_reason = f"{lane_reason};fallback_to_broad_roi_too_thin"
    roi_height = max(1, y_end - y_start)
    broad_peak = float(np.max(broad_smoothed[broad_start:broad_end])) if broad_end > broad_start else float(np.max(broad_smoothed))
    if len(lane_centers) >= int(config["roi_lane_evidence_min_support_count"]) and roi_height / height >= float(config["roi_nonwhite_min_height_fraction"]):
        confidence = "high"
        quality = "ok"
    elif support_peak >= float(config["roi_nonwhite_row_support_floor"]):
        confidence = "medium"
        quality = "review"
    else:
        confidence = "low"
        quality = "review"
    return {
        "y_start": int(y_start),
        "y_end": int(y_end),
        "roi_height": int(roi_height),
        "roi_confidence": confidence,
        "roi_reason": f"{broad_reason};{lane_reason};lane_support={len(lane_centers)};sample_half_width={half_width}",
        "roi_quality_flag": quality,
        "roi_profile_peak_value": f"{max(broad_peak, support_peak):.6f}",
        "roi_profile_threshold": f"{max(float(broad_roi['roi_profile_threshold']), support_threshold):.6f}",
    }


def local_peak_near(smoothed: np.ndarray, target: float, half_window: int, edge_margin: int) -> int:
    left = max(edge_margin, int(round(target)) - half_window)
    right = min(len(smoothed) - edge_margin - 1, int(round(target)) + half_window)
    if right < left:
        return int(np.clip(round(target), edge_margin, len(smoothed) - edge_margin - 1))
    return left + int(np.argmax(smoothed[left : right + 1]))


def merge_close_centers(centers: list[int], sources: dict[int, str], min_distance: int, smoothed: np.ndarray) -> tuple[np.ndarray, list[str]]:
    if not centers:
        return np.array([], dtype=np.int32), []
    priority = {"band_region_strong_peak": 3, "band_region_weak_peak": 2, "conditional_fallback": 1}
    ordered = sorted(set(int(center) for center in centers))
    clusters: list[list[int]] = []
    for center in ordered:
        if not clusters or center - clusters[-1][-1] >= min_distance:
            clusters.append([center])
        else:
            clusters[-1].append(center)
    merged = []
    merged_sources = []
    for cluster in clusters:
        best_priority = max(priority.get(sources.get(center, "conditional_fallback"), 0) for center in cluster)
        best = max((center for center in cluster if priority.get(sources.get(center, "conditional_fallback"), 0) == best_priority), key=lambda center: smoothed[center])
        merged.append(best)
        merged_sources.append(sources.get(best, "conditional_fallback"))
    order = np.argsort(merged)
    return np.array([merged[index] for index in order], dtype=np.int32), [merged_sources[index] for index in order]


def expected_lane_count(review_row: dict[str, str] | None) -> int | None:
    if not review_row:
        return None
    value = review_row.get("expected_lane_count", "").strip()
    return int(value) if value else None


def fallback_decision(image_id: str, peaks: np.ndarray, projection_row: dict[str, str], review_row: dict[str, str] | None, config: dict[str, object]) -> tuple[bool, str, int]:
    override_count = expected_lane_count(review_row)
    if override_count is not None:
        return len(peaks) < override_count, f"manual_expected_lane_count={override_count}", override_count
    high_risk_ids = {str(value) for value in config.get("high_risk_oversegmentation_image_ids", [])}
    if image_id in high_risk_ids and len(peaks) <= int(config.get("high_risk_max_nonfallback_count", 6)):
        return False, "blocked_by_high_risk_low_lane_count_safeguard", int(config["coverage_target_lane_count"])
    issues = projection_row.get("issues", "")
    excluded_tokens = [str(token) for token in config.get("coverage_full_layout_excluded_issue_tokens", [])]
    if any(token in issues for token in excluded_tokens):
        return False, "blocked_by_partial_or_narrow_image_quality_flag", int(config["coverage_target_lane_count"])
    if int(projection_row.get("width", 0) or 0) < int(config["coverage_full_layout_min_width_px"]):
        return False, "blocked_by_width_below_full_layout_threshold", int(config["coverage_target_lane_count"])
    if len(peaks) < int(config["coverage_fallback_min_confident_count"]):
        return False, "blocked_by_too_few_direct_or_weak_peaks", int(config["coverage_target_lane_count"])
    if len(peaks) < int(config["coverage_full_layout_min_direct_count"]):
        return False, "blocked_by_insufficient_full_layout_evidence", int(config["coverage_target_lane_count"])
    return True, "full_layout_supported_by_band_region_peak_count_and_image_width", int(config["coverage_target_lane_count"])


def add_conditional_fallback(peaks: np.ndarray, sources_list: list[str], smoothed: np.ndarray, config: dict[str, object], edge_margin: int, target_count: int) -> tuple[np.ndarray, list[str]]:
    centers = [int(peak) for peak in peaks]
    sources = {int(peak): source for peak, source in zip(peaks, sources_list)}
    if not centers:
        return np.array([], dtype=np.int32), []
    width = len(smoothed)
    expected_spacing = width / (target_count + 1)
    detected_spacing = float(np.median(np.diff(sorted(centers)))) if len(centers) > 1 else expected_spacing
    spacing = min(expected_spacing, detected_spacing) if detected_spacing > 0 else expected_spacing
    half_window = max(int(config["coverage_local_window_min_px"]), round(width * float(config["coverage_local_window_fraction"])))
    gap_multiplier = float(config["coverage_interpolation_gap_multiplier"])
    max_added = max(1, round(max(len(centers), target_count) * float(config["coverage_max_added_fraction"])))
    added = 0
    for left, right in zip(sorted(centers), sorted(centers)[1:]):
        gap = right - left
        if gap <= spacing * gap_multiplier:
            continue
        missing = int(round(gap / spacing)) - 1
        for index in range(1, max(0, missing) + 1):
            if added >= max_added or len(centers) >= target_count:
                break
            candidate = local_peak_near(smoothed, left + gap * index / (missing + 1), half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "conditional_fallback"
                added += 1
    if bool(config.get("coverage_extrapolate_edges", False)) and added < max_added:
        ordered = sorted(centers)
        while len(ordered) < target_count and ordered[0] - spacing > edge_margin and added < max_added:
            candidate = local_peak_near(smoothed, ordered[0] - spacing, half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "conditional_fallback"
                added += 1
                ordered = sorted(centers)
            else:
                break
        while len(ordered) < target_count and ordered[-1] + spacing < width - edge_margin and added < max_added:
            candidate = local_peak_near(smoothed, ordered[-1] + spacing, half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "conditional_fallback"
                added += 1
                ordered = sorted(centers)
            else:
                break
    return merge_close_centers(centers, sources, max(2, round(spacing * 0.35)), smoothed)


def grade_candidate(source: str, prominence: float, smoothed_value: float, config: dict[str, object]) -> tuple[str, str]:
    if source == "band_region_strong_peak":
        return "high", "accepted"
    if source == "band_region_weak_peak":
        return "medium", "accepted_for_review"
    if prominence >= float(config["fallback_confidence_high_prominence"]) and smoothed_value >= float(config["fallback_confidence_high_smoothed_quantile"]):
        return "high", "accepted"
    if prominence >= float(config["fallback_confidence_medium_prominence"]) and smoothed_value >= float(config["fallback_confidence_medium_smoothed_quantile"]):
        return "medium", "accepted_for_review"
    return "low", "review_only"


def detect_centers(image_id: str, whole_profile: np.ndarray, projection_row: dict[str, str], review_row: dict[str, str] | None, config: dict[str, object], roi: dict[str, object]) -> tuple[np.ndarray, dict[str, object]]:
    band_profile, band_profiles, band_ranges = band_region_profiles(image_id, config, roi)
    combined_raw = normalize(float(config["band_projection_weight"]) * band_profile + float(config["whole_projection_weight"]) * whole_profile)
    width = len(combined_raw)
    smoothed = smooth_profile(combined_raw, odd_window_size(width, config))
    band_smoothed_profiles = [smooth_profile(profile, odd_window_size(width, config)) for profile in band_profiles]
    edge_margin = round(width * float(config["edge_margin_fraction"]))
    min_distance = max(1, round(width * float(config["minimum_peak_distance_fraction"])))
    strong_height = float(np.quantile(smoothed, float(config["strong_peak_height_quantile"])))
    weak_height = float(np.quantile(smoothed, float(config["weak_peak_height_quantile"])))
    strong_peaks, _ = find_peaks(smoothed, distance=min_distance, prominence=float(config["strong_peak_prominence"]), height=strong_height)
    weak_peaks, _ = find_peaks(smoothed, distance=min_distance, prominence=float(config["weak_peak_prominence"]), height=weak_height)
    keep_strong = (strong_peaks >= edge_margin) & (strong_peaks <= width - edge_margin - 1)
    keep_weak = (weak_peaks >= edge_margin) & (weak_peaks <= width - edge_margin - 1)
    strong_peaks = strong_peaks[keep_strong]
    weak_peaks = weak_peaks[keep_weak]
    support_thresholds = [float(np.quantile(profile, float(config["weak_peak_min_combined_value_quantile"]))) for profile in band_smoothed_profiles]
    strong_set = {int(peak) for peak in strong_peaks}
    weak_only = []
    for peak in weak_peaks:
        if int(peak) in strong_set:
            continue
        support = sum(1 for profile, threshold in zip(band_smoothed_profiles, support_thresholds) if float(profile[peak]) >= threshold)
        if support >= int(config["weak_peak_min_band_support"]):
            weak_only.append(int(peak))
    centers, sources = merge_close_centers(
        [int(peak) for peak in strong_peaks] + weak_only,
        {**{int(peak): "band_region_strong_peak" for peak in strong_peaks}, **{int(peak): "band_region_weak_peak" for peak in weak_only}},
        min_distance,
        smoothed,
    )
    fallback_allowed, fallback_reason, target_count = fallback_decision(image_id, centers, projection_row, review_row, config)
    if fallback_allowed:
        centers, sources = add_conditional_fallback(centers, sources, smoothed, config, edge_margin, target_count)
    prominences = peak_prominences(smoothed, centers)[0] if len(centers) else np.array([], dtype=np.float32)
    grades = [grade_candidate(source, float(prominences[index]), float(smoothed[center]), config) for index, (center, source) in enumerate(zip(centers, sources))]
    return centers, {
        "combined_raw": combined_raw,
        "band_profile": band_profile,
        "smoothed": smoothed,
        "prominences": prominences,
        "sources": sources,
        "confidences": [confidence for confidence, _ in grades],
        "statuses": [status for _, status in grades],
        "fallback_allowed": fallback_allowed,
        "fallback_reason": fallback_reason,
        "expected_lane_count": expected_lane_count(review_row),
        "band_ranges": band_ranges,
    }


def apply_high_risk_cap(image_id: str, centers: np.ndarray, detection_data: dict[str, object], config: dict[str, object]) -> tuple[np.ndarray, dict[str, object]]:
    high_risk_ids = {str(value) for value in config.get("high_risk_oversegmentation_image_ids", [])}
    max_count = int(config.get("high_risk_max_accepted_count", 0) or 0)
    if image_id not in high_risk_ids or max_count <= 0 or len(centers) <= max_count:
        return centers, detection_data
    sources = detection_data["sources"]
    prominences = detection_data["prominences"]
    smoothed = detection_data["smoothed"]
    priority = {"band_region_strong_peak": 3, "band_region_weak_peak": 2, "conditional_fallback": 1}
    ranked = sorted(
        range(len(centers)),
        key=lambda index: (priority.get(sources[index], 0), float(prominences[index]), float(smoothed[centers[index]])),
        reverse=True,
    )
    keep = set(ranked[:max_count])
    new_statuses = list(detection_data["statuses"])
    new_confidences = list(detection_data["confidences"])
    for index in range(len(centers)):
        if index not in keep:
            new_statuses[index] = "review_only"
            new_confidences[index] = "low"
    detection_data = {**detection_data, "statuses": new_statuses, "confidences": new_confidences}
    return centers, detection_data


def boundary_score(profile: np.ndarray, gradient: np.ndarray, start: int, stop: int, config: dict[str, object]) -> int:
    if stop < start:
        return start
    span = np.arange(start, stop + 1)
    valley = 1.0 - normalize(profile[span])
    edge = normalize(gradient[span])
    score = float(config["boundary_valley_weight"]) * valley + float(config["boundary_gradient_weight"]) * edge
    return int(span[int(np.argmax(score))])


def estimate_boundaries(centers: np.ndarray, detection_data: dict[str, object], config: dict[str, object]) -> list[dict[str, object]]:
    if len(centers) == 0:
        return []
    profile = detection_data["smoothed"]
    width = len(profile)
    spacings = np.diff(centers) if len(centers) > 1 else np.array([width / max(2, int(config["coverage_target_lane_count"]))], dtype=np.float32)
    default_spacing = float(np.median(spacings)) if len(spacings) else width / max(2, int(config["coverage_target_lane_count"]))
    gradient = np.abs(np.gradient(profile))
    min_half = int(config["boundary_min_half_width_px"])
    results = []
    for index, center in enumerate(centers):
        left_neighbor_spacing = center - centers[index - 1] if index > 0 else default_spacing
        right_neighbor_spacing = centers[index + 1] - center if index < len(centers) - 1 else default_spacing
        left_spacing = max(float(left_neighbor_spacing), min_half * 2)
        right_spacing = max(float(right_neighbor_spacing), min_half * 2)
        left_max = max(min_half, round(left_spacing * float(config["boundary_max_half_width_fraction_of_spacing"])))
        right_max = max(min_half, round(right_spacing * float(config["boundary_max_half_width_fraction_of_spacing"])))
        left_search = max(0, center - round(left_spacing * float(config["boundary_search_half_spacing_fraction"])))
        right_search = min(width - 1, center + round(right_spacing * float(config["boundary_search_half_spacing_fraction"])))
        left_min = max(0, center - left_max)
        right_max_x = min(width - 1, center + right_max)
        left_boundary = boundary_score(profile, gradient, left_search, max(left_search, center - min_half), config)
        right_boundary = boundary_score(profile, gradient, min(width - 1, center + min_half), right_search, config)
        left_boundary = int(np.clip(left_boundary, left_min, center - 1))
        right_boundary = int(np.clip(right_boundary, center + 1, right_max_x))
        min_width = round(default_spacing * float(config["boundary_min_coverage_fraction_of_spacing"]))
        max_width = round(default_spacing * float(config["boundary_max_coverage_fraction_of_spacing"]))
        estimated_width = right_boundary - left_boundary + 1
        left_source = "adaptive_valley_gradient"
        right_source = "adaptive_valley_gradient"
        if estimated_width < min_width:
            half = max(min_half, round(min_width / 2))
            left_boundary = max(0, center - half)
            right_boundary = min(width - 1, center + half)
            left_source = "spacing_minimum_expansion"
            right_source = "spacing_minimum_expansion"
        elif estimated_width > max_width:
            half = max(min_half, round(max_width / 2))
            left_boundary = max(0, center - half)
            right_boundary = min(width - 1, center + half)
            left_source = "spacing_maximum_clamp"
            right_source = "spacing_maximum_clamp"
        pad = int(config.get("boundary_edge_padding_px", 0))
        left_boundary = max(0, left_boundary - pad)
        right_boundary = min(width - 1, right_boundary + pad)
        results.append(
            {
                "left_x": int(left_boundary),
                "right_x": int(right_boundary),
                "estimated_width": int(right_boundary - left_boundary + 1),
                "left_boundary_source": left_source,
                "right_boundary_source": right_source,
            }
        )
    return results


def detection_quality(boundary_count: int, widths: np.ndarray, manual_review_required: bool, config: dict[str, object]) -> str:
    if boundary_count == 0:
        return "problematic"
    if manual_review_required:
        return "review"
    if boundary_count < int(config["expected_lane_count_min"]) or boundary_count > int(config["expected_lane_count_max"]):
        return "problematic"
    if boundary_count < int(config["review_lane_count_min"]) or boundary_count > int(config["review_lane_count_max"]):
        return "review"
    if len(widths) and np.min(widths) < int(config["boundary_min_half_width_px"]) * 2:
        return "review"
    return "ok"


def make_diagnostic_plot(image_id: str, whole_profile: np.ndarray, detection_data: dict[str, object], boundaries: list[dict[str, object]], projection_row: dict[str, str]) -> Path:
    output_path = PLOTS_DIR / f"{image_id}_lane_boundary_candidates_v6_2.png"
    x_values = np.arange(len(whole_profile))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_values, whole_profile, color="#9a8c98", linewidth=0.8, alpha=0.45, label="whole-image projection")
    ax.plot(x_values, detection_data["band_profile"], color="#457b9d", linewidth=0.9, alpha=0.60, label="band-region projection")
    ax.plot(x_values, detection_data["smoothed"], color="#4b2e83", linewidth=1.4, label="v6_2 combined smoothed")
    for center_x, source, status, boundary in zip(detection_data["centers"], detection_data["sources"], detection_data["statuses"], boundaries):
        if source == "band_region_strong_peak":
            color = "#c1121f"
        elif source == "band_region_weak_peak":
            color = "#f77f00"
        elif status != "review_only":
            color = "#2a9d8f"
        else:
            color = "#6c757d"
        ax.axvspan(boundary["left_x"], boundary["right_x"], color="#ffd60a", alpha=0.16)
        ax.axvline(center_x, color=color, linewidth=1.0, alpha=0.9)
    ax.set_title(f"{image_id} v6_2 adaptive lane boundaries ({projection_row['quality_flag']}: {projection_row['source_filename']})")
    ax.set_xlabel("x-coordinate (pixels)")
    ax.set_ylabel("normalized inverted grayscale signal")
    ax.set_xlim(0, max(0, len(whole_profile) - 1))
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def candidate_rows(image_id: str, whole_profile: np.ndarray, centers: np.ndarray, detection_data: dict[str, object], boundaries: list[dict[str, object]], method: str, roi: dict[str, object]) -> list[dict[str, str]]:
    rows = []
    for index, (center_x, boundary) in enumerate(zip(centers, boundaries), start=1):
        rows.append(
            {
                "image_id": image_id,
                "candidate_index": str(index),
                "center_x": str(int(center_x)),
                "left_x": str(boundary["left_x"]),
                "right_x": str(boundary["right_x"]),
                "estimated_width": str(boundary["estimated_width"]),
                "y_start": str(roi["y_start"]),
                "y_end": str(roi["y_end"]),
                "roi_height": str(roi["roi_height"]),
                "roi_confidence": str(roi["roi_confidence"]),
                "roi_reason": str(roi["roi_reason"]),
                "roi_quality_flag": str(roi["roi_quality_flag"]),
                "left_boundary_source": str(boundary["left_boundary_source"]),
                "right_boundary_source": str(boundary["right_boundary_source"]),
                "smoothed_projection_value": f"{float(detection_data['smoothed'][center_x]):.6f}",
                "raw_normalized_projection_value": f"{float(whole_profile[center_x]):.6f}",
                "band_region_projection_value": f"{float(detection_data['band_profile'][center_x]):.6f}",
                "prominence": f"{float(detection_data['prominences'][index - 1]):.6f}",
                "method": method,
                "source": str(detection_data["sources"][index - 1]),
                "confidence": str(detection_data["confidences"][index - 1]),
                "status": str(detection_data["statuses"][index - 1]),
            }
        )
    return rows


def main() -> None:
    config = load_config()
    profiles = load_profiles()
    projection_manifest = load_csv_by_image_id(PROJECTION_MANIFEST_PATH)
    lane_count_review = load_lane_count_review()
    v6_1_manifest = load_csv_by_image_id(V6_1_MANIFEST_PATH) if V6_1_MANIFEST_PATH.exists() else {}
    records = load_inventory()
    selected_plots = set(config["sample_diagnostic_image_ids"])
    method = str(config["method"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    all_candidate_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []
    comparison_rows: list[dict[str, str]] = []
    roi_rows: list[dict[str, str]] = []
    for record in records:
        whole_profile = profiles[record.image_id]
        projection_row = projection_manifest[record.image_id]
        review_row = lane_count_review.get(record.image_id)
        roi = estimate_horizontal_roi(record.image_id, whole_profile, config)
        roi_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "width": str(record.width),
                "height": str(record.height),
                "y_start": str(roi["y_start"]),
                "y_end": str(roi["y_end"]),
                "roi_height": str(roi["roi_height"]),
                "roi_confidence": str(roi["roi_confidence"]),
                "roi_reason": str(roi["roi_reason"]),
                "roi_quality_flag": str(roi["roi_quality_flag"]),
                "roi_profile_peak_value": str(roi["roi_profile_peak_value"]),
                "roi_profile_threshold": str(roi["roi_profile_threshold"]),
                "method": method,
            }
        )
        centers, detection_data = detect_centers(record.image_id, whole_profile, projection_row, review_row, config, roi)
        centers, detection_data = apply_high_risk_cap(record.image_id, centers, detection_data, config)
        detection_data["centers"] = centers
        boundaries = estimate_boundaries(centers, detection_data, config)
        statuses = detection_data["statuses"]
        sources = detection_data["sources"]
        accepted_mask = [status in {"accepted", "accepted_for_review"} for status in statuses]
        accepted_centers = np.array([center for center, accepted in zip(centers, accepted_mask) if accepted], dtype=np.int32)
        accepted_widths = np.array([boundary["estimated_width"] for boundary, accepted in zip(boundaries, accepted_mask) if accepted], dtype=np.int32)
        spacings = np.diff(accepted_centers) if len(accepted_centers) > 1 else np.array([], dtype=np.int32)
        direct_strong_count = sum(1 for source in sources if source == "band_region_strong_peak")
        weak_count = sum(1 for source in sources if source == "band_region_weak_peak")
        fallback_count = sum(1 for source in sources if source == "conditional_fallback")
        accepted_fallback_count = sum(1 for source, status in zip(sources, statuses) if source == "conditional_fallback" and status in {"accepted", "accepted_for_review"})
        tentative_count = sum(1 for status in statuses if status == "accepted_for_review")
        review_only_count = sum(1 for status in statuses if status == "review_only")
        manual_review_required = bool(weak_count or fallback_count) or detection_data["fallback_allowed"] is False or projection_row["quality_flag"] != "ok" or roi["roi_quality_flag"] != "ok" or review_row is not None
        quality = detection_quality(len(accepted_centers), accepted_widths, manual_review_required, config)
        plot_path = None
        if record.image_id in selected_plots:
            plot_path = make_diagnostic_plot(record.image_id, whole_profile, detection_data, boundaries, projection_row)
        all_candidate_rows.extend(candidate_rows(record.image_id, whole_profile, centers, detection_data, boundaries, method, roi))
        median_width = "" if len(accepted_widths) == 0 else f"{float(np.median(accepted_widths)):.2f}"
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "quality_flag": projection_row["quality_flag"],
                "issues": projection_row["issues"],
                "width": str(record.width),
                "height": str(record.height),
                "y_start": str(roi["y_start"]),
                "y_end": str(roi["y_end"]),
                "roi_height": str(roi["roi_height"]),
                "roi_confidence": str(roi["roi_confidence"]),
                "roi_reason": str(roi["roi_reason"]),
                "roi_quality_flag": str(roi["roi_quality_flag"]),
                "band_region_y_ranges_px": str(detection_data["band_ranges"]),
                "method_notes": "standalone v6_2 detector using raw images, shared metadata, and one horizontal ROI per image; x-detection stays ROI-limited while shared y-range is expanded from adaptive lane-column non-white support to preserve full lane height",
                "expected_lane_count_override": "" if detection_data["expected_lane_count"] is None else str(detection_data["expected_lane_count"]),
                "detected_boundary_count": str(len(boundaries)),
                "accepted_boundary_count": str(len(accepted_centers)),
                "direct_strong_count": str(direct_strong_count),
                "weak_peak_count": str(weak_count),
                "conditional_fallback_count": str(fallback_count),
                "accepted_fallback_count": str(accepted_fallback_count),
                "accepted_count": str(sum(1 for status in statuses if status == "accepted")),
                "tentative_count": str(tentative_count),
                "review_only_count": str(review_only_count),
                "median_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.median(spacings)):.2f}",
                "median_estimated_width_px": median_width,
                "min_estimated_width_px": "" if len(accepted_widths) == 0 else f"{float(np.min(accepted_widths)):.2f}",
                "max_estimated_width_px": "" if len(accepted_widths) == 0 else f"{float(np.max(accepted_widths)):.2f}",
                "detection_quality_flag": quality,
                "candidate_output_path": CANDIDATES_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "diagnostic_plot_path": "" if plot_path is None else plot_path.relative_to(PROJECT_ROOT).as_posix(),
                "method": method,
                "fallback_allowed": str(bool(detection_data["fallback_allowed"])).lower(),
                "fallback_reason": str(detection_data["fallback_reason"]),
                "manual_review_required": str(manual_review_required).lower(),
            }
        )
        if v6_1_manifest:
            v6_1_row = v6_1_manifest.get(record.image_id, {})
            v6_1_count = int(v6_1_row.get("accepted_boundary_count", 0) or 0)
            comparison_rows.append(
                {
                    "image_id": record.image_id,
                    "source_filename": record.source_filename,
                    "quality_flag": projection_row["quality_flag"],
                    "v6_1_boundary_count": str(v6_1_count),
                    "v6_2_boundary_count": str(len(accepted_centers)),
                    "boundary_count_delta": str(len(accepted_centers) - v6_1_count),
                    "v6_1_detection_quality_flag": v6_1_row.get("detection_quality_flag", ""),
                    "v6_2_detection_quality_flag": quality,
                    "v6_2_median_estimated_width_px": median_width,
                    "fallback_allowed_v6_2": str(bool(detection_data["fallback_allowed"])).lower(),
                    "fallback_reason_v6_2": str(detection_data["fallback_reason"]),
                }
            )
    with ROI_MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ROI_FIELDNAMES)
        writer.writeheader()
        writer.writerows(roi_rows)
    with CANDIDATES_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CANDIDATE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_candidate_rows)
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"Wrote {len(all_candidate_rows)} v6_2 lane-boundary candidates for {len(manifest_rows)} images")
    print(f"Wrote horizontal ROI manifest to {ROI_MANIFEST_PATH}")
    print(f"Wrote candidates to {CANDIDATES_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    if comparison_rows:
        with COMPARISON_PATH.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=COMPARISON_FIELDNAMES)
            writer.writeheader()
            writer.writerows(comparison_rows)
        changed_count = sum(1 for row in comparison_rows if int(row["boundary_count_delta"]) != 0)
        print(f"Wrote optional v6.1-v6_2 comparison to {COMPARISON_PATH}; count changed for {changed_count} images")
    else:
        print("Skipped optional v6.1-v6_2 comparison because v6.1 manifest was not found")
    print(f"Wrote {len(selected_plots)} diagnostic plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
