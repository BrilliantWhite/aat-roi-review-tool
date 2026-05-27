# Web Review Tool Usage and API Guide

## 1. What This Tool Is For

This Web tool is the manual review and lane-level annotation interface for the AAT IEF gel image dissertation workflow.

It is used to:

- inspect automatic **v6** ROI/lane segmentation results
- correct ROI placement
- correct lane boundaries
- remove bad lane splits if needed
- assign lane-level training categories
- export reviewed geometry and annotation artifacts

It is a **local research tool**, not a production web application.

---

## 2. How to Start the Service

From the project environment, the backend is typically started with:

```bash
python -m uvicorn app:app --app-dir "D:/Univercity_information/Dissertation/AAT_Project/Web" --host 127.0.0.1 --port 8008
```

Open in browser:

```text
http://127.0.0.1:8008
```

If the page looks stale after changes, use:

- `Ctrl + F5` on Windows for a hard refresh

---

## 3. Page Layout

The page has two main areas.

### Left sidebar

Contains:

- image list
- current image status panel
- mask opacity slider
- annotation export controls
- review notes
- navigation buttons

### Main workspace

Contains:

- original image
- SVG overlay for ROI/lane review
- hover/callout interactions
- modal entry by clicking a lane

---

## 3A. 导入训练 CSV 恢复编辑

左侧操作栏新增 `导入训练CSV` 按钮。

用途：
- 读取一份训练用 `lane_annotations_review.csv`
- 按 `image_id` 映射回 dataset 原图
- 只恢复 CSV 中已有的泳道分割和 category
- 作为临时编辑会话载入，不会立刻覆盖当前 `Web/review_exports/` 正式保存结果

校验要求：
- 文件必须是 UTF-8 编码 CSV
- 必须包含列：`image_id`, `source_filename`, `candidate_index`, `left_x`, `right_x`, `y_start`, `y_end`, `category`
- `category` 不能为空
- `source_filename` 必须和当前数据集记录匹配
- 坐标必须在原图范围内
- 同图内 `candidate_index` 不能重复

---

## 4. Main Review Workflow

Recommended usage order:

1. after adding images to `dataset/Originial/`, click `更新数据集` once and wait for it to finish
2. select an image from the left sidebar
3. inspect the automatic ROI and lane boundaries
4. adjust the ROI if needed
5. adjust lane boundaries if needed
6. hover lanes to inspect highlight and category state
7. click a lane to open the annotation modal
8. assign or edit lane category
9. save reviewed geometry and optional annotation export
10. move to the next image

---

## 5. Overlay Interaction Rules

## ROI lines

- green horizontal lines represent the shared ROI top and bottom
- they can be dragged up/down
- ROI correction affects all lanes in that image because the current workflow uses one shared horizontal ROI

## Lane boundaries

- yellow vertical boundaries must remain visible at all times
- they can be dragged left/right
- lane review edits are stored in reviewed CSV outputs, not written back into automatic segmentation files

## Lane hover

- moving the mouse over a lane should highlight that lane
- hover should display a lane callout
- hover is for inspection only

## Lane click

- clicking a lane opens the annotation modal
- the modal is the main place for lane category editing and lane deletion

---

## 6. Annotation Modal

The modal uses a **left controls / right preview** layout.

### Left side

Contains:

- category input field
- “add to suggestions” button
- suggestion chips
- placeholder area reserved for future functionality
- delete-lane button
- save/cancel buttons

### Right side

Contains:

- single-lane preview crop
- equal-ratio zoom slider
- export-coordinate note

### Important behavior

- the preview is for visual inspection only
- zoom must not change exported coordinates
- deleting a lane here removes it from the current reviewed state for that image
- at least one lane must remain

---

## 7. Category Suggestions

The tool supports a reusable category list.

Behavior:

- enter a category
- click “添加到常用项” to store it
- suggestions appear as selectable chips
- suggestions are backed by `category_suggestions.txt`

This is useful for consistent training labels.

---

