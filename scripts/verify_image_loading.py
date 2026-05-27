#!/usr/bin/env python3
"""Verify reproducible loading for every image in the inventory."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_loading import load_grayscale, load_inventory, load_rgb  # noqa: E402


def main() -> None:
    records = load_inventory()
    failures: list[str] = []

    for record in records:
        try:
            rgb = load_rgb(record)
            grayscale = load_grayscale(record)
        except Exception as exc:  # pragma: no cover - verification script reports all failures
            failures.append(f"{record.image_id} {record.source_filename}: {exc}")
            continue

        expected_rgb_shape = (record.height, record.width, 3)
        expected_grayscale_shape = (record.height, record.width)
        if rgb.shape != expected_rgb_shape:
            failures.append(f"{record.image_id}: RGB shape {rgb.shape} != {expected_rgb_shape}")
        if grayscale.shape != expected_grayscale_shape:
            failures.append(f"{record.image_id}: grayscale shape {grayscale.shape} != {expected_grayscale_shape}")
        if record.width <= 0 or record.height <= 0:
            failures.append(f"{record.image_id}: non-positive dimensions {record.width}x{record.height}")

    if failures:
        for failure in failures:
            print(failure)
        raise SystemExit(1)

    print(f"Loaded {len(records)} inventory images successfully as RGB and grayscale arrays.")


if __name__ == "__main__":
    main()
