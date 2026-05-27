#!/usr/bin/env python3
"""Detect v4 candidate vertical lane centers using band-region projections."""

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
CONFIG_PATH = PROJECT_ROOT / "configs" / "lane_center_detection_v4.yaml"
LANE_COUNT_REVIEW_PATH = PROJECT_ROOT / "dataset" / "metadata" / "lane_count_review.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers_v4"
CANDIDATES_PATH = OUTPUT_DIR / "lane_center_candidates_v4.csv"
MANIFEST_PATH = OUTPUT_DIR / "lane_center_manifest_v4.csv"
COMPARISON_PATH = OUTPUT_DIR / "lane_center_v3_v4_comparison.csv"
PLOTS_DIR = OUTPUT_DIR / "diagnostics"
V3_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers_v3" / "lane_center_manifest_v3.csv"

CANDIDATE_FIELDNAMES = [
    "image_id",
    "candidate_index",
    "center_x",
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
    "band_region_y_ranges_px",
    "method_notes",
    "expected_lane_count_override",
    "detected_center_count",
    "accepted_center_count",
    "direct_strong_count",
    "weak_peak_count",
    "conditional_fallback_count",
    "accepted_fallback_count",
    "accepted_count",
    "tentative_count",
    "review_only_count",
    "median_center_spacing_px",
    "min_center_spacing_px",
    "max_center_spacing_px",
    "detection_quality_flag",
    "candidate_output_path",
    "diagnostic_plot_path",
    "method",
    "fallback_allowed",
    "fallback_reason",
    "manual_review_required",
]
COMPARISON_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "v3_center_count",
    "v4_center_count",
    "center_count_delta",
    "v3_added_by_conditional_fallback_count",
    "v4_conditional_fallback_count",
    "v4_direct_strong_count",
    "v4_weak_peak_count",
    "v3_detection_quality_flag",
    "v4_detection_quality_flag",
    "fallback_allowed_v4",
    "fallback_reason_v4",
]


def load_config() -> dict[str, object]:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def odd_window_size(width: int, config: dict[str, object]) -> int:
    raw_size = round(width * float(config["smoothing_window_fraction"]))
    size = max(int(config["minimum_smoothing_window_px"]), raw_size)
    size = min(int(config["maximum_smoothing_window_px"]), size)
    if size % 2 == 0:
        size += 1
    return max(1, min(size, width if width % 2 == 1 else width - 1))


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


def band_region_profiles(image_id: str, config: dict[str, object]) -> tuple[np.ndarray, list[np.ndarray], str]:
    grayscale = load_grayscale(image_id).astype(np.float32)
    inverted = 255.0 - grayscale
    height, width = inverted.shape
    profiles = []
    ranges = []
    for start_frac, end_frac in config["band_region_y_ranges"]:
        start = max(0, min(height - 1, round(height * float(start_frac))))
        end = max(start + 1, min(height, round(height * float(end_frac))))
        region = inverted[start:end, :]
        profile = normalize(region.mean(axis=0))
        profiles.append(profile)
        ranges.append(f"{start}-{end}")
    return np.max(np.vstack(profiles), axis=0), profiles, ";".join(ranges)


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


def detect_centers(image_id: str, whole_profile: np.ndarray, projection_row: dict[str, str], review_row: dict[str, str] | None, config: dict[str, object]) -> tuple[np.ndarray, dict[str, object]]:
    band_profile, band_profiles, band_ranges = band_region_profiles(image_id, config)
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


def detection_quality(center_count: int, spacings: np.ndarray, manual_review_required: bool, config: dict[str, object]) -> str:
    if center_count == 0:
        return "problematic"
    if manual_review_required:
        return "review"
    if center_count < int(config["expected_lane_count_min"]) or center_count > int(config["expected_lane_count_max"]):
        return "problematic"
    if center_count < int(config["review_lane_count_min"]) or center_count > int(config["review_lane_count_max"]):
        return "review"
    if len(spacings) and np.min(spacings) < 8:
        return "review"
    return "ok"


