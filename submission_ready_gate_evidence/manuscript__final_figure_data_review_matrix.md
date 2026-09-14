# Final Figure/Data Review Matrix

Use `manuscript\final_figure_data_review_matrix.json` to record the final
per-artifact review for every manuscript figure, embedded image, source-data
table, generated raster, and packaged figure artifact.

After the automated audits run, `manuscript\final_figure_data_review_matrix_template.json`
can be generated from available inventory and package logs. Use that file as a
drafting aid for `required_artifacts`; the reviewer remains responsible for
confirming that the final matrix is complete.

Set the matrix to submission-ready only when every row is complete:

```json
"status": "ready_for_submission"
```

Each row should include:

- `artifact_id`: stable label, for example `Figure 1`, `Figure 4 source data`, or `Figure 5 raster`
- `artifact_type`: one of `figure`, `embedded_image`, `source_data_table`, `generated_raster`, `package_artifact`
- `status`: `pass`, `accepted_non_blocking`, or `not_applicable`
- `evidence`: concrete evidence such as an audit log, rendered page, source-data table, or package path
- `notes`: required for accepted non-blocking or not-applicable rows

Before completing `rows`, list every artifact that must be reviewed in
`required_artifacts`. Each required artifact should include:

- `artifact_id`: the same stable label used by the matching row
- `artifact_type`: one of the allowed artifact types
- `evidence`: why this artifact is required, such as the manuscript citation,
  figure inventory entry, source-data audit record, or package manifest entry

Coverage is checked by the pair `artifact_type` + `artifact_id`. This allows a
rendered figure and its source-data table to share a human-readable figure label
when needed, while still being reviewed as separate artifacts.

Required row flags:

- `caption_matches_rendered_artifact`
- `rendered_artifact_checked`
- `source_data_checked`
- `numeric_sanity_checked`
- `visual_quality_checked`
- `package_artifact_checked`
- `issue_register_cross_checked`

The matrix should be completed before the issue register and final figure/data
sign-off. Any defect found while filling the matrix should be recorded in
`manuscript\final_figure_data_issue_register.json`.
