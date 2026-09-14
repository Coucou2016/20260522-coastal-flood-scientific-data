from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "manuscript_submission_text_audit.txt"
REPORT_JSON = LOG_DIR / "manuscript_submission_text_audit.json"

MAIN_MANUSCRIPT = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md"
REVIEW_HTML = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript_review.html"

REQUIRED_SUPPORT_FILES = [
    MANUSCRIPT_DIR / "title_page_and_declarations_draft.md",
    MANUSCRIPT_DIR / "data_code_availability_final_draft.md",
    MANUSCRIPT_DIR / "ai_use_statement_draft.md",
    MANUSCRIPT_DIR / "supplementary_information_draft.md",
    MANUSCRIPT_DIR / "target_journal_cee_checklist.md",
    MANUSCRIPT_DIR / "publication_readiness_audit.md",
    MANUSCRIPT_DIR / "reference_verification.md",
    MANUSCRIPT_DIR / "figure_source_data_dictionary.md",
]

PLACEHOLDER_PATTERNS = [
    ("editorial marker", re.compile(r"\b(?:TODO|TBD|FIXME|XXX|TK)\b", re.IGNORECASE)),
    ("bracketed insertion placeholder", re.compile(r"\[[^\]\n]*(?:insert|add|todo|tbd|placeholder|xx)[^\]\n]*\]", re.IGNORECASE)),
    ("angle-bracket placeholder", re.compile(r"<\s*(?:insert|todo|tbd|author|affiliation|doi|placeholder)[^>\n]*>", re.IGNORECASE)),
    ("empty DOI field", re.compile(r"\bdoi\s*:\s*(?:$|\n)", re.IGNORECASE)),
    ("unresolved citation marker", re.compile(r"\?\?\?|citation needed|\[cite\]", re.IGNORECASE)),
]

REQUIRED_STATEMENTS = [
    ("Data availability", [r"\bdata availability\b", r"\bdata and code availability\b"]),
    ("Code availability", [r"\bcode availability\b", r"\bdata and code availability\b"]),
    ("Author contributions", [r"\bauthor contributions?\b"]),
    ("Competing interests", [r"\bcompeting interests?\b", r"\bconflicts? of interest\b"]),
    ("Acknowledgements", [r"\backnowledgements?\b", r"\backnowledgments?\b"]),
    ("AI use statement", [r"\bAI[- ]use\b", r"\bartificial intelligence\b", r"\bgenerative AI\b"]),
]

CORE_SECTIONS = [
    ("Abstract", [r"^#+\s+abstract\b"]),
    ("Introduction", [r"^#+\s+introduction\b"]),
    ("Methods", [r"^#+\s+methods?\b", r"^#+\s+materials and methods\b"]),
    ("Results", [r"^#+\s+results\b"]),
    ("Discussion", [r"^#+\s+discussion\b"]),
    ("References", [r"^#+\s+references\b", r"^#+\s+bibliography\b"]),
]

SCIENTIFIC_GUARDRAILS = [
    ("ocean-connected inundation", [r"ocean[- ]connected", r"boundary[- ]connected"]),
    ("interior no-data handling", [r"interior no[- ]data", r"no[- ]data"]),
    ("lowland median elevation", [r"median coastal[- ]lowland elevation", r"median_lowland_elev_m"]),
]


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path, audit: Audit) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        audit.error(f"Missing required text artifact: {rel(path)}")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            audit.error(f"Cannot read {rel(path)}: {exc}")
    except OSError as exc:
        audit.error(f"Cannot read {rel(path)}: {exc}")
    return ""


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def compact_snippet(text: str, start: int, end: int) -> str:
    snippet = text[max(0, start - 50):min(len(text), end + 50)]
    return re.sub(r"\s+", " ", snippet).strip()


