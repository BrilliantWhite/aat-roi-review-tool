from __future__ import annotations

from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WEB_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
STATIC_ROOT = WEB_ROOT / "static"
REVIEW_EXPORT_ROOT = WEB_ROOT / "review_exports"

INVENTORY_PATH = PROJECT_ROOT / "dataset" / "metadata" / "image_inventory.csv"
LANE_COUNT_REVIEW_PATH = PROJECT_ROOT / "dataset" / "metadata" / "lane_count_review.csv"
AUTO_ROI_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6" / "horizontal_roi_manifest_v6.csv"
AUTO_CANDIDATES_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6" / "lane_boundary_candidates_v6.csv"
AUTO_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "lane_roi_boundaries_v6" / "lane_boundary_manifest_v6.csv"
AUTO_OVERLAY_MANIFEST_PATH = PROJECT_ROOT / "outputs" / "lane_segmentation" / "overlays" / "roi_boundaries_v6" / "lane_roi_boundary_overlay_manifest_v6.csv"

REVIEW_ROI_PATH = REVIEW_EXPORT_ROOT / "horizontal_roi_review.csv"
REVIEW_CANDIDATES_PATH = REVIEW_EXPORT_ROOT / "lane_boundary_candidates_review.csv"
REVIEW_MANIFEST_PATH = REVIEW_EXPORT_ROOT / "lane_boundary_manifest_review.csv"
REVIEW_ANNOTATIONS_PATH = REVIEW_EXPORT_ROOT / "lane_annotations_review.csv"
REVIEW_ANNOTATIONS_JSONL_PATH = REVIEW_EXPORT_ROOT / "lane_annotations_review.jsonl"
REVIEW_RESTORE_EXPORT_PATH = REVIEW_EXPORT_ROOT / "review_restore_export.csv"
TRAINING_LANES_EXPORT_PATH = REVIEW_EXPORT_ROOT / "training_lanes_export.csv"
CATEGORY_SUGGESTIONS_PATH = REVIEW_EXPORT_ROOT / "category_suggestions.txt"
