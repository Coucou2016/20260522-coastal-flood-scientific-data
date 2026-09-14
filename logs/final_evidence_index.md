Final Evidence Index
====================

Passed: True
Evidence items: 32
Errors: 0
Warnings: 0

Self Outputs
------------
- logs/final_evidence_index.md
- logs/final_evidence_index.json

| Role | Path | Required | Contextual | Present | Passed | Detail |
| --- | --- | --- | --- | --- | --- | --- |
| Gate report | logs/publication_gate.txt | True | True | True | False | contains failure wording |
| Gate report JSON | logs/publication_gate.json | True | True | True | True | ok |
| Completion status | completion_status.json | True | False | True | True | ok |
| Publication runtime requirements | requirements-publication.txt | True | False | True | True | ok |
| Python wrapper entrypoint | scripts/run_python_checked.cmd | True | False | True | True | ok |
| Environment diagnostics helper | scripts/diagnose_publication_environment.cmd | True | False | True | True | ok |
| Requirements install helper | scripts/install_publication_requirements.cmd | True | False | True | True | ok |
| Package manifest | package_manifest.json | False | False | False | True | missing |
| Packaged manifest | publication_package/package_manifest.json | False | False | True | True | ok |
| Final archive manifest | final_archive_manifest.json | True | False | True | True | ok |
| Publication ZIP | publication_package.zip | True | False | True | True | 11107249 bytes |
| Gate scripts audit | logs/publication_gate_scripts_audit.json | True | False | True | True | ok |
| Environment diagnostics log | logs/publication_environment_diagnostics.txt | True | True | True | True | ok |
| Python runtime dependencies audit | logs/python_runtime_dependencies_audit.json | True | False | True | True | ok |
| Figure inventory | logs/manuscript_figure_inventory.json | True | False | True | True | ok |
| Figure deliverables audit | logs/figure_deliverables_audit.json | True | False | True | True | ok |
| Figure visual-quality audit | logs/figure_visual_quality_audit.json | True | False | True | True | ok |
| Manual figure review sheet | logs/manual_figure_review_sheet.json | True | False | True | True | ok |
| Figure/source-data audit | logs/figure_data_integrity_audit.json | True | False | True | True | ok |
| Manuscript text audit | logs/manuscript_submission_text_audit.json | True | False | True | True | ok |
| Reference metadata audit | logs/reference_metadata_audit.json | True | False | True | True | ok |
| Journal submission metadata audit | logs/journal_submission_metadata_audit.json | True | False | True | True | ok |
| Artifact consistency audit | logs/submission_artifact_consistency_audit.json | True | False | True | True | ok |
| Final QC acceptance audit | logs/final_qc_acceptance_audit.json | True | False | True | True | ok |
| Repository deposit readiness audit | logs/repository_deposit_readiness_audit.json | True | False | True | True | ok |
| Package validation log | logs/publication_package_validation.txt | True | False | True | True | ok |
| Final archive validation log | logs/final_archive_validation.txt | True | False | True | True | ok |
| Archive handoff audit | logs/archive_handoff_audit.json | True | False | True | True | ok |
| Publication readiness summary | logs/publication_readiness_summary.json | True | False | True | True | ok |
| Final QC acceptance record | manuscript/final_qc_acceptance.json | True | False | True | True | ok |
| Gate evidence manifest | publication_gate_evidence/evidence_manifest.json | True | True | True | True | ok |
| Gate evidence manifest SHA256 sidecar | publication_gate_evidence/evidence_manifest.sha256 | True | True | True | True | ok |

Errors
------

Warnings
--------
