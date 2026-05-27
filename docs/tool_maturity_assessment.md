# Tool Maturity Assessment

## Summary

The AAT IEF Gel ROI/Lane Review Tool is usable as an internal research tool for human-in-the-loop segmentation review. It is not yet mature enough to be presented as a validated clinical or production system.

## Current Maturity Rating

| Dimension | Status | Notes |
|---|---|---|
| Core workflow | Good internal prototype | Image update, automatic v6 segmentation, review, annotation, and export form a working loop. |
| Installation | Moderate | `requirements.txt` and `start_web.bat` support reproducible setup on Windows. |
| Data governance | Needs institutional confirmation | Real gel images and reviewed outputs are intentionally excluded from Git. |
| Segmentation accuracy | Needs formal evaluation | v6 is useful as a baseline but requires visual review. |
| UI usability | Moderate | Local Web interface supports main review tasks, but error handling and onboarding can improve. |
| Testing | Limited | Unit tests cover inventory ID preservation and dataset refresh orchestration. |
| Documentation | Improving | README and policy docs exist, but end-user screenshots and troubleshooting can be expanded. |
| Clinical readiness | Not ready | No validated phenotype classification or clinical performance evidence. |

## Strengths

- Stable image ID workflow through `image_inventory.csv`
- Reproducible automatic segmentation pipeline
- Human-in-the-loop Web review surface
- Reviewed geometry and training export support
- Dataset update button reduces manual script-running errors
- Real data excluded from the clean submission package by default

## Main Gaps

- No formal segmentation benchmark table yet
- No gold-standard reviewed subset committed for test use
- No packaged installer or cross-platform launch scripts beyond Windows batch
- Limited automated tests for the Web UI
- Error messages are mostly technical
- No role-based access control or deployment model
- No clinical validation

## Recommended Use Today

Use this tool for:

- internal research annotation
- lane boundary correction
- generation of reviewed segmentation exports
- preparation of lane-level training/evaluation tables

Do not use it for:

- clinical diagnosis
- automated phenotype reporting without expert review
- public release of real patient or research images

## Suggested Next Milestones

1. Create a small approved demo dataset.
2. Add screenshots and a short user guide to the README.
3. Add smoke tests for FastAPI routes.
4. Add a reviewed gold-standard subset for segmentation evaluation.
5. Define quantitative lane detection and boundary metrics.
6. Add a changelog and version tag before sharing with external collaborators.

## Release Recommendation

For collaboration with a research institute, use a private GitHub repository first. Move to a public repository only after data governance, license, and demo-data questions are resolved.
