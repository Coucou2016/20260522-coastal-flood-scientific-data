# Final Figure/Data Issue Register

Use `manuscript\final_figure_data_issue_register.json` to record every figure,
source-data, generated-raster, or publication-package issue found during final
review.

Set the register to submission-ready only when all issues are closed:

```json
"status": "ready_for_submission"
```

Required top-level fields:

- `reviewer`: the person who completed or verified the final review
- `last_updated`: ISO date, for example `2026-06-03`
- `issues`: every detected issue, including resolved and accepted non-blocking issues
- `no_unresolved_issues_attestation`: final confirmation that no unresolved issue remains

Issue statuses:

- `resolved`: fixed and supported by evidence
- `accepted_non_blocking`: scientifically disclosed or immaterial; requires `acceptance_rationale`
- `not_applicable`: checked and determined not to apply

Severity rules:

- `critical` and `major` issues must be `resolved`
- `minor` issues may be `resolved` or `accepted_non_blocking`
- `note` issues may be `resolved`, `accepted_non_blocking`, or `not_applicable`

Examples of issues that must be recorded:

- missing, duplicated, out-of-order, clipped, blank, or illegible figure panels
- figure captions that do not match the rendered result
- source-data tables that cannot reproduce the plotted values
- suspicious NaN/Inf values, all-zero series, impossible ranges, or unit mismatches
- ocean-connectivity or lowland-elevation logic regressions in terrain-sensitivity outputs
- package artifacts that differ from the manuscript or final HTML
