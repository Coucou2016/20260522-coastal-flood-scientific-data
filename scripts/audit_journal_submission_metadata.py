from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "journal_submission_metadata_audit.txt"
REPORT_JSON = LOG_DIR / "journal_submission_metadata_audit.json"

REQUIRED_FILES = [
    MANUSCRIPT_DIR / "title_page_and_declarations_draft.md",
    MANUSCRIPT_DIR / "submission_metadata_required.md",
    MANUSCRIPT_DIR / "target_journal_cee_checklist.md",
    MANUSCRIPT_DIR / "cover_letter_draft.md",
    MANUSCRIPT_DIR / "editorial_significance_statement.md",
    MANUSCRIPT_DIR / "author_final_confirmation_form.md",
    MANUSCRIPT_DIR / "ai_use_statement_draft.md",
    MANUSCRIPT_DIR / "data_code_availability_final_draft.md",
    MANUSCRIPT_DIR / "nature_reporting_summary_preparation.md",
]

PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|TK|XXX|placeholder|insert|author name|affiliation pending|email pending|orcid pending|confirm before submission)\b",
    re.IGNORECASE,
)

REQUIRED_CONCEPTS = {
    "title and declarations": {
        "files": [MANUSCRIPT_DIR / "title_page_and_declarations_draft.md"],
        "patterns": [
            r"\btitle\b",
            r"\bauthors?\b",
            r"\baffiliations?\b",
            r"\bcorresponding author\b",
            r"\bcompeting interests?\b",
            r"\bauthor contributions?\b",
        ],
    },
    "submission metadata": {
        "files": [MANUSCRIPT_DIR / "submission_metadata_required.md"],
        "patterns": [
            r"\babstract\b",
            r"\bkeywords?\b",
            r"\bcorresponding author\b",
            r"\bdata availability\b",
        ],
    },
    "cover letter": {
        "files": [MANUSCRIPT_DIR / "cover_letter_draft.md"],
        "patterns": [
            r"\beditor\b",
            r"\bconsider(?:ation)?\b",
            r"\bnot under consideration\b|\bnot currently under review\b|\bexclusive submission\b",
        ],
    },
    "editorial significance": {
        "files": [MANUSCRIPT_DIR / "editorial_significance_statement.md"],
        "patterns": [
            r"\bsignificance\b|\bimportance\b|\badvance\b",
            r"\bcoastal\b",
            r"\bflood\b|\binundation\b",
        ],
    },
    "author confirmation": {
        "files": [MANUSCRIPT_DIR / "author_final_confirmation_form.md"],
        "patterns": [
            r"\bauthor\b",
            r"\bconfirm\b|\bapproval\b|\bagree\b",
            r"\bsubmission\b",
        ],
    },
    "AI use": {
        "files": [MANUSCRIPT_DIR / "ai_use_statement_draft.md"],
        "patterns": [
            r"\bAI\b|\bartificial intelligence\b|\bgenerative\b",
            r"\buse\b|\bused\b|\bnot used\b",
        ],
    },
    "reporting summary": {
        "files": [MANUSCRIPT_DIR / "nature_reporting_summary_preparation.md"],
        "patterns": [
            r"\breporting summary\b|\breporting\b",
            r"\bdata\b",
            r"\bcode\b|\bsoftware\b",
        ],
    },
}


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_checked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path, audit: Audit) -> str:
    audit.files_checked.append(rel(path))
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        audit.errors.append(f"Missing required journal-submission file: {rel(path)}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return ""


def check_required_files(audit: Audit) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for path in REQUIRED_FILES:
        texts[path] = read_text(path, audit)
    return texts


def check_placeholders(texts: dict[Path, str], audit: Audit) -> None:
    for path, text in texts.items():
        if not text:
            continue
        for match in PLACEHOLDER_PATTERN.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            audit.errors.append(f"{rel(path)} line {line}: unresolved submission placeholder {match.group(0)!r}.")


def check_concepts(texts: dict[Path, str], audit: Audit) -> None:
    for label, spec in REQUIRED_CONCEPTS.items():
        combined = "\n\n".join(texts.get(path, "") for path in spec["files"])
        if not combined.strip():
            continue
        for pattern in spec["patterns"]:
            if not re.search(pattern, combined, flags=re.IGNORECASE):
                audit.errors.append(f"Journal submission metadata is missing {label} concept matching pattern: {pattern}")


def check_nonempty_final_materials(texts: dict[Path, str], audit: Audit) -> None:
    for path, text in texts.items():
        words = re.findall(r"\b\w+\b", text)
        if len(words) < 30:
            audit.warnings.append(f"{rel(path)} is very short for final submission material ({len(words)} words).")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "files_checked": sorted(set(audit.files_checked)),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Journal Submission Metadata Audit",
        "=================================",
        "",
        f"Passed: {audit.passed}",
        f"Files checked: {len(set(audit.files_checked))}",
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
    ]
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    texts = check_required_files(audit)
    check_placeholders(texts, audit)
    check_concepts(texts, audit)
    check_nonempty_final_materials(texts, audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
