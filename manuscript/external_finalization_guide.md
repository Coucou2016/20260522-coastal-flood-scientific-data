# External finalization guide

Use this guide if the local Codex/session command runner cannot start Python or PowerShell. The manuscript package can still be finalized from a normal terminal, another Windows machine, or a controlled CI runner as long as the project directory and required data files are available.

## When to use this guide

Use this guide if commands fail with:

```text
Failed to create unified exec process: setup refresh failed with status exit code: 1
```

This is an execution-environment problem, not evidence that the manuscript workflow itself failed.

## Required project state

The external runner must have access to the full project directory, including:

- `scripts/`
- `manuscript/`
- `figures/`
- `data/processed/`
- required `data/raw/` inputs for GSSR, COAST-RP, Open-Meteo and DeltaDTM
- `requirements.txt`
- `environment.yml`
- `config/combo1_stations.yaml`

## Option A. Run on the same machine from a normal terminal

Open a normal Windows Command Prompt or PowerShell outside the broken session:

```cmd
cd /d E:\Projects\20260522-coastal-flood-scientific-data
scripts\run_finalization.cmd
```

or:

```powershell
cd E:\Projects\20260522-coastal-flood-scientific-data
python scripts\finalize_cee_publication_package.py
```

## Option B. Run in a fresh conda environment

```powershell
cd E:\Projects\20260522-coastal-flood-scientific-data
conda env create -f environment.yml
conda activate coastal-flood-scientific-data
python scripts\finalize_cee_publication_package.py
```

If the environment already exists:

```powershell
conda activate coastal-flood-scientific-data
python scripts\finalize_cee_publication_package.py
```

## Option C. Run with pip

```powershell
cd E:\Projects\20260522-coastal-flood-scientific-data
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts\finalize_cee_publication_package.py
```

## Audit-only mode

To check the manuscript, figures, source tables and support files without rebuilding the package:

```cmd
scripts\run_publication_audit.cmd
```

or:

```powershell
python scripts\audit_publication_readiness.py
```

Audit-only mode is useful before a full finalization run, but it does not replace `scripts\finalize_cee_publication_package.py`.

## Expected success evidence

A finalization run removes stale `publication_package/`, `publication_package.zip`, and previous failure-status files before verification begins. If the run fails, an older package should not be treated as current output.

A successful run should create or refresh:

- `manuscript/publication_readiness_report.md`
- `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`
- `publication_package/`
- `publication_package.zip`
- `publication_package/completion_status.json`
- `publication_package/package_manifest.json`
- `logs/final_archive_validation.txt`
- `final_archive_manifest.json`

The run should include:

```text
PUBLICATION READINESS AUDIT: PASS
PUBLICATION PACKAGE VALIDATION: PASS
```

## If the external run fails

Check:

- `logs/cee_publication_finalize_failed.md`
- `publication_package_failed_status.json`

Resolve the listed failure before treating the package as final.

## Files to inspect after success

1. Open `manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html`.
2. Inspect Figure 4 and Figure 5 against `manuscript/figure_final_qc_protocol.md`.
3. Open `manuscript/publication_readiness_report.md`.
4. Open `publication_package/completion_status.json`.
5. Confirm `publication_package.zip` exists and can be opened.
6. Open `logs/final_archive_validation.txt` and confirm that package validation passed after the final ZIP was written. This validation also checks `final_archive_manifest.json` against `publication_package.zip`.
7. Optionally rerun `python scripts\validate_publication_package.py` to validate the package without rebuilding figures.
8. On Windows, `scripts\validate_publication_package.cmd` can be used for package-only validation.
9. If moving the archive to another machine for validation, move `publication_package.zip` together with the root-level `final_archive_manifest.json`.

## Final note

Do not mark the manuscript package as publication-ready simply because the files exist. Publication readiness requires a successful finalization run and a passing publication-readiness audit. If `publication_package_failed_status.json` reports `safe_to_use_existing_package: false`, do not use any existing `publication_package/` or `publication_package.zip` as current output.
## Archive sidecar

Keep `final_archive_manifest.json` next to `publication_package.zip` when moving, uploading, or depositing the final archive. It is intentionally stored at the project root rather than inside the ZIP because it records the ZIP file's own size and SHA256 hash.
## Optional strict figure-data audit

After the main finalization command succeeds, run:

```cmd
scripts\run_figure_data_integrity_audit.cmd --strict
```

Use `logs\figure_data_integrity_audit.txt` as the final image/source-data QC record. This check is stricter than the package validator and is intended to catch figure-level data flaws before submission.
## One-command external check

