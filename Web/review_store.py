from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from paths import (
    CATEGORY_SUGGESTIONS_PATH,
    REVIEW_ANNOTATIONS_JSONL_PATH,
    REVIEW_ANNOTATIONS_PATH,
    REVIEW_CANDIDATES_PATH,
    REVIEW_EXPORT_ROOT,
    REVIEW_MANIFEST_PATH,
    REVIEW_RESTORE_EXPORT_PATH,
    REVIEW_ROI_PATH,
    TRAINING_LANES_EXPORT_PATH,
)

ROI_REVIEW_FIELDNAMES = [
    "image_id",
    "source_filename",
    "width",
    "height",
    "y_start",
    "y_end",
    "roi_height",
    "auto_y_start",
    "auto_y_end",
    "roi_confidence",
    "roi_reason",
    "roi_quality_flag",
    "review_status",
    "notes",
    "updated_at",
]

CANDIDATE_REVIEW_FIELDNAMES = [
    "image_id",
    "source_filename",
    "width",
    "height",
    "candidate_index",
    "left_x",
    "right_x",
    "center_x",
    "estimated_width",
    "y_start",
    "y_end",
    "auto_left_x",
    "auto_right_x",
    "auto_center_x",
    "auto_estimated_width",
    "auto_status",
    "status",
    "source",
    "confidence",
    "is_manual_added",
    "notes",
    "updated_at",
]

MANIFEST_REVIEW_FIELDNAMES = [
    "image_id",
    "source_filename",
    "width",
    "height",
    "y_start",
    "y_end",
    "roi_height",
    "reviewed_boundary_count",
    "accepted_boundary_count",
    "median_center_spacing_px",
    "median_estimated_width_px",
    "min_estimated_width_px",
    "max_estimated_width_px",
    "quality_flag",
    "detection_quality_flag",
    "review_status",
    "notes",
    "updated_at",
]

ANNOTATION_FIELDNAMES = [
    "image_id",
    "source_filename",
    "candidate_index",
    "left_x",
    "right_x",
    "y_start",
    "y_end",
    "category",
    "updated_at",
]

IMPORTED_ANNOTATION_FIELDNAMES = [
    "image_id",
    "source_filename",
    "candidate_index",
    "left_x",
    "right_x",
    "y_start",
    "y_end",
    "category",
    "updated_at",
]

ACCEPTED_STATUSES = {"accepted", "accepted_for_review", "manual", "manual_review"}
TRAINING_IMPORT_REQUIRED_COLUMNS = {
    "image_id",
    "source_filename",
    "candidate_index",
    "left_x",
    "right_x",
    "y_start",
    "y_end",
    "category",
}

TRAINING_IMPORT_ALTERNATE_COLUMNS = {
    "image_id",
    "source_filename",
    "candidate_index",
    "left_x",
    "right_x",
    "roi_y_start",
    "roi_y_end",
    "label",
}

_IMPORTED_ANNOTATION_ROWS: list[dict[str, str]] = []

RESTORE_EXPORT_FIELDNAMES = [
    "image_id",
    "source_filename",
    "candidate_index",
    "width",
    "height",
    "roi_y_start",
    "roi_y_end",
    "left_x",
    "right_x",
    "center_x",
    "estimated_width",
    "status",
    "source",
    "confidence",
    "is_manual_added",
    "notes",
    "category",
    "updated_at",
]

TRAINING_EXPORT_FIELDNAMES = [
    "image_id",
    "source_filename",
    "candidate_index",
    "roi_y_start",
    "roi_y_end",
    "left_x",
    "right_x",
    "x1",
    "y1",
    "x2",
    "y2",
    "x3",
    "y3",
    "x4",
    "y4",
    "label",
    "updated_at",
]


def _raise_import_error(message: str) -> None:
    raise ValueError(f"CSV validation failed: {message}")


def _parse_int(value: Any, field_name: str, row_number: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError) as exc:
        _raise_import_error(f"row {row_number}: field {field_name} must be numeric")
        raise exc


def _candidate_index_or_none(row: dict[str, Any]) -> int | None:
    try:
        return int(float(row.get("candidate_index") or 0))
    except (TypeError, ValueError):
        return None


def _candidate_sort_key(row: dict[str, Any]) -> tuple[str, int]:
    return str(row.get("image_id", "")), _candidate_index_or_none(row) or 0


def _is_unknown_label(value: str) -> bool:
    return value.strip().lower() == "unknown"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_csv(path: Path, fieldnames: list[str]) -> None:
    REVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    _ensure_csv(path, fieldnames)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_export_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> Path:
    try:
        _write_csv(path, fieldnames, rows)
        return path
    except PermissionError:
        fallback_path = path.with_name(f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}")
        _write_csv(fallback_path, fieldnames, rows)
        return fallback_path


