# Reviewer response preparation

This document prepares concise responses to likely reviewer questions. It should be updated after the finalization workflow has been run and exact line/figure/table references are available.

## Comment type 1. Are the data real, or were any values fabricated?

**Draft response.**  
All plotted numerical results are generated from public data products and local processing scripts. The workflow uses GSSR station surge-residual archives, the COAST-RP storm-tide return-level NetCDF file, Open-Meteo ERA5-derived historical meteorological data, and DeltaDTM GeoTIFF terrain tiles. No data were fabricated. The final manuscript package includes source CSV files for each main figure and publication table, a data dictionary, and an automated publication-readiness audit that checks cross-table consistency and source-file presence.

**Evidence to cite.**

- `data/figure_source/*.csv`
- `manuscript/figure_source_data_dictionary.md`
- `manuscript/publication_readiness_report.md`
- `scripts/audit_publication_readiness.py`

## Comment type 2. Why compare GSSR and COAST-RP if they are different quantities?

**Draft response.**  
The manuscript does not use one product to validate the other. GSSR and COAST-RP are intentionally kept physically distinct: GSSR represents reconstructed surge residuals, while COAST-RP represents storm-tide return levels. The difference metric `D10_m` is therefore interpreted as product-definition divergence and as a diagnostic of coastal setting, not as a model error.

**Evidence to cite.**

- Figure 2
- Table 2
- Methods section on GSSR/COAST-RP comparison
- `manuscript/claims_evidence_matrix.md`

## Comment type 3. Does Figure 4 show unrealistic enclosed flooding?

**Draft response.**  
The terrain screen was revised to exclude isolated low cells. A candidate cell is counted only if it is below the imposed perturbation level and connected by an eight-neighbour path to boundary water/no-data. Interior no-data components are not used as marine seeds unless connected to the map boundary. The audit checks that ocean-connected fractions are never greater than the corresponding non-connected bathtub fractions. The blue overlays in Figure 4 therefore represent ocean-connected static sensitivity, not unfiltered bathtub filling.

**Evidence to cite.**

- Figure 4 caption and legend
- `scripts/make_cee_refined_figures.py`, `flood_connected_mask()`
- `data/figure_source/Fig4_connected_terrain_sensitivity.csv`
- `scripts/audit_publication_readiness.py`

## Comment type 4. Why does Table 4 not use full-window median elevation?

**Draft response.**  
Station-centred terrain windows can include substantial upland and non-coastal terrain, and several DeltaDTM tiles contain upper-range capped values at 30 m. To avoid overinterpreting full-window terrain statistics, the manuscript reports median elevation within the coastal-lowland mask used by the sensitivity analysis. Full-window medians are retained only for audit, not as the main terrain interpretation.

**Evidence to cite.**

- Table 4
- Methods paragraph on DeltaDTM terrain screening
- `data/figure_source/Fig4_connected_terrain_sensitivity.csv`
- `manuscript/publication_readiness_audit.md`

## Comment type 5. Is the process-terrain typology statistically validated?

**Draft response.**  
No. The typology is a qualitative diagnostic synthesis for a small, deliberately selected site set. It is intended to clarify how water-level indicators, meteorological coherence and connected terrain sensitivity can align or decouple. The manuscript explicitly avoids treating it as a trained classifier or regional/global predictive model.

**Evidence to cite.**

- Figure 5
- Discussion and limitations
- `manuscript/claims_evidence_matrix.md`

## Comment type 6. Does the study estimate flood risk?

**Draft response.**  
No. The study screens susceptibility-related diagnostics, not risk. It does not include exposure, vulnerability, economic damages, local defence performance, hydrodynamic propagation, drainage, wave setup, river flow or compound-flood boundary conditions. The manuscript states that more detailed local modelling is required for operational flood-risk assessment.

**Evidence to cite.**

- Abstract and limitations
- Figure 4 caption
- Supplementary Note 8
