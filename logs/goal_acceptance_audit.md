# Goal Acceptance Audit

Generated UTC: 2026-08-23T06:50:20.179440+00:00

Local technical-review ready: **True**
Final submission ready: **False**

| Item | Passed | Severity | Evidence |
|---|---:|---|---|
| 1. Data truth and source-table traceability | True | required | Required source tables exist in data/figure_source and are consumed by current build/audit scripts. |
| 2. DeltaDTM official mask-aware connectivity | True | required | Fig6_mask_aware_terrain_area_metrics.csv rows=74; required mask columns present=True. |
| 3. Connected lowland metric completeness | True | required | Required fraction/area columns present=True. |
| 4. Figure 3 archetype and threshold-response evidence | True | required | Fig6_archetype_map_selection.csv archetypes=['aligned high storm-tide / high connected-terrain', 'high storm-tide / lower connected-terrain', 'lower storm-tide / high connected-terrain']. |
| 5. Conservative statistical interpretation | True | required | Paper frames top-set overlap descriptively and uses raw COAST-RP versus connected terrain statistics. |
| 6. Sample-boundary clarity | True | required | Paper distinguishes primary, distance-unrestricted, GSSR-qualified, retained and source-verified tidal subsets. |
| 7. Uncertainty and perturbation ranges | True | required | Paper names GSSR, COAST-RP, DEM perturbation and window/seed sensitivity as screening ranges. |
| 8. Reproducibility package | True | required | repository_link_status=pending; package zip exists=True. |
| 9. Paper/report synchronized standalone outputs | True | required | All six standalone paper/report outputs exist; standalone validation is covered by validate_standalone_html.py. |
| 10. Non-overclaiming wording | True | required | Forbidden terms in paper/report=[]. |
| local_dtm. Local-DTM cross-check hard gate | True | required | local DTM stations=['sheerness-p015-uk', 'newlyn-p001-uk', 'lowestoft-p024-uk', 'immingham-p026-uk', 'denhelder-hel-nl', 'delfzijl-del-nl', 'hoekvanholla-hvh-nl']. |
| submission_link. External DOI/private reviewer link hard gate | False | submission | Repository link is pending. |
