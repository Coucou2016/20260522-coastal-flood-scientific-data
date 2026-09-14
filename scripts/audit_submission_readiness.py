#!/usr/bin/env python3
"""Final submission-readiness gate.

This check is intentionally stricter than audit_current_outputs.py. The current
outputs can be internally consistent and reproducible while still not being
ready for journal submission because the data/code repository DOI or private
reviewer link has not been filled in.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "submission_links.json"
PAPER_MD = ROOT / "paper.md"
MANIFEST = ROOT / "reproducibility_package" / "manifests" / "source_data_manifest.json"


def clean(value: object) -> str:
    return str(value or "").strip()


def looks_like_persistent_link(value: str) -> bool:
    if not value:
        return False
    return bool(
        re.search(r"https?://", value, re.I)
        or re.search(r"\bdoi:\s*10\.", value, re.I)
        or re.search(r"\b10\.\d{4,9}/", value)
    )


def main() -> int:
    errors: list[str] = []
    if not CONFIG.exists():
        errors.append("Missing config/submission_links.json.")
        links = {}
    else:
        links = json.loads(CONFIG.read_text(encoding="utf-8"))

    data_link = clean(links.get("data_repository_url_or_doi"))
    code_link = clean(links.get("code_repository_url_or_doi"))
    reviewer_link = clean(links.get("private_reviewer_link"))

    has_reviewer_link = looks_like_persistent_link(reviewer_link)
    has_public_pair = looks_like_persistent_link(data_link) and looks_like_persistent_link(code_link)
    if not (has_reviewer_link or has_public_pair):
        errors.append(
            "Repository availability is incomplete: provide either a private reviewer link "
            "or both data and code repository DOI/URL values in config/submission_links.json."
        )

    if PAPER_MD.exists():
        text = PAPER_MD.read_text(encoding="utf-8")
        if "Public repository URL and DOI/private reviewer link: 待补充" in text:
            errors.append("paper.md still contains the DOI/private reviewer link pending placeholder.")
    else:
        errors.append("paper.md is missing.")

    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        status = manifest.get("repository_link_status", {})
        if status.get("status") != "complete":
            errors.append("source_data_manifest.json does not mark repository_link_status as complete.")
    else:
        errors.append("reproducibility_package/manifests/source_data_manifest.json is missing.")

    if errors:
        print("SUBMISSION READINESS: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SUBMISSION READINESS: PASS")
    print("- repository DOI/private reviewer link is recorded")
    print("- paper.md no longer contains the DOI/private reviewer placeholder")
    print("- reproducibility package manifest marks repository_link_status as complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
