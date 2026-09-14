from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "repository_deposit_readiness_audit.txt"
REPORT_JSON = LOG_DIR / "repository_deposit_readiness_audit.json"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "requirements-publication.txt",
    ROOT / "scripts" / "install_publication_requirements.cmd",
    ROOT / "scripts" / "run_python_checked.cmd",
    MANUSCRIPT_DIR / "data_code_availability_final_draft.md",
    MANUSCRIPT_DIR / "data_repository_deposit_checklist.md",
    MANUSCRIPT_DIR / "citation_metadata_template.md",
    MANUSCRIPT_DIR / "license_decision_notes.md",
    MANUSCRIPT_DIR / "software_environment.md",
    MANUSCRIPT_DIR / "figure_source_data_dictionary.md",
    ROOT / "publication_package.zip",
    ROOT / "final_archive_manifest.json",
]

REQUIRED_TEXT_GROUPS = {
    "data/code availability": [
        MANUSCRIPT_DIR / "data_code_availability_final_draft.md",
        MANUSCRIPT_DIR / "data_repository_deposit_checklist.md",
    ],
    "software environment": [MANUSCRIPT_DIR / "software_environment.md"],
    "citation metadata": [MANUSCRIPT_DIR / "citation_metadata_template.md"],
    "license decision": [MANUSCRIPT_DIR / "license_decision_notes.md"],
    "figure source data dictionary": [MANUSCRIPT_DIR / "figure_source_data_dictionary.md"],
}

PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:TODO|TBD|FIXME|TK|XXX|placeholder|insert|add DOI|doi pending|accession pending|repository pending)\b",
    re.IGNORECASE,
)
DOI_OR_URL_PATTERN = re.compile(r"(?:https?://|doi\.org/|10\.\d{4,9}/)", re.IGNORECASE)
LICENSE_PATTERN = re.compile(r"\b(?:CC[- ]BY|Creative Commons|MIT|Apache|BSD|GPL|ODC[- ]BY|ODbL|public domain)\b", re.IGNORECASE)
ENV_PATTERN = re.compile(r"\b(?:Python|R|GDAL|NumPy|Pandas|Matplotlib|Rasterio|environment|requirements)\b", re.IGNORECASE)
REQUIRED_RUNTIME_PACKAGES = ["numpy", "pandas", "matplotlib", "Pillow", "rasterio"]


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
    try:
        audit.files_checked.append(rel(path))
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        audit.errors.append(f"Missing required repository/deposit artifact: {rel(path)}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return ""


def check_required_files(audit: Audit) -> None:
    for path in REQUIRED_FILES:
        if path.suffix.lower() in {".md", ".txt", ".json"}:
            read_text(path, audit)
        elif not path.exists():
            audit.errors.append(f"Missing required repository/deposit artifact: {rel(path)}")
        else:
            audit.files_checked.append(rel(path))


def check_placeholders(audit: Audit) -> None:
    for path in REQUIRED_FILES:
        if path.suffix.lower() not in {".md", ".txt", ".json"} or not path.exists():
            continue
        text = read_text(path, audit)
        for match in PLACEHOLDER_PATTERN.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            audit.errors.append(f"{rel(path)} line {line}: unresolved repository/deposit placeholder {match.group(0)!r}.")


def combined_text(paths: list[Path], audit: Audit) -> str:
    return "\n\n".join(read_text(path, audit) for path in paths if path.exists())


def check_text_requirements(audit: Audit) -> None:
    availability = combined_text(REQUIRED_TEXT_GROUPS["data/code availability"], audit)
    if availability and not DOI_OR_URL_PATTERN.search(availability):
        audit.errors.append("Data/code availability and deposit checklist do not contain a DOI, URL, or repository identifier.")

    citation = combined_text(REQUIRED_TEXT_GROUPS["citation metadata"], audit)
    if citation and not DOI_OR_URL_PATTERN.search(citation):
        audit.warnings.append("Citation metadata does not yet contain a DOI or repository URL.")

    license_text = combined_text(REQUIRED_TEXT_GROUPS["license decision"], audit)
    if license_text and not LICENSE_PATTERN.search(license_text):
        audit.errors.append("License decision notes do not name a recognizable data/code license.")

    environment = combined_text(REQUIRED_TEXT_GROUPS["software environment"], audit)
    if environment and not ENV_PATTERN.search(environment):
        audit.errors.append("Software environment notes do not mention the computational environment or key packages.")

    dictionary = combined_text(REQUIRED_TEXT_GROUPS["figure source data dictionary"], audit)
    if dictionary and len(re.findall(r"\b(?:Figure|Fig\.?)\s*[0-9]+\b", dictionary, flags=re.IGNORECASE)) == 0:
        audit.errors.append("Figure source data dictionary does not mention any numbered figures.")


def check_archive_manifest(audit: Audit) -> None:
    manifest_path = ROOT / "final_archive_manifest.json"
    if not manifest_path.exists():
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        audit.errors.append(f"Invalid JSON in {rel(manifest_path)}: {exc}")
        return
    if not isinstance(data, dict):
        audit.errors.append("final_archive_manifest.json is not a JSON object.")
        return
    text = json.dumps(data, ensure_ascii=False)
    if "sha256" not in text.lower():
        audit.errors.append("final_archive_manifest.json does not contain SHA256 metadata for deposit verification.")


def check_requirements_file(audit: Audit) -> None:
    path = ROOT / "requirements-publication.txt"
    if not path.exists():
        return
    text = read_text(path, audit)
    lowered = text.lower()
    for package in REQUIRED_RUNTIME_PACKAGES:
        if package.lower() not in lowered:
            audit.errors.append(f"requirements-publication.txt does not list required runtime package {package!r}.")


def check_requirements_install_helper(audit: Audit) -> None:
    helper = ROOT / "scripts" / "install_publication_requirements.cmd"
    if not helper.exists():
        return
    try:
        text = helper.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(helper)}: {exc}")
        return
    normalized = " ".join(text.lower().replace("/", "\\").split())
    if "requirements-publication.txt" not in normalized:
        audit.errors.append("install_publication_requirements.cmd does not reference requirements-publication.txt.")
    if "run_python_checked.cmd" not in normalized:
        audit.errors.append("install_publication_requirements.cmd does not use run_python_checked.cmd.")
    if "-m pip install -r" not in normalized:
        audit.errors.append("install_publication_requirements.cmd does not run pip install -r.")


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
        "Repository Deposit Readiness Audit",
        "==================================",
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
    check_required_files(audit)
    check_placeholders(audit)
    check_text_requirements(audit)
    check_archive_manifest(audit)
    check_requirements_file(audit)
    check_requirements_install_helper(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
