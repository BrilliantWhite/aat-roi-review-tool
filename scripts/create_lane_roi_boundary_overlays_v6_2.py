#!/usr/bin/env python3
"""Create original-image overlays for v6_2 horizontal-ROI lane-boundary candidates."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import load_inventory, load_rgb  # noqa: E402

CANDIDATES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6_2" / "lane_boundary_candidates_v6_2.csv"
BOUNDARY_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6_2" / "lane_boundary_manifest_v6_2.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "lane_segmentation" / "overlays" / "roi_boundaries_v6_2"
OVERLAY_MANIFEST_PATH = OUTPUT_DIR / "lane_roi_boundary_overlay_manifest_v6_2.csv"

CENTER_LINE_COLOR = (220, 20, 60, 255)
WEAK_LINE_COLOR = (247, 127, 0, 255)
FALLBACK_LINE_COLOR = (42, 157, 143, 255)
REVIEW_LINE_COLOR = (108, 117, 125, 255)
BOUNDARY_FILL_COLOR = (255, 215, 0, 56)
BOUNDARY_EDGE_COLOR = (255, 193, 7, 180)
REVIEW_FILL_COLOR = (255, 215, 0, 26)
ROI_FILL_COLOR = (46, 204, 113, 40)
ROI_LINE_COLOR = (46, 204, 113, 220)
TEXT_COLOR = (255, 255, 255, 255)
TEXT_BACKGROUND = (0, 0, 0, 170)

MANIFEST_FIELDNAMES = [
    "image_id",
    "source_filename",
    "overlay_path",
    "boundary_count",
    "accepted_boundary_count",
    "median_estimated_width_px",
    "direct_strong_count",
    "weak_peak_count",
    "conditional_fallback_count",
    "accepted_fallback_count",
    "notes",
]


def load_candidates() -> dict[str, list[dict[str, str]]]:
    boundaries_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    with CANDIDATES_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            boundaries_by_image[row["image_id"]].append(row)
    return {image_id: sorted(rows, key=lambda row: int(row["center_x"])) for image_id, rows in boundaries_by_image.items()}


def load_boundary_manifest() -> dict[str, dict[str, str]]:
    with BOUNDARY_MANIFEST_PATH.open(newline="", encoding="utf-8") as csv_file:
        return {row["image_id"]: row for row in csv.DictReader(csv_file)}


def line_width_for_image(width: int) -> int:
    return max(1, round(width / 500))


def draw_label(draw: ImageDraw.ImageDraw, image_id: str, boundary_count: int, accepted_count: int, median_width: str, notes: str) -> None:
    label = f"{image_id}: {accepted_count}/{boundary_count} v6_2 adaptive lane boundaries; median width={median_width or 'n/a'} px"
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


def line_color_for_candidate(row: dict[str, str]) -> tuple[int, int, int, int]:
    if row.get("status") == "review_only":
        return REVIEW_LINE_COLOR
    if row.get("source") == "band_region_weak_peak":
        return WEAK_LINE_COLOR
    if row.get("source") == "conditional_fallback":
        return FALLBACK_LINE_COLOR
    return CENTER_LINE_COLOR


def create_overlay(image_id: str, candidate_rows: list[dict[str, str]], manifest_row: dict[str, str]) -> Path:
    rgb = load_rgb(image_id)
    base = Image.fromarray(rgb).convert("RGBA")
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    line_width = line_width_for_image(width)
    roi_y_start = int(manifest_row.get("y_start") or (candidate_rows[0].get("y_start") if candidate_rows else 0) or 0)
    roi_y_end = int(manifest_row.get("y_end") or (candidate_rows[0].get("y_end") if candidate_rows else height) or height)
    roi_y_start = max(0, min(height - 1, roi_y_start))
    roi_y_end = max(roi_y_start + 1, min(height, roi_y_end))
    draw.rectangle((0, roi_y_start, width - 1, roi_y_end - 1), fill=ROI_FILL_COLOR)
    draw.line((0, roi_y_start, width - 1, roi_y_start), fill=ROI_LINE_COLOR, width=line_width + 1)
    draw.line((0, roi_y_end - 1, width - 1, roi_y_end - 1), fill=ROI_LINE_COLOR, width=line_width + 1)
    for row in candidate_rows:
        center_x = int(row["center_x"])
        left = max(0, int(row["left_x"]))
        right = min(width - 1, int(row["right_x"]))
        y_start = max(0, min(height - 1, int(row.get("y_start") or manifest_row.get("y_start") or 0)))
        y_end = max(y_start + 1, min(height, int(row.get("y_end") or manifest_row.get("y_end") or height)))
        fill_color = REVIEW_FILL_COLOR if row.get("status") == "review_only" else BOUNDARY_FILL_COLOR
        draw.rectangle((left, y_start, right, y_end - 1), fill=fill_color)
        draw.line((left, y_start, left, y_end - 1), fill=BOUNDARY_EDGE_COLOR, width=line_width)
        draw.line((right, y_start, right, y_end - 1), fill=BOUNDARY_EDGE_COLOR, width=line_width)
        draw.line((center_x, y_start, center_x, y_end - 1), fill=line_color_for_candidate(row), width=line_width)
    accepted_count = sum(1 for row in candidate_rows if row.get("status") != "review_only")
    notes = f"roi={manifest_row.get('y_start', '')}-{manifest_row.get('y_end', '')}; roi_quality={manifest_row.get('roi_quality_flag', '')}; detection={manifest_row.get('detection_quality_flag', '')}"
    draw_label(draw, image_id, len(candidate_rows), accepted_count, manifest_row.get("median_estimated_width_px", ""), notes)
    output = Image.alpha_composite(base, overlay).convert("RGB")
    output_path = OUTPUT_DIR / f"{image_id}_lane_boundary_overlay_v6_2.png"
    output.save(output_path)
    return output_path


def main() -> None:
    boundaries_by_image = load_candidates()
    boundary_manifest = load_boundary_manifest()
    records = load_inventory()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []
    for record in records:
        candidate_rows = boundaries_by_image.get(record.image_id, [])
        source_manifest = boundary_manifest.get(record.image_id, {})
        overlay_path = create_overlay(record.image_id, candidate_rows, source_manifest)
        strong_count = sum(1 for row in candidate_rows if row.get("source") == "band_region_strong_peak")
        weak_count = sum(1 for row in candidate_rows if row.get("source") == "band_region_weak_peak")
        fallback_count = sum(1 for row in candidate_rows if row.get("source") == "conditional_fallback")
        accepted_count = sum(1 for row in candidate_rows if row.get("status") != "review_only")
        accepted_fallback_count = sum(1 for row in candidate_rows if row.get("source") == "conditional_fallback" and row.get("status") != "review_only")
        notes = "v6_2 ROI boundary overlay; green band=shared horizontal ROI, yellow span=estimated lane coverage clipped to ROI, yellow edges=estimated boundaries, red/orange/green/grey=center status"
        if source_manifest.get("quality_flag") or source_manifest.get("detection_quality_flag"):
            notes = (
                f"{notes}; image_quality={source_manifest.get('quality_flag', '')}; "
                f"detection_quality={source_manifest.get('detection_quality_flag', '')}; "
                f"fallback_reason={source_manifest.get('fallback_reason', '')}"
            )
        manifest_rows.append(
            {
                "image_id": record.image_id,
                "source_filename": record.source_filename,
                "overlay_path": overlay_path.relative_to(PROJECT_ROOT).as_posix(),
                "boundary_count": str(len(candidate_rows)),
                "accepted_boundary_count": str(accepted_count),
                "median_estimated_width_px": source_manifest.get("median_estimated_width_px", ""),
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
    print(f"Wrote {len(manifest_rows)} v6_2 lane-boundary overlays to {OUTPUT_DIR}")
    print(f"Wrote overlay manifest to {OVERLAY_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
