from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent / "Web"))

import dataset_refresh  # noqa: E402


class DatasetRefreshTests(unittest.TestCase):
    def test_run_dataset_refresh_executes_pipeline_scripts_in_order(self) -> None:
        calls: list[list[str]] = []

        def fake_runner(command: list[str], **kwargs: object) -> object:
            calls.append(command)

            class Result:
                stdout = "ok"
                stderr = ""

            return Result()

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            (project_root / "scripts").mkdir()
            for script_name in dataset_refresh.PIPELINE_SCRIPT_NAMES:
                (project_root / "scripts" / script_name).write_text("", encoding="utf-8")
            (project_root / "dataset" / "metadata").mkdir(parents=True)
            (project_root / "dataset" / "metadata" / "image_inventory.csv").write_text(
                "image_id,source_filename,relative_path,file_ext,width,height,channels,gel_date_raw,gel_date_iso,notes\n",
                encoding="utf-8",
            )
            quality_path = project_root / "dataset" / "metadata" / "image_quality_report.csv"

            with (
                patch.object(dataset_refresh, "PROJECT_ROOT", project_root),
                patch.object(dataset_refresh, "INVENTORY_PATH", project_root / "dataset" / "metadata" / "image_inventory.csv"),
                patch.object(dataset_refresh, "QUALITY_REPORT_PATH", quality_path),
            ):
                summary = dataset_refresh.run_dataset_refresh(runner=fake_runner)

        self.assertEqual(
            [Path(call[1]).name for call in calls],
            dataset_refresh.PIPELINE_SCRIPT_NAMES,
        )
        self.assertEqual(summary["script_count"], len(dataset_refresh.PIPELINE_SCRIPT_NAMES))

    def test_ensure_quality_report_adds_conservative_rows_for_new_inventory_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            metadata_dir = project_root / "dataset" / "metadata"
            metadata_dir.mkdir(parents=True)
            inventory_path = metadata_dir / "image_inventory.csv"
            quality_path = metadata_dir / "image_quality_report.csv"

            inventory_path.write_text(
                "\n".join(
                    [
                        "image_id,source_filename,relative_path,file_ext,width,height,channels,gel_date_raw,gel_date_iso,notes",
                        "IMG_0001,old.png,dataset/Originial/old.png,.png,10,8,3,,,",
                        "IMG_0002,new.png,dataset/Originial/new.png,.png,20,12,3,,,",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            quality_path.write_text(
                "\n".join(
                    [
                        ",".join(dataset_refresh.QUALITY_FIELDNAMES),
                        "IMG_0001,old.png,dataset/Originial/old.png,.png,10,8,3,yes,ok,1,1,1,0,1,1,none,none",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(dataset_refresh, "INVENTORY_PATH", inventory_path), patch.object(dataset_refresh, "QUALITY_REPORT_PATH", quality_path):
                added = dataset_refresh.ensure_quality_report_matches_inventory()

            with quality_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(added, 1)
        self.assertEqual(rows[1]["image_id"], "IMG_0002")
        self.assertEqual(rows[1]["quality_flag"], "review")
        self.assertIn("new_image_pending_quality_review", rows[1]["issues"])


if __name__ == "__main__":
    unittest.main()