If you are running the final verification outside this Codex session, the preferred command is:

```cmd
scripts\run_all_publication_checks.cmd
```

This runs finalization, strict figure/source-data integrity auditing, and final package validation in sequence.
## Preferred publication gate

Use this command for the final external verification run:

```cmd
scripts\run_publication_gate.cmd
```

It creates `logs\publication_gate.txt` and `logs\publication_gate.json`. Do not mark the package publication-ready unless the command exits successfully and the report records `Passed: True`.

The gate entrypoint uses `scripts\run_python_checked.cmd` to confirm that `python` is available on `PATH` and to force UTF-8 Python I/O before running the gate. If Python is missing, fix the local Python environment before interpreting any manuscript or figure output.

Individual audit entrypoints also use the same Python/UTF-8 wrapper, so a standalone audit run and the full publication gate use the same Python environment checks.
## Publication gate pass criteria

The publication gate is strict. Treat either errors or warnings as a failed final check. The required evidence set includes `completion_status.json`, `package_manifest.json` or `publication_package\package_manifest.json`, `final_archive_manifest.json`, `logs\publication_gate_scripts_audit.txt`, `logs\python_runtime_dependencies_audit.txt`, `logs\manuscript_figure_inventory.md`, `logs\figure_deliverables_audit.txt`, `logs\figure_visual_quality_audit.txt`, `logs\manual_figure_review_sheet.md`, `logs\figure_data_integrity_audit.txt`, `logs\manuscript_submission_text_audit.txt`, `logs\reference_metadata_audit.txt`, `logs\journal_submission_metadata_audit.txt`, `logs\submission_artifact_consistency_audit.txt`, `logs\final_qc_acceptance_audit.txt`, `logs\repository_deposit_readiness_audit.txt`, `logs\publication_package_validation.txt`, `logs\final_archive_validation.txt`, `logs\archive_handoff_audit.txt`, `logs\publication_readiness_summary.md`, `logs\final_evidence_index.md`, and `publication_gate_evidence\evidence_manifest.json`.
## Manuscript text audit

The publication gate also runs:

```cmd
scripts\run_manuscript_submission_text_audit.cmd --strict
```

This check must pass before submission. It is intended to catch unresolved editorial placeholders, incomplete declarations, malformed DOI placeholders, figure/table numbering gaps, and missing methodological cautions that can survive figure-level QC.
## Gate evidence bundle

