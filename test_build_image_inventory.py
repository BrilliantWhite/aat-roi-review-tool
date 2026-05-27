from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import build_image_inventory as bii  # noqa: E402


class BuildImageInventoryTests(unittest.TestCase):
    def _write_image(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 3), color=(255, 255, 255)).save(path)

    def _write_existing_inventory(self, output_path: Path, rows: list[dict[str, str]] | None = None) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=bii.FIELDNAMES)
            writer.writeheader()
            writer.writerows(
                rows or [
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "02.01.2025.png",
                        "relative_path": "dataset/Originial/02.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "gel_date_raw": "02.01.2025",
                        "gel_date_iso": "2025-01-02",
                        "notes": "",
                    },
                    {
                        "image_id": "IMG_0002",
                        "source_filename": "03.01.2025.png",
                        "relative_path": "dataset/Originial/03.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "gel_date_raw": "03.01.2025",
                        "gel_date_iso": "2025-01-03",
                        "notes": "",
                    },
                ]
            )

    def _write_quality_report(self, quality_path: Path, rows: list[dict[str, str]]) -> None:
        quality_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "image_id",
            "source_filename",
            "relative_path",
            "file_ext",
            "width",
            "height",
            "channels",
            "readable",
            "quality_flag",
            "blur_score_laplacian",
            "contrast_std",
            "dynamic_range_p01_p99",
            "estimated_tilt_deg",
            "background_unevenness",
            "artifact_border_score",
            "issues",
            "segmentation_implication",
        ]
        with quality_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_preserves_existing_ids_and_appends_new_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            raw_dir = project_root / "dataset" / "Originial"
            output_path = project_root / "dataset" / "metadata" / "image_inventory.csv"
            quality_path = project_root / "dataset" / "metadata" / "image_quality_report.csv"

            self._write_image(raw_dir / "02.01.2025.png")
            self._write_image(raw_dir / "03.01.2025.png")
            self._write_image(raw_dir / "01.01.2025.png")
            self._write_existing_inventory(output_path)

            with patch.object(bii, "PROJECT_ROOT", project_root), patch.object(bii, "RAW_DIR", raw_dir), patch.object(bii, "OUTPUT_PATH", output_path), patch.object(bii, "QUALITY_REPORT_PATH", quality_path, create=True):
                rows = bii.build_inventory()

        ids_by_name = {row["source_filename"]: row["image_id"] for row in rows}
        self.assertEqual(ids_by_name["02.01.2025.png"], "IMG_0001")
        self.assertEqual(ids_by_name["03.01.2025.png"], "IMG_0002")
        self.assertEqual(ids_by_name["01.01.2025.png"], "IMG_0003")
    def test_prefers_quality_report_ids_when_inventory_was_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            raw_dir = project_root / "dataset" / "Originial"
            output_path = project_root / "dataset" / "metadata" / "image_inventory.csv"
            quality_path = project_root / "dataset" / "metadata" / "image_quality_report.csv"

            self._write_image(raw_dir / "02.01.2025.png")
            self._write_image(raw_dir / "03.01.2025.png")
            self._write_image(raw_dir / "01.01.2025.png")
            self._write_existing_inventory(
                output_path,
                rows=[
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "01.01.2025.png",
                        "relative_path": "dataset/Originial/01.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "gel_date_raw": "01.01.2025",
                        "gel_date_iso": "2025-01-01",
                        "notes": "",
                    },
                    {
                        "image_id": "IMG_0002",
                        "source_filename": "02.01.2025.png",
                        "relative_path": "dataset/Originial/02.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "gel_date_raw": "02.01.2025",
                        "gel_date_iso": "2025-01-02",
                        "notes": "",
                    },
                ],
            )
            self._write_quality_report(
                quality_path,
                rows=[
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "02.01.2025.png",
                        "relative_path": "dataset/Originial/02.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "readable": "yes",
                        "quality_flag": "ok",
                        "blur_score_laplacian": "1",
                        "contrast_std": "1",
                        "dynamic_range_p01_p99": "1",
                        "estimated_tilt_deg": "0",
                        "background_unevenness": "1",
                        "artifact_border_score": "1",
                        "issues": "none",
                        "segmentation_implication": "none",
                    },
                    {
                        "image_id": "IMG_0002",
                        "source_filename": "03.01.2025.png",
                        "relative_path": "dataset/Originial/03.01.2025.png",
                        "file_ext": ".png",
                        "width": "4",
                        "height": "3",
                        "channels": "3",
                        "readable": "yes",
                        "quality_flag": "ok",
                        "blur_score_laplacian": "1",
                        "contrast_std": "1",
                        "dynamic_range_p01_p99": "1",
                        "estimated_tilt_deg": "0",
                        "background_unevenness": "1",
                        "artifact_border_score": "1",
                        "issues": "none",
                        "segmentation_implication": "none",
                    },
                ],
            )

            with patch.object(bii, "PROJECT_ROOT", project_root), patch.object(bii, "RAW_DIR", raw_dir), patch.object(bii, "OUTPUT_PATH", output_path), patch.object(bii, "QUALITY_REPORT_PATH", quality_path, create=True):
                rows = bii.build_inventory()

        ids_by_name = {row["source_filename"]: row["image_id"] for row in rows}
        self.assertEqual(ids_by_name["02.01.2025.png"], "IMG_0001")
        self.assertEqual(ids_by_name["03.01.2025.png"], "IMG_0002")
        self.assertEqual(ids_by_name["01.01.2025.png"], "IMG_0003")


if __name__ == "__main__":
    unittest.main()
