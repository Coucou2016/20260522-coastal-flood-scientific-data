# Final Figure/Data Sign-off

Complete `manuscript\final_figure_data_signoff.json` only after the final
rendered manuscript and all figure/source-data artifacts have been reviewed
together.

Required status for submission:

```json
"status": "approved_for_submission"
```

Required review evidence should point to concrete artifacts, for example:

- `logs\manuscript_figure_inventory.md`
- `logs\figure_deliverables_audit.md`
- `logs\figure_visual_quality_audit.md`
- `logs\figure_data_integrity_audit.md`
- `logs\manual_figure_review_sheet.md`
- `logs\final_figure_data_review_matrix_audit.md`
- `logs\final_figure_data_issue_register_audit.md`
- final rendered manuscript pages or screenshots inspected by the reviewer
- source-data CSV/TIFF files checked for the corresponding figure

Do not approve the sign-off if any of the following remain unresolved:

- a manuscript figure is missing, duplicated, out of order, clipped, blank, or illegible
- a figure cannot be traced to its source-data table or generated raster
- numeric ranges show impossible values, unit mismatches, unintended all-zero columns, or NaN/Inf artifacts
- Figure 4 or Figure 5 terrain-sensitivity outputs use an unfiltered bathtub mask instead of ocean-connected flooding
- Table/Figure 5 terrain summaries use capped full-window elevation summaries instead of coastal-lowland elevation summaries
- any blocking issue is listed in `blocking_issues`

Accepted limitations may be listed only when they are scientifically disclosed,
non-blocking, and do not change the manuscript conclusions.
