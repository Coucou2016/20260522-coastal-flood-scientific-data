# Next actions

The manuscript package is prepared for finalization, but the current agent session cannot start Python/PowerShell processes. The next required action is to run the finalization workflow from a working terminal.

## Run

```powershell
python scripts\finalize_cee_publication_package.py
```

or on Windows:

```cmd
scripts\run_finalization.cmd
```

## Success requires

- `PUBLICATION READINESS AUDIT: PASS`
- `PUBLICATION PACKAGE VALIDATION: PASS`
- `manuscript/publication_readiness_report.md`
- `publication_package/`
- `publication_package.zip`
- `publication_package/completion_status.json` with `status: finalized`
- `logs/final_archive_validation.txt`
- `final_archive_manifest.json`

## If it fails

Inspect:

- `logs/cee_publication_finalize_failed.md`
- `publication_package_failed_status.json`

Do not use any existing package if `publication_package_failed_status.json` reports:

```json
{
  "safe_to_use_existing_package": false
}
```

## Final human checks

- Open the standalone HTML and inspect all figures.
- Check Figure 4 and Figure 5 against `manuscript/figure_final_qc_protocol.md`.
- Complete `manuscript/author_final_confirmation_form.md`.
- Deposit processed outputs/code package and update repository DOI fields.
## Archive handoff note

When transferring the final publication archive, keep `final_archive_manifest.json` alongside `publication_package.zip`. The manifest is intentionally outside the ZIP so it can record the ZIP file's own size and SHA256 hash for independent validation.
## Figure and data integrity audit

After `scripts\run_finalization.cmd` succeeds, run `scripts\run_figure_data_integrity_audit.cmd --strict`. Review `logs\figure_data_integrity_audit.txt` and resolve every error or warning before marking the manuscript package publication-ready.
## One-command publication check

When the local execution environment is restored, run `scripts\run_all_publication_checks.cmd`. It performs finalization, strict figure/source-data integrity auditing, and final package validation in sequence.
## Preferred final publication gate

When command execution is available, run `scripts\run_publication_gate.cmd`. The gate runs finalization, strict figure/source-data integrity auditing, and package validation, then writes `logs\publication_gate.txt` and `logs\publication_gate.json`. Treat the manuscript package as publication-ready only if this gate exits successfully and the report says `Passed: True`.

The gate entrypoint first calls `scripts\run_python_checked.cmd`, which checks that `python` is available on `PATH` and sets UTF-8 Python I/O. Resolve Python environment failures before evaluating manuscript, figure, or package readiness.
## Publication gate pass criteria

`scripts\run_publication_gate.cmd` is intentionally strict: errors or warnings both mean the package is not ready. The report must show `Passed: True`, and the required evidence files must include `completion_status.json`, `package_manifest.json` or `publication_package\package_manifest.json`, `final_archive_manifest.json`, `logs\publication_gate_scripts_audit.txt`, `logs\python_runtime_dependencies_audit.txt`, `logs\manuscript_figure_inventory.md`, `logs\figure_deliverables_audit.txt`, `logs\figure_visual_quality_audit.txt`, `logs\manual_figure_review_sheet.md`, `logs\figure_data_integrity_audit.txt`, `logs\manuscript_submission_text_audit.txt`, `logs\reference_metadata_audit.txt`, `logs\journal_submission_metadata_audit.txt`, `logs\submission_artifact_consistency_audit.txt`, `logs\final_qc_acceptance_audit.txt`, `logs\repository_deposit_readiness_audit.txt`, `logs\publication_package_validation.txt`, `logs\final_archive_validation.txt`, `logs\archive_handoff_audit.txt`, `logs\publication_readiness_summary.md`, `logs\final_evidence_index.md`, and `publication_gate_evidence\evidence_manifest.json`.
## Manuscript text audit

Run `scripts\run_manuscript_submission_text_audit.cmd --strict` as part of the final gate. Resolve every placeholder, missing declaration, malformed DOI placeholder, figure/table numbering gap, and missing methodological guardrail before treating the manuscript as ready for journal submission.
## Gate evidence bundle

