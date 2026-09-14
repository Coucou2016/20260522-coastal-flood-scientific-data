# External Major-Revision Resolution Matrix

**Manuscript:** *Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network*  
**Purpose:** auditable mapping from the external review to code, source data, figures and manuscript text.  
**Status vocabulary:** `RESOLVED` means recalculated or corrected; `RESOLVED BY SCOPE` means the claim was narrowed because the requested independent evidence is unavailable; `OPEN EXTERNAL` means the manuscript explicitly retains the limitation and does not claim completion.

## Major Comments

| Review issue | Status | Implemented change | Evidence and acceptance condition |
|---|---|---|---|
| Fixed 2 m EGM2008 terrain threshold is not an event-specific RP water surface | RESOLVED BY SCOPE | The manuscript no longer calls the metric a land response, inundation or flood depth. COAST-RP magnitude is treated as a water-level forcing screen and the 2 m EGM2008 calculation as an independently defined standardized terrain-susceptibility screen. No arithmetic coupling of the two surfaces is performed. | Manuscript title, Abstract, Introduction, Methods and Discussion; no claim that 2 m is local MSL or RP10 water level. Common-datum event surfaces remain `OPEN EXTERNAL`. |
| Top-set null ignored spatial structure | RESOLVED | Replaced the inferential hypergeometric null with 10,000 within-sector permutations for every top-k share from 10% to 40%. The hypergeometric calculation is retained only as a non-spatial descriptive comparator. | `Topk_spatial_null_curves.csv`; Fig. 2c. At top 20%, observed overlap is 1/14, spatial-null 95% envelope is 0–4 and lower-tail p=0.257. |
| Six unequal sectors are insufficient as the sole spatial diagnostic | RESOLVED WITH BOUNDARY | Added within-sector permutation, sector-adjusted rank association, Moran's I at multiple distance thresholds, station jackknife, sector-specific associations and leave-one-sector diagnostics. Six-sector bootstrap is explicitly called composition sensitivity, not a confidence interval. | `Return_period_sensitivity.csv`, `Spatial_autocorrelation_moran.csv`, `Station_influence_jackknife.csv`, `Sector_specific_associations.csv`, `Spatial_sector_bootstrap_intervals.csv`; Fig. 2b. The sector-block ranges still cross zero and are reported as such. |
| RP10 choice was insufficiently tested | RESOLVED | Extracted and analysed COAST-RP RP2, RP5, RP10, RP25, RP50 and RP100 for all 68 stations and five terrain metrics. | `TableS_coastrp_multi_return_period_68stations.csv`, `Return_period_sensitivity.csv`; Fig. 2d. The connected-share association ranges from -0.36 to -0.32. |
| Local-DTM comparison confounded product, datum, resolution and resampling | RESOLVED BY SCOPE | Removed the comparison from main Figure 4, renamed it product/datum/provider-resampling sensitivity, used 4-neighbour topology on both products, and retained continuous differences and intersection-over-union without a validation or accuracy claim. | Supplementary Fig. S4 and `TableS_local_dtm_product_datum_crosscheck.csv`. Common vertical-datum harmonisation remains `OPEN EXTERNAL`. |
| Raster topology and window geometry were treated as secondary | RESOLVED | Four-neighbour connectivity is now primary. Eight-neighbour, 5/20 km windows, 1/3 m thresholds, local-ocean seed, uniform -1/-0.5/+0.5/+1 m shifts and COAST-RP matching alternatives are included in the full one-at-a-time grid. | `Terrain_robustness_grid_74stations.csv`, `Rank_robustness_one_at_a_time.csv`, `Topology_sensitivity_summary.csv`; Fig. 4c–d. The 4/8-neighbour top set has six membership changes and this instability is reported. |
| GSSR atmospheric diagnostic was circular if described as validation | RESOLVED BY SCOPE | Relabelled the analysis predictor-consistency; moved it to Supplementary Fig. S2; stated that reanalysis variables contribute to the reconstruction and therefore cannot independently validate it. The metadata field `corrn` is described only as reconstruction correlation, not extreme-event skill. | Methods, Supplementary Fig. S2, `GSSR_metadata_field_audit.csv`. No independent extreme-event skill field was found in the local metadata. |
| No external flood-hazard benchmark | OPEN EXTERNAL | Removed claims of superiority, distortion, mis-ranking, predictive complementarity or true susceptibility. The conclusion is limited to non-interchangeability of two transparent representations in the sampled network. | Title, Abstract, Discussion and scientific-integrity review. Acceptance condition for a future stronger claim is a preregistered observed/dynamic hazard benchmark comparing water-only, terrain-only and combined screens. |

