#!/usr/bin/env python3
"""Create original-image overlays for v4 lane-center candidates."""

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

CANDIDATES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers_v4" / "lane_center_candidates_v4.csv"
CENTER_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_centers_v4" / "lane_center_manifest_v4.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "overlays" / "centerlines_v4"
OVERLAY_MANIFEST_PATH = OUTPUT_DIR / "lane_center_overlay_manifest_v4.csv"

STRONG_LINE_COLOR = (220, 20, 60, 255)
WEAK_LINE_COLOR = (247, 127, 0, 255)
HIGH_FALLBACK_LINE_COLOR = (42, 157, 143, 255)
LOW_FALLBACK_LINE_COLOR = (108, 117, 125, 255)
STRONG_BAND_COLOR = (255, 215, 0, 42)
WEAK_BAND_COLOR = (255, 165, 0, 34)
HIGH_FALLBACK_BAND_COLOR = (42, 157, 143, 36)
LOW_FALLBACK_BAND_COLOR = (108, 117, 125, 24)
TEXT_COLOR = (255, 255, 255, 255)
TEXT_BACKGROUND = (0, 0, 0, 170)

MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "overlay_path",
    "center_count",
    "accepted_center_count",
    "direct_strong_count",
    "weak_peak_count",
    "conditional_fallback_count",
    "accepted_fallback_count",
    "notes",
]


def load_candidates() -> dict[str, list[dict[str, str]]]:
    centers_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    with CANDIDATES_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            centers_by_image[row["image_id"]].append(row)
    return {image_id: sorted(rows, key=lambda row: int(row["center_x"])) for image_id, rows in centers_by_image.items()}


def load_center_manifest() -> dict[str, dict[str, str]]:
    with CENTER_MANIFEST_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def line_width_for_image(width: int) -> int:
    return max(1, round(width / 500))


def approximate_half_band_width(centers: list[int], image_width: int) -> int:
    if len(centers) < 2:
        return max(3, round(image_width * 0.01))
    median_spacing = float(np.median(np.diff(centers)))
    return max(3, round(median_spacing * 0.20))


def draw_label(draw: ImageDraw.ImageDraw, image_id: str, center_count: int, accepted_count: int, weak_count: int, fallback_count: int, notes: str) -> None:
    label = f"{image_id}: {accepted_count}/{center_count} v4 centerlines ({weak_count} weak, {fallback_count} fallback); diagnostic guide only"
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


def colors_for_candidate(row: dict[str, str]) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    source = row.get("source", "band_region_strong_peak")
    status = row.get("status", "accepted")
    if source == "band_region_strong_peak":
        return STRONG_BAND_COLOR, STRONG_LINE_COLOR
    if source == "band_region_weak_peak":
        return WEAK_BAND_COLOR, WEAK_LINE_COLOR
    if status == "review_only":
        return LOW_FALLBACK_BAND_COLOR, LOW_FALLBACK_LINE_COLOR
    return HIGH_FALLBACK_BAND_COLOR, HIGH_FALLBACK_LINE_COLOR


def create_overlay(image_id: str, candidate_rows: list[dict[str, str]], manifest_row: dict[str, str]) -> Path:
    rgb = load_rgb(image_id)
    base = Image.fromarray(rgb).convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    centers = [int(row["center_x"]) for row in candidate_rows if row.get("status") != "review_only"]
    all_centers = [int(row["center_x"]) for row in candidate_rows]
    half_band_width = approximate_half_band_width(centers or all_centers, width)
    line_width = line_width_for_image(width)
    for row in candidate_rows:
        center_x = int(row["center_x"])
        left = max(0, center_x - half_band_width)
        right = min(width - 1, center_x + half_band_width)
        band_color, line_color = colors_for_candidate(row)
        draw.rectangle((left, 0, right, height - 1), fill=band_color)
        draw.line((center_x, 0, center_x, height - 1), fill=line_color, width=line_width)
    weak_count = sum(1 for row in candidate_rows if row.get("source") == "band_region_weak_peak")
    fallback_count = sum(1 for row in candidate_rows if row.get("source") == "conditional_fallback")
    accepted_count = sum(1 for row in candidate_rows if row.get("status") != "review_only")
    notes = f"quality={manifest_row.get('quality_flag', '')}; detection={manifest_row.get('detection_quality_flag', '')}; fallback={manifest_row.get('fallback_allowed', '')}"
    draw_label(draw, image_id, len(candidate_rows), accepted_count, weak_count, fallback_count, notes)
    output = Image.alpha_composite(base, overlay).convert("RGB")
    output_path = OUTPUT_DIR / f"{image_id}_lane_center_overlay_v4.png"
    output.save(output_path)
    return output_path


def main() -> None:
    centers_by_image = load_candidates()
    center_manifest = load_center_manifest()
    records = load_inventory()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []
    for record in records:
        candidate_rows = centers_by_image.get(record.image_id, [])
        source_manifest = center_manifest.get(record.image_id, {})
        overlay_path = create_overlay(record.image_id, candidate_rows, source_manifest)
        strong_count = sum(1 for row in candidate_rows if row.get("source") == "band_region_strong_peak")
        weak_count = sum(1 for row in candidate_rows if row.get("source") == "band_region_weak_peak")
        fallback_count = sum(1 for row in candidate_rows if row.get("source") == "conditional_fallback")
        accepted_count = sum(1 for row in candidate_rows if row.get("status") != "review_only")
        accepted_fallback_count = sum(1 for row in candidate_rows if row.get("source") == "conditional_fallback" and row.get("status") != "review_only")
        notes = "v4 band-region centerlines; red=strong band-region peak, orange=weak band-region peak, green=accepted fallback, grey=review-only fallback; not final lane boundaries"
        if source_manifest.get("quality_flag") or source_manifest.get("detection_quality_flag"):
            notes = (
                f"{notes}; image_quality={source_manifest.get('quality_flag', '')}; "
                f"detection_quality={source_manifest.get('detection_quality_flag', '')}; "
                f"fallback_reason={source_manifest.get('fallback_reason', '')}; "
                "manual cropping/cleaning may later improve quality but was not required"
            )
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "overlay_path": overlay_path.relative_to(PROJECT_ROOT).as_posix(),
                "center_count": str(len(candidate_rows)),
                "accepted_center_count": str(accepted_count),
                "direct_strong_count": str(strong_count),
                "weak_peak_count": str(weak_count),
                "conditional_fallback_count": str(fallback_count),
                "accepted_fallback_count": str(accepted_fallback_count),
                "notes": notes,
            }
        )
    with OVERLAY_MANIFEST_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"Wrote {len(manifest_rows)} v4 lane-center overlays to {OUTPUT_DIR}")
    print(f"Wrote overlay manifest to {OVERLAY_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
