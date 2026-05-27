from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


WEB_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WEB_ROOT.parent
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
INVENTORY_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_inventory.csv"
QUALITY_REPORT_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_quality_report.csv"

PIPELINE_SCRIPT_NAMES = [
    "build_image_inventory.py",
    "generate_vertical_projections.py",
    "detect_lane_roi_boundaries_v6.py",
    "create_lane_roi_boundary_overlays_v6.py",
]

QUALITY_FIELDNAMES = [
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

Runner = Callable[..., Any]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _default_quality_row(inventory_row: dict[str, str]) -> dict[str, str]:
    return {
        "image_id": inventory_row["image_id"],
        "source_filename": inventory_row["source_filename"],
        "relative_path": inventory_row["relative_path"],
        "file_ext": inventory_row["file_ext"],
        "width": inventory_row["width"],
        "height": inventory_row["height"],
        "channels": inventory_row["channels"],
        "readable": "yes",
        "quality_flag": "review",
        "blur_score_laplacian": "",
        "contrast_std": "",
        "dynamic_range_p01_p99": "",
        "estimated_tilt_deg": "",
        "background_unevenness": "",
        "artifact_border_score": "",
        "issues": "new_image_pending_quality_review",
        "segmentation_implication": "automatic Web segmentation generated before manual quality review",
    }


def ensure_quality_report_matches_inventory() -> int:
    inventory_rows = _read_csv(INVENTORY_PATH)
    quality_rows_by_id = {row["image_id"]: row for row in _read_csv(QUALITY_REPORT_PATH)}
    added_count = 0
    normalized_rows: list[dict[str, str]] = []

    for inventory_row in inventory_rows:
        existing = quality_rows_by_id.get(inventory_row["image_id"])
        if existing is None:
            row = _default_quality_row(inventory_row)
            added_count += 1
        else:
            row = {field: existing.get(field, "") for field in QUALITY_FIELDNAMES}
            for field in ("source_filename", "relative_path", "file_ext", "width", "height", "channels"):
                row[field] = inventory_row[field]
        normalized_rows.append(row)

    _write_csv(QUALITY_REPORT_PATH, normalized_rows, QUALITY_FIELDNAMES)
    return added_count


def _run_script(script_name: str, runner: Runner) -> dict[str, str]:
    script_path = SCRIPTS_ROOT / script_name
    if not script_path.exists():
        raise RuntimeError(f"Pipeline script not found: {script_path}")

    try:
        result = runner(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"{script_name} failed: {detail}") from exc

    return {
        "script": script_name,
        "stdout": str(getattr(result, "stdout", "") or "").strip(),
        "stderr": str(getattr(result, "stderr", "") or "").strip(),
    }


def run_dataset_refresh(runner: Runner = subprocess.run) -> dict[str, Any]:
    script_results = []
    script_results.append(_run_script(PIPELINE_SCRIPT_NAMES[0], runner))
    added_quality_rows = ensure_quality_report_matches_inventory()
    for script_name in PIPELINE_SCRIPT_NAMES[1:]:
        script_results.append(_run_script(script_name, runner))

    image_count = len(_read_csv(INVENTORY_PATH))
    return {
        "image_count": image_count,
        "added_quality_rows": added_quality_rows,
        "script_count": len(script_results),
        "scripts": script_results,
    }
