# Data and algorithm validation notes

**Scope:** process-terrain CEE manuscript, especially Fig. 4 and Fig. 5  
**Current figure logic:** real DeltaDTM terrain + ocean-connected static sensitivity

## Data authenticity

The manuscript figures use local files that were previously verified by:

```powershell
python scripts\verify_downloads.py --strict
python scripts\combo1_quality_audit.py
```

The last successful strict verification confirmed:

- COAST-RP NetCDF: `data/raw/coast_rp/extracted/COAST-RP.nc`
- GSSR ERA5 archives for all eight stations
- DeltaDTM tile index: `data/raw/deltadtm/index/deltadtm_tiles.gpkg`
- Real DeltaDTM GeoTIFF tiles for the five European terrain sites:
  - Sheerness: `DeltaDTM_v1_1_N51E000.tif`
  - Hoek van Holland: `DeltaDTM_v1_1_N51E004.tif` + `DeltaDTM_v1_1_N52E004.tif`
  - Newlyn: `DeltaDTM_v1_1_N50W006.tif`
  - Brest: `DeltaDTM_v1_1_N48W005.tif`
  - Aberdeen: `DeltaDTM_v1_1_N57W003.tif`

No synthetic DEM is used by the refined main-figure script.

## Algorithm correction for Fig. 4 and Fig. 5

The earlier static terrain screen used a non-connected bathtub criterion:

```text
candidate = valid land cell and DEM <= eta
```

This can incorrectly colour isolated inland depressions as flooded. The refined script now uses an ocean-connected static criterion:

```text
candidate = valid land cell and DEM <= eta
connected = candidate belongs to an eight-neighbour component connected to
            boundary no-data water/ocean cells
```

This is implemented in:

```text
scripts/make_cee_refined_figures.py::flood_connected_mask
```

The script asserts that connected fractions cannot exceed non-connected bathtub fractions for all scenarios and all terrain sites.

## Result of the correction

The correction materially changes the interpretation of Hoek van Holland:

| Site | Non-connected +2 m lowland | Ocean-connected +2 m lowland |
| --- | ---: | ---: |
| Sheerness | 42.78% | 39.25% |
| Hoek van Holland | 34.72% | 3.10% |
| Newlyn | 8.26% | 8.22% |
| Brest | 7.63% | 5.33% |
| Aberdeen | 7.24% | 6.09% |

This is scientifically useful rather than inconvenient: Hoek van Holland becomes a key example of decoupling between low terrain and immediate ocean-connected static sensitivity under the selected terrain window and assumptions.

## Refined figure-generation command

```powershell
cd E:\Projects\20260522-coastal-flood-scientific-data
python scripts\make_cee_refined_figures.py
python scripts\build_cee_review_html.py
```

## Current execution note

The refined script has been updated, but the latest attempt to execute Python from the tool environment was blocked by repeated permission-review timeouts after the code changes. Once command execution permission is available, the two commands above will regenerate Fig. 2-Fig. 5 and refresh the self-contained review HTML.

