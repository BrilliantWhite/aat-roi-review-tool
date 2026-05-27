#!/usr/bin/env python3
"""Build the raw gel image inventory for the AAT project."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment check
    raise SystemExit("Pillow is required to read image dimensions. Install Pillow and rerun this script.") from exc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "dataset" / "Originial"
OUTPUT_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_inventory.csv"
QUALITY_REPORT_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_quality_report.csv"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
FIELDNAMES = [
    "image_id",
    "source_filename",
    "relative_path",
    "file_ext",
    "width",
    "height",
    "channels",
    "gel_date_raw",
    "gel_date_iso",
    "notes",
]


def parse_date_from_stem(stem: str) -> tuple[str, str, str]:
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})", stem)
    if not match:
        return "", "", "date_not_parsed"

    day_raw, month_raw, year_raw = match.groups()
    gel_date_raw = f"{day_raw}.{month_raw}.{year_raw}"
    year = int(year_raw)
    if len(year_raw) == 2:
        year += 2000

    try:
        parsed = date(year, int(month_raw), int(day_raw))
    except ValueError:
        return gel_date_raw, "", "invalid_date_in_filename"

    return gel_date_raw, parsed.isoformat(), ""


def channel_count(mode: str) -> int:
    if mode in {"1", "L", "P", "I", "F"}:
        return 1
    return len(mode)


def load_existing_inventory() -> tuple[dict[str, dict[str, str]], int]:
    if not OUTPUT_PATH.exists():
        return {}, 0

    existing_rows: dict[str, dict[str, str]] = {}
    max_index = 0
    with OUTPUT_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            existing_rows[row["source_filename"]] = row
            match = re.match(r"^IMG_(\d+)$", row["image_id"])
            if match:
                max_index = max(max_index, int(match.group(1)))
    return existing_rows, max_index



def load_quality_report_ids() -> tuple[dict[str, str], int]:
    if not QUALITY_REPORT_PATH.exists():
        return {}, 0

    ids_by_filename: dict[str, str] = {}
    max_index = 0
    with QUALITY_REPORT_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            image_id = row["image_id"]
            ids_by_filename[row["source_filename"]] = image_id
            match = re.match(r"^IMG_(\d+)$", image_id)
            if match:
                max_index = max(max_index, int(match.group(1)))
    return ids_by_filename, max_index



def build_inventory() -> list[dict[str, str | int]]:
    if not RAW_DIR.exists():
        raise SystemExit(f"Raw dataset directory not found: {RAW_DIR}")

    image_paths = sorted(
        path for path in RAW_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    existing_rows, existing_max_index = load_existing_inventory()
    quality_ids_by_filename, quality_max_index = load_quality_report_ids()

    rows: list[dict[str, str | int]] = []
    next_index = max(existing_max_index, quality_max_index) + 1
    used_ids: set[str] = set()
    for path in image_paths:
        with Image.open(path) as image:
            width, height = image.size
            channels = channel_count(image.mode)

        gel_date_raw, gel_date_iso, notes = parse_date_from_stem(path.stem)
        if path.name in quality_ids_by_filename:
            image_id = quality_ids_by_filename[path.name]
        else:
            existing_row = existing_rows.get(path.name)
            existing_id = existing_row["image_id"] if existing_row else ""
            existing_match = re.match(r"^IMG_(\d+)$", existing_id)
            existing_index = int(existing_match.group(1)) if existing_match else 0
            can_reuse_existing_id = (
                existing_row is not None
                and (quality_max_index == 0 or existing_index > quality_max_index)
                and existing_id not in used_ids
            )
            if can_reuse_existing_id:
                image_id = existing_id
            else:
                while f"IMG_{next_index:04d}" in used_ids:
                    next_index += 1
                image_id = f"IMG_{next_index:04d}"
                next_index += 1

        used_ids.add(image_id)
        rows.append({
            "image_id": image_id,
            "source_filename": path.name,
            "relative_path": path.relative_to(PROJECT_ROOT).as_posix(),
            "file_ext": path.suffix.lower(),
            "width": width,
            "height": height,
            "channels": channels,
            "gel_date_raw": gel_date_raw,
            "gel_date_iso": gel_date_iso,
            "notes": notes,
        })

    return rows


def write_inventory(rows: list[dict[str, str | int]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build_inventory()
    write_inventory(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
