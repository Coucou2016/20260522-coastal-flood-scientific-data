# Submission-Ready Terminal Run Record

Use `manuscript\submission_ready_terminal_run_record.json` to record the actual
external Windows terminal run that proves the final package is ready for
submission.

The recommended final command is:

```cmd
scripts\run_final_submission_handoff.cmd
```

It runs the submission-ready gate, records the successful terminal run, and
audits this record, then writes `logs\final_submission_handoff_report.md`. If
running the steps manually, first run:

```cmd
scripts\run_submission_ready_gate.cmd
```

either complete the record manually or generate it automatically:

```cmd
scripts\record_submission_ready_terminal_run.cmd
```

Only record the run if:

- the command exited with code `0`
- `logs\submission_ready_gate_report.md` says `Passed: True`
- `logs\submission_ready_failure_summary.md` lists no blockers
- the final evidence bundle and archive/package files are present

Set:

```json
"status": "ready_for_submission"
```

Then audit the record:

```cmd
scripts\run_submission_ready_terminal_run_record_audit.cmd
```

This run record is intentionally outside the main gate, because it documents
the external terminal run after the gate has completed.
