# Citation metadata template

Use this template to create `CITATION.cff` or repository citation metadata after the final author list and archive DOI are confirmed.

## Suggested citation fields

```yaml
cff-version: 1.2.0
message: "If you use this manuscript package, processed source data, or code, please cite both the archived package and the upstream data products."
title: "Process-terrain coastal flood susceptibility screening using open water-level, meteorological and terrain data"
authors:
  - family-names: "[Family name]"
    given-names: "[Given name]"
    affiliation: "[Affiliation]"
    orcid: "[ORCID if available]"
doi: "[Repository DOI after deposit]"
date-released: "[YYYY-MM-DD]"
version: "[Release version]"
repository-code: "[Repository URL]"
type: dataset
keywords:
  - coastal flooding
  - storm surge
  - storm tide
  - DeltaDTM
  - GSSR
  - COAST-RP
  - ERA5
  - terrain sensitivity
  - reproducible screening
```

## Required upstream citations

The repository citation should not replace upstream data citations. Cite at minimum:

- GSSR data collection: https://doi.org/10.6084/m9.figshare.c.5124878
- COAST-RP: https://doi.org/10.4121/13392314
- DeltaDTM Scientific Data paper: https://doi.org/10.1038/s41597-024-03091-9
- ERA5: https://doi.org/10.1002/qj.3803

## Before release

- Replace all bracketed fields.
- Confirm final author order.
- Confirm whether the archive should be typed as `dataset`, `software`, or a repository-specific mixed object.
- Ensure the repository DOI matches the Data availability and Code availability statements in the manuscript.
