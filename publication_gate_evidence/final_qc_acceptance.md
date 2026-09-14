# Final QC Acceptance Record

Use this record only for non-blocking audit notes that require human confirmation, such as SVG manual review notices or figure content reaching the canvas edge. Do not use this record to override audit errors or warnings. Errors and warnings must be resolved in the manuscript, figures, source data, or package before the publication gate can pass.

The machine-readable acceptance record is `manuscript/final_qc_acceptance.json`. Each accepted note must include the audit file, item text, reviewer, review date, decision, and justification.

Example entry:

```json
{
  "audit": "logs/figure_visual_quality_audit.json",
  "item": "Figure 2: image content reaches the canvas edge; visually confirm it is intentional and not clipped.",
  "reviewer": "Author name",
  "review_date": "2026-06-01",
  "decision": "accepted",
  "justification": "The map frame intentionally fills the canvas and all axis labels remain visible."
}
```
