#!/usr/bin/env python3
"""Create original-image overlays for current lane-center candidates."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import load_inventory, load_rgb  # noqa: E402

CANDIDATES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers" / "lane_center_candidates.csv"
CENTER_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers" / "lane_center_manifest.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "overlays" / "centerlines"
OVERLAY_MANIFEST_PATH = OUTPUT_DIR / "lane_center_overlay_manifest.csv"

LINE_COLOR = (220, 20, 60, 255)
BAND_COLOR = (255, 215, 0, 46)
TEXT_COLOR = (255, 255, 255, 255)
TEXT_BACKGROUND = (0, 0, 0, 170)

MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "overlay_path",
    "center_count",
    "notes",
]


def load_candidates() -> dict[str, list[int]]:
    centers_by_image: dict[str, list[int]] = defaultdict(list)
    with CANDIDATES_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            centers_by_image[row["image_id"]].append(int(row["center_x"]))
    return {image_id: sorted(centers) for image_id, centers in centers_by_image.items()}


def load_center_manifest() -> dict[str, dict[str, str]]:
    with CENTER_MANIFEST_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def line_width_for_image(width: int) -> int:
    return max(1, round(width / 500))


def approximate_half_band_width(centers: list[int], image_width: int) -> int:
    if len(centers) < 2:
        return max(3, round(image_width * 0.01))
    median_spacing = float(np.median(np.diff(centers)))
    return max(3, round(median_spacing * 0.22))


def draw_label(draw: ImageDraw.ImageDraw, image_id: str, center_count: int, notes: str) -> None:
    label = f"{image_id}: {center_count} centerlines; approximate guide bands, not final boundaries"
    if notes:
        label = f"{label}; {notes}"
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    bbox = draw.textbbox((0, 0), label, font=font)
    pad = 5
    draw.rectangle((0, 0, bbox[2] + pad * 2, bbox[3] + pad * 2), fill=TEXT_BACKGROUND)
    draw.text((pad, pad), label, fill=TEXT_COLOR, font=font)


def create_overlay(image_id: str, centers: list[int], manifest_row: dict[str, str]) -> Path:
    rgb = load_rgb(image_id)
    base = Image.fromarray(rgb).convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    half_band_width = approximate_half_band_width(centers, width)
    line_width = line_width_for_image(width)

    for center_x in centers:
        left = max(0, center_x - half_band_width)
        right = min(width - 1, center_x + half_band_width)
        draw.rectangle((left, 0, right, height - 1), fill=BAND_COLOR)
        draw.line((center_x, 0, center_x, height - 1), fill=LINE_COLOR, width=line_width)

    notes = f"quality={manifest_row.get('quality_flag', '')}; detection={manifest_row.get('detection_quality_flag', '')}"
    draw_label(draw, image_id, len(centers), notes)

    output = Image.alpha_composite(base, overlay).convert("RGB")
    output_path = OUTPUT_DIR / f"{image_id}_lane_center_overlay.png"
    output.save(output_path)
    return output_path


def main() -> None:
    centers_by_image = load_candidates()
    center_manifest = load_center_manifest()
    records = load_inventory()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    for record in records:
        centers = centers_by_image.get(record.image_id, [])
        source_manifest = center_manifest.get(record.image_id, {})
        overlay_path = create_overlay(record.image_id, centers, source_manifest)
        notes = "approximate centerlines and guide bands from current Option A baseline; not final lane boundaries"
        if source_manifest.get("quality_flag") or source_manifest.get("detection_quality_flag"):
            notes = (
                f"{notes}; image_quality={source_manifest.get('quality_flag', '')}; "
                f"detection_quality={source_manifest.get('detection_quality_flag', '')}"
            )
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "overlay_path": overlay_path.relative_to(PROJECT_ROOT).as_posix(),
                "center_count": str(len(centers)),
                "notes": notes,
            }
        )

    with OVERLAY_MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Wrote {len(manifest_rows)} lane-center overlays to {OUTPUT_DIR}")
    print(f"Wrote overlay manifest to {OVERLAY_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
