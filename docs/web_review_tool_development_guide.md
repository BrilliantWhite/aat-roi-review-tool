# Web Review Tool Development Guide

## 1. Purpose in This Dissertation Project

This Web tool is the local human-in-the-loop review surface for the AAT IEF gel image workflow. It is not a separate product track. Its job is to make the current automatic lane segmentation outputs reviewable, correctable, and exportable for downstream annotation and model preparation.

In the current project scope, the Web tool sits between:

1. automatic lane/ROI detection outputs under `outputs/lane_segmentation/`
2. manual segmentation correction and lane-level category annotation
3. reviewed CSV / JSONL artifacts under `Web/review_exports/`

The current automatic geometry baseline for the Web tool is **v6**. The tool must always preserve the distinction between:

- **automatic detector outputs**: read-only baseline inputs
- **reviewed outputs**: manually corrected exports written separately

This separation is critical for dissertation defensibility and reproducibility.

---

## 2. Current Scope

The Web tool currently supports:

- loading the automatic **v6** ROI/lane boundary baseline
- displaying one shared horizontal ROI per image
- displaying lane boundaries and lane centers
- dragging ROI top/bottom boundaries
- dragging lane boundaries left/right
- reviewing images one by one
- saving reviewed geometry into dedicated review CSV files
- resetting one image back to automatic results
- lane-level category annotation for training data preparation
- optional annotation export to **CSV** and **JSONL**
- category suggestions stored on the backend
- hover highlight and modal-based single-lane review/annotation
- lane deletion from the annotation modal

The tool is explicitly designed for **manual review and training-data preparation**, not for public deployment.

---

## 3. Architecture Overview

### 3.1 Backend

The backend is a lightweight FastAPI app in `Web/app.py`.

Responsibilities:

- serve the static frontend
- return image/review payloads
- return raw source images
- accept reviewed geometry saves
- accept reset requests
- manage category suggestions

### 3.2 Loader Layer

`Web/review_loader.py` builds the frontend payload by combining:

- image inventory
- automatic v6 ROI results
- automatic v6 boundary results
- reviewed geometry overrides
- annotation sidecar data

This file controls the “reviewed overrides automatic” behavior.

### 3.3 Storage Layer

`Web/review_store.py` is the persistence layer.

Responsibilities:

- ensure export files exist
- load/save reviewed ROI rows
- load/save reviewed lane rows
- load/save reviewed manifest rows
- load/save lane-level annotation rows
- write JSONL annotation exports
- manage category suggestion storage

### 3.4 Frontend

The frontend is static and lives in:

- `Web/static/index.html`
- `Web/static/style.css`
- `Web/static/app.js`

It uses:

- plain HTML/CSS
- vanilla JavaScript
- one `<img>` plus SVG overlay for interactions
- one modal for single-lane annotation

There is no frontend framework.

---

## 4. Key Files and Responsibilities

## `Web/paths.py`

Defines the active data sources and review export locations.

Important: the Web app is currently wired to **v6**, not v6.1 or v6.2.

Key paths include:

- `AUTO_ROI_PATH`
- `AUTO_CANDIDATES_PATH`
- `AUTO_MANIFEST_PATH`
- `AUTO_OVERLAY_MANIFEST_PATH`
- `REVIEW_ROI_PATH`
- `REVIEW_CANDIDATES_PATH`
- `REVIEW_MANIFEST_PATH`
- `REVIEW_ANNOTATIONS_PATH`
- `REVIEW_ANNOTATIONS_JSONL_PATH`
- `CATEGORY_SUGGESTIONS_PATH`

If a future AI changes these paths accidentally, the whole review workflow will silently shift to another segmentation version. Always verify before editing.

## `Web/app.py`

Defines:

- Pydantic request payloads
- FastAPI routes
- save/reset/category endpoints

Key routes:

- `GET /`
- `GET /api/images`
- `GET /api/images/{image_id}`
- `GET /api/images/{image_id}/raw`
- `POST /api/images/{image_id}/review`
- `POST /api/images/{image_id}/reset`
- `GET /api/categories`
- `POST /api/categories`
- `DELETE /api/categories/{category}`

## `Web/review_loader.py`

Builds the frontend payload for each image.

Important behavior:

- reviewed ROI overrides automatic ROI
- reviewed boundaries override automatic boundaries
- boundary annotation is attached per lane by `candidate_index`

This file determines what the frontend sees.

## `Web/review_store.py`

This is the authoritative reviewed-output writer.

Reviewed geometry is stored separately from automatic segmentation results.

Exports currently include:

- `horizontal_roi_review.csv`
- `lane_boundary_candidates_review.csv`
- `lane_boundary_manifest_review.csv`
- `lane_annotations_review.csv`
- `lane_annotations_review.jsonl`
- `category_suggestions.txt`

## `Web/static/index.html`

Defines:

- sidebar layout
- overlay image stage
- annotation/export panel
- modal DOM for lane annotation

## `Web/static/style.css`

Defines:

- overall page layout
- overlay styles
- hover/highlight styles
- modal layout
- delete button styling
- preview scaling behavior

## `Web/static/app.js`

This is the main interaction controller.

Responsibilities:

- fetch image list and image payloads
- maintain current frontend state
- render overlay
- handle ROI drag
- handle lane boundary drag
- handle hover and selection
- open/close annotation modal
- draw lane preview
- save reviewed geometry
- reset current image
- manage category suggestions

This is the highest-risk file for regressions.

---

## 5. Current Data Flow

### Automatic-to-frontend flow

1. Automatic v6 segmentation files are read from `outputs/lane_segmentation/lane_roi_boundaries_v6/`
2. `review_loader.py` combines those with inventory metadata
3. If reviewed exports exist for the same `image_id`, reviewed values override automatic ones
4. The combined payload is returned by `GET /api/images/{image_id}`
5. `static/app.js` stores the payload in `state.payload`
6. `drawOverlay()` renders the current ROI/lane state

### Frontend-to-reviewed-output flow

1. User drags ROI or boundaries / edits category / deletes a lane
2. Frontend updates in-memory `state.payload`
3. Save sends a payload to `POST /api/images/{image_id}/review`
4. `app.py` validates bounds/order
5. `review_store.py` writes reviewed CSV rows
6. Optional lane annotation CSV/JSONL is written if requested
7. Repository refresh occurs and the image reloads from reviewed data

---

## 6. Current UI Behavior Contract

This section is the most important one for future AI edits.

### 6.1 Overlay behavior that must remain true

- lane boundaries must remain **always visible**
- ROI lines must remain visible
- lane hover should highlight the hovered lane
- hover should not require clicking the top status dot first
- active hover should show the lane callout
- boundary dragging must remain possible while hover exists
- hover must not swallow boundary dragging
- clicking a lane opens the modal
- deleting a lane must not delete all lanes; at least one lane must remain

### 6.2 Modal behavior that must remain true

- modal layout is **left controls / right preview**
- right preview keeps the crop in original aspect ratio
- equal-ratio zoom slider must remain available unless the user explicitly removes it
- lane deletion is currently handled from the modal, not from overlay buttons
- category editing is per lane
- category suggestions are editable

### 6.3 Export behavior that must remain true

- reviewed geometry is separate from automatic outputs
- annotation export is lane-level
- annotation meaning is training-data category annotation, not general notes
- CSV and JSONL export are selectable independently
- blank category lanes are not exported
- export coordinates use the real reviewed lane rectangle, not preview zoom state

---

## 7. Review Export Files

## `horizontal_roi_review.csv`

One row per image for reviewed ROI.

Key fields:

- `image_id`
- `y_start`
- `y_end`
- `auto_y_start`
- `auto_y_end`
- `review_status`
- `notes`

## `lane_boundary_candidates_review.csv`

One row per reviewed lane candidate.

Key fields:

- `image_id`
- `candidate_index`
- `left_x`
- `right_x`
- `center_x`
- `estimated_width`
- `auto_left_x`
- `auto_right_x`
- `status`
- `source`
- `is_manual_added`

## `lane_boundary_manifest_review.csv`

One row per image-level reviewed summary.

Key fields:

- `reviewed_boundary_count`
- `accepted_boundary_count`
- width and spacing summaries
- `review_status`
- `notes`

## `lane_annotations_review.csv`

Training annotation export.

Key fields:

- `image_id`
- `candidate_index`
- `left_x`
- `right_x`
- `y_start`
- `y_end`
- `category`
- `updated_at`