def make_diagnostic_plot(image_id: str, profile: np.ndarray, detection_data: dict[str, object], projection_row: dict[str, str]) -> Path:
    output_path = PLOTS_DIR / f"{image_id}_lane_center_candidates_v4.png"
    x_values = np.arange(len(profile))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_values, profile, color="#9a8c98", linewidth=0.8, alpha=0.45, label="whole-image projection")
    ax.plot(x_values, detection_data["band_profile"], color="#457b9d", linewidth=0.9, alpha=0.60, label="band-region projection")
    ax.plot(x_values, detection_data["smoothed"], color="#4b2e83", linewidth=1.4, label="v4 combined smoothed")
    for center_x, source, status in zip(detection_data["centers"], detection_data["sources"], detection_data["statuses"]):
        if source == "band_region_strong_peak":
            color = "#c1121f"
        elif source == "band_region_weak_peak":
            color = "#f77f00"
        elif status != "review_only":
            color = "#2a9d8f"
        else:
            color = "#6c757d"
        ax.axvline(center_x, color=color, linewidth=1.0, alpha=0.9)
    ax.set_title(f"{image_id} v4 band-region lane-center candidates ({projection_row['quality_flag']}: {projection_row['source_filename']})")
    ax.set_xlabel("x-coordinate (pixels)")
    ax.set_ylabel("normalized inverted grayscale signal")
    ax.set_xlim(0, max(0, len(profile) - 1))
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def candidate_rows(image_id: str, whole_profile: np.ndarray, centers: np.ndarray, detection_data: dict[str, object], method: str) -> list[dict[str, str]]:
    rows = []
    for index, center_x in enumerate(centers, start=1):
        rows.append(
            {
                "image_id": image_id,
                "candidate_index": str(index),
                "center_x": str(int(center_x)),
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
    v3_manifest = load_csv_by_image_id(V3_MANIFEST_PATH) if V3_MANIFEST_PATH.exists() else {}
    records = load_inventory()
    selected_plots = set(config["sample_diagnostic_image_ids"])
    method = str(config["method"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    all_candidate_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []
    comparison_rows: list[dict[str, str]] = []
    for record in records:
        whole_profile = profiles[record.image_id]
        projection_row = projection_manifest[record.image_id]
        review_row = lane_count_review.get(record.image_id)
        centers, detection_data = detect_centers(record.image_id, whole_profile, projection_row, review_row, config)
        centers, detection_data = apply_high_risk_cap(record.image_id, centers, detection_data, config)
        detection_data["centers"] = centers
        statuses = detection_data["statuses"]
        sources = detection_data["sources"]
        accepted_mask = [status in {"accepted", "accepted_for_review"} for status in statuses]
        accepted_centers = np.array([center for center, accepted in zip(centers, accepted_mask) if accepted], dtype=np.int32)
        spacings = np.diff(accepted_centers) if len(accepted_centers) > 1 else np.array([], dtype=np.int32)
        direct_strong_count = sum(1 for source in sources if source == "band_region_strong_peak")
        weak_count = sum(1 for source in sources if source == "band_region_weak_peak")
        fallback_count = sum(1 for source in sources if source == "conditional_fallback")
        accepted_fallback_count = sum(1 for source, status in zip(sources, statuses) if source == "conditional_fallback" and status in {"accepted", "accepted_for_review"})
        tentative_count = sum(1 for status in statuses if status == "accepted_for_review")
        review_only_count = sum(1 for status in statuses if status == "review_only")
        manual_review_required = bool(weak_count or fallback_count) or detection_data["fallback_allowed"] is False or projection_row["quality_flag"] != "ok" or review_row is not None
        quality = detection_quality(len(accepted_centers), spacings, manual_review_required, config)
        plot_path = None
        if record.image_id in selected_plots:
            plot_path = make_diagnostic_plot(record.image_id, whole_profile, detection_data, projection_row)
        all_candidate_rows.extend(candidate_rows(record.image_id, whole_profile, centers, detection_data, method))
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "quality_flag": projection_row["quality_flag"],
                "issues": projection_row["issues"],
                "width": str(record.width),
                "band_region_y_ranges_px": str(detection_data["band_ranges"]),
                "method_notes": "max projection across configured band-region y zones blended with whole-image projection; manual cropping/cleaning may later improve quality but is not required for v4",
                "expected_lane_count_override": "" if detection_data["expected_lane_count"] is None else str(detection_data["expected_lane_count"]),
                "detected_center_count": str(len(centers)),
                "accepted_center_count": str(len(accepted_centers)),
                "direct_strong_count": str(direct_strong_count),
                "weak_peak_count": str(weak_count),
                "conditional_fallback_count": str(fallback_count),
                "accepted_fallback_count": str(accepted_fallback_count),
                "accepted_count": str(sum(1 for status in statuses if status == "accepted")),
                "tentative_count": str(tentative_count),
                "review_only_count": str(review_only_count),
                "median_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.median(spacings)):.2f}",
                "min_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.min(spacings)):.2f}",
                "max_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.max(spacings)):.2f}",
                "detection_quality_flag": quality,
                "candidate_output_path": CANDIDATES_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "diagnostic_plot_path": "" if plot_path is None else plot_path.relative_to(PROJECT_ROOT).as_posix(),
                "method": method,
                "fallback_allowed": str(bool(detection_data["fallback_allowed"])).lower(),
                "fallback_reason": str(detection_data["fallback_reason"]),
                "manual_review_required": str(manual_review_required).lower(),
            }
        )
        v3_row = v3_manifest.get(record.image_id, {})
        v3_count = int(v3_row.get("accepted_center_count", 0) or 0)
        comparison_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "quality_flag": projection_row["quality_flag"],
                "v3_center_count": str(v3_count),
                "v4_center_count": str(len(accepted_centers)),
                "center_count_delta": str(len(accepted_centers) - v3_count),
                "v3_added_by_conditional_fallback_count": v3_row.get("added_by_conditional_fallback_count", ""),
                "v4_conditional_fallback_count": str(fallback_count),
                "v4_direct_strong_count": str(direct_strong_count),
                "v4_weak_peak_count": str(weak_count),
                "v3_detection_quality_flag": v3_row.get("detection_quality_flag", ""),
                "v4_detection_quality_flag": quality,
                "fallback_allowed_v4": str(bool(detection_data["fallback_allowed"])).lower(),
                "fallback_reason_v4": str(detection_data["fallback_reason"]),
            }
        )
    with CANDIDATES_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CANDIDATE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_candidate_rows)
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)
    with COMPARISON_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=COMPARISON_FIELDNAMES)
        writer.writeheader()
        writer.writerows(comparison_rows)
    increased_count = sum(1 for row in comparison_rows if int(row["center_count_delta"]) > 0)
    print(f"Wrote {len(all_candidate_rows)} v4 lane-center candidates for {len(manifest_rows)} images")
    print(f"Wrote candidates to {CANDIDATES_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Wrote v3-v4 comparison to {COMPARISON_PATH}; v4 increased accepted center counts for {increased_count} images")
    print(f"Wrote {len(selected_plots)} diagnostic plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