def section_present(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def statement_present(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def audit_placeholders(path: Path, text: str, audit: Audit) -> None:
    for label, pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            audit.error(
                f"{rel(path)} line {line_number(text, match.start())}: unresolved {label}: "
                f"{compact_snippet(text, match.start(), match.end())!r}"
            )


def remove_embedded_data_uris(text: str) -> str:
    return re.sub(
        r"""data:image/[a-zA-Z0-9.+-]+;base64,[^"']+""",
        "data:image/embedded;base64,embedded-image-data-omitted",
        text,
    )


def audit_required_sections(text: str, audit: Audit) -> None:
    for label, patterns in CORE_SECTIONS:
        if not section_present(text, patterns):
            audit.error(f"Main manuscript is missing a recognizable {label} section heading.")


def audit_required_statements(all_text: str, audit: Audit) -> None:
    for label, patterns in REQUIRED_STATEMENTS:
        if not statement_present(all_text, patterns):
            audit.error(f"Submission text set is missing a recognizable {label} statement.")


def audit_guardrails(text: str, audit: Audit) -> None:
    for label, patterns in SCIENTIFIC_GUARDRAILS:
        if not statement_present(text, patterns):
            audit.error(f"Main manuscript does not document the required guardrail: {label}.")


def audit_figure_and_table_sequences(text: str, audit: Audit) -> None:
    figure_numbers = sorted({int(value) for value in re.findall(r"\b(?:Figure|Fig\.?)\s+([0-9]+)\b", text, flags=re.IGNORECASE)})
    if not figure_numbers:
        audit.error("Main manuscript does not reference any numbered figures.")
    elif figure_numbers != list(range(1, max(figure_numbers) + 1)):
        audit.error(f"Main manuscript figure numbering has gaps or starts late: {figure_numbers}.")

    caption_numbers = sorted({int(value) for value in re.findall(r"^(?:#+\s*)?(?:\*\*)?(?:Figure|Fig\.?)\s+([0-9]+)[.:\s]", text, flags=re.IGNORECASE | re.MULTILINE)})
    if figure_numbers and caption_numbers and set(caption_numbers) != set(figure_numbers):
        audit.error(f"Figure references {figure_numbers} do not match detected captions {caption_numbers}.")

    table_numbers = sorted({int(value) for value in re.findall(r"\bTable\s+([0-9]+)\b", text, flags=re.IGNORECASE)})
    if table_numbers and table_numbers != list(range(1, max(table_numbers) + 1)):
        audit.error(f"Main manuscript table numbering has gaps or starts late: {table_numbers}.")


def audit_reference_health(text: str, audit: Audit) -> None:
    doi_urls = re.findall(r"https?://doi\.org/([^\s)\]]+)", text, flags=re.IGNORECASE)
    for doi in doi_urls:
        clean = doi.rstrip(".,;")
        if "/" not in clean or clean.lower() in {"xx", "todo", "tbd"}:
            audit.error(f"Malformed DOI URL detected: https://doi.org/{doi}")
    if "https://doi.org/" not in text and re.search(r"^#+\s+references\b", text, flags=re.IGNORECASE | re.MULTILINE):
        audit.warn("References section contains no DOI URLs; verify that reference metadata is complete.")


def audit_support_files(audit: Audit) -> list[tuple[Path, str]]:
    texts: list[tuple[Path, str]] = []
    for path in REQUIRED_SUPPORT_FILES:
        text = read_text(path, audit)
        if text:
            texts.append((path, text))
            audit_placeholders(path, text, audit)
    return texts


def write_reports(audit: Audit, checked_files: list[str], strict: bool) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    passed = not audit.errors and not (strict and audit.warnings)
    data = {
        "passed": passed,
        "strict": strict,
        "errors": audit.errors,
        "warnings": audit.warnings,
        "notes": audit.notes,
        "checked_files": checked_files,
    }
    REPORT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "Manuscript submission text audit",
        "================================",
        "",
        f"Passed: {passed}",
        f"Strict: {strict}",
        f"Files checked: {len(checked_files)}",
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
    parser = argparse.ArgumentParser(description="Audit manuscript and submission text for publication-blocking placeholders.")
    parser.add_argument("--strict", action="store_true", help="Return a nonzero exit code when warnings are present.")
    args = parser.parse_args()

    audit = Audit()
    checked: list[str] = []

    manuscript_text = read_text(MAIN_MANUSCRIPT, audit)
    if manuscript_text:
        checked.append(rel(MAIN_MANUSCRIPT))
        audit_placeholders(MAIN_MANUSCRIPT, manuscript_text, audit)
        audit_required_sections(manuscript_text, audit)
        audit_guardrails(manuscript_text, audit)
        audit_figure_and_table_sequences(manuscript_text, audit)
        audit_reference_health(manuscript_text, audit)

    html_text = read_text(REVIEW_HTML, audit)
    if html_text:
        checked.append(rel(REVIEW_HTML))
        audit_placeholders(REVIEW_HTML, remove_embedded_data_uris(html_text), audit)

    support_texts = audit_support_files(audit)
    checked.extend(rel(path) for path, _ in support_texts)

    all_text = "\n\n".join([manuscript_text, html_text, *(text for _, text in support_texts)])
    audit_required_statements(all_text, audit)

    write_reports(audit, checked, args.strict)
    print(REPORT_TXT.relative_to(ROOT))
    if audit.errors:
        return 1
    if args.strict and audit.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
