#!/usr/bin/env python3
"""Generate representative grayscale preprocessing examples."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import convert_rgb_to_grayscale, get_image_record, load_rgb  # noqa: E402

QUALITY_REPORT_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_quality_report.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "preprocessing" / "grayscale_examples"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"
SELECTED_IMAGE_IDS = ["IMG_0006", "IMG_0001", "IMG_0002"]
FIELDNAMES = [
    "image_id",
    "source_filename",
    "quality_flag",
    "issues",
    "output_path",
    "grayscale_min",
    "grayscale_max",
    "grayscale_std",
    "dynamic_range_p01_p99",
    "contrast_note",
]


def load_quality_rows() -> dict[str, dict[str, str]]:
    with QUALITY_REPORT_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def grayscale_metrics(grayscale: np.ndarray) -> dict[str, str]:
    p01, p99 = np.percentile(grayscale, [1, 99])
    dynamic_range = float(p99 - p01)
    std = float(np.std(grayscale))
    note = "pass" if dynamic_range > 50 and std > 10 else "review"
    return {
        "grayscale_min": str(int(np.min(grayscale))),
        "grayscale_max": str(int(np.max(grayscale))),
        "grayscale_std": f"{std:.2f}",
        "dynamic_range_p01_p99": f"{dynamic_range:.2f}",
        "contrast_note": note,
    }


def main() -> None:
    quality_rows = load_quality_rows()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    for image_id in SELECTED_IMAGE_IDS:
        record = get_image_record(image_id)
        rgb = load_rgb(record)
        grayscale = convert_rgb_to_grayscale(rgb)
        output_path = OUTPUT_DIR / f"{record.image_id}_grayscale.png"
        Image.fromarray(grayscale, mode="L").save(output_path)

        quality = quality_rows[record.image_id]
        row = {
            "image_id": record.image_id,
            "source_filename": record.source_filename,
            "quality_flag": quality["quality_flag"],
            "issues": quality["issues"],
            "output_path": output_path.relative_to(PROJECT_ROOT).as_posix(),
        }
        row.update(grayscale_metrics(grayscale))
        manifest_rows.append(row)

    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote {len(manifest_rows)} grayscale examples to {OUTPUT_DIR}")
    print(f"Wrote manifest to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