`scripts\run_publication_gate.cmd` also writes `publication_gate_evidence\`. Keep this directory with the final archive during handoff. It contains the gate report, audit logs, validation logs, completion status, final archive manifest, and `evidence_manifest.json` with byte sizes and SHA256 hashes for the copied evidence files.
## Submission artifact consistency audit

The publication gate now runs `scripts\run_submission_artifact_consistency_audit.cmd`. This cross-check verifies that manuscript Markdown, review HTML, audit logs, completion status, package manifests, `publication_package.zip`, and `final_archive_manifest.json` agree with each other before the package is treated as ready.
## Publication readiness summary

The final gate writes `logs\publication_readiness_summary.md` and `logs\publication_readiness_summary.json`. Use this summary as the first human-readable sign-off page: it consolidates completion status, figure/source-data audit, manuscript text audit, artifact consistency audit, package validation, final archive validation, archive handoff status when available, and ZIP hash agreement.
## Manuscript figure inventory

The final gate runs `scripts\run_manuscript_figure_inventory.cmd` and writes `logs\manuscript_figure_inventory.md` plus `logs\manuscript_figure_inventory.json`. Use this inventory to confirm every image referenced or embedded in the manuscript review files has a recorded location, byte size, dimensions, and SHA256 hash.
## Publication gate scripts audit

The final gate begins with `scripts\run_publication_gate_scripts_audit.cmd`. This checks that the publication-gate Python scripts compile and that the command entrypoints exist, call their expected target scripts, and propagate exit codes before any manuscript/package evidence is trusted.

Command target matching is normalized for case, slash style, and whitespace. Wrapper entrypoints such as `scripts\run_all_publication_checks.cmd` must also forward command-line arguments to the wrapped gate command.
## Figure visual-quality audit

The final gate runs `scripts\run_figure_visual_quality_audit.cmd` after building the manuscript figure inventory. It checks raster figures for low resolution, very low contrast, nearly blank exports, and excessive transparency. Warnings block publication readiness until resolved or explicitly accepted in the final QC notes; notes identify manual review items that do not by themselves fail the automated gate.
## Figure deliverables audit

The final gate runs `scripts\run_figure_deliverables_audit.cmd` after building the manuscript figure inventory. It checks that main figures are numbered contiguously, that captions are detectable, that figure image records exist, and that source-data tables can be associated with each main figure.
## Final QC acceptance

The final gate runs `scripts\run_final_qc_acceptance_audit.cmd`. Use `manuscript\final_qc_acceptance.json` only to accept non-blocking audit notes that require human confirmation, such as SVG/manual-review notices. Do not use it to override errors or warnings; those must be resolved before the publication gate can pass.
## Archive handoff audit

The final gate runs `scripts\run_archive_handoff_audit.cmd` after the gate report and `publication_gate_evidence\` have been written once. This audit checks that `publication_package.zip` contains the manuscript files while root-level sidecars such as `final_archive_manifest.json` and the gate evidence bundle remain outside the ZIP for independent validation.
## Repository deposit readiness audit

The final gate runs `scripts\run_repository_deposit_readiness_audit.cmd`. This audit checks that the data/code availability text, repository deposit checklist, citation metadata, license notes, software environment, figure source-data dictionary, final archive manifest, and publication ZIP are present and free of obvious unresolved deposit placeholders.
## Final evidence index

The final gate writes `logs\final_evidence_index.md` and `logs\final_evidence_index.json` after the archive handoff audit and final readiness summary. Use this index as the compact map of every required evidence artifact, its role, path, presence, and pass/fail state.

The gate writes the report and evidence bundle once before building the evidence index, then writes them again after the index is generated. This avoids a self-referential index while still ensuring the final evidence bundle contains the index files.

In the evidence index, the live gate report and gate evidence manifest are listed as contextual evidence rather than preconditions. This prevents the index from requiring final evidence files that already contain the index step before the index itself has been generated; the archive handoff audit remains responsible for checking the evidence manifest before final indexing.
## Journal submission metadata audit

The final gate runs `scripts\run_journal_submission_metadata_audit.cmd`. This audit checks title/declarations, submission metadata, target-journal checklist, cover letter, editorial significance statement, author confirmation, AI-use statement, data/code availability text, and reporting-summary preparation for required concepts and unresolved placeholders.
## Reference metadata audit

The final gate runs `scripts\run_reference_metadata_audit.cmd`. This audit checks the manuscript References section, DOI formatting, duplicate DOIs, unresolved reference placeholders, publication-year presence, and the reference verification document.
## Evidence manifest hash sidecar

The final evidence bundle includes `publication_gate_evidence\evidence_manifest.sha256`, a non-self-referential SHA256 sidecar for `publication_gate_evidence\evidence_manifest.json`. The archive handoff audit verifies this sidecar before final handoff.
## Python runtime dependencies audit

The final gate runs `scripts\run_python_runtime_dependencies_audit.cmd` after the gate-script self-audit. It scans project Python scripts, identifies external imports, and checks whether those modules are available in the active Python environment before finalization and figure generation are trusted.

Hard dependency failures are errors. Explicitly optional dependencies, when present, are reported as notes rather than readiness blockers.
## Publication runtime requirements

Use `requirements-publication.txt` as the external Python environment requirements file for the final gate. It is included in the final evidence bundle and checked by the repository deposit readiness audit.

In a normal terminal, run `scripts\install_publication_requirements.cmd` to install the publication runtime packages before running `scripts\run_publication_gate.cmd`.

You may append pip options to the install helper if required by the local environment. Installing requirements does not prove readiness; only a successful publication gate report with `Passed: True` does.
## Publication environment diagnostics

`scripts\run_publication_gate.cmd` first runs `scripts\diagnose_publication_environment.cmd`, which writes `logs\publication_environment_diagnostics.txt`. If the gate fails early, inspect this diagnostics log before interpreting manuscript, figure, or package readiness.
## Manual figure review sheet

The final gate runs `scripts\run_manual_figure_review_sheet.cmd`. It writes `logs\manual_figure_review_sheet.md` and `logs\manual_figure_review_sheet.json`, summarizing manuscript images, dimensions, SHA256 values, visual audit problems/notes, and inferred mappings for final human review.
