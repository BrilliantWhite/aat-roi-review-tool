#!/usr/bin/env python3
"""Detect coverage-oriented candidate vertical lane centers from projection profiles."""

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

from image_loading import load_inventory  # noqa: E402

PROFILES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_profiles.csv"
PROJECTION_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_manifest.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "lane_center_detection_v2.yaml"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers_v2"
CANDIDATES_PATH = OUTPUT_DIR / "lane_center_candidates_v2.csv"
MANIFEST_PATH = OUTPUT_DIR / "lane_center_manifest_v2.csv"
COMPARISON_PATH = OUTPUT_DIR / "lane_center_v1_v2_comparison.csv"
PLOTS_DIR = OUTPUT_DIR / "diagnostics"
V1_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers" / "lane_center_manifest.csv"

CANDIDATE_FIELDNAMES = [
    "image_id",
    "candidate_index",
    "center_x",
    "smoothed_projection_value",
    "raw_normalized_projection_value",
    "prominence",
    "method",
    "source",
]
MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "issues",
    "width",
    "detected_center_count",
    "median_center_spacing_px",
    "min_center_spacing_px",
    "max_center_spacing_px",
    "detection_quality_flag",
    "candidate_output_path",
    "diagnostic_plot_path",
    "method",
    "added_by_coverage_fallback_count",
]
COMPARISON_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "v1_center_count",
    "v2_center_count",
    "center_count_delta",
    "coverage_increased",
    "v1_detection_quality_flag",
    "v2_detection_quality_flag",
    "v2_added_by_coverage_fallback_count",
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
    return min(size, width if width % 2 == 1 else width - 1)


def smooth_profile(values: np.ndarray, window_size: int) -> np.ndarray:
    if window_size <= 1:
        return values.copy()
    pad = window_size // 2
    padded = np.pad(values, pad_width=pad, mode="edge")
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    return np.convolve(padded, kernel, mode="valid")


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


def load_projection_manifest() -> dict[str, dict[str, str]]:
    with PROJECTION_MANIFEST_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def load_v1_manifest() -> dict[str, dict[str, str]]:
    with V1_MANIFEST_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def local_peak_near(smoothed: np.ndarray, target: float, half_window: int, edge_margin: int) -> int:
    left = max(edge_margin, int(round(target)) - half_window)
    right = min(len(smoothed) - edge_margin - 1, int(round(target)) + half_window)
    if right < left:
        return int(np.clip(round(target), edge_margin, len(smoothed) - edge_margin - 1))
    return left + int(np.argmax(smoothed[left : right + 1]))


def merge_close_centers(centers: list[int], sources: dict[int, str], min_distance: int, smoothed: np.ndarray) -> tuple[np.ndarray, list[str]]:
    if not centers:
        return np.array([], dtype=np.int32), []
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
        best = max(cluster, key=lambda center: smoothed[center])
        merged.append(best)
        if any(sources.get(center) == "coverage_fallback" for center in cluster) and sources.get(best) != "detected_peak":
            merged_sources.append("coverage_fallback")
        else:
            merged_sources.append(sources.get(best, "detected_peak"))
    return np.array(merged, dtype=np.int32), merged_sources