def _read_csv_by_image(path: Path, valid_image_sources: dict[str, str] | None = None) -> dict[str, dict[str, str]]:
    return {
        row["image_id"]: row
        for row in _read_csv(path)
        if _row_matches_current_source(row, valid_image_sources)
    }


def _row_matches_current_source(row: dict[str, Any], valid_image_sources: dict[str, str] | None = None) -> bool:
    if valid_image_sources is None:
        return True
    image_id = str(row.get("image_id", "")).strip()
    source_filename = str(row.get("source_filename", "")).strip()
    return bool(image_id) and valid_image_sources.get(image_id) == source_filename


def export_review_restore_csv(valid_image_sources: dict[str, str] | None = None) -> dict[str, Any]:
    ensure_review_exports()
    roi_by_image = _read_csv_by_image(REVIEW_ROI_PATH, valid_image_sources)
    annotation_index = build_annotation_index()
    candidate_rows = _read_csv(REVIEW_CANDIDATES_PATH)
    export_rows: list[dict[str, Any]] = []

    for row in candidate_rows:
        image_id = row["image_id"]
        if not _row_matches_current_source(row, valid_image_sources):
            continue
        roi_row = roi_by_image.get(image_id)
        if not roi_row:
            continue
        candidate_index = int(row.get("candidate_index") or 0)
        annotation_row = annotation_index.get(image_id, {}).get(candidate_index, {})
        left_x = int(float(row["left_x"]))
        right_x = int(float(row["right_x"]))
        center_x = int(float(row.get("center_x") or round((left_x + right_x) / 2)))
        export_rows.append(
            {
                "image_id": image_id,
                "source_filename": row["source_filename"],
                "candidate_index": candidate_index,
                "width": int(float(row["width"])),
                "height": int(float(row["height"])),
                "roi_y_start": int(float(roi_row["y_start"])),
                "roi_y_end": int(float(roi_row["y_end"])),
                "left_x": left_x,
                "right_x": right_x,
                "center_x": center_x,
                "estimated_width": int(float(row.get("estimated_width") or (right_x - left_x))),
                "status": row.get("status", ""),
                "source": row.get("source", ""),
                "confidence": row.get("confidence", ""),
                "is_manual_added": row.get("is_manual_added", "false"),
                "notes": row.get("notes", ""),
                "category": annotation_row.get("category", ""),
                "updated_at": row.get("updated_at", roi_row.get("updated_at", "")),
            }
        )

    export_rows.sort(key=lambda row: (row["image_id"], int(row["candidate_index"])))
    export_path = _write_export_csv(REVIEW_RESTORE_EXPORT_PATH, RESTORE_EXPORT_FIELDNAMES, export_rows)
    return {
        "path": str(export_path),
        "filename": export_path.name,
        "image_count": len({row["image_id"] for row in export_rows}),
        "lane_count": len(export_rows),
    }


def export_training_lanes_csv(include_unlabeled: bool = True, valid_image_sources: dict[str, str] | None = None) -> dict[str, Any]:
    ensure_review_exports()
    roi_by_image = _read_csv_by_image(REVIEW_ROI_PATH, valid_image_sources)
    annotation_index = build_annotation_index()
    candidate_rows = _read_csv(REVIEW_CANDIDATES_PATH)
    export_rows: list[dict[str, Any]] = []

    for row in candidate_rows:
        image_id = row["image_id"]
        if not _row_matches_current_source(row, valid_image_sources):
            continue
        roi_row = roi_by_image.get(image_id)
        if not roi_row:
            continue
        candidate_index = int(row.get("candidate_index") or 0)
        annotation_row = annotation_index.get(image_id, {}).get(candidate_index, {})
        label = annotation_row.get("category", "").strip() or "unknown"
        if not include_unlabeled and label == "unknown":
            continue

        left_x = int(float(row["left_x"]))
        right_x = int(float(row["right_x"]))
        roi_y_start = int(float(roi_row["y_start"]))
        roi_y_end = int(float(roi_row["y_end"]))
        export_rows.append(
            {
                "image_id": image_id,
                "source_filename": row["source_filename"],
                "candidate_index": candidate_index,
                "roi_y_start": roi_y_start,
                "roi_y_end": roi_y_end,
                "left_x": left_x,
                "right_x": right_x,
                "x1": left_x,
                "y1": roi_y_start,
                "x2": right_x,
                "y2": roi_y_start,
                "x3": left_x,
                "y3": roi_y_end,
                "x4": right_x,
                "y4": roi_y_end,
                "label": label,
                "updated_at": row.get("updated_at", roi_row.get("updated_at", "")),
            }
        )

    export_rows.sort(key=lambda row: (row["image_id"], int(row["candidate_index"])))
    export_path = _write_export_csv(TRAINING_LANES_EXPORT_PATH, TRAINING_EXPORT_FIELDNAMES, export_rows)
    return {
        "path": str(export_path),
        "filename": export_path.name,
        "image_count": len({row["image_id"] for row in export_rows}),
        "lane_count": len(export_rows),
        "include_unlabeled": include_unlabeled,
    }


