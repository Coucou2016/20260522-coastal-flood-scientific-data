# Task A: Terrain algorithm, statistics, and reproducibility remediation

## Background and objective

This repository supports a Communications Earth & Environment manuscript comparing COAST-RP storm-tide magnitude with a DeltaDTM-derived connected-lowland screening metric across Northwest Europe. A penetrating audit found that arithmetic identities are internally consistent, but the terrain connectivity implementation, sample construction, statistical uncertainty, and rebuild chain require correction before the scientific results can be trusted for submission.

You are an external senior scientific-software engineer. Inspect every provided script and machine-readable source table relevant to these findings. Produce the smallest coherent code/data patch that corrects the implementation and regenerates auditable outputs. Do not accept existing manuscript claims or audit PASS files as evidence by themselves.

## Current architecture and boundaries

- Python scientific/geospatial workflow under `scripts/`.
- Canonical manuscript source: `manuscript/process_terrain_coastal_flood_CEE_manuscript.md`.
- Figure/table source data: `data/figure_source/` and `data/processed/`.
- Main figures: `figures/main/`.
- Publication gates are Windows `.cmd` wrappers plus Python audit scripts.
- Raw COAST-RP NetCDF, DeltaDTM tiles, local DTM rasters, tokens, credentials, browser state, and large generated standalone HTML are intentionally excluded from the review ZIP.
- Do not fabricate raw-data validation. Where a rerun requires excluded raw inputs, implement/test the logic with synthetic fixtures and specify the exact local command and expected invariants for Codex to run against the real local data.

## Required remediation

1. Fix the finite-window marine seed bug. The present `binary_propagation(ocean, mask=ocean|river)` silently returns zero for windows containing river class but no ocean class. Implement a defensible rule: build/consume a larger ocean-to-river connectivity context before the 10 km analysis crop, or classify such windows as unresolved/excluded. Never interpret absence of an ocean seed in the crop as zero connected terrain.
2. Use official DeltaDTM mask semantics: land=0, ocean=1, lake=2, river=3, clipped=255. Lakes and 255 are never marine seeds. Rivers may be tidal seeds only when connected to an ocean component in the larger context. Record per-window class counts and seed provenance.
3. Add explicit COAST-RP spatial-match eligibility/sensitivity. The current 74-site table contains matches up to about 39 km although manuscript/audits claim <6 km. Implement one declared primary threshold and sensitivity tables for practical alternatives. No hidden focal-site-only audit.
4. Add spatial/coastal-sector block bootstrap or permutation for the 74-site main sample. Keep ordinary station permutation as a comparator. Report effect sizes and two-sided uncertainty. Top-set overlap/mismatch must remain descriptive unless it falls outside its null envelope.
5. Correct determinism and geospatial details: stable RNG seeds (not Python `hash()`), deterministic tile ordering, transform-derived cell centres/areas, CRS/transform assertions, rasterio reprojection instead of array-only zoom when grids differ, and actual MD5/SHA verification of downloaded mask inputs.
6. Resolve return-level implementation ambiguity. The current function labelled Weibull uses a discrete order statistic and RP50/RP100 can collapse to the sample maximum. Either implement/document the exact empirical estimator with valid interpolation and record-length limits, or rename it honestly and restrict unsupported return periods. Remove dead GEV-bootstrap columns or execute a valid reproducible bootstrap.
7. Replace statistical-significance gates with correctness gates. Audit scripts must test formulas, dimensions, allowed mask classes, sample definitions, file provenance, deterministic hashes, and semantic invariants; they must not fail merely because a scientific p-value exceeds 0.05.
8. Repair the reproducibility package. Preserve paths/import closure, generate a canonical fail-fast DAG/entrypoint, run from an empty extracted directory, and prevent stale output reuse. Figure 1/2, water-level diagnostics, terrain metrics, statistics, manuscript/report exports, and audits must have explicit provenance. If raw licensed inputs cannot be redistributed, the package must fail clearly and document acquisition/hash checks rather than silently reuse outputs.
9. Add focused automated tests using compact synthetic rasters/tables. At minimum cover ocean+river connectivity, river-without-ocean unresolved behavior, lake exclusion, 255 exclusion, four/eight-neighbour behavior, deterministic overlap resolution, match-distance filtering, top-k null behavior, and clean-package import closure.

## Scientific framing constraint

COAST-RP return levels and the fixed `2 m` DeltaDTM/EGM2008 screening threshold are not presently harmonized to a common local vertical datum. Do not claim that RP10 has been converted into terrain inundation. Either propose a concrete harmonization workflow with required source data, or enforce a code/manuscript boundary that treats them as two complementary standardized indicators.

## Deliverables

1. `TASK_A_REVIEW.md`: findings, reasoning, assumptions, and any raw-data blockers.
2. A unified diff against the provided tree, plus a ZIP containing every added/modified file with original relative paths.
3. Automated tests and exact commands.
4. A machine-readable output/data dictionary for changed canonical tables.
5. A migration note identifying legacy outputs that must be deleted, regenerated, or labelled historical.
6. A proposed primary sample definition and statistical endpoint, with sensitivity hierarchy.

## Mandatory tests

- Python AST/compile check for all scripts.
- Unit tests for the cases above.
- Deterministic rerun: two clean runs must produce byte-identical machine-readable results or documented exceptions.
- Empty-directory reproducibility package extraction and entrypoint test.
- Recalculation of arithmetic identities: connected + unconnected = all below; fractions and areas share the same denominator; threshold curves are monotonic where scientifically required.
- Comparison of 74-site baseline with no-ocean-seed exclusions/unresolved records and declared COAST-RP distance thresholds.

## Prohibited actions and claims

- Do not invent missing raw data, datum transformations, station metadata, values, citations, DOIs, authors, funding, or validation outcomes.
- Do not call a native-datum local DTM comparison an independent validation.
- Do not use `distortion`, `mis-rank`, `true hotspot`, or beyond-chance language without a defensible truth benchmark/test.
- Do not require statistical significance for a software audit to pass.
- Do not commit, push, create a PR, deploy, or modify production/external services.

## Acceptance criteria

- Every record with no defensible ocean/tidal seed is unresolved/excluded rather than silently zero.
- Primary/sensitivity sample membership and COAST-RP distances are machine-readable and consistent with prose.
- Spatially aware uncertainty is reported for the main 74-site diagnostic.
- Tests fail on the old seed bug and pass on the corrected implementation.
- A clean extracted package runs without reaching into the original parent workspace or reusing stale artifacts.
- All result-generating scripts use deterministic seeds/order and preserve geospatial transforms.

