# AAT IEF Gel Image Dissertation Plan

## Context

This project follows the proposal topic: automated diagnosis of Alpha-1 Antitrypsin (AAT) phenotypes from isoelectric focusing (IEF) gel images. The original proposal aimed to combine lane/band segmentation, CNN/ViT phenotype classification, clinical validation, and a user interface. The current practical constraint changes the strategy: only 87 gel images are available and they are not labelled. Therefore the first deliverable should not be a fully supervised classifier. The project should first establish a reproducible image-processing pipeline for vertical patient-lane segmentation, then use the segmented lanes to create labels, measurements, baselines, and only then test whether learning-based classification is defensible.

The supervisor's suggested starting point is vertical lane segmentation. This plan ignores the proposal timeline and breaks the work into the smallest practical research and implementation units.

## Goal

Build a defensible dissertation project around a small, initially unlabelled AAT IEF gel dataset by producing:

1. a reproducible dataset inventory;
2. a vertical lane segmentation pipeline;
3. a manual annotation protocol for image/lane/phenotype labels;
4. quantitative evaluation of segmentation quality;
5. baseline phenotype analysis from segmented lanes;
6. optional lightweight classification experiments only if labels become sufficient;
7. dissertation-ready figures, tables, and evaluation evidence.

## Working Assumptions

- Data size: 87 unlabelled IEF gel images.
- Raw unlabelled dataset path: `dataset/Originial/`.
- Current raw file formats: 70 PNG, 10 JPG, and 7 BMP files.
- Initial technical focus: vertical patient-lane segmentation, not end-to-end phenotype classification.
- Main unit of analysis should become the lane, not the whole gel image.
- Phenotype classification is only valid after enough lane-level labels exist.
- Classical computer vision baselines are required because the dataset is too small for training large CNN/ViT models from scratch.
- Synthetic/generated data may be used for training or stress-testing, but it must be clearly separated from real data and never used as a substitute for real-data evaluation.

## Dataset ID and Metadata Schema

Bottom numbers in each gel image should be treated as lane indices, not patient IDs or phenotype labels. Each vertical lane usually corresponds to one sample/patient lane, but marker/control/reference lanes must be marked separately when identified.

Recommended IDs:

| Field | Meaning | Example |
|---|---|---|
| `image_id` | Stable ID for one raw gel image | `IMG_0001` |
| `source_filename` | Original filename | `03.10.2025.png` |
| `gel_date` | Date parsed from filename if reliable | `2025-10-03` |
| `lane_index` | Bottom lane number or left-to-right lane order | `1` to `18` |
| `lane_id` | Stable lane ID | `IMG_0001_L01` |
| `sample_id` | Real patient/sample identifier if later available | `unknown` initially |
| `is_patient_lane` | Whether lane is patient/sample lane | `unknown`, `yes`, `no` |
| `lane_role` | Lane type | `patient`, `control`, `marker`, `reference`, `unknown` |
| `phenotype_label` | Expert phenotype label if later available | `unknown`, `PiMM`, `PiMZ`, etc. |
| `label_confidence` | Confidence of phenotype label | `unknown`, `low`, `medium`, `high` |
| `segmentation_quality` | Manual quality review | `unreviewed`, `good`, `partial`, `failed` |
| `notes` | Free-text issues | tilt, faint bands, artifacts |

Minimum inventory tables:

1. `image_inventory.csv` — one row per raw image.
2. `lane_inventory.csv` — one row per detected/cropped lane.
3. `lane_review.csv` — manual review and correction status.

## Candidate Image Processing Strategies

Use no more than three lane-segmentation strategies for comparison. The first method should be the default baseline.

| Option | Method | Best For | Main Risk | Comparison Output |
|---|---|---|---|---|
| A | Manual/automatic gel crop + grayscale invert + smoothed x-axis projection + peak detection | Clean cropped gels with clear vertical lanes | Text, bottom numbers, or borders may affect projection | Lane centers, overlays, crop quality, precision/recall |
| B | Gel crop + purple-signal extraction + smoothed x-axis projection + peak detection | Images where purple bands should be separated from black text or grey background | Colour variation may weaken faint bands | Same metrics as A plus failure comparison |
| C | Gel crop + adaptive threshold/morphology + connected vertical-region analysis | Noisier images with uneven background or strong artifacts | May merge adjacent lanes or split one lane into multiple regions | Same metrics as A/B plus false merge/split count |

