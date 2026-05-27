#!/usr/bin/env python3
"""Detect candidate vertical lane centers from projection profiles."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from scipy.signal import find_peaks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import load_inventory  # noqa: E402

PROFILES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_profiles.csv"
PROJECTION_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections" / "vertical_projection_manifest.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "lane_center_detection.yaml"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers"
CANDIDATES_PATH = OUTPUT_DIR / "lane_center_candidates.csv"
MANIFEST_PATH = OUTPUT_DIR / "lane_center_manifest.csv"
PLOTS_DIR = OUTPUT_DIR / "diagnostics"

CANDIDATE_FIELDNAMES = [
    "image_id",
    "candidate_index",
    "center_x",
    "smoothed_projection_value",
    "raw_normalized_projection_value",
    "prominence",
    "method",
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


def detect_centers(profile: np.ndarray, config: dict[str, object]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
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
    properties = {key: value[keep] for key, value in properties.items()}
    return peaks, {"smoothed": smoothed, **properties}


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


def make_diagnostic_plot(
    image_id: str,
    profile: np.ndarray,
    smoothed: np.ndarray,
    centers: np.ndarray,
    manifest_row: dict[str, str],
) -> Path:
    output_path = PLOTS_DIR / f"{image_id}_lane_center_candidates.png"
    x_values = np.arange(len(profile))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_values, profile, color="#9a8c98", linewidth=0.8, alpha=0.55, label="normalized projection")
    ax.plot(x_values, smoothed, color="#4b2e83", linewidth=1.4, label="smoothed projection")
    for center_x in centers:
        ax.axvline(center_x, color="#c1121f", linewidth=1.0, alpha=0.85)
    ax.set_title(
        f"{image_id} lane-center candidates "
        f"({manifest_row['quality_flag']}: {manifest_row['source_filename']})"
    )
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


def candidate_rows(
    image_id: str,
    profile: np.ndarray,
    centers: np.ndarray,
    detection_data: dict[str, np.ndarray],
    method: str,
) -> list[dict[str, str]]:
    prominences = detection_data.get("prominences", np.zeros(len(centers), dtype=np.float32))
    smoothed = detection_data["smoothed"]
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
            }
        )
    return rows


def main() -> None:
    config = load_config()
    profiles = load_profiles()
    projection_manifest = load_projection_manifest()
    records = load_inventory()
    selected_plots = set(config["sample_diagnostic_image_ids"])
    method = str(config["method"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    all_candidate_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []

    for record in records:
        profile = profiles[record.image_id]
        centers, detection_data = detect_centers(profile, config)
        spacings = np.diff(centers) if len(centers) > 1 else np.array([], dtype=np.int32)
        plot_path = None
        projection_row = projection_manifest[record.image_id]
        if record.image_id in selected_plots:
            plot_path = make_diagnostic_plot(record.image_id, profile, detection_data["smoothed"], centers, projection_row)

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
                "detection_quality_flag": detection_quality(len(centers), spacings, config),
                "candidate_output_path": CANDIDATES_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "diagnostic_plot_path": "" if plot_path is None else plot_path.relative_to(PROJECT_ROOT).as_posix(),
                "method": method,
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

    print(f"Wrote {len(all_candidate_rows)} lane-center candidates for {len(manifest_rows)} images")
    print(f"Wrote candidates to {CANDIDATES_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Wrote {len(selected_plots)} diagnostic plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
