# Repository deposit and final submission-readiness instructions

This document records the remaining external step before the manuscript can be
called submission-ready.

## Current local status

The local manuscript package is internally auditable:

- `paper.html`, `paper.md`, `paper.pdf`
- `report.html`, `report.md`, `report.pdf`
- `reproducibility_package/`
- `reproducibility_package.zip`
- `data/figure_source/`
- `scripts/validate_standalone_html.py`
- `scripts/audit_current_outputs.py`
- `scripts/audit_submission_readiness.py`

The current local audit passes, but the final submission-readiness gate remains
open until a real public repository DOI/URL or a private reviewer-access link is
recorded.

## What to upload

Upload `reproducibility_package.zip` to one of the following:

- Zenodo, Figshare, OSF, institutional repository, or a similar DOI-issuing repository;
- a GitHub/GitLab release connected to Zenodo or another archive;
- a journal-accessible private reviewer repository.

The uploaded package should keep the current directory structure intact. It
contains processed source tables, current paper/report outputs, raw-file hashes,
software/package records, scripts, and the one-command rebuild workflow. It does
not redistribute multi-GB raw products; those are traced through file names,
hashes and public source descriptions.

## How to record the repository link

If a private reviewer link is available, record it with:

```powershell
scripts\run_python_checked.cmd scripts\set_submission_links.py --reviewer "https://..."
```

If separate public data and code repositories are used, record both:

```powershell
scripts\run_python_checked.cmd scripts\set_submission_links.py --data "https://doi.org/..." --code "https://doi.org/..."
```

The script writes `config/submission_links.json`. Do not manually edit the final
paper exports; they are regenerated from the configuration.

## Final rebuild and gate

After recording the link, rebuild and verify:

```powershell
scripts\run_python_checked.cmd scripts\build_standalone_paper.py
scripts\run_python_checked.cmd scripts\build_research_report.py
scripts\run_python_checked.cmd scripts\build_reproducibility_package.py
scripts\run_python_checked.cmd scripts\validate_standalone_html.py paper.html
scripts\run_python_checked.cmd scripts\validate_standalone_html.py report.html
scripts\run_python_checked.cmd scripts\audit_current_outputs.py
scripts\run_python_checked.cmd scripts\audit_submission_readiness.py
```

The manuscript should be treated as submission-ready only when both audits pass.

## Expected final gate

`audit_current_outputs.py` checks internal reproducibility and consistency.

`audit_submission_readiness.py` checks the external repository requirement. It
fails while the DOI/private reviewer link is missing, even if all local science
and figure audits pass. This is intentional and prevents accidental submission
with unresolved Data availability / Code availability metadata.
