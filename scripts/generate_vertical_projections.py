#!/usr/bin/env python3
"""Generate vertical x-axis intensity projections for raw gel images."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import ImageRecord, load_grayscale, load_inventory  # noqa: E402

QUALITY_REPORT_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_quality_report.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "projections"
PROFILES_PATH = OUTPUT_DIR / "vertical_projection_profiles.csv"
MANIFEST_PATH = OUTPUT_DIR / "vertical_projection_manifest.csv"
PLOTS_DIR = OUTPUT_DIR / "plots"
SELECTED_PLOT_IMAGE_IDS = [
    "IMG_0006",  # ok
    "IMG_0001",  # review
    "IMG_0002",  # problematic
    "IMG_0025",  # narrow/tilted problematic crop
    "IMG_0041",  # large ok image
]

PROFILE_FIELDNAMES = [
    "image_id",
    "x",
    "projection_value",
    "normalized_projection_value",
]
MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "issues",
    "projection_output_path",
    "plot_output_path",
    "width",
    "profile_length",
    "height",
    "projection_min",
    "projection_max",
    "projection_mean",
    "projection_std",
    "normalized_projection_min",
    "normalized_projection_max",
]


def load_quality_rows() -> dict[str, dict[str, str]]:
    with QUALITY_REPORT_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def compute_vertical_projection(grayscale: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    inverted_signal = 255.0 - grayscale.astype(np.float32)
    projection = inverted_signal.mean(axis=0)
    projection_min = float(np.min(projection))
    projection_max = float(np.max(projection))
    projection_range = projection_max - projection_min
    if projection_range == 0:
        normalized = np.zeros_like(projection, dtype=np.float32)
    else:
        normalized = (projection - projection_min) / projection_range
    return projection, normalized


def make_projection_plot(record: ImageRecord, normalized: np.ndarray, quality_row: dict[str, str]) -> Path:
    output_path = PLOTS_DIR / f"{record.image_id}_vertical_projection.png"
    x_values = np.arange(normalized.shape[0])

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(x_values, normalized, color="#4b2e83", linewidth=1.2)
    ax.set_title(
        f"{record.image_id} vertical intensity projection "
        f"({quality_row['quality_flag']}: {record.source_filename})"
    )
    ax.set_xlabel("x-coordinate (pixels)")
    ax.set_ylabel("normalized inverted grayscale signal")
    ax.set_xlim(0, max(0, normalized.shape[0] - 1))
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def profile_rows(record: ImageRecord, projection: np.ndarray, normalized: np.ndarray) -> list[dict[str, str]]:
    rows = []
    for x, (projection_value, normalized_value) in enumerate(zip(projection, normalized, strict=True)):
        rows.append(
            {
                "image_id": record.image_id,
                "x": str(x),
                "projection_value": f"{float(projection_value):.6f}",
                "normalized_projection_value": f"{float(normalized_value):.6f}",
            }
        )
    return rows


def manifest_row(
    record: ImageRecord,
    quality_row: dict[str, str],
    projection: np.ndarray,
    normalized: np.ndarray,
    plot_path: Path | None,
) -> dict[str, str]:
    return {
        "image_id": record.image_id,
        "source_filename": record.source_filename,
        "quality_flag": quality_row["quality_flag"],
        "issues": quality_row["issues"],
        "projection_output_path": PROFILES_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "plot_output_path": "" if plot_path is None else plot_path.relative_to(PROJECT_ROOT).as_posix(),
        "width": str(record.width),
        "profile_length": str(len(projection)),
        "height": str(record.height),
        "projection_min": f"{float(np.min(projection)):.6f}",
        "projection_max": f"{float(np.max(projection)):.6f}",
        "projection_mean": f"{float(np.mean(projection)):.6f}",
        "projection_std": f"{float(np.std(projection)):.6f}",
        "normalized_projection_min": f"{float(np.min(normalized)):.6f}",
        "normalized_projection_max": f"{float(np.max(normalized)):.6f}",
    }


def main() -> None:
    quality_rows = load_quality_rows()
    records = load_inventory()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    all_profile_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []

    for record in records:
        grayscale = load_grayscale(record)
        projection, normalized = compute_vertical_projection(grayscale)
        quality_row = quality_rows[record.image_id]
        plot_path = None
        if record.image_id in SELECTED_PLOT_IMAGE_IDS:
            plot_path = make_projection_plot(record, normalized, quality_row)

        all_profile_rows.extend(profile_rows(record, projection, normalized))
        manifest_rows.append(manifest_row(record, quality_row, projection, normalized, plot_path))

    with PROFILES_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PROFILE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_profile_rows)

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote {len(all_profile_rows)} projection points for {len(manifest_rows)} images")
    print(f"Wrote profiles to {PROFILES_PATH}")
    print(f"Wrote manifest to {MANIFEST_PATH}")
    print(f"Wrote {len(SELECTED_PLOT_IMAGE_IDS)} representative plots to {PLOTS_DIR}")


if __name__ == "__main__":
    main()
