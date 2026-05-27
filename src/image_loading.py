"""Reproducible image loading utilities for raw AAT IEF gel images."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_inventory.csv"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}

ImageMode = Literal["rgb", "grayscale"]


@dataclass(frozen=True)
class ImageRecord:
    image_id: str
    source_filename: str
    relative_path: str
    file_ext: str
    width: int
    height: int
    channels: int
    gel_date_raw: str = ""
    gel_date_iso: str = ""
    notes: str = ""

    @property
    def path(self) -> Path:
        return PROJECT_ROOT / self.relative_path


def load_inventory(inventory_path: Path = INVENTORY_PATH) -> list[ImageRecord]:
    records: list[ImageRecord] = []
    with inventory_path.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            file_ext = row["file_ext"].lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported image extension for {row['image_id']}: {file_ext}")
            records.append(
                ImageRecord(
                    image_id=row["image_id"],
                    source_filename=row["source_filename"],
                    relative_path=row["relative_path"],
                    file_ext=file_ext,
                    width=int(row["width"]),
                    height=int(row["height"]),
                    channels=int(row["channels"]),
                    gel_date_raw=row.get("gel_date_raw", ""),
                    gel_date_iso=row.get("gel_date_iso", ""),
                    notes=row.get("notes", ""),
                )
            )
    return records


def get_image_record(image_id: str, inventory_path: Path = INVENTORY_PATH) -> ImageRecord:
    for record in load_inventory(inventory_path):
        if record.image_id == image_id:
            return record
    raise KeyError(f"Image ID not found in inventory: {image_id}")


def load_image(record_or_image_id: ImageRecord | str, mode: ImageMode = "rgb") -> np.ndarray:
    if mode not in {"rgb", "grayscale"}:
        raise ValueError(f"Unsupported image loading mode: {mode}")

    record = record_or_image_id if isinstance(record_or_image_id, ImageRecord) else get_image_record(record_or_image_id)
    pil_mode = "RGB" if mode == "rgb" else "L"

    with Image.open(record.path) as image:
        array = np.asarray(image.convert(pil_mode))

    if mode == "rgb" and array.ndim != 3:
        raise ValueError(f"Expected RGB image for {record.image_id}, got shape {array.shape}")
    if mode == "grayscale" and array.ndim != 2:
        raise ValueError(f"Expected grayscale image for {record.image_id}, got shape {array.shape}")
    return array.copy()


def load_rgb(record_or_image_id: ImageRecord | str) -> np.ndarray:
    return load_image(record_or_image_id, mode="rgb")


def load_grayscale(record_or_image_id: ImageRecord | str) -> np.ndarray:
    return load_image(record_or_image_id, mode="grayscale")


def convert_rgb_to_grayscale(rgb: np.ndarray) -> np.ndarray:
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"Expected RGB image with shape (height, width, 3), got {rgb.shape}")

    grayscale = np.dot(rgb[..., :3], np.array([0.299, 0.587, 0.114]))
    return np.rint(grayscale).clip(0, 255).astype(np.uint8)