def load_category_suggestions() -> list[str]:
    if not CATEGORY_SUGGESTIONS_PATH.exists():
        return []
    values = []
    for line in CATEGORY_SUGGESTIONS_PATH.read_text(encoding="utf-8").splitlines():
        category = line.strip()
        if category and category not in values:
            values.append(category)
    return values


def save_category_suggestions(categories: list[str]) -> None:
    REVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    cleaned = []
    for category in categories:
        value = str(category).strip()
        if value and value not in cleaned:
            cleaned.append(value)
    CATEGORY_SUGGESTIONS_PATH.write_text("\n".join(cleaned) + ("\n" if cleaned else ""), encoding="utf-8")


def add_category_suggestion(category: str) -> list[str]:
    value = category.strip()
    categories = load_category_suggestions()
    if value and value not in categories:
        categories.append(value)
        save_category_suggestions(categories)
    return categories


def delete_category_suggestion(category: str) -> list[str]:
    value = category.strip()
    categories = [item for item in load_category_suggestions() if item != value]
    save_category_suggestions(categories)
    return categories


def ensure_review_exports() -> None:
    _ensure_csv(REVIEW_ROI_PATH, ROI_REVIEW_FIELDNAMES)
    _ensure_csv(REVIEW_CANDIDATES_PATH, CANDIDATE_REVIEW_FIELDNAMES)
    _ensure_csv(REVIEW_MANIFEST_PATH, MANIFEST_REVIEW_FIELDNAMES)
    _ensure_csv(REVIEW_ANNOTATIONS_PATH, ANNOTATION_FIELDNAMES)
    REVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    if not REVIEW_ANNOTATIONS_JSONL_PATH.exists():
        REVIEW_ANNOTATIONS_JSONL_PATH.write_text("", encoding="utf-8")


def load_review_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    ensure_review_exports()
    return (
        _read_csv(REVIEW_ROI_PATH),
        _read_csv(REVIEW_CANDIDATES_PATH),
        _read_csv(REVIEW_MANIFEST_PATH),
    )


def load_annotation_rows() -> list[dict[str, str]]:
    ensure_review_exports()
    return _read_csv(REVIEW_ANNOTATIONS_PATH)


def load_imported_annotation_rows() -> list[dict[str, str]]:
    return [row.copy() for row in _IMPORTED_ANNOTATION_ROWS]


def save_imported_annotation_rows(rows: list[dict[str, Any]]) -> None:
    global _IMPORTED_ANNOTATION_ROWS
    _IMPORTED_ANNOTATION_ROWS = [
        {key: str(row.get(key, "")) for key in IMPORTED_ANNOTATION_FIELDNAMES}
        for row in rows
    ]


def clear_imported_annotation_rows() -> None:
    global _IMPORTED_ANNOTATION_ROWS
    _IMPORTED_ANNOTATION_ROWS = []


def clear_imported_annotation_rows_for_image(image_id: str) -> None:
    global _IMPORTED_ANNOTATION_ROWS
    _IMPORTED_ANNOTATION_ROWS = [row for row in _IMPORTED_ANNOTATION_ROWS if row["image_id"] != image_id]


def build_annotation_index() -> dict[str, dict[int, dict[str, str]]]:
    rows_by_image: dict[str, dict[int, dict[str, str]]] = defaultdict(dict)
    for row in load_annotation_rows():
        image_id = str(row.get("image_id", "")).strip()
        candidate_index = _candidate_index_or_none(row)
        if not image_id or candidate_index is None:
            continue
        rows_by_image[image_id][candidate_index] = row
    return rows_by_image


def build_review_indexes() -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]], dict[str, dict[str, str]]]:
    roi_rows, candidate_rows, manifest_rows = load_review_rows()

    roi_by_image = {row["image_id"]: row for row in roi_rows}
    candidates_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_image[row["image_id"]].append(row)
    for rows in candidates_by_image.values():
        rows.sort(key=_candidate_sort_key)

    manifest_by_image = {row["image_id"]: row for row in manifest_rows}
    return roi_by_image, candidates_by_image, manifest_by_image


