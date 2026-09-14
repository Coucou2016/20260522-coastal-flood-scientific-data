# Data repository deposit checklist

Use this checklist before depositing the processed data and compact reproducibility package in Zenodo, OSF, Figshare, institutional repository, or another suitable public archive.

## Deposit recommended

- `publication_package.zip`
- `publication_package/package_manifest.json`
- `manuscript/publication_readiness_report.md`
- `data/figure_source/*.csv`
- `figures/main/*.png`
- `figures/main/*.pdf`
- `scripts/` key processing, figure-generation and audit scripts included in the compact package
- `requirements.txt`
- `environment.yml`
- `config/combo1_stations.yaml`
- `manuscript/figure_source_data_dictionary.md`
- `manuscript/software_environment.md`
- `manuscript/reference_verification.md`

## Cite rather than duplicate, unless repository policy and licenses support duplication

- Full GSSR upstream archives
- Full COAST-RP upstream dataset
- Full DeltaDTM continental or global archives
- Full Open-Meteo / ERA5 raw API responses if large

These upstream products should be cited through their original repositories and DOIs. If selected raw subsets are deposited, document exactly which files are included and why.

## Metadata to provide

- Title
- Authors and affiliations
- Description of processed outputs
- Related manuscript title
- Related upstream data DOIs
- Software requirements
- License for processed source tables and scripts
- Version number or release date
- Contact email

## Suggested keywords

- coastal flooding
- storm surge
- storm tide
- DeltaDTM
- GSSR
- COAST-RP
- ERA5
- Open-Meteo
- terrain sensitivity
- reproducible screening

## License considerations

Confirm upstream data terms before assigning a license to redistributed processed outputs. Code and processed summary tables may require different licenses. Do not imply that upstream raw data are relicensed by this project.

## After deposit

- Record repository DOI or persistent URL in the manuscript Data availability section.
- Record code/package DOI or persistent URL in the Code availability section.
- Update `author_final_confirmation_form.md`.
- Update `publication_release_notes_template.md` for the archived version.
