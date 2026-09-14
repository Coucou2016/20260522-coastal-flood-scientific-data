# Final figure QC protocol

Use this protocol after running `scripts/finalize_cee_publication_package.py` and before sending the manuscript package to anyone else.

## Global figure checks

- PNG and PDF versions exist for every main figure.
- Text is readable at single-column and double-column review sizes.
- Axis labels include units where needed.
- Legends do not cover data.
- Colours remain interpretable when printed or viewed by readers with common colour-vision deficiencies.
- Captions state whether the panel is data, diagnostic synthesis or concept art.
- Every plotted quantitative value has a corresponding source table under `data/figure_source/`.

## Figure 1

- Treat as conceptual and design-oriented.
- Confirm the caption states that the map background is schematic while station coordinates are real.
- Do not use Figure 1 as evidence for coastline geometry.

## Figure 2

- Confirm `D10_m = COAST-RP RP10 - GSSR RP10`.
- Confirm Europe and comparison-site grouping is visually clear.
- Confirm the figure does not call the difference an error or validation residual.
- Confirm station matching distances remain below 5 km in source data.

## Figure 3

- Confirm pressure, wind and precipitation correlations use the same sign convention as the source table.
- Confirm the Newlyn and Charleston detailed panels match their heatmap values.
- Confirm the figure is described as meteorological coherence, not causal attribution.

## Figure 4

- Confirm every terrain panel is labelled with a real DeltaDTM GeoTIFF or mosaic source.
- Confirm blue overlays represent connected +2 m static water depth only.
- Confirm isolated inland low cells are not shown as marine flooding unless connected to boundary water/no-data.
- Confirm scale bars, station stars, latitude/longitude axes and map keys are readable.
- Confirm the bottom note states that results are not dynamic flood extents and do not include defences, waves, rivers or datum transformations.

## Figure 5

- Confirm hypsometry is labelled as coastal-lowland mask hypsometry.
- Confirm response bars use ocean-connected fractions.
- Confirm open symbols, if shown, are clearly labelled as non-connected bathtub contrast.
- Confirm phase-space classes are qualitative diagnostics, not a trained model.
- Confirm the Sheerness hotspot interpretation and terrain-buffered interpretation match the manuscript text.

## Stop conditions

Do not send the manuscript package if any of the following are true:

- Figure 4 shows obvious enclosed blue areas that are not connected to the ocean boundary.
- Table 4 or Figure 5 uses capped full-window median elevation as a central interpretive metric.
- A figure caption implies flood prediction rather than static terrain sensitivity.
- The standalone HTML embeds stale images or depends on local image paths.
- Any source table needed for a main figure is missing.
## Automated figure-data integrity audit

After the normal finalization run succeeds, run:

```cmd
scripts\run_figure_data_integrity_audit.cmd --strict
```

The audit scans manuscript Markdown/HTML image references, embedded image data, and candidate figure/source CSV files. It reports missing images, unreadable or likely blank raster files, low-resolution exports, non-finite source values, impossible percentages or correlations, non-monotonic quantiles, and cases where ocean-connected flooded area exceeds the corresponding bathtub area.
## Manuscript text readiness audit

Figure QC is not sufficient for submission. After figure/source-data checks, run:

```cmd
scripts\run_manuscript_submission_text_audit.cmd --strict
```

This audit checks the main manuscript, review HTML, and required support files for unresolved placeholders, missing core sections, missing submission statements, malformed DOI placeholders, figure/table numbering gaps, and required methodological guardrails such as ocean-connected inundation handling and coastal-lowland median elevation reporting.
## Figure inventory sign-off

Before accepting the manuscript figures, confirm that `logs\manuscript_figure_inventory.md` lists every local or embedded image used by the manuscript Markdown and review HTML. The corresponding JSON file must report `passed: true`, `image_count` greater than zero, `error_count: 0`, and one record per image.
## Figure visual-quality audit

Run `scripts\run_figure_visual_quality_audit.cmd` after the manuscript figure inventory is generated. This check flags low resolution, very low luminance dynamic range, nearly blank white or black exports, and excessive transparency. Treat warnings as requiring figure regeneration or documented manual acceptance. Treat notes, such as SVG/manual-review notices or edge-content notices, as required human review items that do not by themselves fail the automated gate.
## Figure deliverables audit

Run `scripts\run_figure_deliverables_audit.cmd` after the manuscript figure inventory is generated. This audit checks that the manuscript's numbered main figures are contiguous from Figure 1, that each figure has a detected caption, that each figure can be linked to an image inventory record, and that each figure has a detected source-data table. Treat failures as submission blockers until corrected or explicitly documented in final QC notes.

If the audit reports inferred image or source-table mappings, verify them manually against the rendered manuscript and source-data dictionary. Inferred mappings are acceptable only when the figure order is unambiguous and the final QC evidence records no unresolved errors or warnings.
## Final QC acceptance record

Use `manuscript\final_qc_acceptance.json` only for non-blocking audit notes that require human confirmation. Each accepted note must identify the audit file, exact note text, reviewer, review date, decision, and justification. Do not use the acceptance record to override errors or warnings.
## Manual figure review sheet

Run `scripts\run_manual_figure_review_sheet.cmd` after the figure inventory, figure deliverables audit, and visual-quality audit. The generated `logs\manual_figure_review_sheet.md` summarizes every manuscript image, dimensions, byte size, SHA256, visual problems, visual notes, and inferred mappings. Use the reviewer sign-off section for final human inspection of rendered figures.