Do not use SAM/SAM2 as the main method unless these baselines fail. SAM-style foundation models can be kept as optional comparison or future work because IEF lanes are structured repeated signal regions rather than natural object boundaries.

Recommended first implementation order:

1. Implement Option A on 5 representative images.
2. Add Option B if black text, labels, or background interfere with grayscale projection.
3. Add Option C only for images where projection-based methods fail.
4. Compare all attempted methods using the same reviewed subset and choose the simplest reliable pipeline.

## Phase 1: Project and Data Grounding

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 1.1 | done | Create project folder structure | `data/`, `notebooks/`, `src/`, `outputs/`, `docs/` structure | Empty but named directories exist and purpose is clear |
| 1.2 | done | Copy or reference raw images | Raw image location documented: `dataset/Originial/` | All 87 images are reachable without modifying originals |
| 1.3 | done | Build image inventory | CSV with image id, filename, dimensions, format, notes | Every image has one row |
| 1.4 | done | Inspect image quality | Visual notes on blur, rotation, contrast, artifacts | Problematic images are flagged |
| 1.5 | pending | Define dataset split strategy | Split policy document | Strategy avoids leakage between lanes from same gel image |
| 1.6 | done | Define naming convention and ID schema | File naming rules plus image/lane ID schema | Raw image, processed image, lane crop, annotation names and IDs are consistent |

## Phase 2: Literature and Method Scope Refinement

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 2.1 | pending | Extract proposal claims | Short notes from proposal | Aim, objectives, risks, and proposed methods are summarized |
| 2.2 | pending | Review AAT IEF interpretation | Notes on phenotype bands and lane patterns | M/M2/M4/M6/M7/M8 or relevant band references are understood |
| 2.3 | pending | Review gel lane segmentation methods | Method comparison notes | Classical projection, thresholding, active contours, U-Net/SAM are compared |
| 2.4 | pending | Decide reduced dissertation scope | Scope statement | Scope explains why lane segmentation comes before classification |
| 2.5 | pending | Define evaluation questions | Research questions | Questions are answerable with 87 unlabelled images plus manual annotation |

Recommended research questions:

1. Can vertical patient lanes be segmented reliably from AAT IEF gel images using classical or prompt-based computer vision methods?
2. What preprocessing steps improve lane segmentation robustness under staining, tilt, and background variation?
3. After lane segmentation, can lane-level band intensity profiles support phenotype annotation or baseline classification?
4. What are the limitations of supervised deep learning when only 87 initially unlabelled images are available?

## Phase 3: Preprocessing Pipeline

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 3.1 | done | Load images reproducibly | Image loading function/script | All formats load with consistent RGB/grayscale handling |
| 3.2 | done | Convert to grayscale | Grayscale output examples | Band contrast is preserved |
| 3.3 | pending | Normalize image size or resolution | Normalized copies or transform metadata | Processing is consistent across images |
| 3.4 | pending | Estimate gel region | Gel bounding box candidates | Background margins are removed where possible |
| 3.5 | pending | Correct rotation/tilt | Deskewed examples | Vertical lanes become approximately vertical |
| 3.6 | pending | Improve contrast | Contrast-enhanced examples | Faint lanes/bands become more visible without destroying strong bands |
| 3.7 | pending | Denoise images | Denoised examples | Noise reduced while band edges remain visible |
| 3.8 | pending | Save preprocessing parameters | Config file | Same image produces same processed output |