def build_imported_annotation_index() -> dict[str, list[dict[str, str]]]:
    rows_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in load_imported_annotation_rows():
        image_id = str(row.get("image_id", "")).strip()
        if image_id:
            rows_by_image[image_id].append(row)
    for rows in rows_by_image.values():
        rows.sort(key=_candidate_sort_key)
    return rows_by_image


def validate_and_normalize_training_annotation_rows(
    rows: list[dict[str, str]],
    image_sizes: dict[str, tuple[int, int]],
    image_sources: dict[str, str],
) -> list[dict[str, Any]]:
    if not rows:
        _raise_import_error("file has no importable data rows")

    normalized: list[dict[str, Any]] = []
    seen_by_image: dict[str, set[int]] = defaultdict(set)

    for row_number, row in enumerate(rows, start=2):
        has_annotation_schema = TRAINING_IMPORT_REQUIRED_COLUMNS.issubset(row.keys())
        has_training_export_schema = TRAINING_IMPORT_ALTERNATE_COLUMNS.issubset(row.keys())
        if has_annotation_schema:
            y_start_key = "y_start"
            y_end_key = "y_end"
            category_key = "category"
        elif has_training_export_schema:
            y_start_key = "roi_y_start"
            y_end_key = "roi_y_end"
            category_key = "label"
        else:
            required = TRAINING_IMPORT_REQUIRED_COLUMNS | TRAINING_IMPORT_ALTERNATE_COLUMNS
            missing = [column for column in sorted(required) if column not in row]
            _raise_import_error(
                "missing columns for annotation import. Use lane_annotations_review.csv, "
                "or training_lanes_export.csv if you only need labels/ROI geometry. "
                f"Missing: {', '.join(missing)}"
            )
            continue

        missing = [
            column
            for column in ("image_id", "source_filename", "candidate_index", "left_x", "right_x", y_start_key, y_end_key, category_key)
            if column not in row
        ]
        if missing:
            _raise_import_error(f"missing columns: {', '.join(sorted(missing))}")

        image_id = str(row.get("image_id", "")).strip()
        source_filename = str(row.get("source_filename", "")).strip()
        category = str(row.get(category_key, "")).strip()
        if has_training_export_schema and _is_unknown_label(category):
            category = ""
        if not image_id:
            _raise_import_error(f"row {row_number}: image_id is blank")
        if image_id not in image_sizes:
            _raise_import_error(f"row {row_number}: image_id is not in the current dataset: {image_id}")
        if not source_filename:
            _raise_import_error(f"row {row_number}: source_filename is blank")
        expected_source_filename = image_sources.get(image_id, "")
        if source_filename != expected_source_filename:
            _raise_import_error(
                f"row {row_number}: source_filename does not match current dataset for {image_id}: {source_filename}"
            )
        if not category and not has_training_export_schema:
            _raise_import_error(f"row {row_number}: category/label is blank")

        candidate_index = _parse_int(row.get("candidate_index", ""), "candidate_index", row_number)
        left_x = _parse_int(row.get("left_x", ""), "left_x", row_number)
        right_x = _parse_int(row.get("right_x", ""), "right_x", row_number)
        y_start = _parse_int(row.get(y_start_key, ""), y_start_key, row_number)
        y_end = _parse_int(row.get(y_end_key, ""), y_end_key, row_number)

        width, height = image_sizes[image_id]
        if left_x >= right_x:
            _raise_import_error(f"row {row_number}: left_x must be smaller than right_x")
        if y_start >= y_end:
            _raise_import_error(f"row {row_number}: ROI y_start must be smaller than y_end")
        if left_x < 0 or right_x > width:
            _raise_import_error(f"row {row_number}: horizontal coordinates are outside image bounds")
        if y_start < 0 or y_end > height:
            _raise_import_error(f"row {row_number}: vertical coordinates are outside image bounds")
        if candidate_index in seen_by_image[image_id]:
            _raise_import_error(f"row {row_number}: duplicate candidate_index within image: {candidate_index}")

        seen_by_image[image_id].add(candidate_index)

        normalized.append(
            {
                "image_id": image_id,
                "source_filename": source_filename,
                "candidate_index": candidate_index,
                "left_x": left_x,
                "right_x": right_x,
                "y_start": y_start,
                "y_end": y_end,
                "category": category,
                "updated_at": str(row.get("updated_at", "")).strip(),
            }
        )

    return normalized


