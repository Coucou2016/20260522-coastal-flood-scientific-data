# Data and code availability final draft

This draft is written in a form that can be adapted directly into the manuscript after the processed outputs and compact package have been archived in a public repository.

## Data availability

The upstream data products used in this study are publicly available. The Global Storm Surge Reconstruction (GSSR) database is described by Tadesse and Wahl and is available as a Figshare collection (https://doi.org/10.6084/m9.figshare.c.5124878). COAST-RP storm-tide return levels are available through 4TU.ResearchData / Figshare (https://doi.org/10.4121/13392314). DeltaDTM is described by Pronk et al. and available through its public data release. ERA5-derived meteorological variables were accessed through the Open-Meteo historical weather API.

The processed data products generated for this manuscript include station metadata, matched COAST-RP indicators, GSSR empirical return-level indicators, Open-Meteo/GSSR daily merged driver tables, meteorological-correlation tables, DeltaDTM terrain-sensitivity summaries, and figure source CSV files. These processed outputs should be deposited in a public repository before submission. Repository URL and DOI should be inserted here after deposit.

## Code availability

Custom code used to download, verify, process, analyse and visualize the data is stored in the local `scripts/` directory. The final local release workflow is `scripts/finalize_cee_publication_package.py`, which rebuilds figures, rebuilds the standalone manuscript review HTML, verifies data and figure consistency, and assembles `publication_package/` and `publication_package.zip`. The code and compact publication package should be archived in a public repository before submission. Repository URL and DOI should be inserted here after deposit.

## Repository deposit checklist

Before replacing this draft in the manuscript:

- Archive `publication_package.zip`.
- Archive figure-source CSV files.
- Archive key scripts and environment files.
- Include `publication_readiness_report.md`.
- Include upstream-data DOI references.
- Add repository DOI or persistent URL to the manuscript.
- Confirm that raw large upstream data files are either deposited where allowed or clearly referenced through their original public repositories.
