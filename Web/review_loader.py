from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from paths import (
    AUTO_CANDIDATES_PATH,
    AUTO_MANIFEST_PATH,
    AUTO_OVERLAY_MANIFEST_PATH,
    AUTO_ROI_PATH,
    INVENTORY_PATH,
    LANE_COUNT_REVIEW_PATH,
    SRC_ROOT,
)
from review_store import build_annotation_index, build_imported_annotation_index, build_review_indexes, ensure_review_exports

sys.path.insert(0, str(SRC_ROOT))
from image_loading import get_image_record, load_inventory  # type: ignore  # noqa: E402


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _read_csv_by_image(path: Path) -> dict[str, dict[str, str]]:
    return {row["image_id"]: row for row in _read_csv(path)}


def _read_candidates(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(path):
        grouped[row["image_id"]].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["candidate_index"]))
    return grouped


def _int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def _float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _build_imported_roi(rows: list[dict[str, str]]) -> dict[str, int]:
    y_start = min(_int(row.get("y_start")) for row in rows)
    y_end = max(_int(row.get("y_end")) for row in rows)
    return {"y_start": y_start, "y_end": y_end}


def _build_imported_boundaries(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    boundaries = []
    for row in rows:
        left_x = _int(row.get("left_x"))
        right_x = _int(row.get("right_x"))
        center_x = round((left_x + right_x) / 2)
        boundaries.append(
            {
                "candidate_index": _int(row.get("candidate_index")),
                "left_x": left_x,
                "right_x": right_x,
                "center_x": center_x,
                "estimated_width": right_x - left_x,
                "status": "imported_training_csv",
                "source": "imported_training_csv",
                "confidence": "imported",
                "notes": "",
                "auto_left_x": left_x,
                "auto_right_x": right_x,
                "auto_center_x": center_x,
                "auto_estimated_width": right_x - left_x,
                "auto_status": "imported_training_csv",
                "is_manual_added": False,
                "annotation": {"category": str(row.get("category", "")).strip()},
            }
        )
    boundaries.sort(key=lambda row: row["candidate_index"])
    return boundaries


def _matches_inventory_source(row: dict[str, str], inventory_records: dict[str, Any]) -> bool:
    image_id = str(row.get("image_id", "")).strip()
    source_filename = str(row.get("source_filename", "")).strip()
    record = inventory_records.get(image_id)
    return bool(record) and source_filename == record.source_filename


class ReviewRepository:
    def __init__(self) -> None:
        ensure_review_exports()
        self.refresh()

    def refresh(self) -> None:
        self.inventory_records = {record.image_id: record for record in load_inventory()}
        self.lane_count_review = _read_csv_by_image(LANE_COUNT_REVIEW_PATH)
        self.auto_roi = _read_csv_by_image(AUTO_ROI_PATH)
        self.auto_manifest = _read_csv_by_image(AUTO_MANIFEST_PATH)
        self.auto_overlays = _read_csv_by_image(AUTO_OVERLAY_MANIFEST_PATH)
        self.auto_candidates = _read_candidates(AUTO_CANDIDATES_PATH)
        self.review_roi, self.review_candidates, self.review_manifest = build_review_indexes()
        self.annotations = build_annotation_index()
        self.imported_annotations = build_imported_annotation_index()
        self.review_roi = {
            image_id: row
            for image_id, row in self.review_roi.items()
            if _matches_inventory_source(row, self.inventory_records)
        }
        self.review_manifest = {
            image_id: row
            for image_id, row in self.review_manifest.items()
            if _matches_inventory_source(row, self.inventory_records)
        }
        self.review_candidates = {
            image_id: [row for row in rows if _matches_inventory_source(row, self.inventory_records)]
            for image_id, rows in self.review_candidates.items()
            if image_id in self.inventory_records
        }
        self.annotations = {
            image_id: {
                candidate_index: row
                for candidate_index, row in rows.items()
                if _matches_inventory_source(row, self.inventory_records)
            }
            for image_id, rows in self.annotations.items()
            if image_id in self.inventory_records
        }

    def list_images(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for image_id, record in self.inventory_records.items():
            manifest = self.auto_manifest.get(image_id, {})
            review_manifest = self.review_manifest.get(image_id)
            lane_review = self.lane_count_review.get(image_id, {})
            imported_rows = self.imported_annotations.get(image_id, [])
            items.append(
                {
                    "image_id": image_id,
                    "source_filename": record.source_filename,
                    "width": record.width,
                    "height": record.height,
                    "quality_flag": manifest.get("quality_flag", ""),
                    "detection_quality_flag": manifest.get("detection_quality_flag", ""),
                    "manual_review_required": str(manifest.get("manual_review_required", "false")).lower() == "true",
                    "accepted_boundary_count": len(imported_rows) if imported_rows else _int(manifest.get("accepted_boundary_count", 0)),
                    "review_status": "imported" if imported_rows else (review_manifest.get("review_status") if review_manifest else lane_review.get("review_status", "unreviewed")),
                    "has_review": bool(review_manifest),
                    "has_imported_session": bool(imported_rows),
                    "notes": review_manifest.get("notes") if review_manifest else lane_review.get("notes", ""),
                }
            )
        items.sort(key=lambda row: row["image_id"])
        return items

    def get_image_payload(self, image_id: str) -> dict[str, Any]:
        if image_id not in self.inventory_records:
            raise KeyError(f"Unknown image_id: {image_id}")

        record = self.inventory_records[image_id]
        auto_roi = self.auto_roi.get(image_id, {})
        auto_manifest = self.auto_manifest.get(image_id, {})
        overlay_manifest = self.auto_overlays.get(image_id, {})
        auto_candidates = self.auto_candidates.get(image_id, [])
        review_roi = self.review_roi.get(image_id)
        review_candidates = self.review_candidates.get(image_id)
        review_manifest = self.review_manifest.get(image_id)
        lane_review = self.lane_count_review.get(image_id, {})
        imported_rows = self.imported_annotations.get(image_id, [])
        annotation_rows = self.annotations.get(image_id, {})

        if imported_rows:
            imported_roi = _build_imported_roi(imported_rows)
            y_start = imported_roi["y_start"]
            y_end = imported_roi["y_end"]
            roi_source = "imported_training_csv"
            boundary_rows = imported_rows
            boundary_source = "imported_training_csv"
        elif review_roi:
            y_start = _int(review_roi["y_start"])
            y_end = _int(review_roi["y_end"])
            roi_source = "reviewed"
            boundary_rows = review_candidates if review_candidates else auto_candidates
            boundary_source = "reviewed" if review_candidates else "automatic"
        else:
            y_start = _int(auto_roi.get("y_start"))
            y_end = _int(auto_roi.get("y_end"))
            roi_source = "automatic"
            boundary_rows = auto_candidates
            boundary_source = "automatic"

        if imported_rows:
            boundaries = _build_imported_boundaries(imported_rows)
        else:
            boundaries = []
            for row in boundary_rows:
                left_x = _int(row.get("left_x"))
                right_x = _int(row.get("right_x"))
                center_x = _int(row.get("center_x"), round((left_x + right_x) / 2))
                candidate_index = _int(row.get("candidate_index"))
                annotation_row = annotation_rows.get(candidate_index, {})
                boundaries.append(
                    {
                        "candidate_index": candidate_index,
                        "left_x": left_x,
                        "right_x": right_x,
                        "center_x": center_x,
                        "estimated_width": _int(row.get("estimated_width"), right_x - left_x),
                        "status": row.get("status", "accepted"),
                        "source": row.get("source", "manual_review" if review_candidates else row.get("source", "")),
                        "confidence": row.get("confidence", "manual" if review_candidates else row.get("confidence", "")),
                        "notes": row.get("notes", ""),
                        "auto_left_x": _int(row.get("auto_left_x"), left_x),
                        "auto_right_x": _int(row.get("auto_right_x"), right_x),
                        "auto_center_x": _int(row.get("auto_center_x"), center_x),
                        "auto_estimated_width": _int(row.get("auto_estimated_width"), right_x - left_x),
                        "auto_status": row.get("auto_status", row.get("status", "accepted")),
                        "is_manual_added": str(row.get("is_manual_added", "false")).lower() == "true",
                        "annotation": {
                            "category": annotation_row.get("category", ""),
                        },
                    }
                )

        return {
            "image": {
                "image_id": image_id,
                "source_filename": record.source_filename,
                "width": record.width,
                "height": record.height,
                "image_url": f"/api/images/{image_id}/raw",
                "relative_path": record.relative_path,
            },
            "roi": {
                "y_start": y_start,
                "y_end": y_end,
                "source": roi_source,
                "auto_y_start": _int(auto_roi.get("y_start")),
                "auto_y_end": _int(auto_roi.get("y_end")),
                "roi_confidence": auto_roi.get("roi_confidence", ""),
                "roi_reason": auto_roi.get("roi_reason", ""),
                "roi_quality_flag": auto_roi.get("roi_quality_flag", ""),
                "method": auto_roi.get("method", ""),
            },
            "boundaries": boundaries,
            "boundary_source": boundary_source,
            "manifest": {
                "quality_flag": auto_manifest.get("quality_flag", ""),
                "issues": auto_manifest.get("issues", ""),
                "detection_quality_flag": auto_manifest.get("detection_quality_flag", ""),
                "manual_review_required": str(auto_manifest.get("manual_review_required", "false")).lower() == "true",
                "accepted_boundary_count": _int(auto_manifest.get("accepted_boundary_count", 0)),
                "detected_boundary_count": _int(auto_manifest.get("detected_boundary_count", 0)),
                "expected_lane_count_override": auto_manifest.get("expected_lane_count_override", ""),
                "fallback_reason": auto_manifest.get("fallback_reason", ""),
                "roi_profile_threshold": _float(auto_roi.get("roi_profile_threshold", 0.0)),
                "roi_profile_peak_value": _float(auto_roi.get("roi_profile_peak_value", 0.0)),
            },
            "review": {
                "review_status": "imported" if imported_rows else (review_manifest.get("review_status") if review_manifest else lane_review.get("review_status", "unreviewed")),
                "notes": review_manifest.get("notes") if review_manifest else lane_review.get("notes", ""),
                "has_review": bool(review_manifest),
                "has_imported_session": bool(imported_rows),
            },
            "overlay": {
                "overlay_path": overlay_manifest.get("overlay_path", ""),
                "notes": overlay_manifest.get("notes", ""),
            },
            "annotation": {
                "enabled": bool(imported_rows) or bool(annotation_rows),
                "has_annotation_file": bool(imported_rows) or bool(annotation_rows),
                "annotated_lane_count": len(boundaries),
            },
        }

    def get_image_path(self, image_id: str) -> Path:
        return get_image_record(image_id).path
