# Claims-evidence matrix

This matrix links the manuscript's major scientific claims to the specific evidence that supports them. It is intended for final internal review before submission and for rapid response if reviewers ask how a claim was derived.

## Claim 1. Surge-residual and storm-tide indicators diverge by coastal setting

| Item | Details |
|---|---|
| Claim | GSSR 10-year surge-residual indicators and COAST-RP 10-year storm-tide indicators are substantially different at several European sites, while selected comparison sites show smaller differences. |
| Evidence | Figure 2; Table 2; `data/figure_source/Fig2_water_level_divergence.csv`; `data/figure_source/Table2_water_level_indicators.csv`. |
| Calculation | `D10_m = coast_rp_rp10_m - gssr_rp10_m`. |
| Required audit | `audit_publication_readiness.py` checks that `D10_m` equals COAST-RP RP10 minus GSSR RP10 and that station matching distances are below 5 km. |
| Interpretation boundary | This is product-definition divergence, not validation error. GSSR and COAST-RP represent different physical quantities. |

## Claim 2. Reconstructed surge has regime-dependent meteorological coherence

| Item | Details |
|---|---|
| Claim | Daily GSSR surge residuals show strong pressure coherence at several European extratropical sites, while some comparison sites show weaker daily local coherence. |
| Evidence | Figure 3; Table 3; `data/figure_source/Fig3_driver_correlations.csv`; `data/figure_source/Fig3_daily_merged_source.parquet`. |
| Calculation | Spearman rank correlations between daily GSSR surge and station-centred Open-Meteo ERA5-derived pressure, wind and precipitation summaries. |
| Required audit | Correlation values must be within `[-1, 1]`; daily sample sizes must be adequate; detailed panels must match heatmap values. |
| Interpretation boundary | Correlation is a coherence diagnostic, not a causal attribution model. |

## Claim 3. Ocean-connected terrain sensitivity is concentrated at Sheerness in the current five-site terrain set

| Item | Details |
|---|---|
| Claim | Among the five European terrain-screening sites, Sheerness has the highest +2 m ocean-connected coastal-lowland sensitivity. |
| Evidence | Figure 4; Figure 5; Table 4; `data/figure_source/Fig4_connected_terrain_sensitivity.csv`; `data/figure_source/Fig5_process_terrain_typology.csv`. |
| Calculation | Low cells below each perturbation level are filtered by eight-neighbour connectivity to boundary water/no-data; the metric is the percentage of coastal-lowland-mask cells that pass this filter. |
| Required audit | Connected fractions must not exceed non-connected bathtub fractions; DEM sources must start with `DeltaDTM`; Table 4 must use `median_lowland_elev_m`. |
| Interpretation boundary | Static sensitivity is not observed flood extent, hydrodynamic modelling, defence failure, or local flood-risk prediction. |

## Claim 4. Low terrain and marine access can be decoupled

| Item | Details |
|---|---|
| Claim | Hoek van Holland illustrates that low terrain by elevation alone can become much less sensitive after ocean-connectivity filtering. |
| Evidence | Figure 4; Figure 5b; Table 4; `Fig4_connected_terrain_sensitivity.csv`. |
| Calculation | Compare non-connected bathtub +2 m fraction with ocean-connected +2 m fraction for the same coastal-lowland mask. |
| Required audit | The final Figure 4 overlay must show only connected +2 m static water depth; isolated low cells must be excluded. |
| Interpretation boundary | Terrain buffering in this screen may represent topographic barriers, engineered surfaces or DEM connectivity structure; it does not prove operational protection under real storm conditions. |

## Claim 5. A process-terrain typology is useful as a diagnostic synthesis

| Item | Details |
|---|---|
| Claim | Combining water-level indicator divergence, meteorological coherence and connected terrain sensitivity helps distinguish aligned hotspots from terrain-buffered cases. |
| Evidence | Figure 5; `data/figure_source/Fig5_process_terrain_typology.csv`. |
| Calculation | Figure 5 inherits `D10_m` from Figure 2, pressure correlation from Figure 3, and +2 m connected lowland sensitivity from Figure 4. |
| Required audit | `audit_publication_readiness.py` checks exact inheritance of these upstream values. |
| Interpretation boundary | This is a qualitative diagnostic typology based on a small site set, not a trained classifier or global predictive model. |

## Claims that should not be made

- The study does not validate COAST-RP with GSSR or validate GSSR with COAST-RP.
- The study does not provide dynamic flood inundation maps.
- The study does not estimate risk, exposure, vulnerability, damages or adaptation benefits.
- The study does not generalize statistically from five DeltaDTM terrain windows to all European or global coasts.
- The study does not claim that local Open-Meteo variables fully explain storm-surge generation.