def import_training_annotation_csv(
    csv_text: str,
    image_sizes: dict[str, tuple[int, int]],
    image_sources: dict[str, str],
) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        _raise_import_error("CSV header is missing")
    rows = list(reader)
    normalized = validate_and_normalize_training_annotation_rows(rows, image_sizes, image_sources)
    save_imported_annotation_rows(normalized)
    return {
        "imported_image_count": len({row["image_id"] for row in normalized}),
        "imported_lane_count": len(normalized),
    }


def import_review_restore_csv(
    csv_text: str,
    image_sizes: dict[str, tuple[int, int]],
    image_sources: dict[str, str],
    *,
    skip_unknown_images: bool = False,
) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        _raise_import_error("CSV header is missing")

    rows = list(reader)
    if not rows:
        _raise_import_error("file has no importable data rows")

    required_columns = {
        "image_id",
        "source_filename",
        "candidate_index",
        "width",
        "height",
        "roi_y_start",
        "roi_y_end",
        "left_x",
        "right_x",
    }
    missing_from_header = sorted(column for column in required_columns if column not in (reader.fieldnames or []))
    if missing_from_header:
        _raise_import_error(
            "review restore import requires review_restore_export.csv. "
            f"Missing columns: {', '.join(missing_from_header)}"
        )

    updated_at = _timestamp()
    restore_rows_by_image: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_by_image: dict[str, set[int]] = defaultdict(set)

    for row_number, row in enumerate(rows, start=2):
        image_id = str(row.get("image_id", "")).strip()
        source_filename = str(row.get("source_filename", "")).strip()
        if not image_id:
            _raise_import_error(f"row {row_number}: image_id is blank")
        if image_id not in image_sizes:
            if skip_unknown_images:
                continue
            _raise_import_error(f"row {row_number}: image_id is not in the current dataset: {image_id}")
        expected_source_filename = image_sources.get(image_id, "")
        if source_filename != expected_source_filename:
            if skip_unknown_images:
                continue
            _raise_import_error(
                f"row {row_number}: source_filename does not match current dataset for {image_id}: {source_filename}"
            )

        width, height = image_sizes[image_id]
        row_width = _parse_int(row.get("width", ""), "width", row_number)
        row_height = _parse_int(row.get("height", ""), "height", row_number)
        if row_width != width or row_height != height:
            _raise_import_error(
                f"row {row_number}: image size does not match current dataset for {image_id}: "
                f"{row_width}x{row_height}, expected {width}x{height}"
            )

        candidate_index = _parse_int(row.get("candidate_index", ""), "candidate_index", row_number)
        if candidate_index in seen_by_image[image_id]:
            _raise_import_error(f"row {row_number}: duplicate candidate_index within image: {candidate_index}")
        seen_by_image[image_id].add(candidate_index)

        roi_y_start = _parse_int(row.get("roi_y_start", ""), "roi_y_start", row_number)
        roi_y_end = _parse_int(row.get("roi_y_end", ""), "roi_y_end", row_number)
        left_x = _parse_int(row.get("left_x", ""), "left_x", row_number)
        right_x = _parse_int(row.get("right_x", ""), "right_x", row_number)
        center_x = _parse_int(row.get("center_x") or round((left_x + right_x) / 2), "center_x", row_number)
        estimated_width = _parse_int(row.get("estimated_width") or (right_x - left_x), "estimated_width", row_number)

        if left_x >= right_x:
            _raise_import_error(f"row {row_number}: left_x must be smaller than right_x")
        if roi_y_start >= roi_y_end:
            _raise_import_error(f"row {row_number}: roi_y_start must be smaller than roi_y_end")
        if left_x < 0 or right_x > width:
            _raise_import_error(f"row {row_number}: horizontal coordinates are outside image bounds")
        if roi_y_start < 0 or roi_y_end > height:
            _raise_import_error(f"row {row_number}: vertical coordinates are outside image bounds")

        restore_rows_by_image[image_id].append(
            {
                "image_id": image_id,
                "source_filename": source_filename,
                "width": width,
                "height": height,
                "candidate_index": candidate_index,
                "roi_y_start": roi_y_start,
                "roi_y_end": roi_y_end,
                "left_x": left_x,
                "right_x": right_x,
                "center_x": center_x,
                "estimated_width": estimated_width,
                "status": str(row.get("status", "")).strip() or "accepted",
                "source": str(row.get("source", "")).strip() or "review_restore_import",
                "confidence": str(row.get("confidence", "")).strip() or "restored",
                "is_manual_added": str(row.get("is_manual_added", "false")).strip().lower() == "true",
                "notes": str(row.get("notes", "")).strip(),
                "category": str(row.get("category", "")).strip(),
            }
        )

    if not restore_rows_by_image:
        _raise_import_error("no rows in the restore CSV match the current dataset")

    ensure_review_exports()
    existing_roi_rows, existing_candidate_rows, existing_manifest_rows = load_review_rows()
    restored_image_ids = set(restore_rows_by_image)
    roi_rows = [row for row in existing_roi_rows if row.get("image_id") not in restored_image_ids]
    candidate_rows = [row for row in existing_candidate_rows if row.get("image_id") not in restored_image_ids]
    manifest_rows = [row for row in existing_manifest_rows if row.get("image_id") not in restored_image_ids]
    annotation_rows = [row for row in load_annotation_rows() if row.get("image_id") not in restored_image_ids]

    for image_id, image_rows in restore_rows_by_image.items():
        image_rows.sort(key=lambda row: int(row["candidate_index"]))
        first = image_rows[0]
        roi_y_start = min(int(row["roi_y_start"]) for row in image_rows)
        roi_y_end = max(int(row["roi_y_end"]) for row in image_rows)
        width = int(first["width"])
        height = int(first["height"])
        source_filename = str(first["source_filename"])

        roi_rows.append(
            {
                "image_id": image_id,
                "source_filename": source_filename,
                "width": width,
                "height": height,
                "y_start": roi_y_start,
                "y_end": roi_y_end,
                "roi_height": roi_y_end - roi_y_start,
                "auto_y_start": roi_y_start,
                "auto_y_end": roi_y_end,
                "roi_confidence": "restored",
                "roi_reason": "review_restore_import",
                "roi_quality_flag": "",
                "review_status": "reviewed",
                "notes": "restored from review_restore_export.csv",
                "updated_at": updated_at,
            }
        )

        center_values: list[float] = []
        width_values: list[float] = []
        accepted_count = 0

        for row in image_rows:
            status = str(row["status"])
            if status in ACCEPTED_STATUSES:
                accepted_count += 1
            center_values.append(float(row["center_x"]))
            width_values.append(float(row["estimated_width"]))
            candidate_rows.append(
                {
                    "image_id": image_id,
                    "source_filename": source_filename,
                    "width": width,
                    "height": height,
                    "candidate_index": int(row["candidate_index"]),
                    "left_x": int(row["left_x"]),
                    "right_x": int(row["right_x"]),
                    "center_x": int(row["center_x"]),
                    "estimated_width": int(row["estimated_width"]),
                    "y_start": roi_y_start,
                    "y_end": roi_y_end,
                    "auto_left_x": int(row["left_x"]),
                    "auto_right_x": int(row["right_x"]),
                    "auto_center_x": int(row["center_x"]),
                    "auto_estimated_width": int(row["estimated_width"]),
                    "auto_status": status,
                    "status": status,
                    "source": row["source"],
                    "confidence": row["confidence"],
                    "is_manual_added": "true" if row["is_manual_added"] else "false",
                    "notes": row["notes"],
                    "updated_at": updated_at,
                }
            )

            if row["category"]:
                annotation_rows.append(
                    {
                        "image_id": image_id,
                        "source_filename": source_filename,
                        "candidate_index": int(row["candidate_index"]),
                        "left_x": int(row["left_x"]),
                        "right_x": int(row["right_x"]),
                        "y_start": roi_y_start,
                        "y_end": roi_y_end,
                        "category": row["category"],
                        "updated_at": updated_at,
                    }
                )

        center_values.sort()
        spacings = [center_values[index + 1] - center_values[index] for index in range(len(center_values) - 1)]
        manifest_rows.append(
            {
                "image_id": image_id,
                "source_filename": source_filename,
                "width": width,
                "height": height,
                "y_start": roi_y_start,
                "y_end": roi_y_end,
                "roi_height": roi_y_end - roi_y_start,
                "reviewed_boundary_count": len(image_rows),
                "accepted_boundary_count": accepted_count,
                "median_center_spacing_px": _median_or_blank(spacings),
                "median_estimated_width_px": _median_or_blank(width_values),
                "min_estimated_width_px": _min_or_blank(width_values),
                "max_estimated_width_px": _max_or_blank(width_values),
                "quality_flag": "",
                "detection_quality_flag": "",
                "review_status": "reviewed",
                "notes": "restored from review_restore_export.csv",
                "updated_at": updated_at,
            }
        )

    roi_rows.sort(key=lambda row: row["image_id"])
    candidate_rows.sort(key=_candidate_sort_key)
    manifest_rows.sort(key=lambda row: row["image_id"])
    annotation_rows.sort(key=_candidate_sort_key)

    _write_csv(REVIEW_ROI_PATH, ROI_REVIEW_FIELDNAMES, roi_rows)
    _write_csv(REVIEW_CANDIDATES_PATH, CANDIDATE_REVIEW_FIELDNAMES, candidate_rows)
    _write_csv(REVIEW_MANIFEST_PATH, MANIFEST_REVIEW_FIELDNAMES, manifest_rows)
    _write_csv(REVIEW_ANNOTATIONS_PATH, ANNOTATION_FIELDNAMES, annotation_rows)
    with REVIEW_ANNOTATIONS_JSONL_PATH.open("w", encoding="utf-8") as jsonl_file:
        for row in annotation_rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    clear_imported_annotation_rows()
    return {
        "restored_image_count": len(restored_image_ids),
        "restored_lane_count": sum(len(rows) for rows in restore_rows_by_image.values()),
    }


