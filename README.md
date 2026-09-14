# Process-Terrain Coastal Flood Screening

This repository contains the local analysis workflow, manuscript package, figures and audit material for a process-terrain coastal flood screening study.

**Public repository:** <https://github.com/Coucou2016/20260522-coastal-flood-scientific-data>

For independent review, begin with the manuscript, the scientific-integrity
review, and the external-review resolution matrix:

- `paper.html` or `paper.pdf`
- `manuscript/scientific_integrity_review.md`
- `manuscript/external_review_resolution.md`
- `major_revision_manifest.json`
- `DATA_AVAILABILITY.md`

## Study Scope

The project compares physically distinct coastal-flood diagnostics across a frozen Northwest European station inventory:

- GSSR reconstructed daily surge residuals
- COAST-RP storm-tide return levels
- Open-Meteo ERA5-derived meteorological drivers
- DeltaDTM coastal terrain windows

The manuscript tests whether storm-tide magnitude recovers rankings produced by static connected-lowland response. The supported conclusion is weak concordance and non-interchangeability, not predictive complementarity. DeltaDTM outputs are interpreted as static terrain classifications, not hydrodynamic flood forecasts.

## Frozen Major-Revision Rebuild

Run the current manuscript, source-table, figure and document workflow with:

```powershell
python scripts/run_major_revision_rebuild.py
```

The command rebuilds the mask-aware terrain diagnostics, frozen 68-station analysis, national/local DTM product-and-datum cross-check, SciencePlots figures, manuscript, Supplementary Information, research report and scientific-integrity review. It then validates all standalone HTML files, runs the scientific contract tests and writes `major_revision_manifest.json` with output sizes and SHA-256 hashes.

This is the authoritative entry point for the current major revision. The older publication/finalization scripts are retained as historical workflow records and must not be used to regenerate the current manuscript package.

Build the credential-scanned reviewer archive after a successful rebuild with:

```powershell
python scripts/build_major_revision_package.py
```

The archive receipt is written to `major_revision_package_receipt.json`.

## Historical Entry Points

- Historical local handoff gate: `scripts/run_final_submission_handoff.cmd`
- Historical publication gate: `scripts/run_publication_gate.cmd`
- Historical package finalization: `scripts/run_finalization.cmd`
- Publication requirements installer: `scripts/install_publication_requirements.cmd`

The final package is written to `publication_package/` and `publication_package.zip`. Archive metadata are recorded in `final_archive_manifest.json`.

## Manuscript and Figures

- Main manuscript Markdown: `manuscript/process_terrain_coastal_flood_CEE_manuscript.md`
- Standalone review HTML: `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`
- Main figures: `figures/main/`
- Figure and table source data: `data/figure_source/`

## Environment

Use `requirements-publication.txt` for the publication gate environment. The workflow expects Python plus the scientific/geospatial stack listed there, including NumPy, Pandas, Matplotlib, Pillow and Rasterio.

## Deposit Notes

The compact publication package is intended for repository deposit with the manuscript source tables, figures, audit reports and key scripts. Large upstream raw products should be cited through their original repositories and DOIs unless repository policy and upstream licenses support redistribution.

The public repository therefore includes all project-authored code, derived
data, source tables, figures, documents, logs and review evidence. Upstream raw
products and third-party reference PDFs are represented by source citations and
SHA-256 manifests rather than copied into Git. Credential-scanned archive
bundles are distributed through GitHub Releases. See `DATA_AVAILABILITY.md`.