After `scripts\run_publication_gate.cmd` succeeds, retain `publication_gate_evidence\` with the final archive. This folder contains the gate report, manuscript text audit, figure/source-data audit, package validation logs, completion status, archive manifest, and `evidence_manifest.json` with byte sizes and SHA256 hashes for the copied evidence files.
## Submission artifact consistency audit

The publication gate also runs:

```cmd
scripts\run_submission_artifact_consistency_audit.cmd
```

This final cross-check compares the manuscript Markdown, review HTML, audit logs, completion status, package manifests, `publication_package.zip`, and `final_archive_manifest.json`. It is intended to catch stale HTML, residual failure state, mismatched figure/table references, or archive hash mismatches before handoff.
## Publication readiness summary

The publication gate writes:

```text
logs\publication_readiness_summary.md
logs\publication_readiness_summary.json
```

Use the Markdown summary as the first sign-off page after a successful run. It consolidates completion status, manuscript text audit, figure/source-data audit, artifact consistency audit, package validation, final archive validation, archive handoff status when available, and ZIP hash agreement.
## Manuscript figure inventory

The publication gate runs:

```cmd
scripts\run_manuscript_figure_inventory.cmd
```

It writes `logs\manuscript_figure_inventory.md` and `logs\manuscript_figure_inventory.json`, listing every local or embedded image found in the manuscript Markdown and review HTML with its source document, location, byte size, dimensions, and SHA256 hash.
## Publication gate scripts audit

The publication gate begins with:

```cmd
scripts\run_publication_gate_scripts_audit.cmd
```

This self-check confirms that the gate-related Python scripts compile and that the command entrypoints are present, call their expected target scripts, and propagate exit codes before the final manuscript/package evidence is trusted.

Command target matching is normalized for case, slash style, and whitespace. Wrapper entrypoints such as `scripts\run_all_publication_checks.cmd` must also forward command-line arguments to the wrapped gate command.
## Figure visual-quality audit

The publication gate runs:

```cmd
scripts\run_figure_visual_quality_audit.cmd
```

This audit checks raster figures for low resolution, very low contrast, nearly blank white or black exports, and excessive transparency. Warnings should be resolved or explicitly accepted in final QC notes before submission; notes identify manual review items that do not by themselves fail the automated gate.
## Figure deliverables audit

The publication gate runs:

```cmd
scripts\run_figure_deliverables_audit.cmd
```

This audit checks that main figures are numbered contiguously, captions are detectable, figure image records exist, and source-data tables can be associated with each main figure.
## Final QC acceptance

The publication gate runs:

```cmd
scripts\run_final_qc_acceptance_audit.cmd
```

Use `manuscript\final_qc_acceptance.json` only for non-blocking audit notes that require human confirmation. Errors and warnings cannot be accepted away; they must be resolved before the gate can pass.
## Archive handoff audit

The publication gate runs:

```cmd
scripts\run_archive_handoff_audit.cmd
```

This audit checks that `publication_package.zip` contains the manuscript files while root-level sidecars such as `final_archive_manifest.json` and `publication_gate_evidence\` remain outside the ZIP for independent validation and handoff.
## Repository deposit readiness audit

The publication gate runs:

```cmd
scripts\run_repository_deposit_readiness_audit.cmd
```

This audit checks that data/code availability text, repository deposit checklist, citation metadata, license notes, software environment, figure source-data dictionary, final archive manifest, and publication ZIP are present and free of obvious unresolved deposit placeholders.
## Final evidence index

The publication gate writes:

```text
logs\final_evidence_index.md
logs\final_evidence_index.json
```

Use this index as the compact map of every required evidence artifact, its role, path, presence, and pass/fail state after the archive handoff audit and final readiness summary have run.

The gate writes the report and evidence bundle once before building the evidence index, then writes them again after the index is generated. This avoids a self-referential index while still ensuring the final evidence bundle contains the index files.

In the evidence index, the live gate report and gate evidence manifest are contextual evidence rather than preconditions. This prevents the index from requiring final evidence files that already contain the index step before the index itself has been generated; the archive handoff audit remains responsible for checking the evidence manifest before final indexing.
## Journal submission metadata audit

The publication gate runs:

```cmd
scripts\run_journal_submission_metadata_audit.cmd
```

This audit checks title/declarations, submission metadata, target-journal checklist, cover letter, editorial significance statement, author confirmation, AI-use statement, data/code availability text, and reporting-summary preparation for required concepts and unresolved placeholders.
## Reference metadata audit

The publication gate runs:

```cmd
scripts\run_reference_metadata_audit.cmd
```

This audit checks the manuscript References section, DOI formatting, duplicate DOIs, unresolved reference placeholders, publication-year presence, and the reference verification document.
## Evidence manifest hash sidecar

The final evidence bundle includes `publication_gate_evidence\evidence_manifest.sha256`, a non-self-referential SHA256 sidecar for `publication_gate_evidence\evidence_manifest.json`. The archive handoff audit verifies this sidecar before final handoff.
## Python runtime dependencies audit

The publication gate runs:

```cmd
scripts\run_python_runtime_dependencies_audit.cmd
```

This audit scans project Python scripts, identifies external imports, and checks whether those modules are available in the active Python environment before finalization and figure generation are trusted.

Hard dependency failures are errors. Explicitly optional dependencies, when present, are reported as notes rather than readiness blockers.
## Publication runtime requirements

Use `requirements-publication.txt` as the external Python environment requirements file for the final gate. Install those packages in the active environment before running `scripts\run_publication_gate.cmd`.

Recommended install command:

```cmd
scripts\install_publication_requirements.cmd
```

Additional pip options can be appended to that command if needed by the local environment. Installing requirements is only an environment-preparation step; publication readiness still requires `scripts\run_publication_gate.cmd` to complete successfully with `Passed: True`.
## Publication environment diagnostics

`scripts\run_publication_gate.cmd` first runs:

```cmd
scripts\diagnose_publication_environment.cmd
```

This writes `logs\publication_environment_diagnostics.txt`. If the gate fails early, inspect this diagnostics log before interpreting manuscript, figure, or package readiness.

The diagnostics log is informational only and is not a pass/fail readiness report. Use it to troubleshoot Python, pip, path, or missing-file problems before rerunning the publication gate.
## Manual figure review sheet

The publication gate runs:

```cmd
scripts\run_manual_figure_review_sheet.cmd
```

It writes `logs\manual_figure_review_sheet.md` and `logs\manual_figure_review_sheet.json`, summarizing manuscript images, dimensions, SHA256 values, visual audit problems/notes, and inferred mappings for final human review.