def restore_existing_review_restore_export(
    image_sizes: dict[str, tuple[int, int]],
    image_sources: dict[str, str],
) -> dict[str, Any]:
    if not REVIEW_RESTORE_EXPORT_PATH.exists():
        _raise_import_error(f"{REVIEW_RESTORE_EXPORT_PATH.name} does not exist. Export restore CSV first.")
    csv_text = REVIEW_RESTORE_EXPORT_PATH.read_text(encoding="utf-8-sig")
    return import_review_restore_csv(
        csv_text,
        image_sizes,
        image_sources,
        skip_unknown_images=True,
    )


def _median_or_blank(values: list[float]) -> str:
    if not values:
        return ""
    return f"{median(values):.2f}"


def _min_or_blank(values: list[float]) -> str:
    if not values:
        return ""
    return f"{min(values):.2f}"


def _max_or_blank(values: list[float]) -> str:
    if not values:
        return ""
    return f"{max(values):.2f}"


def save_image_review(
    *,
    image_id: str,
    source_filename: str,
    width: int,
    height: int,
    auto_roi: dict[str, Any],
    auto_manifest: dict[str, Any],
    y_start: int,
    y_end: int,
    boundaries: list[dict[str, Any]],
    review_status: str,
    notes: str,
    annotation: dict[str, Any] | None = None,
    write_annotation_csv: bool = False,
    write_annotation_jsonl: bool = False,
) -> None:
    ensure_review_exports()
    roi_rows, candidate_rows, manifest_rows = load_review_rows()
    updated_at = _timestamp()

    roi_rows = [row for row in roi_rows if row["image_id"] != image_id]
    candidate_rows = [row for row in candidate_rows if row["image_id"] != image_id]
    manifest_rows = [row for row in manifest_rows if row["image_id"] != image_id]

    roi_rows.append(
        {
            "image_id": image_id,
            "source_filename": source_filename,
            "width": width,
            "height": height,
            "y_start": y_start,
            "y_end": y_end,
            "roi_height": y_end - y_start,
            "auto_y_start": auto_roi["y_start"],
            "auto_y_end": auto_roi["y_end"],
            "roi_confidence": auto_roi.get("roi_confidence", ""),
            "roi_reason": auto_roi.get("roi_reason", ""),
            "roi_quality_flag": auto_roi.get("roi_quality_flag", ""),
            "review_status": review_status,
            "notes": notes,
            "updated_at": updated_at,
        }
    )

    sorted_boundaries = sorted(boundaries, key=lambda row: int(row["candidate_index"]))
    center_values: list[float] = []
    width_values: list[float] = []
    accepted_count = 0

    for boundary in sorted_boundaries:
        left_x = int(boundary["left_x"])
        right_x = int(boundary["right_x"])
        center_x = round((left_x + right_x) / 2)
        estimated_width = right_x - left_x
        center_values.append(center_x)
        width_values.append(estimated_width)
        status = str(boundary.get("status", "accepted"))
        if status in ACCEPTED_STATUSES:
            accepted_count += 1

        candidate_rows.append(
            {
                "image_id": image_id,
                "source_filename": source_filename,
                "width": width,
                "height": height,
                "candidate_index": int(boundary["candidate_index"]),
                "left_x": left_x,
                "right_x": right_x,
                "center_x": center_x,
                "estimated_width": estimated_width,
                "y_start": y_start,
                "y_end": y_end,
                "auto_left_x": boundary.get("auto_left_x", ""),
                "auto_right_x": boundary.get("auto_right_x", ""),
                "auto_center_x": boundary.get("auto_center_x", ""),
                "auto_estimated_width": boundary.get("auto_estimated_width", ""),
                "auto_status": boundary.get("auto_status", ""),
                "status": status,
                "source": boundary.get("source", "manual_review"),
                "confidence": boundary.get("confidence", "manual"),
                "is_manual_added": "true" if boundary.get("is_manual_added") else "false",
                "notes": boundary.get("notes", ""),
                "updated_at": updated_at,
            }
        )

    center_values.sort()
    spacings = [center_values[index + 1] - center_values[index] for index in range(len(center_values) - 1)]

    manifest_rows.append(
        {
            "image_id": image_id,
            "source_filename": source_filename,
            "width": width,
            "height": height,
            "y_start": y_start,
            "y_end": y_end,
            "roi_height": y_end - y_start,
            "reviewed_boundary_count": len(sorted_boundaries),
            "accepted_boundary_count": accepted_count,
            "median_center_spacing_px": _median_or_blank(spacings),
            "median_estimated_width_px": _median_or_blank(width_values),
            "min_estimated_width_px": _min_or_blank(width_values),
            "max_estimated_width_px": _max_or_blank(width_values),
            "quality_flag": auto_manifest.get("quality_flag", ""),
            "detection_quality_flag": auto_manifest.get("detection_quality_flag", ""),
            "review_status": review_status,
            "notes": notes,
            "updated_at": updated_at,
        }
    )

    roi_rows.sort(key=lambda row: row["image_id"])
    candidate_rows.sort(key=_candidate_sort_key)
    manifest_rows.sort(key=lambda row: row["image_id"])

    _write_csv(REVIEW_ROI_PATH, ROI_REVIEW_FIELDNAMES, roi_rows)
    _write_csv(REVIEW_CANDIDATES_PATH, CANDIDATE_REVIEW_FIELDNAMES, candidate_rows)
    _write_csv(REVIEW_MANIFEST_PATH, MANIFEST_REVIEW_FIELDNAMES, manifest_rows)

    if write_annotation_csv or write_annotation_jsonl:
        existing_annotation_rows = [row for row in load_annotation_rows() if row["image_id"] != image_id]
        new_annotation_rows: list[dict[str, Any]] = []
        boundary_by_index = {int(boundary["candidate_index"]): boundary for boundary in sorted_boundaries}

        for lane in (annotation or {}).get("lanes", []):
            category = str(lane.get("category", "")).strip()
            if not category:
                continue
            candidate_index = int(lane.get("candidate_index", 0))
            boundary = boundary_by_index.get(candidate_index)
            if not boundary:
                continue
            left_x = int(boundary["left_x"])
            right_x = int(boundary["right_x"])
            new_annotation_rows.append(
                {
                    "image_id": image_id,
                    "source_filename": source_filename,
                    "candidate_index": candidate_index,
                    "left_x": left_x,
                    "right_x": right_x,
                    "y_start": y_start,
                    "y_end": y_end,
                    "category": category,
                    "updated_at": updated_at,
                }
            )

        all_annotation_rows = existing_annotation_rows + new_annotation_rows
        all_annotation_rows.sort(key=_candidate_sort_key)

        if write_annotation_csv:
            _write_csv(REVIEW_ANNOTATIONS_PATH, ANNOTATION_FIELDNAMES, all_annotation_rows)

        if write_annotation_jsonl:
            REVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
            with REVIEW_ANNOTATIONS_JSONL_PATH.open("w", encoding="utf-8") as jsonl_file:
                for row in all_annotation_rows:
                    jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def reset_image_review(image_id: str) -> None:
    ensure_review_exports()
    roi_rows, candidate_rows, manifest_rows = load_review_rows()
    annotation_rows = load_annotation_rows()
    roi_rows = [row for row in roi_rows if row["image_id"] != image_id]
    candidate_rows = [row for row in candidate_rows if row["image_id"] != image_id]
    manifest_rows = [row for row in manifest_rows if row["image_id"] != image_id]
    annotation_rows = [row for row in annotation_rows if row["image_id"] != image_id]
    _write_csv(REVIEW_ROI_PATH, ROI_REVIEW_FIELDNAMES, roi_rows)
    _write_csv(REVIEW_CANDIDATES_PATH, CANDIDATE_REVIEW_FIELDNAMES, candidate_rows)
    _write_csv(REVIEW_MANIFEST_PATH, MANIFEST_REVIEW_FIELDNAMES, manifest_rows)
    _write_csv(REVIEW_ANNOTATIONS_PATH, ANNOTATION_FIELDNAMES, annotation_rows)
    REVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    with REVIEW_ANNOTATIONS_JSONL_PATH.open("w", encoding="utf-8") as jsonl_file:
        for row in annotation_rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
