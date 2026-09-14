# Title page and declarations draft

This file records the title-page and declaration metadata that accompany the manuscript. Author-governance details are supplied through the journal submission system and the signed author confirmation form.

## Title

A process-terrain screening framework for coastal flood susceptibility using open water-level, meteorological and terrain data

## Running title

Process-terrain coastal flood screening

## Authors

Author identities, affiliations and ORCID identifiers are supplied through the journal submission system and the signed author confirmation form.

## Corresponding author

The corresponding-author identity, email address and institutional address are supplied through the journal submission system and the signed author confirmation form.

## Keywords

coastal flooding; storm surge; storm tide; DeltaDTM; GSSR; COAST-RP; ERA5; terrain sensitivity; reproducible screening

## Data availability

The upstream data products used in this study are publicly available. The Global Storm Surge Reconstruction (GSSR) database is described by Tadesse and Wahl and is available as a Figshare collection (https://doi.org/10.6084/m9.figshare.c.5124878). COAST-RP storm-tide return levels are available through 4TU.ResearchData / Figshare (https://doi.org/10.4121/13392314). DeltaDTM is described by Pronk et al. and available through its public data release. ERA5-derived meteorological variables were accessed through the Open-Meteo historical weather API.

Processed source tables and the compact reproducibility package are prepared for public repository deposit. Repository URL and DOI metadata are recorded in the repository deposit checklist and final archive manifest after deposit.

## Code availability

Custom code used for data verification, processing, figure generation, manuscript report generation and publication-readiness auditing is stored under `scripts/`. The final local workflow is `scripts/finalize_cee_publication_package.py`. Code archive metadata are recorded in the repository deposit checklist and final archive manifest after deposit.

## Funding

The funding statement is supplied through the journal submission system and the signed author confirmation form.

## Competing interests

The authors declare no competing interests.

## Author contributions

Author contribution statements are supplied through the journal submission system and the signed author confirmation form. They are not inferred from computational provenance.

## Ethics and permissions

This study uses public environmental datasets and does not involve human participants, animal subjects, clinical samples, personal data or restricted data.

## AI-use disclosure

AI-assisted tools were used to support code review, workflow organization, manuscript editing, figure-quality review, and the preparation of reproducibility/audit documentation. The scientific framing, interpretation boundaries, data selection, and final manuscript decisions remain the responsibility of the authors. All numerical results, figures and tables used in the manuscript are required to be generated from the cited public datasets and local processing scripts; no data were fabricated. No AI tool is listed as an author.

## Final submission checks

- `python scripts\finalize_cee_publication_package.py` exited with code 0.
- `PUBLICATION READINESS AUDIT: PASS` is recorded in `manuscript/publication_readiness_report.md`.
- `publication_package.zip` exists and has been inspected.
- Author/funding/competing-interest/repository metadata have been completed.
