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
    raise ValueError(f"训练CSV校验失败：{message}")


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


def _read_csv_by_image(path: Path) -> dict[str, dict[str, str]]:
    return {row["image_id"]: row for row in _read_csv(path)}


def export_review_restore_csv() -> dict[str, Any]:
    ensure_review_exports()
    roi_by_image = _read_csv_by_image(REVIEW_ROI_PATH)
    annotation_index = build_annotation_index()
    candidate_rows = _read_csv(REVIEW_CANDIDATES_PATH)
    export_rows: list[dict[str, Any]] = []

    for row in candidate_rows:
        image_id = row["image_id"]
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
    _write_csv(REVIEW_RESTORE_EXPORT_PATH, RESTORE_EXPORT_FIELDNAMES, export_rows)
    return {
        "path": str(REVIEW_RESTORE_EXPORT_PATH),
        "image_count": len({row["image_id"] for row in export_rows}),
        "lane_count": len(export_rows),
    }


def export_training_lanes_csv(include_unlabeled: bool = True) -> dict[str, Any]:
    ensure_review_exports()
    roi_by_image = _read_csv_by_image(REVIEW_ROI_PATH)
    annotation_index = build_annotation_index()
    candidate_rows = _read_csv(REVIEW_CANDIDATES_PATH)
    export_rows: list[dict[str, Any]] = []

    for row in candidate_rows:
        image_id = row["image_id"]
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
    _write_csv(TRAINING_LANES_EXPORT_PATH, TRAINING_EXPORT_FIELDNAMES, export_rows)
    return {
        "path": str(TRAINING_LANES_EXPORT_PATH),
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
        candidate_index = int(row.get("candidate_index") or 0)
        rows_by_image[row["image_id"]][candidate_index] = row
    return rows_by_image


def build_review_indexes() -> tuple[dict[str, dict[str, str]], dict[str, list[dict[str, str]]], dict[str, dict[str, str]]]:
    roi_rows, candidate_rows, manifest_rows = load_review_rows()

    roi_by_image = {row["image_id"]: row for row in roi_rows}
    candidates_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_image[row["image_id"]].append(row)
    for rows in candidates_by_image.values():
        rows.sort(key=lambda row: int(row["candidate_index"]))

    manifest_by_image = {row["image_id"]: row for row in manifest_rows}
    return roi_by_image, candidates_by_image, manifest_by_image


def build_imported_annotation_index() -> dict[str, list[dict[str, str]]]:
    rows_by_image: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in load_imported_annotation_rows():
        rows_by_image[row["image_id"]].append(row)
    for rows in rows_by_image.values():
        rows.sort(key=lambda row: int(row.get("candidate_index") or 0))
    return rows_by_image


def validate_and_normalize_training_annotation_rows(
    rows: list[dict[str, str]],
    image_sizes: dict[str, tuple[int, int]],
    image_sources: dict[str, str],
) -> list[dict[str, Any]]:
    if not rows:
        _raise_import_error("文件没有可导入的数据行")

    normalized: list[dict[str, Any]] = []
    seen_by_image: dict[str, set[int]] = defaultdict(set)

    for row_number, row in enumerate(rows, start=2):
        missing = [column for column in TRAINING_IMPORT_REQUIRED_COLUMNS if column not in row]
        if missing:
            _raise_import_error(f"缺少列：{', '.join(sorted(missing))}")

        image_id = str(row.get("image_id", "")).strip()
        source_filename = str(row.get("source_filename", "")).strip()
        category = str(row.get("category", "")).strip()
        if not image_id:
            _raise_import_error(f"第 {row_number} 行 image_id 为空")
        if image_id not in image_sizes:
            _raise_import_error(f"第 {row_number} 行 image_id 不存在于当前数据集：{image_id}")
        if not source_filename:
            _raise_import_error(f"第 {row_number} 行 source_filename 为空")
        expected_source_filename = image_sources.get(image_id, "")
        if source_filename != expected_source_filename:
            _raise_import_error(
                f"第 {row_number} 行 source_filename 与当前数据集不匹配：{image_id} -> {source_filename}"
            )
        if not category:
            _raise_import_error(f"第 {row_number} 行 category 为空")

        try:
            candidate_index = int(float(row.get("candidate_index", "")))
            left_x = int(float(row.get("left_x", "")))
            right_x = int(float(row.get("right_x", "")))
            y_start = int(float(row.get("y_start", "")))
            y_end = int(float(row.get("y_end", "")))
        except ValueError:
            _raise_import_error(f"第 {row_number} 行存在无法解析的数值字段")

        width, height = image_sizes[image_id]
        if left_x >= right_x:
            _raise_import_error(f"第 {row_number} 行 left_x 必须小于 right_x")
        if y_start >= y_end:
            _raise_import_error(f"第 {row_number} 行 y_start 必须小于 y_end")
        if left_x < 0 or right_x > width:
            _raise_import_error(f"第 {row_number} 行横向坐标超出图片范围")
        if y_start < 0 or y_end > height:
            _raise_import_error(f"第 {row_number} 行纵向坐标超出图片范围")
        if candidate_index in seen_by_image[image_id]:
            _raise_import_error(f"第 {row_number} 行 candidate_index 在同图内重复：{candidate_index}")

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
        _raise_import_error("CSV 缺少表头")
    rows = list(reader)
    normalized = validate_and_normalize_training_annotation_rows(rows, image_sizes, image_sources)
    save_imported_annotation_rows(normalized)
    return {
        "imported_image_count": len({row["image_id"] for row in normalized}),
        "imported_lane_count": len(normalized),
    }


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
    candidate_rows.sort(key=lambda row: (row["image_id"], int(row["candidate_index"])))
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
        all_annotation_rows.sort(key=lambda row: (row["image_id"], int(row.get("candidate_index") or 0)))

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