## 8. Export Controls

The annotation panel supports two export checkboxes:

- export CSV annotation
- export JSONL annotation

You can:

- enable only CSV
- enable only JSONL
- enable both

Blank category lanes are not exported.

---

## 8A. 更新数据集

The left action panel includes `更新数据集`.

Use it after adding, replacing, or removing images under:

```text
dataset/Originial/
```

The button runs the automatic Web input refresh pipeline:

1. rebuild `dataset/metadata/image_inventory.csv`
2. append conservative `review` placeholder rows to `dataset/metadata/image_quality_report.csv` for newly discovered images
3. regenerate vertical projection metadata
4. rerun automatic v6 ROI/lane boundary detection
5. regenerate v6 overlay manifests
6. reload the Web app image list from the refreshed automatic outputs

Existing reviewed geometry and annotation exports under `Web/review_exports/` are not deleted by this button. If an image already has reviewed geometry, the Web tool will still prefer the reviewed rows when displaying that image.

---

## 9. Review Output Files

All review outputs are written under:

```text
Web/review_exports/
```

### Geometry review files

#### `horizontal_roi_review.csv`
Reviewed image-level ROI rows.

#### `lane_boundary_candidates_review.csv`
Reviewed lane geometry rows.

#### `lane_boundary_manifest_review.csv`
Reviewed image-level lane summary rows.

### Annotation files

#### `review_restore_export.csv`
Full reviewed segmentation restore export. One row per lane, including shared ROI range, lane geometry, and category if present. Use this file to reproduce manually corrected segmentation state later.

#### `training_lanes_export.csv`
Full training export. One row per lane, including lane corner coordinates and label. By default unlabeled lanes are exported as `unknown`; the export flow can also skip unlabeled lanes.

#### `lane_annotations_review.csv`
Lane-level training annotation CSV.

Key fields:

- `image_id`
- `source_filename`
- `candidate_index`
- `left_x`
- `right_x`
- `y_start`
- `y_end`
- `category`
- `updated_at`

#### `lane_annotations_review.jsonl`
Line-delimited JSON version of the same annotation export.

#### `category_suggestions.txt`
One category suggestion per line.

---

## 9A. Full Restore and Training Exports

The left action panel now provides two additional export actions:

### 导出可复现分割CSV

- writes `review_restore_export.csv`
- exports all images and all reviewed lanes
- each row contains the image id, ROI range, lane boundary geometry, and category if available
- intended for restoring manually corrected segmentation state later

### 导出训练CSV

- writes `training_lanes_export.csv`
- exports all images and all reviewed lanes as one row per lane
- includes lane rectangle corner coordinates derived from `left_x`, `right_x`, `roi_y_start`, and `roi_y_end`
- default mode exports unlabeled lanes with `label=unknown`
- optional mode skips unlabeled lanes entirely

These exports are additive and do not overwrite the existing review CSV semantics.

---

## 10. Reset Behavior

The left sidebar now provides two related operations:

### 从已保存结果全局刷新

- 重新同步左侧列表、当前图、category 常用项
- 当前图如有未保存修改，会先提示确认
- 刷新后会保留当前后端临时导入会话，但会丢弃前端未保存修改

### 重置

点击 `重置` 后可选择：

- `重置当前图为自动结果`
- `重置所有图为自动结果`

规则：
- 当前图重置只影响当前图
- 当前图重置会同时清除该图的 reviewed 结果和该图的临时导入训练 CSV 会话数据
- 所有图重置会清除全部 reviewed 结果，并清除当前导入训练 CSV 会话
- 重置后，页面会重新显示 automatic v6 geometry

---

## 11. Current Automatic Baseline

The Web tool is currently wired to **v6** automatic outputs.

This means the automatic baseline comes from files under:

- `outputs/lane_segmentation/lane_roi_boundaries_v6/`
- `outputs/lane_segmentation/overlays/roi_boundaries_v6/`

If the displayed result seems different from expected automatic geometry, first check whether reviewed rows already exist for that image.

