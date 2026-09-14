from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "reference_metadata_audit.txt"
REPORT_JSON = LOG_DIR / "reference_metadata_audit.json"

MAIN_MANUSCRIPT = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md"
REFERENCE_VERIFICATION = MANUSCRIPT_DIR / "reference_verification.md"

PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|TK|XXX|citation needed|reference needed|doi pending|placeholder)\b",
    re.IGNORECASE,
)
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
DOI_URL_PATTERN = re.compile(r"https?://(?:dx\.)?doi\.org/([^\s)\]>]+)", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    reference_count: int = 0
    doi_count: int = 0

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path, audit: Audit) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        audit.errors.append(f"Missing required reference artifact: {rel(path)}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return ""


def references_section(text: str) -> str:
    match = re.search(r"^#+\s+references\b", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        match = re.search(r"^#+\s+bibliography\b", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    section = text[match.end():]
    next_heading = re.search(r"^#+\s+\S+", section, flags=re.MULTILINE)
    return section[: next_heading.start()] if next_heading else section


def split_reference_entries(section: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current).strip())
                current = []
            continue
        if re.match(r"^(?:[-*]|\[[0-9]+\]|[0-9]+[.)])\s+", stripped):
            if current:
                entries.append(" ".join(current).strip())
            current = [stripped]
        elif current:
            current.append(stripped)
        else:
            current = [stripped]
    if current:
        entries.append(" ".join(current).strip())
    return [entry for entry in entries if len(entry) > 20]


def normalized_doi(raw: str) -> str:
    return raw.strip().rstrip(".,;:)]}").lower()


def check_placeholders(path: Path, text: str, audit: Audit) -> None:
    for match in PLACEHOLDER_PATTERN.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        audit.errors.append(f"{rel(path)} line {line}: unresolved reference placeholder {match.group(0)!r}.")


def check_dois(section: str, audit: Audit) -> None:
    url_matches = list(DOI_URL_PATTERN.finditer(section))
    url_dois = [normalized_doi(match.group(1)) for match in url_matches]
    section_without_doi_urls = section
    for match in reversed(url_matches):
        section_without_doi_urls = (
            section_without_doi_urls[: match.start()]
            + " " * (match.end() - match.start())
            + section_without_doi_urls[match.end():]
        )
    dois = [normalized_doi(value) for value in DOI_PATTERN.findall(section_without_doi_urls)]
    all_dois = dois + url_dois
    audit.doi_count = len(set(all_dois))
    duplicates = sorted({doi for doi in all_dois if all_dois.count(doi) > 1})
    for doi in duplicates:
        audit.errors.append(f"Duplicate DOI appears in references: {doi}")
    for url_doi in url_dois:
        if not DOI_PATTERN.fullmatch(url_doi):
            audit.errors.append(f"Malformed DOI URL target in references: {url_doi}")


def check_reference_entries(entries: list[str], audit: Audit) -> None:
    audit.reference_count = len(entries)
    if len(entries) < 10:
        audit.errors.append(f"References section has only {len(entries)} detected entries; verify that bibliography was not truncated.")
    for index, entry in enumerate(entries, start=1):
        if not YEAR_PATTERN.search(entry):
            audit.errors.append(f"Reference entry {index} has no detected publication year: {entry[:120]}")
        if len(entry.split()) < 6:
            audit.errors.append(f"Reference entry {index} is very short and may be incomplete: {entry}")


def check_reference_verification(text: str, audit: Audit) -> None:
    if not text.strip():
        return
    check_placeholders(REFERENCE_VERIFICATION, text, audit)
    if not re.search(r"\b(?:verified|verification|checked|cross[- ]checked)\b", text, flags=re.IGNORECASE):
        audit.errors.append("reference_verification.md does not describe reference verification status.")
    negative_status = re.search(r"\b(?:unverified|not verified|pending verification)\b", text, flags=re.IGNORECASE)
    explicit_clearance = re.search(
        r"\b(?:no|none|zero)\s+(?:unverified|not verified|pending verification|pending references?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if negative_status and not explicit_clearance:
        audit.errors.append("reference_verification.md still reports unverified or pending references.")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "notes": audit.notes,
                "reference_count": audit.reference_count,
                "doi_count": audit.doi_count,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Reference Metadata Audit",
        "========================",
        "",
        f"Passed: {audit.passed}",
        f"References detected: {audit.reference_count}",
        f"Unique DOI count: {audit.doi_count}",
        f"Errors: {len(audit.errors)}",
        f"Warnings: {len(audit.warnings)}",
        "",
        "Errors",
        "------",
        *(f"- {item}" for item in audit.errors),
        "",
        "Warnings",
        "--------",
        *(f"- {item}" for item in audit.warnings),
        "",
        "Notes",
        "-----",
        *(f"- {item}" for item in audit.notes),
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    manuscript = read_text(MAIN_MANUSCRIPT, audit)
    verification = read_text(REFERENCE_VERIFICATION, audit)
    if manuscript:
        check_placeholders(MAIN_MANUSCRIPT, manuscript, audit)
        section = references_section(manuscript)
        if not section.strip():
            audit.errors.append("Main manuscript has no detected References section.")
        else:
            entries = split_reference_entries(section)
            check_reference_entries(entries, audit)
            check_dois(section, audit)
    check_reference_verification(verification, audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
