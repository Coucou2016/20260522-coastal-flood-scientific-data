# Current Acceptance Status

Generated UTC: 2026-09-14T11:50:40.186791+00:00

Overall status: **submission_ready_repository_link_recorded**

This file supersedes older finalized/status files for the current mask-aware paper/report package. The local technical-review package is auditable, but final journal submission remains pending until a real public repository DOI/URL or private reviewer link is recorded.

## Acceptance Items

| Item | Status | Evidence |
|---|---|---|
| 1. data truth and source-table traceability | complete | Core figures and tables are generated from data/figure_source tables and audited by scripts/audit_current_outputs.py. |
| 2. DeltaDTM official mask-aware connectivity | complete | data\figure_source\Fig6_mask_aware_terrain_area_metrics.csv rows=74; mask class table present=True. |
| 3. connected fraction and area metrics | complete | Mask-aware source table includes connected/all-below/unconnected areas and denominator metrics. |
| 4. Figure 3 archetype evidence grid | complete | data\figure_source\Fig6_archetype_map_selection.csv contains 3 archetype rows. |
| 5. conservative statistical interpretation | complete | Top-set overlap is treated as decision-oriented description; formal statistics use raw COAST-RP versus connected fraction/area. |
| 6. sample-boundary clarity | complete | Paper/report distinguish the 68-station primary, 74-station distance-unrestricted, 44-station GSSR-qualified, 30-station retained and 13-station source-verified tidal subsets. |
| 7. uncertainty and perturbation ranges | complete | GSSR bootstrap/prediction-bound, COAST-RP spatial matching, DeltaDTM DEM perturbation and window/seed sensitivity are reported as screening ranges. |
| 8. reproducibility package | complete | reproducibility_package.zip exists; repository DOI/private reviewer link status=complete. |
| 9. paper/report synchronized standalone outputs | complete | paper.html/md/pdf and report.html/md/pdf exist and standalone HTML validation passes. |
| 10. non-overclaiming wording | complete | Final paper/report avoid distortion, mis-rank and true hotspot in core wording. |
| local_dtm. local DTM product/datum cross-check | complete | data\figure_source\TableS_local_dtm_validation.csv stations=sheerness-p015-uk; newlyn-p001-uk; lowestoft-p024-uk; immingham-p026-uk; denhelder-hel-nl; delfzijl-del-nl; hoekvanholla-hvh-nl. |
| submission_readiness. external submission repository link | complete | Set config/submission_links.json and rerun scripts/audit_submission_readiness.py. |

## Final External Step

Record a real repository link with one of the following commands:

```powershell
scripts\run_python_checked.cmd scripts\set_submission_links.py --reviewer "https://..."
scripts\run_python_checked.cmd scripts\set_submission_links.py --data "https://doi.org/..." --code "https://doi.org/..."
```

Then rebuild and run:

```powershell
scripts\run_python_checked.cmd scripts\build_standalone_paper.py
scripts\run_python_checked.cmd scripts\build_research_report.py
scripts\run_python_checked.cmd scripts\build_reproducibility_package.py
scripts\run_python_checked.cmd scripts\audit_submission_readiness.py
```
