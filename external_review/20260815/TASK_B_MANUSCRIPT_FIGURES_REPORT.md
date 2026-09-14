# Task B: Manuscript, figures, report, references, and submission coherence remediation

## Background and objective

The study currently argues that COAST-RP storm-tide magnitude and a fixed-threshold DeltaDTM connected-lowland metric produce different screening priorities across Northwest Europe. The draft is scientifically promising but contains stale figures, mixed legacy/current tables, incomplete citations, overly strong wording in places, and non-canonical standalone exports. Your role is an external senior CEE-style manuscript and scientific-visualization reviewer/author.

Review the supplied manuscript, research-report source, figures, source tables, and audit documents. Produce a publication-focused rewrite and figure specification that is fully consistent with the corrected scientific boundaries below. Code changes to figure/report generators are expected where needed.

## Non-negotiable scientific boundaries

- The fixed `2 m` terrain threshold is referenced to DeltaDTM/EGM2008 and is a standardized static terrain screen, not a site-specific RP10 flood level or forecast.
- COAST-RP RP10 and connected-terrain response are complementary indicators unless a verified vertical-datum conversion is added.
- Top-set mismatch is descriptive and is interpreted against a null envelope; it is not automatically more discordant than chance.
- Local DTM comparisons in native ODN/NAP/other datums are cross-product/datum sensitivity checks, not independent validation.
- River-only windows lacking an ocean seed are unresolved until Task A corrects/reruns them.
- The 74-site all-spatial sample is the intended primary terrain-ranking sample only after seed and distance eligibility are corrected; GSSR-qualified subsets serve product-definition analyses.
- Do not invent data, citations, authors, funding, repository DOI, or missing metadata. Mark them `待补充`/`TO BE COMPLETED` where necessary.

## Required remediation

1. Rewrite title, abstract, Introduction, Results, Discussion, Methods, conclusions, captions, cover letter, and significance statement so claims match the evidence. Remove implications that water-level magnitude was converted into terrain response or that connected terrain is ground truth.
2. Repair reference coverage and ordering. Every reference must be cited at the relevant first occurrence and numbered in first-appearance order. Add year/access information to web references where verifiable from the supplied material; otherwise flag it. Do not fabricate bibliographic metadata.
3. Replace stale Figure 1 content (`30 stations`, `1/6`, `83%`) with the current study design and clearly distinguish the all-spatial, GSSR-qualified, tidal-metadata, focal, and local-DTM subsets. Figure 1 must use a real geographic basemap or defensible static geographic context and readable station coordinates/legend.
4. Correct Figure 2 so the tidal panel visibly distinguishes the 13 source-verified tidal stations from indicative/context-only stations and reports exactly which subset each statistic uses.
5. Redesign Figure 3 as a transparent connectivity audit. Use deterministic/archetype-selection language; show ocean/tidal seed, connected cells, unconnected low cells, other denominator land, excluded/clipped cells, station, crop boundary, scale bar, and connected path/component evidence. Do not visually inflate low inundation or suppress saturated/high-response cells. Prefer nine logically grouped panels only if each remains legible at final size.
6. Make Figure 4 the central statistical synthesis: raw magnitude versus raw terrain metric, top-k overlap curve with null median/envelope, spatial/block uncertainty, explicit direction of ranks, and declared sample eligibility. Avoid sign confusion.
7. Separate legacy degree-window/boundary-proxy outputs from current fixed-km official-mask results. Legacy values may appear only as clearly labelled historical/sensitivity comparisons, not mixed in current result tables.
8. Move dense tables and peripheral meteorological diagnostics to Supplementary Information. Main text should retain at most one or two compact tables and four coherent main figures.
9. Update the parallel research report in Chinese. It must explain research background, data provenance, methods, equations/terms, audit history, results, limitations, and conclusions in accessible but rigorous language. Every figure/table needs detailed context and interpretation. Unknowns must be marked, never invented.
10. Preserve fully self-contained `paper.html` and `report.html`: internal CSS, Base64 images, inline HTML tables, no local/network dependencies. Also produce matching Markdown and PDF through local generators.
11. Align all manuscript/report/title-page/cover-letter/checklist files to one canonical title and one result version. Add an appropriate AI-use disclosure location per journal guidance, without inventing author approval.

## Deliverables

1. `TASK_B_REVIEW.md`: prioritized editorial/scientific findings with exact file references.
2. Unified diff plus ZIP of added/modified files preserving paths.
3. Revised manuscript source and research-report source.
4. Revised figure-generation code/specification and source-data mapping for each panel.
5. Reference citation map: reference -> first in-text citation -> supporting claim.
6. A submission-coherence checklist covering title, sample sizes, statistics, figure numbers, captions, supplementary tables, data/code statements, and pending metadata.

## Mandatory checks

- Search all deliverables for stale `30-station`, `1/6`, `83%`, legacy Sheerness `39.25%`, legacy Hoek `3.10%`, and overclaim vocabulary; each occurrence must be current, explicitly historical, or removed.
- Verify every displayed number against the supplied source table and record the file/column.
- Verify every main and supplementary figure is cited, captioned, and uniquely mapped to source data.
- Verify font/readability at final manuscript size and no row contains more than two dense maps unless a nine-panel audit remains legible.
- Validate standalone HTML; visually inspect rendered HTML/PDF at desktop and print widths.
- Do not mark submission-ready while author, DOI/reviewer link, funding, or repository metadata remain pending.

## Prohibited actions and claims

- Do not fabricate values, affiliations, authors, funding, repository URLs, DOI, or real-world flood validation.
- Do not make stylistic changes that conceal zero/low results or exaggerate visual balance.
- Do not present map basemaps or third-party tiles without attribution/licence compatibility.
- Do not commit, push, deploy, or contact the journal.

## Acceptance criteria

- One canonical title, sample definition, statistic set, and figure numbering across all artifacts.
- The abstract states the main effect size, its spatially aware uncertainty status, and the complementary-indicator interpretation without overstating null-envelope evidence.
- Figure 1 reflects the corrected current sample; Figure 3 directly demonstrates classification/connection; Figure 4 transparently shows the statistical result and null comparison.
- All references are actually cited and ordered correctly.
- Manuscript, report, HTML, Markdown, PDF, source tables, and captions agree numerically.
- Remaining external blockers are explicit and cannot be mistaken for completed validation or submission readiness.