## Phase 4: Vertical Lane Segmentation Baseline

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 4.1 | done | Compute vertical intensity projection | Projection plots for Option A and, if needed, Option B | Each image has x-axis intensity profile |
| 4.2 | done | Detect lane centers | v4 high-sensitivity band-region projection completed and tested; v3 conditional fallback remains previous baseline | Visible lane centers are marked on sample images; faint full-layout lanes improve without reintroducing low-lane-count over-segmentation |
| 4.3 | done | Estimate lane width | v5 standalone adaptive boundary estimates and overlays | Boundary overlays exist for all 87 images and remain visually reviewable before cropping |
| 4.4 | pending | Crop lane candidates | Lane crop images with stable `lane_id` values | Each detected lane is saved with parent image id |
| 4.5 | done | Overlay segmentation result | Diagnostic overlay figures for each method option tested | Lane boxes are drawn on original images |
| 4.6 | pending | Handle variable lane counts | Lane count logic using bottom numbers when visible and left-to-right order otherwise | Images with different numbers of lanes are not forced into one fixed count |
| 4.7 | pending | Handle marker/control lanes | Metadata flag in `lane_inventory.csv` | Non-patient/reference lanes can be excluded or labelled separately |
| 4.8 | pending | Record failures | Failure log by method option | Missed, merged, or false lanes are documented |
| 4.9 | pending | Compare lane segmentation options | Method comparison table | No more than three methods are compared and the final pipeline is justified |

## Current Segmentation Development Notes

