# Data availability and redistribution boundary

This public repository contains the complete project-authored analysis code,
configuration, tests, processed station tables, figure-source tables, figures,
manuscript exports, scientific-integrity audit and revision records needed to
inspect the reported calculations.

## Included in Git

- `data/processed/`: project-generated intermediate and station-level outputs.
- `data/figure_source/`: machine-readable source data for every reported figure
  and supplementary analysis.
- `config/`, `scripts/`, and `tests/`: the frozen analysis configuration,
  executable workflow and scientific contract tests.
- `figures/`, `manuscript/`, `reports/`, `docs/`, `logs/`, and the standalone
  HTML, Markdown and PDF exports.
- `data/upstream_raw_manifest.csv` and
  `data/upstream_raw_manifest.json`: local path, byte size, SHA-256 digest,
  source DOI/URL and redistribution status for every upstream raw file used in
  the local workspace at release time.

## Not copied into Git

Upstream raw products are not committed. They total several gigabytes, include
files larger than GitHub's per-file limit, and remain governed by their source
providers' licences and citation requirements. The manifest and download code
allow a reviewer to identify and reacquire the exact inputs without treating
third-party files as project-authored data.

| Dataset | Role in this study | Authoritative source |
| --- | --- | --- |
| COAST-RP v2 | Storm-tide return levels | <https://doi.org/10.4121/13392314.v2> |
| Global Storm Surge Reconstruction (GSSR) | Daily reconstructed surge residuals and metadata | <https://doi.org/10.6084/m9.figshare.c.5124878> |
| DeltaDTM v1.1 | Standardized coastal terrain screen and mask classes | <https://doi.org/10.4121/21997565.v4> |
| Open-Meteo Historical Weather API | ERA5-derived process-coherence variables | <https://open-meteo.com/en/docs/historical-weather-api> |
| Environment Agency LiDAR | United Kingdom local-DTM cross-checks | <https://environment.data.gov.uk/> |
| AHN / PDOK | Netherlands local-DTM cross-checks | <https://www.ahn.nl/> |
| Natural Earth | Map context | <https://www.naturalearthdata.com/> |
| CARTO basemap tiles | Historical map cache only; not redistributed | <https://carto.com/attributions> |

The local-DTM comparisons use native provider datums and are reported as
product/datum/provider-resampling sensitivity, not validation against a common
flood surface. The `+2 m` terrain threshold is referenced to the DeltaDTM
EGM2008 product datum and is not a local mean-sea-level flood elevation.

## Reference articles

PDF and Markdown copies of third-party reference papers used during manuscript
editing are deliberately excluded from the public repository. The manuscript
bibliography and the table above provide authoritative DOI links. Their absence
does not remove any project result or executable analysis dependency.

## Release archives

The credential-scanned reviewer bundle and reproducibility bundle are attached
to the GitHub release. They are kept out of Git history because their contents
duplicate repository files. SHA-256 receipts are committed at repository root.

## Rebuilding

After acquiring the upstream inputs, run:

```powershell
python scripts/run_major_revision_rebuild.py
python scripts/build_major_revision_package.py
```

The first command rebuilds the analysis and all documents, validates standalone
HTML, and runs the scientific contract tests. The second produces the reviewer
archive and its credential-scan receipt.

