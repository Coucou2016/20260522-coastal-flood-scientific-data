# Reproduction environment follow-up

## Scope

This is an internal execution record, not an independent peer review or proof of scientific validity. It records the environment and gates used to reproduce the archived analysis. Scientific interpretation remains bounded by the limitations stated in the manuscript.

## Resolved environment issue

The earlier Python 3.13 / NumPy 2.x environment emitted a native binary-compatibility warning when a unit test unnecessarily coupled a geographic nearest-neighbour assertion to NetCDF4 writing. The assertion is now tested as a pure great-circle calculation, while actual COAST-RP reading is retained as a separate product-file smoke check.

A clean Python 3.11.15 environment was created without system site packages. The principal versions are NumPy 1.26.4, pandas 2.2.3, SciPy 1.14.1, xarray 2024.11.0, netCDF4 1.7.2, rasterio 1.4.4, pyproj 3.7.2 and Matplotlib 3.11.2. The exact package set is recorded in `requirements-lock.txt`; `pip check` reports no broken requirements.

The real COAST-RP file opens with runtime warnings treated as errors. All eight focal match indices remain unchanged: Sheerness 19997, Newlyn 18950, Aberdeen 19650, Hoek van Holland 19616, Brest 19691, New York 18455, Hong Kong 19794 and Charleston 18765.

## Full upstream reconstruction

The full workflow was executed successfully on 17 October 2026. `reproduction_receipt.json` records `mode: full` and `status: PASS` after verifying 278 upstream files by size and SHA-256. The workflow rebuilt station matching, return-level diagnostics, mask-aware terrain metrics, the frozen 68-station analysis, spatial and decision-stability diagnostics, all figures, the standalone manuscript, Supplementary Information, research report and internal consistency audit.

All four standalone HTML files passed the self-containment validator. The scientific and reproducibility suite now contains 32 tests, all of which pass. Remaining test warnings are limited to upstream SciencePlots/Matplotlib and rasterio API deprecations; no NumPy ABI, NetCDF data-read or scientific-contract warning remains.

The derived workflow canonicalizes floating-point station tables before ranking and serialization. This removes machine-readable differences caused only by CSV round-tripping or column insertion order. The reviewer archive gate independently verifies every packaged file, executes derived reproduction in a clean temporary environment and compares nine prespecified deterministic output hashes. Its authoritative result is written beside the archive in `reviewer_archive_validation_receipt.json` after final package assembly.

## Interpretation boundary

Passing these gates establishes code, data-flow and artifact reproducibility for the archived workflow. It does not establish that the static terrain screen is a flood-inundation model or an independent measure of true coastal risk. Three scientific limitations remain explicit:

- DeltaDTM and national/local terrain products are not yet harmonized to a common local sea-level vertical datum at all sites.
- No independent dynamic or observed flood-hazard benchmark is currently available for validating screening performance.
- A short great-circle COAST-RP match is coordinate-plausible but does not by itself prove hydrodynamic equivalence along the same coastal component.

These are reported as limits on interpretation and targets for subsequent work, not hidden by the successful software gates.
