# Core reference verification

This file records the key source checks used by the manuscript. It is not a substitute for journal-format reference management, but it prevents accidental citation drift during revision.

## Verified core sources

| Manuscript use | Verified source | DOI / persistent URL | Notes |
|---|---|---|---|
| Global Storm Surge Reconstruction (GSSR) | Tadesse, M. G. & Wahl, T. A database of global storm surge reconstructions. *Scientific Data* 8, 125 (2021). | https://doi.org/10.1038/s41597-021-00906-x | Supports the GSSR surge-residual reconstruction database framing. |
| GSSR data collection | A Database of Global Storm Surge Reconstruction (GSSR). figshare collection. | https://doi.org/10.6084/m9.figshare.c.5124878 | Persistent data collection referenced by the Scientific Data paper. |
| COAST-RP | COAST-RP: A global COastal dAtaset of Storm Tide Return Periods. 4TU.ResearchData / Figshare. | https://doi.org/10.4121/13392314 | Contains storm-tide return levels for 1, 2, 5, 10, 25, 50, 100, 250, 500 and 1000-year return periods. |
| DeltaDTM | Pronk, M. et al. DeltaDTM: A global coastal digital terrain model. *Scientific Data* 11, 273 (2024). | https://doi.org/10.1038/s41597-024-03091-9 | Supports use of DeltaDTM as global coastal terrain data. |
| ERA5 | Hersbach, H. et al. The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society* 146, 1999-2049 (2020). | https://doi.org/10.1002/qj.3803 | Supports ERA5-derived meteorological variables accessed through Open-Meteo. |

## Citation cautions

- COAST-RP is a storm-tide return-level product, not a surge-residual product.
- GSSR provides reconstructed surge residuals and should not be described as observed total water level.
- Open-Meteo is an access route for meteorological variables in this workflow; the scientific data provenance for historical weather is ERA5.
- DeltaDTM supports terrain screening, but the present manuscript uses relative static sensitivity rather than dynamic flood modelling.

## Sources checked

- Nature Scientific Data page for GSSR: `https://www.nature.com/articles/s41597-021-00906-x`
- Figshare/4TU COAST-RP dataset page: `https://figshare.com/articles/dataset/COAST-RP_A_global_COastal_dAtaset_of_Storm_Tide_Return_Periods/13392314`
- Nature Scientific Data page for DeltaDTM: `https://www.nature.com/articles/s41597-024-03091-9`
- Wiley DOI page for ERA5: `https://doi.org/10.1002/qj.3803`
