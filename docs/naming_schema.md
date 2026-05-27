# Naming and ID Schema

## Raw image IDs

- Raw gel images are never renamed or modified.
- Each raw image receives a stable `image_id` in `dataset/metadata/image_inventory.csv`.
- `image_id` values are assigned by sorting raw image filenames lexicographically and numbering from `IMG_0001`.
- Example: the first sorted raw filename is assigned `IMG_0001`.

## Image inventory fields

| Field | Meaning |
|---|---|
| `image_id` | Stable project ID for one raw gel image. |
| `source_filename` | Original raw filename exactly as stored in `dataset/Originial/`. |
| `relative_path` | Path to the raw file relative to the project root. |
| `file_ext` | Lowercase file extension. |
| `width` | Image width in pixels. |
| `height` | Image height in pixels. |
| `channels` | Number of channels inferred from the image mode. |
| `gel_date_raw` | Date-like prefix parsed from the filename when available. |
| `gel_date_iso` | Parsed ISO date (`YYYY-MM-DD`) when valid. |
| `notes` | Inventory notes such as date parsing issues. |

## Lane indices and lane IDs

- `lane_index` is the visible bottom lane number when a gel image has readable bottom numbering.
- If bottom numbering is missing, unclear, or unusable, `lane_index` is assigned from the left-to-right visible lane order within the parent gel image.
- Bottom lane numbers in gel images are lane indices only. They are not patient IDs, sample IDs, or phenotype labels.
- `lane_index` values map to the physical lane order in the image, usually `1`, `2`, `3`, etc. from left to right.
- `lane_id` values should use `IMG_0001_L01`, `IMG_0001_L02`, etc., assigned from the `lane_index` within each parent image.
- `sample_id` remains `unknown` unless later expert or clinical metadata provides a real patient/sample identifier.
- `phenotype_label` remains `unknown` unless later expert or clinical metadata provides a phenotype interpretation.

## Future derived outputs

- Processed image outputs should include the parent `image_id` in the filename.
- Lane crop and annotation files should preserve traceability to the parent `image_id`, `lane_index`, and `lane_id`.