- Current baseline: Option A grayscale inversion vertical projection has been generated for all 87 images.
- v1 visual diagnostic: original-image overlays are available under `outputs/lane_segmentation/overlays/centerlines/`.
- User review of v1 overlays: detected lane positions are generally acceptable where found, but coverage is insufficient; faint/weak lanes are often missed.
- v2 coverage-improved lane center detection is complete and tested. Outputs are versioned under `outputs/lane_segmentation/lane_centers_v2/` and `outputs/lane_segmentation/overlays/centerlines_v2/`.
- v2 summary: 1,558 candidate centers across 87 images; center counts range from 16 to 21 per image; 1,152 direct `detected_peak` candidates and 406 `coverage_fallback` candidates.
- v2 comparison: coverage increased for all 87 images. For IMG_0001 to IMG_0005, center-count deltas are +4, +17, +12, +7, and +10.
- v2 user review: several high-risk images actually contain only a few visible lanes, but v2 over-infers many extra lane centers because the fallback pushes toward the common ~18-lane layout.
- v3 lane center detection is complete and tested. Outputs are versioned under `outputs/lane_segmentation/lane_centers_v3/` and `outputs/lane_segmentation/overlays/centerlines_v3/`.
- v3 changes: conditional 18-lane fallback, `dataset/metadata/lane_count_review.csv` manual expected lane count override table, and candidate `source`/`confidence`/`status` grading.
- v3 summary: 1,354 candidate rows across 87 images; 1,178 accepted candidates; fallback blocked on 22 images; v3 reduced accepted center counts for 73 images and increased none compared with v2.
- High-risk v2 to v3 reductions: IMG_0023 17→3, IMG_0024 17→3, IMG_0025 18→4, IMG_0032 17→3, IMG_0056 18→5, IMG_0057 17→3, IMG_0064 18→5, IMG_0087 17→9.
- v4 high-sensitivity lane center detection is complete and tested. Outputs are versioned under `outputs/lane_segmentation/lane_centers_v4/` and `outputs/lane_segmentation/overlays/centerlines_v4/`.
- v5 adaptive lane boundary detection is complete and lightly validated. Outputs are versioned under `outputs/lane_segmentation/lane_boundaries_v5/` and `outputs/lane_segmentation/overlays/boundaries_v5/`.
- v5 changes: standalone detector using raw/shared inputs, v4-style center detection logic, adaptive valley/gradient boundary estimates around centers, and yellow overlay spans representing estimated lane coverage rather than fixed guide bands.
- v5 summary: 1,417 boundary candidate rows across 87 images; 1,312 accepted boundaries; 87 overlays; optional v4-v5 comparison changed accepted counts for 0 images, meaning v5 keeps v4 center counts while adding adaptive left/right boundaries.
- v5 target review examples: IMG_0017 has 11 accepted boundaries with median estimated width 28 px, IMG_0025 has 3 accepted boundaries with median width 30 px, and IMG_0048 has 13 accepted boundaries with median width 27 px.
- v5 user review: IMG_0017 still misses a middle lane around the annotated central region; IMG_0025 splits the first visible lane into two detections; IMG_0048 produces many false detections because side annotations, QC box, page marks, and other contamination are included in the analysis area.
- v5.1 recommended direction: add gel-content ROI/artifact masking first, then add duplicate-center merge and local gap-fill logic; do not move to lane crops until these visual failures are addressed.
- v5 standalone rule: the main v5 workflow does not require v4 outputs; v4 is read only for optional comparison if present.
- v4 changes: standalone detector using raw/shared inputs, multi-band-region projection, preserved v3 safeguards, manual expected-count override support, confidence/status grading, and high-risk accepted-count caps.
- v4 summary: 1,417 candidate rows across 87 images; 1,312 accepted candidates; 87 overlays; 50 images increased accepted counts versus v3; high-risk accepted counts remain capped.
- v4 target improvements: IMG_0002 9→16, IMG_0009 9→16, IMG_0017 8→11 accepted centers compared with v3.
- v4 high-risk safeguards: IMG_0023=6, IMG_0024=3, IMG_0025=3, IMG_0032=3, IMG_0056=5, IMG_0057=5, IMG_0064=6, IMG_0087=6 accepted centers; none return to v2-like high counts.
- Known caution: all v4 detections remain diagnostic lane-center candidates, not final boundaries. Manual visual review is still required before cropping, especially for weak, fallback, review-only, or high-risk candidates.
- Versioning rule: keep v1/v2/v3/v4 outputs intact; do not overwrite previous versions when tuning future variants.
- Next resume point: visually review v5 boundary overlays for IMG_0017, IMG_0025, IMG_0048, IMG_0002, IMG_0009, and high-risk images before deciding whether to tune boundary width further or proceed to `4.4` lane crops.
- v6 horizontal ROI-aware adaptive lane boundary detection is complete and lightly validated. Outputs are versioned under `outputs/lane_segmentation/lane_roi_boundaries_v6/` and `outputs/lane_segmentation/overlays/roi_boundaries_v6/`.
- v6 changes: standalone detector using raw/shared inputs, one shared horizontal `y_start`/`y_end` ROI per image, ROI-limited lane-center/boundary projections, preserved v5 high-risk/manual-count safeguards, and green/yellow original-image overlays clipped to the ROI.
- v6 summary: 1,414 boundary candidate rows across 87 images; 1,299 accepted boundaries; 87 horizontal ROI rows; 87 overlays; no per-image shared-y violations in candidate rows; optional v5-v6 comparison changed accepted counts for 24 images.
- v6 target sanity checks: IMG_0017 ROI 33-252 with 12 accepted boundaries, IMG_0023 ROI 45-181 with 6 accepted boundaries, IMG_0041 ROI 372-1114 with 13 accepted boundaries, IMG_0048 ROI 88-236 with 12 accepted boundaries, IMG_0087 ROI 93-270 with 6 accepted boundaries, IMG_0025 ROI 180-463 with 2 accepted boundaries.
- v6 user review: many horizontal ROI failures are caused by vertical placement rather than lane-center logic. Common pattern: ROI starts too high and includes header/slide text while missing lower band information (examples include IMG_0019, IMG_0016, IMG_0013); opposite pattern also exists where upper band information is excluded or compressed by a too-low/top-truncated ROI (example IMG_0044).
- v6.1 rewritten in-place after user rejection of the first v6.1 logic. Outputs remain under `outputs/lane_segmentation/lane_roi_boundaries_v6_1/` and `outputs/lane_segmentation/overlays/roi_boundaries_v6_1/`; v6 outputs were not modified.
- rewritten v6.1 changes: starts from v6-style broad ROI, aggregates within-image lane-like vertical evidence to refine one shared `y_start`/`y_end`, strengthens lower-half retention, applies conservative bottom guard against lane-number rows, and falls back to the broad v6-style ROI if refinement is too thin or low-overlap.
- rewritten v6.1 summary: 1,417 boundary candidate rows across 87 images; 1,312 accepted boundaries; 87 horizontal ROI rows; 87 overlays; no per-image shared-y violations in candidate rows; optional v6-v6.1 comparison changed accepted counts for 3 images.
- rewritten v6.1 target sanity checks: IMG_0004 ROI 167-433 with 16 accepted boundaries, IMG_0009 ROI 59-489 with 15 accepted boundaries, IMG_0019 ROI 59-475 with 14 accepted boundaries, IMG_0013 ROI 58-508 with 17 accepted boundaries, IMG_0016 ROI 114-654 with 18 accepted boundaries, IMG_0044 ROI 156-365 with 15 accepted boundaries, IMG_0048 ROI 88-236 with 12 accepted boundaries, IMG_0023 ROI 45-181 with 6 accepted boundaries, IMG_0087 ROI 93-270 with 6 accepted boundaries.
- rewritten v6.1 is a candidate replacement for the rejected v6.1, but overlays still require visual review before lane crops/classification.
- Current Web review workflow status: the local review app under `Web/` is now the active human-in-the-loop review surface for segmentation correction and lane-level training annotation. It is wired to automatic `v6` inputs, writes reviewed geometry to `Web/review_exports/`, supports lane-level category annotation export to CSV/JSONL, and should be treated as part of the dissertation evidence pipeline rather than a temporary demo.

