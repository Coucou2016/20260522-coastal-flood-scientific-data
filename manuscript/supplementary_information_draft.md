# Supplementary Information draft

## Supplementary Note 1. Site selection and diagnostic scope

The analysis was designed as a reproducible multi-site screening study rather than a local flood-risk assessment. The eight tide-gauge sites were selected to span contrasting coastal settings while keeping data processing tractable. Five European sites were used for DeltaDTM terrain screening because the relevant DeltaDTM Europe tiles were locally available and could be audited directly. New York-The Battery, Charleston and Hong Kong were retained as water-level and meteorological comparison sites but were not included in the present DeltaDTM terrain-screening subset.

## Supplementary Note 2. Product definitions

GSSR and COAST-RP are used as physically distinct diagnostics. GSSR provides reconstructed surge residuals at tide-gauge locations. COAST-RP provides storm-tide return levels at coastal points. The manuscript therefore interprets `D10_m` as a product-definition divergence rather than a validation residual. This distinction is central to the study design and should be retained in all interpretations.

## Supplementary Note 3. Empirical 10-year surge indicator

The GSSR 10-year surge indicator is derived from the station-level reconstructed surge-residual time series. The final workflow stores the plotted values in `data/figure_source/Fig2_water_level_divergence.csv` and the publication-facing table in `data/figure_source/Table2_water_level_indicators.csv`. The publication-readiness audit checks that `D10_m` equals `coast_rp_rp10_m - gssr_rp10_m`.

## Supplementary Note 4. Meteorological coherence diagnostics

Open-Meteo ERA5-derived historical variables are summarized at the daily scale and matched with daily GSSR surge residuals. Spearman rank correlations are computed between surge and pressure, wind and precipitation diagnostics. These correlations are interpreted as meteorological coherence indicators rather than causal attribution or complete physical explanations of surge generation.

## Supplementary Note 5. DeltaDTM terrain screening

DeltaDTM one-degree GeoTIFF tiles are used for the five European terrain-screening sites. Terrain sensitivity is calculated as a relative static perturbation screen at +0.5 m, +1.0 m and +2.0 m. Candidate cells are land cells below the perturbation level. A candidate cell is counted as ocean-connected only if it is part of an eight-neighbour connected component linked to boundary water/no-data. Interior no-data components are not used as marine seeds unless they are connected to the map boundary.

The reported denominator is the coastal-lowland mask rather than the full map window. This is used because station-centred terrain windows can include uplands and non-coastal terrain. Several DeltaDTM tiles also contain upper-range capped values at 30 m; therefore full-window medians are retained only for audit and are not used as the main interpretive terrain statistic.

## Supplementary Note 6. Figure source data

Every main figure is paired with source data under `data/figure_source/`. The finalization workflow verifies that declared source CSV files exist and are non-empty. The data dictionary in `manuscript/figure_source_data_dictionary.md` defines the key columns and interpretation boundaries.

## Supplementary Note 7. Publication-readiness audit

The final local workflow is:

```powershell
python scripts\finalize_cee_publication_package.py
```

The workflow rebuilds figures, rebuilds the standalone manuscript review HTML, compiles key scripts, verifies raw downloads, runs the quality audit, runs publication-readiness checks and assembles `publication_package/` plus `publication_package.zip`.

The audit checks include:

- HTML has no external dependencies and embeds the current PNG figures as Base64.
- PNG and PDF versions of all main figures exist.
- Figure source tables are present and non-empty.
- Figure 2 `D10_m` arithmetic is correct.
- Figure 3 correlations are within valid bounds.
- Figure 4 uses DeltaDTM sources and ocean-connected fractions do not exceed non-connected bathtub fractions.
- Figure 5 inherits its inputs exactly from Figure 2, Figure 3 and Figure 4 source tables.
- Table 4 reports coastal-lowland median elevation rather than capped full-window median elevation.
- The manuscript contains no unresolved submission placeholders.

## Supplementary Note 8. Interpretation boundaries

The workflow does not estimate dynamic inundation, observed flood extent, asset exposure, vulnerability, damages, adaptation benefits or operational flood risk. It is a screening framework designed to identify where water-level processes, meteorological coherence and connected lowland terrain align or decouple. More detailed local modelling would be required for flood-depth prediction, defence-performance analysis or policy-grade risk assessment.
