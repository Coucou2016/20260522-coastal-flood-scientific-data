# Nature Portfolio Reporting Summary preparation

This document prepares information likely needed if Communications Earth & Environment requests a Nature Portfolio Reporting Summary. It is based on Nature Portfolio reporting-standards guidance checked on 2026-06-01.

## Official guidance checked

- Nature Portfolio reporting standards and availability of data, materials, code and protocols: `https://www.nature.com/nature/editorial-policies/reporting-standards`
- Nature Portfolio Reporting Summary PDF template: `https://www.nature.com/documents/nr-reporting-summary-Apr-2023-flat.pdf`
- Springer Nature Earth, environmental and space sciences repository guidance: `https://www.springernature.com/gp/authors/research-data-policy/earth-and-environmental-science-repositories/12327148`

## Study design

| Item | Prepared response |
|---|---|
| Study type | Reproducible environmental data-integration and screening study. |
| Randomization | Not applicable. The analysis uses fixed public environmental datasets and selected tide-gauge sites. |
| Blinding | Not applicable. No treatment assignment or human/animal subjects are involved. |
| Sample size | Eight tide-gauge sites for water-level and meteorological diagnostics; five European sites for DeltaDTM terrain screening. Site selection is purposive and diagnostic, not powered for statistical population inference. |
| Replication | Computational replication is supported through scripts, figure source data, and the finalization workflow. Statistical replication across a broader site set is future work. |

## Data exclusions

| Item | Prepared response |
|---|---|
| Excluded stations | No selected station is excluded from the water-level and meteorological diagnostic workflow. Only the five European sites are included in the current DeltaDTM terrain-screening subset because the relevant DeltaDTM Europe tiles were processed locally. |
| Excluded terrain cells | DeltaDTM no-data cells are masked. Terrain sensitivity is reported for a coastal-lowland mask, and ocean-connected sensitivity excludes isolated low cells not connected to boundary water/no-data. |
| Outliers | The current workflow uses empirical diagnostics and rank correlations; no manual outlier removal should be applied unless documented in source code and audit logs. |

## Data availability

| Item | Prepared response |
|---|---|
| Upstream data | GSSR, COAST-RP, DeltaDTM, ERA5/Open-Meteo historical meteorology. |
| Processed data | Station metadata, matched COAST-RP indicators, GSSR empirical indicators, meteorological correlations, DeltaDTM terrain summaries, and figure source CSV files. |
| Repository requirement | Processed outputs and compact reproducibility package should be deposited in a public repository before final submission. |

## Code availability

| Item | Prepared response |
|---|---|
| Custom code | Local scripts under `scripts/`. |
| Main finalization entry point | `scripts/finalize_cee_publication_package.py`. |
| Audit entry point | `scripts/audit_publication_readiness.py`. |
| Archive requirement | Code and compact package should be archived with a DOI or persistent identifier before final submission. |

## Software and dependencies

See `software_environment.md`, `requirements.txt`, and `environment.yml`.

## Human or animal subjects

Not applicable. The study uses public environmental datasets and does not involve human participants, animal subjects, clinical samples, or personal data.

## Image integrity

The figures are generated from scripts and source tables. The final package includes PNG/PDF versions of main figures and source CSV files. Figure 4 terrain overlays are computed using a documented ocean-connected static sensitivity mask; they should not be interpreted as photographic imagery or observed flood extents.

## Remaining author actions

- Complete repository DOI fields.
- Confirm author, funding, competing-interest and ethics statements.
- Review current Nature Portfolio Reporting Summary form immediately before submission.
