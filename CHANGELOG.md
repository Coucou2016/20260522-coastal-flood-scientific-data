# Changelog

This log records the scientific and publication-facing states that can be
verified from the retained manifests and revision evidence. Older exploratory
scripts remain available for audit but are not authoritative entry points.

## 2026-09-05 - External-review major revision frozen

- Froze the primary station network at 68 stations passing the 6 km COAST-RP
  spatial-match rule.
- Standardized the primary terrain workflow to a 10 km window, an EGM2008
  `+2 m` terrain threshold, official DeltaDTM mask classes and 4-neighbour
  connectivity; retained 8-neighbour results as sensitivity analysis.
- Replaced the legacy composite interpretation with separate lowland
  prevalence, conditional connectivity and absolute connected-area metrics.
- Added RP2-RP100, spatial-sector, top-k null, station-influence, denominator,
  topology and match-distance diagnostics.
- Reframed `1/14` top-set overlap as a descriptive priority-list difference,
  not evidence of overlap below the spatial null expectation.
- Rebuilt Figures 1-4 and Supplementary Figures S1-S5 with SciencePlots and
  Times New Roman, and completed multi-pass visual inspection.
- Rebuilt the manuscript, Supplementary Information, Chinese research report
  and scientific-integrity review as self-contained HTML, Markdown and PDF.
- The authoritative ten-step rebuild completed with all steps successful and
  17 scientific contract tests passing.

## 2026-08-23 - Reproducibility package and reporting pass

- Generated the local reproducibility bundle, source-data package, standalone
  report and submission handoff evidence.
- Added data/code availability placeholders rather than fabricating repository
  metadata before public deposit.

## 2026-08-15 - Structured external review handoff

- Created versioned review packages and separate algorithm/statistics and
  manuscript/figure review briefs.
- Retained handoff records and package checksums under `external_review/`.

## Historical development

Earlier degree-window, 8-neighbour and focal-site workflows are retained only
as provenance. `scripts/run_major_revision_rebuild.py` is the sole authoritative
entry point for the current reported outputs.