---

## 12. FastAPI Routes

## `GET /`
Returns the static review page.

## `GET /api/images`
Returns sidebar image list data.

Typical fields:

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
Returns the full payload for one image.

Top-level payload sections:

- `image`
- `roi`
- `boundaries`
- `boundary_source`
- `manifest`
- `review`
- `overlay`
- `annotation`

### Example boundary fields

Each boundary contains values like:

- `candidate_index`
- `left_x`
- `right_x`
- `center_x`
- `estimated_width`
- `status`
- `source`
- `confidence`
- `auto_left_x`
- `auto_right_x`
- `auto_center_x`
- `auto_estimated_width`
- `auto_status`
- `is_manual_added`
- `annotation.category`

## `GET /api/images/{image_id}/raw`
Returns the raw source image file.

## `POST /api/images/{image_id}/review`
Saves reviewed geometry and optional lane annotation.

### Important request fields

- `y_start`
- `y_end`
- `boundaries[]`
- `annotation.enabled`
- `annotation.lanes[]`
- `write_annotation_csv`
- `write_annotation_jsonl`
- `review_status`
- `notes`

### Boundary request fields

Each boundary row typically includes:

- `candidate_index`
- `left_x`
- `right_x`
- `status`
- `notes`
- `source`
- `confidence`
- `auto_left_x`
- `auto_right_x`
- `auto_center_x`
- `auto_estimated_width`
- `auto_status`
- `is_manual_added`

### Annotation request shape

```json
{
  "enabled": true,
  "lanes": [
    {
      "candidate_index": 7,
      "category": "MZ"
    }
  ]
}
```

## `POST /api/reload`
Reloads current CSV state into the backend repository without rerunning automatic segmentation.

## `POST /api/dataset/update`
Runs the dataset refresh pipeline used by the `更新数据集` button.

Typical response fields:

- `image_count`
- `added_quality_rows`
- `script_count`
- `scripts`

## `POST /api/images/{image_id}/reset`
Resets reviewed data for one image.

## `GET /api/categories`
Returns category suggestions.

### Response shape

```json
{
  "categories": ["M", "MZ", "SZ"]
}
```

## `POST /api/categories`
Adds a suggestion.

### Request shape

```json
{
  "category": "ZZ"
}
```

## `DELETE /api/categories/{category}`
Deletes a suggestion and returns the updated list.

---

## 13. Common Troubleshooting

## The page still shows old UI

Use:

- `Ctrl + F5`

The browser may still be using an old cached `app.js` or `style.css`.

## Hover does not highlight the lane

Check whether the current `app.js` still uses coordinate-based hover detection in `handleOverlayMouseMove()`.

## Boundaries look wrong

Possible reasons:

1. the image already has reviewed geometry rows
2. the ROI or lane boundaries were edited and saved previously
3. the current source is reviewed output rather than automatic v6

Try the reset action on that image if you want to inspect the automatic baseline again.

## Annotation export looks incomplete

Blank category lanes are intentionally omitted from CSV/JSONL export.

## Category suggestions are missing

Check:

- whether `category_suggestions.txt` exists
- whether categories were added through the modal

## Preview zoom changed the display but not export coordinates

This is expected. Preview zoom is visual only.

---

## 14. Human Usage Notes

This tool is best used after automatic segmentation has reached a visually usable baseline.

Recommended discipline:

- do not use the Web tool to hide segmentation problems; record them
- keep reviewed outputs separate from automatic outputs
- use lane category annotation only when the geometry looks trustworthy
- if a UI change is requested later, preserve existing working behavior unless explicitly replaced

---

## 15. What a New AI Should Read Next

If a fresh AI opens this project and wants to work on the Web tool, it should read:

1. `docs/web_review_tool_development_guide.md`
2. this file
3. `Web/paths.py`
4. `Web/static/app.js`
5. `Web/review_store.py`
6. `plan.md`

That order gives enough context to understand both usage and implementation constraints.
