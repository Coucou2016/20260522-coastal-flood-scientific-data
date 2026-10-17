# Northwest European Coastal Screening

This repository contains the analysis, source tables, figures, manuscript and audit evidence for a Northwest European coastal-screening study.

**Public repository:** <https://github.com/Coucou2016/20260522-coastal-flood-scientific-data>

## What this paper does

The study asks whether coastal sites prioritized by COAST-RP storm-tide magnitude are also prioritized by a standardized static connected-lowland screen derived from DeltaDTM. The primary sample contains 68 matched stations. Terrain results are decomposed into lowland prevalence, conditional raster connectivity, connected represented-land share and connected area.

The evidence supports **limited rank concordance and decision-level disagreement** in this sampled network. It does not establish a stable negative physical law, statistically unusual Top-20% disagreement, predictive complementarity or a true flood-risk ranking. The terrain maps are raster classifications, not hydrodynamic flood forecasts.

## Start here

- Paper: `paper.html`, `paper.md`, `paper.pdf`
- Supplementary Information: `supplementary_information.html`, `.md`, `.pdf`
- Detailed research report: `report.html`, `.md`, `.pdf`
- Internal evidence audit: `manuscript/internal_scientific_consistency_audit.md`
- External-review resolution record: `manuscript/external_review_resolution.md`
- Data and redistribution boundary: `DATA_AVAILABILITY.md`

## Install

Python 3.11-3.13 is the declared compatibility range, not a claim that every version/platform combination has been tested. The canonical project metadata are in `pyproject.toml`.

```powershell
python -m pip install -r requirements-publication.txt
```

`requirements-publication.txt` installs the exact tested packages in `requirements-lock.txt` plus the editable project. For development without a locked solve, install from project metadata:

```powershell
python -m pip install -e ".[test,full]"
```

`environment-lock.yml` records a Windows environment snapshot; it is not proof of a clean dependency solve. Raster/GIS results may depend on GDAL, PROJ and GEOS builds, so a successful run must also satisfy the scientific contract tests. NumPy binary-compatibility warnings fail the test gate. Use an isolated environment rather than mixing incompatible Conda and pip binaries.

## Reproduce

### Compact reviewer mode

```powershell
python scripts/reproduce.py --mode derived
```

This mode verifies archived inputs in `data/derived_input_manifest.json` by byte size and SHA-256, then rebuilds the 68-station statistics, decision diagnostics, Figures 2 and 4 and Supplementary Figure S1, manuscript, Supplementary Information, report and internal audit. Other figures are retained as archived assets because their generation requires rasters or map context. It is a **derived-input-to-paper** reproduction, not a raw-data reconstruction.

### Full upstream mode

After acquiring the provider files listed in `data/upstream_raw_manifest.csv`, verify them before calculation:

```powershell
python scripts/reproduce.py --mode full --verify-only
```

Then run the full local raw-to-paper chain:

```powershell
python scripts/reproduce.py --mode full
```

This mode rebuilds station integration, return-level diagnostics, official-mask terrain metrics, the 74 x 40 robustness grid, the frozen 68-station analysis, spatial statistics, local-DTM product/datum checks, all figures and all documents. Large third-party inputs are intentionally not copied into Git.

## Release gate

The publication gate runs the full workflow, updates checksummed manifests, builds the credential-scanned reviewer ZIP and executes that ZIP in a temporary isolated directory:

```powershell
python scripts/run_major_revision_rebuild.py
```

To build and validate the archive separately:

```powershell
python scripts/build_major_revision_package.py
python scripts/validate_reviewer_archive.py
```

Receipts record package byte size, SHA-256 and Git baseline. A PASS proves that the archived derived workflow executes in the tested environment; it does not validate upstream scientific products or substitute for an independent flood-outcome benchmark.

## Methods encoded in the repository

- `config/coastal_spatial_blocks_v2.csv` provides reviewed station-to-basin mappings and 100/150/250 km approximate coastline-contiguous blocks. Coordinate-threshold sectors are not used for inference.
- The primary terrain topology uses an 8-neighbour official water graph and a 4-neighbour land graph. All four water/land 4/8 combinations are reported as sensitivity analyses.
- Restricted-permutation two-sided probabilities use empirical lower and upper tails of the constrained null distribution; they are not centered on zero.
- Top-k selection is deterministic at ties using station identifiers.
- Source tables for every figure and reported diagnostic are under `data/figure_source/`.
- Scientific contracts are under `tests/` and can be run with:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest tests
```

## Repository structure

```text
src/coastal_screening/   reusable scientific logic
scripts/                 command-line workflows and document builders
tests/                   scientific and reproducibility contracts
config/                  frozen, reviewed analysis configuration
data/figure_source/      project-generated source tables
figures/main/            SciencePlots figures in PNG and PDF
manuscript/              manuscript, supplement and audit documents
audit/                   review and release evidence
docs/                    project documentation
```

## Data and citation

The repository includes project-authored code and derived data. COAST-RP, GSSR, DeltaDTM, national LiDAR/AHN data, basemap data and third-party papers remain governed by their providers. Their authoritative sources, local SHA-256 records and redistribution status are documented in `DATA_AVAILABILITY.md` and `data/upstream_raw_manifest.csv`.

Author metadata, funding statements and a formal archival DOI remain to be supplied before journal submission; they are not inferred by the workflow.