## Phase 5: Manual Annotation Protocol

Manual annotation in this project includes a lightweight ROI/lane review web tool plus reviewed CSV exports. The web tool is part of the segmentation review workflow, not a separate standalone product track.

Current implementation note: the Web tool now exists as a local FastAPI + static HTML/CSS/JS review app wired to the automatic **v6** segmentation baseline. It already supports reviewed ROI/boundary save/reset, lane-level category annotation, CSV/JSONL annotation export, hover highlight, modal-based single-lane review, category suggestions, and lane deletion within the annotation modal. Future work in this phase should treat the tool as an existing maintained component rather than a greenfield placeholder.

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 5.1 | pending | Define annotation levels | Annotation schema | Image-level, lane-level, and band-level fields are defined |
| 5.2 | done | Build ROI/lane review web tool | Local review app | Users can open an image, see automatic overlays, and drag shared ROI and lane boundaries |
| 5.3 | done | Export reviewed geometry | Review CSV/manifests | Corrected ROI/lane geometry is saved separately from automatic outputs and can be reloaded |
| 5.4 | pending | Manually review and correct segmentation | Reviewed geometry set | Each image is checked and marked corrected, accepted, partial, false positive, or missed as appropriate |
| 5.5 | pending | Ask expert for phenotype labels if possible | Expert label table | At least a subset of lanes has phenotype labels |
| 5.6 | pending | Define uncertain label policy | Label confidence rules | Ambiguous lanes are not forced into hard labels |
| 5.7 | pending | Create gold-standard subset | Curated subset | A small high-confidence subset exists for evaluation |

## Phase 6: Segmentation Evaluation

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 6.1 | pending | Define segmentation metrics | Metric definitions | Detection precision/recall and boundary quality are specified |
| 6.2 | pending | Count lane detection outcomes | TP/FP/FN table | Each image has expected vs detected lane counts |
| 6.3 | pending | Measure crop quality | Quality scores | Crops are rated usable/not usable or scored ordinally |
| 6.4 | pending | Analyze failure cases | Failure taxonomy | Common failure causes are grouped: tilt, low contrast, overlapping lanes, artifacts |
| 6.5 | pending | Compare preprocessing variants | Results table | At least two preprocessing settings are compared |
| 6.6 | pending | Select final segmentation pipeline | Final method choice | Chosen method is justified by metrics and examples |

## Phase 7: Lane-Level Band/Profile Analysis

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 7.1 | pending | Normalize lane crop height | Standardized lane crops | Lanes can be compared vertically |
| 7.2 | pending | Compute horizontal intensity profile per lane | Profile plots | Each lane has y-axis band intensity curve |
| 7.3 | pending | Detect band peaks | Peak coordinates | Major bands are identified in example lanes |
| 7.4 | pending | Align bands to reference levels | Band alignment method | Approximate M2/M4/M6/M7/M8 positions are comparable |
| 7.5 | pending | Extract lane features | Feature table | Peak count, peak positions, intensity ratios, spacing features exist |
| 7.6 | pending | Visualize phenotype-like patterns | Figures | Example profiles show interpretable differences |
| 7.7 | pending | Document limitations | Limitation notes | Cases where profiles fail are described |

