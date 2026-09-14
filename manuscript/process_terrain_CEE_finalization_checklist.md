# CEE manuscript finalization checklist

Use this checklist after every substantial manuscript or figure revision.

## Required finalization command

```powershell
python scripts\finalize_cee_publication_package.py
```

This command rebuilds the refined main figures, rebuilds the standalone review HTML, compiles key scripts, runs raw-data verification and runs the publication-readiness audit.
It also creates `publication_package/`, a compact manuscript archive containing the review HTML, manuscript Markdown, main figures, figure-source CSV files, key scripts and audit documents. A zipped copy is written to `publication_package.zip`.

## Required final outputs

- `manuscript/process_terrain_coastal_flood_CEE_manuscript.md`
- `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`
- `manuscript/publication_readiness_report.md`
- `figures/main/Fig1_process_terrain_design.png`
- `figures/main/Fig2_water_level_divergence.png`
- `figures/main/Fig3_meteorological_coherence.png`
- `figures/main/Fig4_deltadtm_terrain_sensitivity.png`
- `figures/main/Fig5_process_terrain_typology.png`
- `figures/main/Fig1_process_terrain_design.pdf`
- `figures/main/Fig2_water_level_divergence.pdf`
- `figures/main/Fig3_meteorological_coherence.pdf`
- `figures/main/Fig4_deltadtm_terrain_sensitivity.pdf`
- `figures/main/Fig5_process_terrain_typology.pdf`
- all corresponding source CSV files under `data/figure_source/`
- `publication_package/README.md`
- `publication_package/package_manifest.json`
- `publication_package.zip`

## Scientific gates

- GSSR, COAST-RP, Open-Meteo and DeltaDTM are read from real local files.
- The manuscript does not claim that GSSR validates COAST-RP or that COAST-RP validates GSSR.
- Figure 4 and Figure 5 use ocean-connected static sensitivity, not unfiltered bathtub flooding.
- Ocean-connected cells are seeded only by boundary water/no-data components.
- Table 4 and synthesis text use coastal-lowland median elevation, not capped full-window median elevation.
- Figure 5 is described as a qualitative diagnostic typology, not a trained classifier or regional statistical model.
- All figures have source data tables.
- The standalone HTML has no external image, CSS or JavaScript dependencies.

## Submission caveats still requiring human completion

- Public repository URL and DOI.
- Funding, acknowledgements and author contribution details.
- Journal-specific formatting, word limit and reference style.
- Optional external expert review of the connected-static terrain screening assumptions.
