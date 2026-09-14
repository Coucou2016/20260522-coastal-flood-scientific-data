#!/usr/bin/env python3
"""Set or inspect repository links used by the submission-readiness gate."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "submission_links.json"


DEFAULT_CONFIG = {
    "data_repository_url_or_doi": "",
    "code_repository_url_or_doi": "",
    "private_reviewer_link": "",
    "notes": (
        "Fill at least one real public DOI/repository URL or private reviewer-access URL before journal submission. "
        "Leave empty while the package remains local-only."
    ),
}


def looks_like_link(value: str) -> bool:
    value = value.strip()
    return bool(
        re.search(r"https?://", value, re.I)
        or re.search(r"\bdoi:\s*10\.", value, re.I)
        or re.search(r"\b10\.\d{4,9}/", value)
    )


def load_config() -> dict[str, str]:
    if CONFIG.exists():
        current = json.loads(CONFIG.read_text(encoding="utf-8"))
    else:
        current = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: str(v) for k, v in current.items()})
    return merged


def save_config(config: dict[str, str]) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def readiness_status(config: dict[str, str]) -> tuple[bool, str]:
    reviewer = config.get("private_reviewer_link", "").strip()
    data = config.get("data_repository_url_or_doi", "").strip()
    code = config.get("code_repository_url_or_doi", "").strip()
    if reviewer:
        return looks_like_link(reviewer), "private reviewer link"
    if data or code:
        return looks_like_link(data) and looks_like_link(code), "public data/code repository pair"
    return False, "missing repository link"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="Public data repository URL or DOI.")
    parser.add_argument("--code", help="Public code repository URL or DOI.")
    parser.add_argument("--reviewer", help="Private reviewer-access repository URL.")
    parser.add_argument("--clear", action="store_true", help="Clear all repository link fields.")
    parser.add_argument("--show", action="store_true", help="Print the current configuration.")
    args = parser.parse_args()

    config = load_config()
    if args.clear:
        config["data_repository_url_or_doi"] = ""
        config["code_repository_url_or_doi"] = ""
        config["private_reviewer_link"] = ""
    if args.data is not None:
        config["data_repository_url_or_doi"] = args.data.strip()
    if args.code is not None:
        config["code_repository_url_or_doi"] = args.code.strip()
    if args.reviewer is not None:
        config["private_reviewer_link"] = args.reviewer.strip()

    save_config(config)
    complete, basis = readiness_status(config)
    if args.show or not any([args.clear, args.data is not None, args.code is not None, args.reviewer is not None]):
        print(json.dumps(config, indent=2, ensure_ascii=False))
    print(f"submission_link_status: {'complete' if complete else 'pending'} ({basis})")
    if not complete:
        print(
            "Next step: provide either --reviewer URL, or both --data and --code DOI/URL values, "
            "then rebuild paper/package and run scripts\\audit_submission_readiness.py."
        )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
