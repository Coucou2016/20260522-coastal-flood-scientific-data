# Publication-readiness audit for the process-terrain coastal flood manuscript

This audit records the checks required before treating the manuscript, figures, source data, and HTML review file as publication-ready. It is intentionally conservative: an item is marked ready only when the current artifact can be traced to real input data and a reproducible script output.

## Current high-priority audit findings

1. **DeltaDTM terrain values are real, but full-window median elevation is not an ideal interpretive statistic.**  
   Several DeltaDTM tiles contain many valid land cells at the product upper cap of 30 m. Therefore, full-window median elevation can be 30.00 m for cliffed or upland-dominated windows and should not be interpreted as a natural terrain median. Manuscript interpretation and Table 4 should use the coastal-lowland-mask median elevation instead.

2. **The inundation screen must remain ocean-connected.**  
   Static bathtub results can include isolated inland low cells. Figure 4 and Figure 5 should use the ocean-connected mask: a low cell is counted only when it is part of an eight-neighbour connected component linked to boundary water/no-data. Interior no-data cells must not be used as ocean seeds unless they are connected to the map boundary. Non-connected bathtub fractions may be shown only as a comparison or diagnostic.

3. **Figure 5 is descriptive, not inferential.**  
   The typology currently uses five European terrain-screening sites. It is suitable as a process-terrain diagnostic framework, but the manuscript must not present it as a statistical classification model or as regional generalization.

4. **Water-level products are physically distinct.**  
   GSSR daily surge residual return indicators and COAST-RP storm-tide return levels should be compared as diagnostic indicators, not as validation targets. Any language implying one validates the other should be removed.

5. **Terrain sensitivity is not flood prediction.**  
   DeltaDTM-based connected sensitivity excludes isolated low cells but still omits hydrodynamics, flood defences, drainage structures, river flow, wave setup, roughness and local datum conversion. Captions and discussion should keep this boundary explicit.

## Required verification gates

Before declaring the manuscript final, run and archive the output of:

```powershell
python scripts\verify_downloads.py --strict
python scripts\combo1_quality_audit.py
python scripts\make_cee_refined_figures.py
python scripts\build_cee_review_html.py
python -m py_compile scripts\make_cee_refined_figures.py scripts\build_cee_review_html.py
```

Then run a figure-source consistency audit that confirms:

- The review HTML embeds exactly the current main figures as Base64 images and has no external image, CSS or script dependencies.
- Figure 2 `D10_m` equals `COAST-RP RP10 - GSSR RP10` for every station.
- Figure 3 correlation coefficients are within `[-1, 1]` and match the processed driver-correlation table.
- Figure 4 uses DeltaDTM GeoTIFF sources only, and every ocean-connected percentage is less than or equal to the corresponding non-connected bathtub percentage.
- Figure 5 inherits `D10_m`, pressure correlation and connected +2 m lowland fraction exactly from the Figure 2, Figure 3 and Figure 4 source tables.
- Table 4 reports coastal-lowland median elevation, not capped full-window median elevation.

## Figure-level readiness checklist

### Figure 1

- Status: concept figure; not the primary data claim.
- Required caution: the locator background is schematic. Captions should state that station coordinates are real but the base map is an offline schematic locator.

### Figure 2

- Status: quantitative diagnostic figure.
- Required checks: matched station distances; `D10_m` arithmetic; region labels; no language implying product validation.

### Figure 3

- Status: meteorological coherence diagnostic.
- Required checks: Spearman rank correlations from daily merged GSSR/Open-Meteo table; Newlyn and Charleston panel values match heatmap values; pressure axis and sign convention stated clearly.

### Figure 4

- Status: key terrain figure.
- Required checks: all panels use real DeltaDTM GeoTIFF windows; blue overlay is ocean-connected +2 m static water depth only; isolated low cells are excluded; legends distinguish terrain elevation and connected water depth; station markers and scale bars remain readable.

### Figure 5

- Status: synthesis and typology figure.
- Required checks: hypsometry is computed within the coastal-lowland mask; response bars use ocean-connected fractions; open symbols show non-connected bathtub only as a contrast; phase-space classes are described as qualitative diagnostics.

## Final readiness status

Not yet final. The manuscript has been substantially improved, but final readiness requires one clean regeneration-and-audit pass after the latest Table 4/lowland-median corrections have been propagated to all generated artifacts.