## `lane_annotations_review.jsonl`

Same annotation content as line-delimited JSON for downstream model tooling.

## `category_suggestions.txt`

One category per line.

Used to populate the modal suggestion list.

---

## 8. API Contract Summary

## `GET /api/images`

Returns image list items for sidebar rendering.

Includes:

- `image_id`
- `source_filename`
- `width`
- `height`
- `quality_flag`
- `detection_quality_flag`
- `manual_review_required`
- `accepted_boundary_count`
- `review_status`
- `has_review`
- `notes`

## `GET /api/images/{image_id}`

Returns the full review payload for one image.

Top-level sections:

- `image`
- `roi`
- `boundaries`
- `boundary_source`
- `manifest`
- `review`
- `overlay`
- `annotation`

Each boundary includes:

- geometry
- automatic fallback geometry
- review state
- `annotation.category`

## `POST /api/images/{image_id}/review`

Accepts reviewed geometry and annotation.

Important fields:

- `y_start`
- `y_end`
- `boundaries[]`
- `annotation.enabled`
- `annotation.lanes[]`
- `write_annotation_csv`
- `write_annotation_jsonl`
- `review_status`
- `notes`

## `POST /api/images/{image_id}/reset`

Deletes reviewed rows for the image and restores automatic baseline behavior.

## Category endpoints

- `GET /api/categories`
- `POST /api/categories`
- `DELETE /api/categories/{category}`

These are UI support endpoints for modal suggestions.

---

## 9. Rules for Future AI Sessions

A new AI should read this file before editing the Web tool.

### Non-negotiable rules

1. **Do not change the automatic baseline version silently.**
   Verify `Web/paths.py` before changing segmentation source paths.

2. **Do not overwrite automatic outputs.**
   Reviewed outputs must remain separate.

3. **Do not break existing working UI behavior.**
   This is now a project rule.

4. **Do not remove interaction features without explicit approval.**
   Examples: hover, drag, delete, modal zoom, export toggles.

5. **Do not treat annotation as a generic note system.**
   It is lane-level training category metadata.

6. **Do not move fast by guessing.**
   If hover/drag/overlay breaks, investigate the event flow and draw order first.

### Practical checklist before editing UI

- Read `Web/static/app.js`
- Read `Web/static/index.html`
- Read `Web/static/style.css`
- Confirm whether the requested change could break:
  - boundary visibility
  - drag behavior
  - hover behavior
  - click-to-open modal
  - lane deletion
  - export behavior
- After editing, verify those behaviors in code and, if requested, in the running app

---

## 10. Known Risk Areas

### `drawOverlay()` risk

This function is sensitive because SVG draw order affects visibility and interactivity.

Common failure modes:

- boundary lines disappear because layering changed
- hover works only on status dots, not lane area
- dragging breaks because hover redraw interferes
- click handlers conflict with hit-lines

### `handleOverlayMouseMove()` risk

This function must coordinate:

- hover highlight
- drag state
- lane coordinate hit-testing

If this logic becomes conditional on the wrong target element, hover regresses.

### modal preview risk

Preview behavior must stay visually accurate:

- preserve ratio
- use lane crop plus preview padding
- export coordinates must ignore preview zoom

### delete behavior risk

Deleting a lane is not just removing a row from an array. It must preserve valid neighbor boundaries and keep the overlay usable.

---

## 11. Agent / Team Development Guidance

If future work uses agent teams:

- one fix agent should focus on implementation only
- one test/review agent should validate behavior/code paths separately
- agents should be told explicitly not to break existing working UI behavior
- when current outer working directory is not the git repo root, use the configured worktree hooks that redirect to `AAT_Project`

Recommended split:

- **implementation agent**: file edits only
- **test/review agent**: syntax checks, payload checks, logic-path verification

---

## 12. Minimal Start-Up for a New AI

A fresh AI session should do this in order:

1. Read this file.
2. Read `docs/web_review_tool_usage_and_api.md`.
3. Read `Web/paths.py` to confirm active segmentation baseline.
4. Read `Web/static/app.js` if the request touches UI behavior.
5. Read `Web/review_store.py` if the request touches export behavior.
6. Read `plan.md` to understand current dissertation-phase status.

If the task is UI-related, the AI should confirm layout/interaction ambiguities before editing.
