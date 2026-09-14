# Process-terrain CEE manuscript execution report

**Date:** 2026-05-27  
**Manuscript baseline:** `manuscript/process_terrain_coastal_flood_CEE_manuscript.md`  
**Figure plan baseline:** `manuscript/process_terrain_CEE_figure_work_plan.md`

## What was completed

- Generated five CEE-style main figures from real project data; Fig. 2-Fig. 5 were redrawn with a refined journal-style layout on 2026-05-27.
- Wrote PNG and PDF versions to `figures/main/`.
- Wrote figure source data and main-table CSV files to `data/figure_source/`.
- Updated the manuscript Markdown with Fig. 1-Fig. 5 references and final generated figure captions.
- Built a standalone HTML review copy with embedded main figures:
  `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`
- Added a reproducible refined figure-building script: `scripts/make_cee_refined_figures.py`.
- Added individual wrapper scripts matching the work-plan structure:
  - `scripts/make_fig1_design_map.py`
  - `scripts/make_fig2_water_level_divergence.py`
  - `scripts/make_fig3_meteorological_coherence.py`
  - `scripts/make_fig4_deltadtm_terrain_sensitivity.py`
  - `scripts/make_fig5_process_terrain_typology.py`
  - `scripts/build_main_tables.py`

## Generated main figures

| Figure | PNG | PDF | Source data |
| --- | --- | --- | --- |
| Fig. 1 | `figures/main/Fig1_process_terrain_design.png` | `figures/main/Fig1_process_terrain_design.pdf` | `data/figure_source/Fig1_station_metadata.csv` |
| Fig. 2 | `figures/main/Fig2_water_level_divergence.png` | `figures/main/Fig2_water_level_divergence.pdf` | `data/figure_source/Fig2_water_level_divergence.csv` |
| Fig. 3 | `figures/main/Fig3_meteorological_coherence.png` | `figures/main/Fig3_meteorological_coherence.pdf` | `data/figure_source/Fig3_driver_correlations.csv`; pressure-bin CSVs; merged parquet |
| Fig. 4 | `figures/main/Fig4_deltadtm_terrain_sensitivity.png` | `figures/main/Fig4_deltadtm_terrain_sensitivity.pdf` | `data/figure_source/Fig4_connected_terrain_sensitivity.csv` |
| Fig. 5 | `figures/main/Fig5_process_terrain_typology.png` | `figures/main/Fig5_process_terrain_typology.pdf` | `data/figure_source/Fig5_process_terrain_typology.csv`; `Fig4_hypsometry_curves.csv` |

## Data authenticity checks

Commands run successfully:

```powershell
python scripts\verify_downloads.py --strict
python scripts\combo1_quality_audit.py
python scripts\make_cee_main_figures.py
```

Key checks:

- GSSR archives for all eight stations exist and were parsed.
- COAST-RP NetCDF exists and contains 23,226 coastal points.
- Open-Meteo files are present and verified.
- DeltaDTM terrain figures use real GeoTIFF tiles under `data/raw/deltadtm/tiles/`; no synthetic DEM fallback was used in the main figures.
- The refined Fig. 4-Fig. 5 terrain metrics use an ocean-connected static mask: candidate cells below each perturbation are counted only if connected to a no-data ocean/water component at the map boundary. This fixes the earlier non-connected bathtub artefact where isolated low cells could be shown as flooded.

## Environment notes

- Python: 3.13.12
- Confirmed available: `matplotlib`, `pandas`, `numpy`, `rasterio`
- Not available: `pandoc`, `python-docx`, `cartopy`

Because Pandoc and python-docx are not installed, the updated Word document was not regenerated in this run. The authoritative updated manuscript is the Markdown file. Figures are available as publication-ready PNG/PDF outputs and can be inserted into Word manually or converted once Pandoc is installed.
The standalone HTML review copy is self-contained for figures and CSS; DOI URLs remain as text references.

## Rebuild commands

```powershell
cd E:\Projects\20260522-coastal-flood-scientific-data
python scripts\make_cee_refined_figures.py
python scripts\build_main_tables.py
```

Individual figures can be rebuilt with:

```powershell
python scripts\make_fig1_design_map.py
python scripts\make_fig2_water_level_divergence.py
python scripts\make_fig3_meteorological_coherence.py
python scripts\make_fig4_deltadtm_terrain_sensitivity.py
python scripts\make_fig5_process_terrain_typology.py
```

## Remaining submission items

- Add author names, affiliations, correspondence, funding and acknowledgements.
- Deposit processed figure-source data and code snapshot to Zenodo/OSF/GitHub and add DOI/URL.
- Decide whether to keep the Figure 1 locator map as an offline schematic or replace it with a cartographic coastline map after installing Cartopy or supplying a Natural Earth shapefile.
- If the target journal requires DOCX, install Pandoc or python-docx and regenerate the manuscript package.