## Additional P0/P1 Items

| Review item | Status | Evidence |
|---|---|---|
| Complete 40-configuration robustness table including ±0.5/±1 m | RESOLVED | `Terrain_robustness_grid_74stations.csv` has 74 × 40 = 2,960 rows; Fig. 4d summarizes the grid. |
| Figure S1 n=13/source consistency | RESOLVED | `FigS1_tidal_source_audit.csv` contains exactly 13 source-verified rows; all 13 points are drawn and labels were visually checked using deterministic label repulsion. |
| Hino reference article number | RESOLVED | Reference corrected from Article 383 to Article 404; automated test prevents regression. |
| GSSR 0.55 threshold interpretation | RESOLVED | It is identified as daily reconstruction correlation (`corrn`), not extreme-event cross-validation skill. It is not used to restrict the 68-station COAST-RP–terrain primary analysis. |
| Denominator and represented-land geometry | RESOLVED | Added nominal-window area, represented-land fraction, below-window share and connected-window share. RP10 versus represented-land fraction rho=0.003; controlling represented-land fraction changes connected-share rho from -0.333 to -0.336. See `Denominator_geometry_68stations.csv` and `Denominator_adjusted_associations.csv`. |
| Station influence and tidal-regime decomposition | RESOLVED WITH SAMPLE BOUNDARY | Added leave-one-station jackknife and 13-site source-verified tidal analyses, including partial rank control. The 13-site result is not generalized to all 68 stations. See `Station_influence_jackknife.csv` and `Tidal_covariation_diagnostics.csv`. |
| COAST-RP nearest-point audit | RESOLVED | Added source-point coordinates, recomputed geodesic distance and an explicit 6 km inclusion rule. 68 sites pass; six fail. See Supplementary Fig. S5 and `Match_distance_audit_74stations.csv`. |
| Sampling imbalance | RESOLVED WITH BOUNDARY | Figure 1 displays the same six sectors used in inference and the manuscript states that the GSSR-derived inventory is not a uniform coastal sample. Moran's I and sector methods quantify, but do not remove, the limitation. An independent shoreline inventory remains `OPEN EXTERNAL`. |
| Figure 2 point-size/log-display issues | RESOLVED | All points have fixed area; the positive connected share is plotted on an ordinary log axis; panel b distinguishes within-sector p-values from block-resampling ranges. |
| Figure 3 geographic frame and uncertainty-band issues | RESOLVED | Maps use local metric coordinates and 2 km scale bars. Uniform DEM offsets are shown as three separately calculated curves, not a shaded confidence band. The 3 × 3 structure decomposes lowland prevalence, conditional connectivity and connected share without enlarging classified cells. |
| Figure 4 provenance and interpretation | RESOLVED | Main Figure 4 is now the metric-decomposition and robustness figure. The confounded local-DTM diagnostic is Supplementary Fig. S4. Every panel has a machine-readable source table. |
| Empirical GSSR return-level method | RESOLVED | Methods specify annual maxima, ascending order, `F_m=m/(n+1)`, target `F=1-1/T`, linear interpolation in F, and no extrapolation beyond empirical support. Unit tests reproduce the 25-year synthetic example. |

## Current Scientific Boundary

The revised analysis establishes that a COAST-RP storm-tide magnitude ranking and an independently defined standardized connected-terrain ranking cannot substitute for one another in this spatially clustered station network. It does not establish that one list is true, that their observed overlap is unusually low under the spatial null, or that either list predicts actual inundation. The remaining common-datum and external-benchmark tasks are deliberately visible in the manuscript, report and scientific-integrity review.

## Reproduction Gate

Run:

```powershell
python scripts/run_major_revision_rebuild.py
python scripts/build_major_revision_package.py
```

Acceptance requires all scientific contracts to pass, standalone HTML to contain only embedded resources, Figures 1–4 and S1–S5 to exist as PNG/PDF, and the manifest/package receipt to record sizes and SHA-256 values.
