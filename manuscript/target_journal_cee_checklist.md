# Communications Earth & Environment submission checklist

This checklist is based on the Communications Earth & Environment / Nature Portfolio guidance checked on 2026-06-01. Verify the journal website again immediately before submission because publisher requirements may change.

## Official pages checked

- Content types: `https://www.nature.com/commsenv/submit/content-types`
- Submission guidelines: `https://www.nature.com/commsenv/submit/submission-guidelines`
- Guide to authors: `https://www.nature.com/commsenv/submit/guide-to-authors`
- Editorial process: `https://www.nature.com/commsenv/submit/editorial-process`
- Nature Portfolio AI policy: `https://www.nature.com/nature-portfolio/editorial-policies/ai`
- Nature Portfolio reporting standards and data/code availability: `https://www.nature.com/nature/editorial-policies/reporting-standards`

## Initial-submission implications for this manuscript

| Requirement area | Practical action for this project |
|---|---|
| Article type | Treat the manuscript as an Article / primary research submission. |
| Initial formatting | The journal indicates that strict formatting is not required at initial submission; still keep the manuscript clear, complete and professionally structured. |
| Figures in initial submission | Embed figures in the main review file and ensure that all figures are legible at review scale. The standalone HTML and main PNG/PDF files support this. |
| Data availability | Provide public upstream data citations and a repository/persistent identifier for processed source tables before final submission. |
| Code availability | Provide a public code archive or package DOI before final submission. Nature Portfolio guidance indicates that code availability should be a separate section after data availability and before references. |
| Reporting summary | If the manuscript is sent to review, be prepared to complete the Nature Portfolio Reporting Summary. |
| Funding and competing interests | Require author confirmation; do not infer from analysis files. |
| AI-use statement | Nature Portfolio policy indicates that LLMs do not meet authorship criteria. Use beyond AI-assisted copy-editing should be documented in Methods or another suitable section. |
| Earth/environmental data sharing | Nature Portfolio reporting guidance states that Earth, space and environmental science papers should share data through appropriate repositories where available. Deposit processed source tables and the compact reproducibility package before final submission. |

## Project-specific readiness checks

- Run `python scripts\finalize_cee_publication_package.py`.
- Confirm `PUBLICATION READINESS AUDIT: PASS`.
- Open `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html` and visually inspect all figures.
- Confirm Figure 4 uses boundary-seeded ocean-connected sensitivity, not unfiltered bathtub flooding.
- Confirm Table 4 reports `Median coastal-lowland elevation (m)`.
- Confirm no unresolved placeholders remain in the manuscript text.
- Complete `author_final_confirmation_form.md`.
- Complete repository DOI fields after public archival.

## Items not solved by code

- Author order and affiliations.
- Journal account/submission metadata.
- Funding and competing-interest statements.
- Repository release and DOI creation.
- Final journal-specific production formatting after acceptance.
