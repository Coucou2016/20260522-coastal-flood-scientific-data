# Software environment for manuscript finalization

This document records the intended local software environment for reproducing the final manuscript figures, source-data tables, standalone HTML review file and compact publication package.

## Recommended runner

From the project root:

```powershell
python scripts\finalize_cee_publication_package.py
```

If PowerShell process creation is unavailable, use the batch wrapper:

```cmd
scripts\run_finalization.cmd
```

## Python dependencies

The workflow uses the existing project environment files where available:

- `requirements.txt`
- `environment.yml`

The key runtime libraries used by the final manuscript workflow are:

- `numpy`
- `pandas`
- `matplotlib`
- `scipy`
- `pyyaml`
- `xarray`
- `netCDF4` or a compatible NetCDF backend
- `rasterio`
- `geopandas`
- `shapely`
- `pyproj`
- `Pillow`
- `pyarrow`

The finalization workflow also uses Python standard-library modules including `hashlib`, `json`, `subprocess`, `shutil`, `html.parser`, `pathlib`, and `datetime`.

## Required local data products

The publication-finalization workflow expects the already downloaded local data tree:

- GSSR station archives under `data/raw/gssr/`
- COAST-RP NetCDF under `data/raw/coast_rp/`
- Open-Meteo historical JSON files under `data/raw/open_meteo/`
- DeltaDTM tile index and European GeoTIFF tiles under `data/raw/deltadtm/`
- Processed intermediate tables under `data/processed/`

The command `python scripts\verify_downloads.py --strict` is part of the finalization workflow and should fail if required raw inputs are missing.

## Reproducibility outputs

A successful finalization run should produce:

- `manuscript/publication_readiness_report.md`
- `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`
- refreshed `figures/main/*.png` and `figures/main/*.pdf`
- refreshed `data/figure_source/*.csv`
- `publication_package/`

## Known current execution issue

If command execution fails with:

```text
Failed to create unified exec process: setup refresh failed with status exit code: 1
```

then the project files may be ready for finalization, but the finalization workflow has not actually been executed in the current session. Do not treat the package as final until the finalization command exits successfully and `scripts/audit_publication_readiness.py` reports `PUBLICATION READINESS AUDIT: PASS`.
## Publication gate requirements

Use the root-level `requirements-publication.txt` file as the Python package requirements list for rerunning the final publication gate. The gate also runs `scripts\run_python_runtime_dependencies_audit.cmd` to confirm that the active Python environment can import the external modules required by the project scripts.

Install the publication runtime packages with:

```cmd
scripts\install_publication_requirements.cmd
```