## Phase 8: Synthetic / Generated Data Workflow

Synthetic data may be useful for training lane segmentation models, stress-testing preprocessing, balancing rare phenotype-like patterns, or prototyping classifiers. It must be treated as an auxiliary training resource, not as real clinical evidence.

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 8.1 | pending | Define synthetic data purpose | Synthetic data scope note | It is clear whether generated data supports segmentation, band/profile analysis, or classification |
| 8.2 | pending | Separate real and generated data storage | Data directory policy | Synthetic files cannot be confused with real patient gel images |
| 8.3 | pending | Design generation method | Generation protocol | Method documents source, assumptions, labels, and controllable parameters |
| 8.4 | pending | Generate pilot synthetic samples | Pilot generated dataset | Small sample set exists with metadata and visual inspection notes |
| 8.5 | pending | Validate visual plausibility | Plausibility review table | Generated images/lanes are reviewed against real examples and failure cases are recorded |
| 8.6 | pending | Define synthetic labels and metadata | Synthetic metadata table | Every generated sample has known generation parameters and label provenance |
| 8.7 | pending | Train only with explicit synthetic flag | Training config | Experiments clearly state whether synthetic data is used |
| 8.8 | pending | Evaluate on real data only | Real-data evaluation results | Final reported performance is measured on real held-out or reviewed real data |
| 8.9 | pending | Compare real-only vs synthetic-assisted training | Comparison table | Benefit or harm of synthetic data is quantified |
| 8.10 | pending | Document synthetic data limitations | Dissertation notes | The thesis clearly states synthetic data cannot replace expert-labelled clinical data |

## Phase 9: Classification Feasibility Check

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 9.1 | pending | Count available labels | Label summary | Number of labelled lanes per class is known |
| 9.2 | pending | Decide if supervised classification is valid | Go/no-go decision | Classification only proceeds if labels are sufficient |
| 9.3 | pending | Build non-deep baseline if labels exist | Baseline model results | Logistic regression, SVM, kNN, or random forest tested on extracted features |
| 9.4 | pending | Use cross-validation carefully | CV results | Splits keep lanes from same gel together |
| 9.5 | pending | Report uncertainty | Confidence intervals or caveats | Small-data limitations are explicit |
| 9.6 | pending | Avoid overclaiming CNN/ViT | Dissertation justification | Deep learning is framed as future work unless data supports it |

Optional only if enough labels exist:

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 9.7 | pending | Test transfer learning CNN | Small experiment | Frozen-pretrained model compared to feature baseline |
| 9.8 | pending | Test augmentation sensitivity | Augmentation results | Shows whether augmentation helps or destabilizes results |
| 9.9 | pending | Compare against feature baseline | Comparison table | Deep model must beat simple baseline to be worth discussing as result |

## Phase 10: Explainability and Clinical Interpretability

| ID | Status | Task | Output | Done Criteria |
|---|---|---|---|---|
| 10.1 | pending | Link features to bands | Interpretation table | Extracted features correspond to visible bands/levels |
| 10.2 | pending | Create annotated visual examples | Figure panels | Original image, lane boxes, crop, profile, detected peaks shown together |
| 10.3 | pending | Document human-in-the-loop workflow | Workflow diagram/text | Expert validation remains part of proposed clinical use |
| 10.4 | pending | Discuss edge cases | Examples and notes | Ambiguous or low-quality lanes are shown, not hidden |

## Phase 11: Dissertation Writing Plan

