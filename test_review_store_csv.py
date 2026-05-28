from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent / "Web"))

import review_store  # noqa: E402


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _csv_text(fieldnames: list[str], rows: list[dict[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class ReviewStoreCsvTests(unittest.TestCase):
    def _patch_review_paths(self, stack: ExitStack, export_root: Path) -> None:
        stack.enter_context(patch.object(review_store, "REVIEW_EXPORT_ROOT", export_root))
        stack.enter_context(patch.object(review_store, "REVIEW_ROI_PATH", export_root / "horizontal_roi_review.csv"))
        stack.enter_context(patch.object(review_store, "REVIEW_CANDIDATES_PATH", export_root / "lane_boundary_candidates_review.csv"))
        stack.enter_context(patch.object(review_store, "REVIEW_MANIFEST_PATH", export_root / "lane_boundary_manifest_review.csv"))
        stack.enter_context(patch.object(review_store, "REVIEW_ANNOTATIONS_PATH", export_root / "lane_annotations_review.csv"))
        stack.enter_context(patch.object(review_store, "REVIEW_ANNOTATIONS_JSONL_PATH", export_root / "lane_annotations_review.jsonl"))
        stack.enter_context(patch.object(review_store, "REVIEW_RESTORE_EXPORT_PATH", export_root / "review_restore_export.csv"))
        stack.enter_context(patch.object(review_store, "TRAINING_LANES_EXPORT_PATH", export_root / "training_lanes_export.csv"))
        stack.enter_context(patch.object(review_store, "CATEGORY_SUGGESTIONS_PATH", export_root / "category_suggestions.txt"))

    def test_import_review_restore_csv_writes_reviewed_geometry_and_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, ExitStack() as stack:
            export_root = Path(tmp_dir) / "review_exports"
            self._patch_review_paths(stack, export_root)

            csv_text = _csv_text(
                review_store.RESTORE_EXPORT_FIELDNAMES,
                [
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "gel.png",
                        "candidate_index": 1,
                        "width": 100,
                        "height": 80,
                        "roi_y_start": 10,
                        "roi_y_end": 60,
                        "left_x": 5,
                        "right_x": 25,
                        "center_x": 15,
                        "estimated_width": 20,
                        "status": "accepted",
                        "category": "M",
                    },
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "gel.png",
                        "candidate_index": 2,
                        "width": 100,
                        "height": 80,
                        "roi_y_start": 10,
                        "roi_y_end": 60,
                        "left_x": 30,
                        "right_x": 50,
                        "center_x": 40,
                        "estimated_width": 20,
                        "status": "accepted",
                        "category": "",
                    },
                ],
            )

            summary = review_store.import_review_restore_csv(
                csv_text,
                {"IMG_0001": (100, 80)},
                {"IMG_0001": "gel.png"},
            )

            self.assertEqual(summary["restored_image_count"], 1)
            self.assertEqual(summary["restored_lane_count"], 2)
            roi_rows = _read_rows(export_root / "horizontal_roi_review.csv")
            candidate_rows = _read_rows(export_root / "lane_boundary_candidates_review.csv")
            manifest_rows = _read_rows(export_root / "lane_boundary_manifest_review.csv")
            annotation_rows = _read_rows(export_root / "lane_annotations_review.csv")

        self.assertEqual(roi_rows[0]["y_start"], "10")
        self.assertEqual(roi_rows[0]["y_end"], "60")
        self.assertEqual(len(candidate_rows), 2)
        self.assertEqual(manifest_rows[0]["reviewed_boundary_count"], "2")
        self.assertEqual(annotation_rows[0]["category"], "M")

    def test_training_export_csv_can_be_imported_as_temporary_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, ExitStack() as stack:
            export_root = Path(tmp_dir) / "review_exports"
            self._patch_review_paths(stack, export_root)
            review_store.clear_imported_annotation_rows()

            csv_text = _csv_text(
                review_store.TRAINING_EXPORT_FIELDNAMES,
                [
                    {
                        "image_id": "IMG_0001",
                        "source_filename": "gel.png",
                        "candidate_index": 1,
                        "roi_y_start": 10,
                        "roi_y_end": 60,
                        "left_x": 5,
                        "right_x": 25,
                        "label": "M",
                    }
                ],
            )

            summary = review_store.import_training_annotation_csv(
                csv_text,
                {"IMG_0001": (100, 80)},
                {"IMG_0001": "gel.png"},
            )
            rows = review_store.load_imported_annotation_rows()
            review_store.clear_imported_annotation_rows()

        self.assertEqual(summary["imported_lane_count"], 1)
        self.assertEqual(rows[0]["category"], "M")
        self.assertEqual(rows[0]["y_start"], "10")
        self.assertEqual(rows[0]["y_end"], "60")

    def test_restore_export_skips_reviewed_rows_outside_current_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir, ExitStack() as stack:
            export_root = Path(tmp_dir) / "review_exports"
            self._patch_review_paths(stack, export_root)
            review_store._write_csv(
                review_store.REVIEW_ROI_PATH,
                review_store.ROI_REVIEW_FIELDNAMES,
                [
                    {"image_id": "IMG_OLD", "source_filename": "old.png", "width": 100, "height": 80, "y_start": 10, "y_end": 60},
                    {"image_id": "IMG_NEW", "source_filename": "new.png", "width": 100, "height": 80, "y_start": 12, "y_end": 62},
                ],
            )
            review_store._write_csv(
                review_store.REVIEW_CANDIDATES_PATH,
                review_store.CANDIDATE_REVIEW_FIELDNAMES,
                [
                    {
                        "image_id": "IMG_OLD",
                        "source_filename": "old.png",
                        "width": 100,
                        "height": 80,
                        "candidate_index": 1,
                        "left_x": 5,
                        "right_x": 25,
                        "center_x": 15,
                        "estimated_width": 20,
                    },
                    {
                        "image_id": "IMG_NEW",
                        "source_filename": "new.png",
                        "width": 100,
                        "height": 80,
                        "candidate_index": 1,
                        "left_x": 30,
                        "right_x": 50,
                        "center_x": 40,
                        "estimated_width": 20,
                    },
                ],
            )

            summary = review_store.export_review_restore_csv(valid_image_ids={"IMG_NEW"})
            export_rows = _read_rows(export_root / "review_restore_export.csv")

        self.assertEqual(summary["image_count"], 1)
        self.assertEqual(summary["lane_count"], 1)
        self.assertEqual(export_rows[0]["image_id"], "IMG_NEW")


if __name__ == "__main__":
    unittest.main()