def add_coverage_centers(peaks: np.ndarray, smoothed: np.ndarray, config: dict[str, object], edge_margin: int) -> tuple[np.ndarray, list[str]]:
    centers = [int(peak) for peak in peaks]
    sources = {int(peak): "detected_peak" for peak in peaks}
    if len(centers) < int(config["coverage_fallback_min_confident_count"]):
        return np.array(centers, dtype=np.int32), [sources[center] for center in centers]

    width = len(smoothed)
    target_count = int(config["coverage_target_lane_count"])
    expected_spacing = width / (target_count + 1)
    if len(centers) > 1:
        detected_spacing = float(np.median(np.diff(sorted(centers))))
        spacing = min(expected_spacing, detected_spacing) if detected_spacing > 0 else expected_spacing
    else:
        spacing = expected_spacing

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
            if added >= max_added:
                break
            candidate = local_peak_near(smoothed, left + gap * index / (missing + 1), half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "coverage_fallback"
                added += 1

    if bool(config.get("coverage_extrapolate_edges", False)) and added < max_added:
        ordered = sorted(centers)
        while len(ordered) < target_count and ordered[0] - spacing > edge_margin and added < max_added:
            candidate = local_peak_near(smoothed, ordered[0] - spacing, half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "coverage_fallback"
                added += 1
                ordered = sorted(centers)
            else:
                break
        while len(ordered) < target_count and ordered[-1] + spacing < width - edge_margin and added < max_added:
            candidate = local_peak_near(smoothed, ordered[-1] + spacing, half_window, edge_margin)
            if all(abs(candidate - center) >= max(2, round(spacing * 0.45)) for center in centers):
                centers.append(candidate)
                sources[candidate] = "coverage_fallback"
                added += 1
                ordered = sorted(centers)
            else:
                break

    min_merge_distance = max(2, round(spacing * 0.35))
    return merge_close_centers(centers, sources, min_merge_distance, smoothed)


def detect_centers(profile: np.ndarray, config: dict[str, object]) -> tuple[np.ndarray, dict[str, np.ndarray | list[str]]]:
    width = len(profile)
    smoothed = smooth_profile(profile, odd_window_size(width, config))
    edge_margin = round(width * float(config["edge_margin_fraction"]))
    min_distance = max(1, round(width * float(config["minimum_peak_distance_fraction"])))
    height_threshold = float(np.quantile(smoothed, float(config["peak_height_quantile"])))

    peaks, properties = find_peaks(
        smoothed,
        distance=min_distance,
        prominence=float(config["peak_prominence"]),
        height=height_threshold,
    )
    keep = (peaks >= edge_margin) & (peaks <= width - edge_margin - 1)
    peaks = peaks[keep]
    centers, sources = add_coverage_centers(peaks, smoothed, config, edge_margin)
    prominences = peak_prominences(smoothed, centers)[0] if len(centers) else np.array([], dtype=np.float32)
    return centers, {"smoothed": smoothed, "prominences": prominences, "sources": sources}


def detection_quality(center_count: int, spacings: np.ndarray, config: dict[str, object]) -> str:
    if center_count == 0:
        return "problematic"
    if center_count < int(config["expected_lane_count_min"]) or center_count > int(config["expected_lane_count_max"]):
        return "problematic"
    if center_count < int(config["review_lane_count_min"]) or center_count > int(config["review_lane_count_max"]):
        return "review"
    if len(spacings) and np.min(spacings) < 8:
        return "review"
    return "ok"


def make_diagnostic_plot(image_id: str, profile: np.ndarray, smoothed: np.ndarray, centers: np.ndarray, sources: list[str], manifest_row: dict[str, str]) -> Path:
    output_path = PLOTS_DIR / f"{image_id}_lane_center_candidates_v2.png"
    x_values = np.arange(len(profile))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_values, profile, color="#9a8c98", linewidth=0.8, alpha=0.55, label="normalized projection")
    ax.plot(x_values, smoothed, color="#4b2e83", linewidth=1.4, label="less-smoothed projection")
    for center_x, source in zip(centers, sources):
        color = "#c1121f" if source == "detected_peak" else "#f77f00"
        ax.axvline(center_x, color=color, linewidth=1.0, alpha=0.9)
    ax.set_title(f"{image_id} v2 coverage lane-center candidates ({manifest_row['quality_flag']}: {manifest_row['source_filename']})")
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


def candidate_rows(image_id: str, profile: np.ndarray, centers: np.ndarray, detection_data: dict[str, np.ndarray | list[str]], method: str) -> list[dict[str, str]]:
    prominences = detection_data.get("prominences", np.zeros(len(centers), dtype=np.float32))
    smoothed = detection_data["smoothed"]
    sources = detection_data.get("sources", ["detected_peak"] * len(centers))
    rows = []
    for index, center_x in enumerate(centers, start=1):
        rows.append(
            {
                "image_id": image_id,
                "candidate_index": str(index),
                "center_x": str(int(center_x)),
                "smoothed_projection_value": f"{float(smoothed[center_x]):.6f}",
                "raw_normalized_projection_value": f"{float(profile[center_x]):.6f}",
                "prominence": f"{float(prominences[index - 1]):.6f}",
                "method": method,
                "source": str(sources[index - 1]),
            }
        )
    return rows


def main() -> None:
    config = load_config()
    profiles = load_profiles()
    projection_manifest = load_projection_manifest()
    v1_manifest = load_v1_manifest()
    records = load_inventory()
    selected_plots = set(config["sample_diagnostic_image_ids"])
    method = str(config["method"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    all_candidate_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []
    comparison_rows: list[dict[str, str]] = []

    for record in records:
        profile = profiles[record.image_id]
        centers, detection_data = detect_centers(profile, config)
        spacings = np.diff(centers) if len(centers) > 1 else np.array([], dtype=np.int32)
        plot_path = None
        projection_row = projection_manifest[record.image_id]
        sources = detection_data.get("sources", [])
        added_count = sum(1 for source in sources if source == "coverage_fallback")
        if record.image_id in selected_plots:
            plot_path = make_diagnostic_plot(record.image_id, profile, detection_data["smoothed"], centers, sources, projection_row)

        quality = detection_quality(len(centers), spacings, config)
        all_candidate_rows.extend(candidate_rows(record.image_id, profile, centers, detection_data, method))
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "quality_flag": projection_row["quality_flag"],
                "issues": projection_row["issues"],
                "width": str(record.width),
                "detected_center_count": str(len(centers)),
                "median_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.median(spacings)):.2f}",
                "min_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.min(spacings)):.2f}",
                "max_center_spacing_px": "" if len(spacings) == 0 else f"{float(np.max(spacings)):.2f}",
                "detection_quality_flag": quality,
                "candidate_output_path": CANDIDATES_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "diagnostic_plot_path": "" if plot_path is None else plot_path.relative_to(PROJECT_ROOT).as_posix(),
                "method": method,
                "added_by_coverage_fallback_count": str(added_count),
            }
        )
        v1_row = v1_manifest.get(record.image_id, {})
        v1_count = int(v1_row.get("detected_center_count", 0) or 0)
        comparison_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "quality_flag": projection_row["quality_flag"],
                "v1_center_count": str(v1_count),
                "v2_center_count": str(len(centers)),
                "center_count_delta": str(len(centers) - v1_count),
                "coverage_increased": str(len(centers) > v1_count).lower(),
                "v1_detection_quality_flag": v1_row.get("detection_quality_flag", ""),
                "v2_detection_quality_flag": quality,
                "v2_added_by_coverage_fallback_count": str(added_count),
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

    increased_count = sum(1 for row in comparison_rows if row["coverage_increased"] == "true")
    print(f"Wrote {len(all_candidate_rows)} v2 lane-center candidates for {len(manifest_rows)} images")
    print(f"Wrote candidates to {CANDIDATES_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Wrote v1-v2 comparison to {COMPARISON_PATH}; v2 increased coverage for {increased_count} images")
    print(f"Wrote {len(selected_plots)} diagnostic plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