| ID | Status | Chapter/Section | Required Evidence | Done Criteria |
|---|---|---|---|---|
| 11.1 | pending | Introduction | AATD motivation, IEF diagnostic context | Problem and contribution are clear |
| 11.2 | pending | Literature Review | AAT phenotyping, gel image analysis, segmentation, small-data ML | Methods are positioned realistically |
| 11.3 | pending | Dataset | 87-image inventory, ethical/de-identification notes | Dataset limitations are transparent |
| 11.4 | pending | Methodology | Preprocessing, lane segmentation, annotation, profile extraction, synthetic data protocol if used | Pipeline is reproducible |
| 11.5 | pending | Experiments | Segmentation evaluation, synthetic-assisted comparisons if used, and optional classification | Experiments match available data |
| 11.6 | pending | Results | Metrics, figures, failure analysis, real-only vs synthetic-assisted comparison if used | Claims are supported by evidence |
| 11.7 | pending | Discussion | Clinical relevance, limitations, synthetic data caveats, future work | No overclaiming beyond data |
| 11.8 | pending | Conclusion | Summary of achieved pipeline and feasibility | Contribution is defensible |

## Critical Path

```text
Image inventory
  -> preprocessing
  -> vertical lane segmentation
  -> manual lane validation
  -> segmentation evaluation
  -> lane profile extraction
  -> optional synthetic data generation protocol
  -> label feasibility check
  -> optional classifier
  -> dissertation results and discussion
```

## Main Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Images are unlabelled | High | Start with segmentation and annotation workflow; avoid promising classifier first |
| 87 images are too few for deep learning | High | Use classical CV, feature baselines, and carefully controlled synthetic data only as training support |
| Synthetic data creates unrealistic patterns | High | Validate generated samples visually and evaluate final claims on real data only |
| Synthetic data contaminates evaluation | High | Keep generated data in separate folders and never include it in final real-data test sets |
| Lane segmentation fails on tilted/noisy gels | Medium | Add deskewing, contrast normalization, failure taxonomy, and manual correction option |
| Phenotype labels are unavailable | High | Evaluate segmentation and profile extraction independently; request expert labels for subset |
| Lanes from same gel leak across train/test | High | Split by parent image, not by lane crop |
| Ambiguous rare variants | Medium | Use confidence labels and exclude uncertain cases from hard classification |
| Results look less ambitious than proposal | Medium | Frame contribution as robust small-data pipeline and feasibility study |

## Minimum Viable Dissertation Result

The minimum defensible outcome is:

1. all 87 images inventoried;
2. reproducible preprocessing pipeline implemented;
3. vertical lane segmentation attempted on every image;
4. manual validation of segmentation quality completed;
5. quantitative segmentation metrics reported;
6. lane crops and band intensity profiles generated;
7. if synthetic data is used, generation method, metadata, separation policy, and real-data-only evaluation are documented;
8. clear discussion of whether phenotype classification is feasible with current labels.

This is enough for a coherent dissertation even if supervised phenotype classification is not yet reliable.

## Stretch Goals

Only attempt these after the minimum result is complete:

1. expert phenotype labels for a subset of lanes;
2. synthetic lane or gel image generation for training support;
3. feature-based phenotype classifier;
4. transfer-learning CNN comparison;
5. SAM-assisted segmentation comparison;
6. simple review interface for lane crops and labels;
7. clinical-style report output for each gel image.

## Verification Plan

- Run the pipeline on a small subset of 5 images first.
- Check that preprocessing outputs are visually correct.
- Check that lane overlays align with visible vertical lanes.
- Confirm every lane crop has traceable metadata back to parent image.
- Manually review segmentation for all 87 images.
- Compute lane detection precision, recall, false positives, and false negatives on the reviewed subset.
- Generate profile plots for accepted lane crops.
- If synthetic data is used, verify generated data is stored separately, fully labelled as synthetic, and excluded from final real-data evaluation.
- If labels exist, run grouped cross-validation by parent gel image.
- Export final figures and tables for dissertation chapters.

## Immediate Next Actions

1. Locate the 87 raw images and record their folder path.
2. Create the project directory structure inside `AAT_Project`.
3. Build the image inventory CSV.
4. Implement or prototype preprocessing on 5 representative images.
5. Prototype vertical projection lane segmentation on those 5 images.
6. Review results with the supervisor before scaling to all 87 images.
