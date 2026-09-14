# Publication Gate Terminal Run

Run the final submission handoff from a normal Windows terminal at the repository root:

```cmd
scripts\run_final_submission_handoff.cmd
```

These compatibility entrypoints now delegate to the same final handoff:

```cmd
scripts\run_all_publication_checks.cmd
scripts\run_publication_gate_logged.cmd
```

If Python packages are missing, install the publication runtime first:

```cmd
scripts\install_publication_requirements.cmd
```

Publication readiness is proven only when the final handoff exits with code
`0`, the submission-ready gate reports `Passed: True` in
`logs\submission_ready_gate_report.md`, the terminal-run record audit passes,
and `logs\final_submission_handoff_report.md` reports `Passed: True`. The run is
not submission-ready unless the core publication gate, final figure/data
sign-off audit, combined submission-ready report, submission-ready evidence
bundle, terminal-run record, terminal-run record audit, final handoff evidence
bundle, final handoff evidence bundle audit, and final handoff report all exit
with code `0`.

Before the final submission run, complete:

- `manuscript\final_figure_data_review_matrix.json`
- `manuscript\final_figure_data_issue_register.json`
- `manuscript\final_figure_data_signoff.json`

Set the review matrix `status` to `ready_for_submission` only after every
manuscript figure, embedded image, source-data table, generated raster, and
packaged figure artifact has a completed review row.
The gate writes `manuscript\final_figure_data_review_matrix_template.json` as a
helper derived from available audit logs; use it to populate and verify the
formal `final_figure_data_review_matrix.json`, but do not treat the template as
review approval.
Set `status` to `approved_for_submission` only after the rendered manuscript,
embedded images, figure files, source-data tables, generated rasters, and
publication package have been reviewed together.
Set the issue register `status` to `ready_for_submission` only after all
detected figure/data issues are resolved, accepted as non-blocking, or marked
not applicable with evidence.

After a successful run, check these evidence files:

- `logs\submission_ready_gate_latest.log`
- `logs\final_submission_handoff_latest.log`
- `logs\final_submission_handoff_report.md`
- `logs\final_submission_handoff_report.json`
- `final_submission_handoff_evidence\evidence_manifest.json`
- `final_submission_handoff_evidence\evidence_manifest.sha256`
- `logs\final_submission_handoff_evidence_bundle_audit.md`
- `logs\final_submission_handoff_evidence_bundle_audit.json`
- `logs\submission_ready_failure_summary.md`
- `logs\submission_ready_failure_summary.json`
- `logs\publication_gate_report.md`
- `logs\publication_gate_report.json`
- `logs\submission_ready_gate_scripts_audit.md`
- `logs\submission_ready_gate_scripts_audit.json`
- `logs\submission_ready_gate_report.md`
- `logs\submission_ready_gate_report.json`
- `publication_gate_evidence\evidence_manifest.json`
- `publication_gate_evidence\evidence_manifest.sha256`
- `submission_ready_gate_evidence\evidence_manifest.json`
- `submission_ready_gate_evidence\evidence_manifest.sha256`
- `logs\submission_ready_evidence_bundle_audit.md`
- `logs\submission_ready_evidence_bundle_audit.json`
- `logs\final_figure_data_review_matrix_template.md`
- `logs\final_figure_data_review_matrix_template.json`
- `logs\final_figure_data_review_matrix_audit.md`
- `logs\final_figure_data_review_matrix_audit.json`
- `logs\final_figure_data_issue_register_audit.md`
- `logs\final_figure_data_issue_register_audit.json`
- `logs\final_figure_data_signoff_audit.md`
- `logs\final_figure_data_signoff_audit.json`
- `publication_package.zip`
- `final_archive_manifest.json`

The `submission_ready_gate_evidence` bundle intentionally contains the core
publication evidence, figure/data sign-off evidence, package, and archive
manifest. The final `submission_ready_gate_report` is generated after that
bundle is audited, so it is checked beside the bundle rather than copied into
the bundle itself.

If the gate fails, start with `logs\submission_ready_failure_summary.md`; it
collects blockers and warnings from the individual audit reports into one
repair list.
If the final handoff fails before or after the gate, first check
`logs\final_submission_handoff_report.md`, then follow any blockers into
`logs\submission_ready_failure_summary.md` and the individual audit reports.
The final handoff report should also list the final handoff evidence manifest
and its SHA256 sidecar paths.
The submission-ready and final handoff evidence audits check both the copied
bundle files and their current source files in the worktree, including byte
counts and SHA256 hashes.
The submission-ready and final handoff evidence bundles are rebuilt from
scratch on each successful run; do not place manual files in those directories,
because unlisted files will fail the audits.
It lists both the timestamped handoff log used for that run and the expected
`logs\final_submission_handoff_latest.log` convenience copy. The latest log is
created after the report step finishes.
If a handoff run fails before evidence-bundle generation, any existing
`final_submission_handoff_evidence` directory may be from an earlier run; trust
the current handoff report and timestamped log for the run status.

The final handoff automatically generates
`manuscript\submission_ready_terminal_run_record.json` and audits it. To run
those post-gate steps manually, use:

```cmd
scripts\record_submission_ready_terminal_run.cmd
```

Then audit that record:

```cmd
scripts\run_submission_ready_terminal_run_record_audit.cmd
```

The manuscript, figures, source data, validation logs, repository-deposit checks, and final evidence bundle should all be treated as unverified until this gate has run successfully in the current worktree.
