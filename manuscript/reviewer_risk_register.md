# Reviewer risk register

This register lists likely reviewer concerns and the project artifact that should answer each concern. It is written as an internal final-check document, not as manuscript text.

## Risk 1. The analysis compares unlike water-level products

- **Concern:** GSSR surge residuals and COAST-RP storm-tide return levels are not physically equivalent.
- **Current handling:** The manuscript frames `D10_m` as product-definition divergence rather than validation error.
- **Evidence to retain:** `Fig2_water_level_divergence.csv`, Table 2, Figure 2 caption, and discussion language on physically distinct diagnostics.
- **Do not claim:** GSSR validates COAST-RP, COAST-RP validates GSSR, or the difference is a model error.

## Risk 2. Static terrain screen overstates inundation by filling isolated low cells

- **Concern:** A simple bathtub model can flood inland depressions disconnected from the sea.
- **Current handling:** Figure 4 and Figure 5 use an ocean-connected mask seeded only by boundary water/no-data components.
- **Evidence to retain:** `flood_connected_mask()` in `scripts/make_cee_refined_figures.py`; `Fig4_connected_terrain_sensitivity.csv`; publication-readiness audit result that connected fractions never exceed non-connected bathtub fractions.
- **Do not claim:** The blue areas are observed flood extents, hydrodynamic predictions, or defence-failure simulations.

## Risk 3. DeltaDTM 30 m cap affects terrain summary statistics

- **Concern:** Some full-window medians can equal 30 m because the product has upper-range capped terrain values.
- **Current handling:** Manuscript interpretation and Table 4 use `median_lowland_elev_m`, not full-window `median_elev_m`.
- **Evidence to retain:** Table 4, methods paragraph noting 30 m capping, and audit check that Table 4 does not expose capped full-window median elevation.
- **Do not claim:** Full-window median elevation characterizes coastal floodplain geometry.

## Risk 4. The typology is overinterpreted

- **Concern:** Five terrain-screening sites are not enough for a statistical global classification.
- **Current handling:** Figure 5 is described as a qualitative process-terrain diagnostic.
- **Evidence to retain:** Figure 5 caption, limitations section, and `Fig5_process_terrain_typology.csv`.
- **Do not claim:** The typology is a trained classifier, a validated predictive model, or a regional generalization.

## Risk 5. Meteorological coherence is mistaken for causality

- **Concern:** Correlations between daily surge and local meteorological variables do not prove causal mechanisms.
- **Current handling:** Figure 3 is described as a coherence diagnostic and regime indicator.
- **Evidence to retain:** `Fig3_driver_correlations.csv`, `Fig3_daily_merged_source.parquet`, methods language on Spearman rank correlation.
- **Do not claim:** Open-Meteo variables alone explain all surge dynamics.

## Risk 6. Standalone HTML or figures are stale

- **Concern:** The HTML report might embed old images after scripts are changed.
- **Current handling:** `audit_publication_readiness.py` compares embedded Base64 image hashes against current `figures/main/*.png`.
- **Evidence to retain:** `publication_readiness_report.md` from the finalization run.

## Risk 7. Raw data provenance is weak

- **Concern:** Reviewers may ask whether the plots are based on real local data files.
- **Current handling:** `verify_downloads.py --strict` and `combo1_quality_audit.py` are part of the finalization workflow.
- **Evidence to retain:** finalization command log, raw-data file sizes/hashes where available, and `reference_verification.md`.

## Risk 8. Missing archival metadata

- **Concern:** The manuscript cannot be submitted with placeholder repository DOI, funding, acknowledgements or author contribution fields.
- **Current handling:** These are explicitly listed as human-completion items in the finalization checklist.
- **Evidence to retain:** `process_terrain_CEE_finalization_checklist.md`.
