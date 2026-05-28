from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from dataset_refresh import run_dataset_refresh
from paths import STATIC_ROOT
from review_loader import ReviewRepository
from review_store import (
    add_category_suggestion,
    clear_imported_annotation_rows,
    clear_imported_annotation_rows_for_image,
    delete_category_suggestion,
    export_review_restore_csv,
    export_training_lanes_csv,
    import_review_restore_csv,
    import_training_annotation_csv,
    load_category_suggestions,
    reset_image_review,
    restore_existing_review_restore_export,
    save_image_review,
)


class BoundaryPayload(BaseModel):
    candidate_index: int
    left_x: int
    right_x: int
    status: str = "accepted"
    notes: str = ""
    source: str = "manual_review"
    confidence: str = "manual"
    auto_left_x: int | None = None
    auto_right_x: int | None = None
    auto_center_x: int | None = None
    auto_estimated_width: int | None = None
    auto_status: str | None = None
    is_manual_added: bool = False

    @field_validator("right_x")
    @classmethod
    def validate_right_x(cls, value: int, info: Any) -> int:
        left_x = info.data.get("left_x")
        if left_x is not None and value <= left_x:
            raise ValueError("right_x must be greater than left_x")
        return value


class LaneAnnotationPayload(BaseModel):
    candidate_index: int
    category: str = ""


class AnnotationPayload(BaseModel):
    enabled: bool = False
    lanes: list[LaneAnnotationPayload] = Field(default_factory=list)


class CategorySuggestionPayload(BaseModel):
    category: str


class ResetScopePayload(BaseModel):
    scope: str = "current"

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: str) -> str:
        if value not in {"current", "all"}:
            raise ValueError("scope must be current or all")
        return value


class ExportTrainingPayload(BaseModel):
    include_unlabeled: bool = True


class ReviewSavePayload(BaseModel):
    y_start: int
    y_end: int
    boundaries: list[BoundaryPayload] = Field(default_factory=list)
    annotation: AnnotationPayload = Field(default_factory=AnnotationPayload)
    write_annotation_csv: bool = False
    write_annotation_jsonl: bool = False
    review_status: str = "reviewed"
    notes: str = ""

    @field_validator("y_end")
    @classmethod
    def validate_y_end(cls, value: int, info: Any) -> int:
        y_start = info.data.get("y_start")
        if y_start is not None and value <= y_start:
            raise ValueError("y_end must be greater than y_start")
        return value


app = FastAPI(title="AAT ROI/Lane Review Tool")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

repository = ReviewRepository()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/api/images")
def list_images() -> list[dict[str, Any]]:
    repository.refresh()
    return repository.list_images()


