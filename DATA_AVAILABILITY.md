# Data availability and redistribution boundary

This public repository contains project-authored analysis code, configuration, tests, processed station tables, figure-source tables, figures, manuscript exports and audit records needed to inspect the reported calculations.

## Included in Git

- `src/`, `scripts/`, `tests/` and `config/`: scientific logic, executable workflows, contracts and frozen analysis configuration.
- `data/processed/` and `data/figure_source/`: project-generated intermediate, station-level and figure-source outputs.
- `figures/`, `manuscript/`, `audit/`, `docs/` and the standalone HTML, Markdown and PDF exports.
- `data/upstream_raw_manifest.csv` and `.json`: local relative path, byte size, SHA-256, provider source and redistribution status for upstream files used at release time.
- `data/derived_input_manifest.json`: hashes of compact derived inputs used by reviewer-mode reproduction.

## Not copied into Git

Upstream raw products total several gigabytes, include files above GitHub limits and remain subject to provider licences. Third-party reference PDFs are also excluded. They are identified through DOI/URL citations and manifests rather than presented as project-authored data.

| Dataset | Role | Authoritative source |
| --- | --- | --- |
| COAST-RP v2 | Storm-tide return levels | <https://doi.org/10.4121/13392314.v2> |
| Global Storm Surge Reconstruction | Daily reconstructed surge residuals and metadata | <https://doi.org/10.6084/m9.figshare.c.5124878> |
| DeltaDTM v1.1 | Standardized terrain elevations and official mask classes | <https://doi.org/10.4121/21997565.v4> |
| Open-Meteo Historical Weather API | Supporting process-coherence variables | <https://open-meteo.com/en/docs/historical-weather-api> |
| Environment Agency LiDAR | United Kingdom local-DTM cross-checks | <https://environment.data.gov.uk/> |
| AHN / PDOK | Netherlands local-DTM cross-checks | <https://www.ahn.nl/> |
| Natural Earth | Map context | <https://www.naturalearthdata.com/> |

The local-DTM comparisons retain native provider vertical datums and are reported only as product/datum/resolution/provider-resampling sensitivity. They are not validation against a common flood surface. The regional `+2 m` terrain threshold is referenced to the DeltaDTM EGM2008 product datum and is not a local mean-sea-level flood elevation.

## Reproduction scopes

Reviewer mode starts from archived, checksummed derived inputs:

```powershell
python -m pip install -e ".[test]"
python scripts/reproduce.py --mode derived
```

Full mode verifies and then uses the locally acquired upstream files:

```powershell
python -m pip install -e ".[test,full]"
python scripts/reproduce.py --mode full --verify-only
python scripts/reproduce.py --mode full
```

The two modes must not be described interchangeably. Derived mode recalculates statistics and Figures 2, 4 and S1; raster-dependent maps and other supplementary figures remain archived inputs. Full mode requires the provider data listed in `data/upstream_raw_manifest.csv`. Supporting historical GSSR, meteorological and tidal inputs also remain provenance-tracked dependencies; successful execution must not be described as reacquisition of every upstream product.

## Release archives

The reviewer ZIP is produced only after a credential scan and is kept out of Git history because it duplicates repository content. Its receipt records SHA-256 and Git baseline. Independent archive validation extracts the ZIP to a new temporary directory, installs it without resolving new dependencies, reruns derived reproduction and verifies deterministic scientific outputs.

```powershell
python scripts/build_major_revision_package.py
python scripts/validate_reviewer_archive.py
```

The GitHub release may distribute the reviewer ZIP and receipt. A formal repository DOI is pending final version freeze.