@app.get("/api/images/{image_id}")
def get_image(image_id: str) -> dict[str, Any]:
    repository.refresh()
    try:
        return repository.get_image_payload(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/images/{image_id}/raw")
def get_image_raw(image_id: str) -> FileResponse:
    try:
        image_path = repository.get_image_path(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(image_path)


@app.post("/api/import/training-annotations")
async def import_training_annotations(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    raw_bytes = await file.read()
    try:
        csv_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    image_sizes = {
        image_id: (record.width, record.height)
        for image_id, record in repository.inventory_records.items()
    }
    image_sources = {
        image_id: record.source_filename
        for image_id, record in repository.inventory_records.items()
    }
    try:
        summary = import_training_annotation_csv(csv_text, image_sizes, image_sources)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository.refresh()
    return {"ok": True, **summary}


@app.post("/api/import/review-restore")
async def import_review_restore(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    raw_bytes = await file.read()
    try:
        csv_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    image_sizes = {
        image_id: (record.width, record.height)
        for image_id, record in repository.inventory_records.items()
    }
    image_sources = {
        image_id: record.source_filename
        for image_id, record in repository.inventory_records.items()
    }
    try:
        summary = import_review_restore_csv(csv_text, image_sizes, image_sources)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository.refresh()
    return {"ok": True, **summary}


@app.delete("/api/import/training-annotations")
def clear_imported_training_annotations() -> dict[str, Any]:
    clear_imported_annotation_rows()
    repository.refresh()
    return {"ok": True}


@app.post("/api/reload")
def reload_state() -> dict[str, Any]:
    clear_imported_annotation_rows()
    repository.refresh()
    return {"ok": True}


@app.post("/api/restore/review-restore-export")
def restore_review_restore_export() -> dict[str, Any]:
    image_sizes = {
        image_id: (record.width, record.height)
        for image_id, record in repository.inventory_records.items()
    }
    image_sources = {
        image_id: record.source_filename
        for image_id, record in repository.inventory_records.items()
    }
    try:
        summary = restore_existing_review_restore_export(image_sizes, image_sources)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository.refresh()
    return {"ok": True, **summary}


@app.post("/api/dataset/update")
def update_dataset() -> dict[str, Any]:
    try:
        summary = run_dataset_refresh()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    repository.refresh()
    return {"ok": True, **summary}


@app.post("/api/exports/review-restore")
def export_review_restore() -> dict[str, Any]:
    try:
        summary = export_review_restore_csv(valid_image_ids=set(repository.inventory_records))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **summary}


@app.post("/api/exports/training-lanes")
def export_training_lanes(payload: ExportTrainingPayload) -> dict[str, Any]:
    try:
        summary = export_training_lanes_csv(
            include_unlabeled=payload.include_unlabeled,
            valid_image_ids=set(repository.inventory_records),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **summary}


@app.post("/api/images/{image_id}/review")
def save_review(image_id: str, payload: ReviewSavePayload) -> dict[str, Any]:
    repository.refresh()
    try:
        image_payload = repository.get_image_payload(image_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    width = int(image_payload["image"]["width"])
    height = int(image_payload["image"]["height"])
    if payload.y_start < 0 or payload.y_end > height:
        raise HTTPException(status_code=400, detail="ROI is out of image bounds")

    boundaries = []
    for boundary in payload.boundaries:
        if boundary.left_x < 0 or boundary.right_x > width:
            raise HTTPException(status_code=400, detail=f"Boundary {boundary.candidate_index} is out of image bounds")
        boundaries.append(boundary.model_dump())

    ordered = sorted(boundaries, key=lambda row: row["candidate_index"])
    for previous, current in zip(ordered, ordered[1:]):
        if current["left_x"] < previous["left_x"]:
            raise HTTPException(status_code=400, detail="Boundaries must remain ordered from left to right")

    save_image_review(
        image_id=image_id,
        source_filename=str(image_payload["image"]["source_filename"]),
        width=width,
        height=height,
        auto_roi=image_payload["roi"],
        auto_manifest=image_payload["manifest"],
        y_start=payload.y_start,
        y_end=payload.y_end,
        boundaries=ordered,
        annotation=payload.annotation.model_dump(),
        write_annotation_csv=payload.write_annotation_csv,
        write_annotation_jsonl=payload.write_annotation_jsonl,
        review_status=payload.review_status,
        notes=payload.notes,
    )
    repository.refresh()
    return {"ok": True}


@app.get("/api/categories")
def get_categories() -> dict[str, list[str]]:
    return {"categories": load_category_suggestions()}


@app.post("/api/categories")
def add_category(payload: CategorySuggestionPayload) -> dict[str, list[str]]:
    category = payload.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="category is required")
    return {"categories": add_category_suggestion(category)}


@app.delete("/api/categories/{category}")
def remove_category(category: str) -> dict[str, list[str]]:
    return {"categories": delete_category_suggestion(category)}


@app.post("/api/images/{image_id}/reset")
def reset_review(image_id: str) -> dict[str, Any]:
    reset_image_review(image_id)
    repository.refresh()
    return {"ok": True}


@app.post("/api/images/{image_id}/reset-scope")
def reset_scope(image_id: str, payload: ResetScopePayload) -> dict[str, Any]:
    if payload.scope == "all":
        clear_imported_annotation_rows()
        for item in repository.list_images():
            reset_image_review(item["image_id"])
        repository.refresh()
        return {"ok": True, "scope": "all"}

    clear_imported_annotation_rows_for_image(image_id)
    reset_image_review(image_id)
    repository.refresh()
    return {"ok": True, "scope": "current"}
