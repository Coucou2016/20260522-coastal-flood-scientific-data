from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
ACCEPTANCE_JSON = MANUSCRIPT_DIR / "final_qc_acceptance.json"
REPORT_TXT = LOG_DIR / "final_qc_acceptance_audit.txt"
REPORT_JSON = LOG_DIR / "final_qc_acceptance_audit.json"

NOTE_SOURCES = [
    LOG_DIR / "figure_visual_quality_audit.json",
    LOG_DIR / "figure_data_integrity_audit.json",
    LOG_DIR / "manuscript_submission_text_audit.json",
    LOG_DIR / "submission_artifact_consistency_audit.json",
]

REQUIRED_ENTRY_FIELDS = ["audit", "item", "reviewer", "review_date", "decision", "justification"]
PLACEHOLDER_PATTERN = re.compile(r"\b(?:todo|tbd|fixme|placeholder|author name|reviewer name|xx)\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_notes: list[dict[str, str]] = field(default_factory=list)
    accepted_notes: list[dict[str, str]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, audit: Audit, required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            audit.errors.append(f"Missing required JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        audit.errors.append(f"Invalid JSON in {rel(path)}: {exc}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return None


def note_key(audit_path: str, item: str) -> tuple[str, str]:
    return audit_path.replace("\\", "/"), re.sub(r"\s+", " ", item).strip()


def collect_required_notes(audit: Audit) -> None:
    for path in NOTE_SOURCES:
        data = load_json(path, audit, required=False)
        if data is None:
            continue
        if not isinstance(data, dict):
            audit.errors.append(f"Audit note source is not a JSON object: {rel(path)}")
            continue
        if data.get("errors"):
            audit.errors.append(f"{rel(path)} still reports errors; final QC acceptance cannot override errors.")
        if data.get("warnings"):
            audit.errors.append(f"{rel(path)} still reports warnings; final QC acceptance cannot override warnings.")
        notes = data.get("notes") or []
        if not isinstance(notes, list):
            audit.errors.append(f"{rel(path)} has a non-list notes field.")
            continue
        for item in notes:
            if not isinstance(item, str):
                audit.errors.append(f"{rel(path)} contains a non-string note item.")
                continue
            audit.required_notes.append({"audit": rel(path), "item": re.sub(r"\s+", " ", item).strip()})


def validate_acceptance_entries(audit: Audit) -> None:
    data = load_json(ACCEPTANCE_JSON, audit)
    if not isinstance(data, dict):
        audit.errors.append(f"{rel(ACCEPTANCE_JSON)} must be a JSON object.")
        return
    entries = data.get("accepted_notes")
    if not isinstance(entries, list):
        audit.errors.append(f"{rel(ACCEPTANCE_JSON)} must contain an accepted_notes list.")
        return
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            audit.errors.append(f"accepted_notes entry {index} is not a JSON object.")
            continue
        missing = [field for field in REQUIRED_ENTRY_FIELDS if not str(entry.get(field, "")).strip()]
        if missing:
            audit.errors.append(f"accepted_notes entry {index} is missing required field(s): {', '.join(missing)}.")
            continue
        values = {field: str(entry.get(field, "")).strip() for field in REQUIRED_ENTRY_FIELDS}
        if values["decision"].lower() != "accepted":
            audit.errors.append(f"accepted_notes entry {index} decision must be 'accepted'.")
        if not DATE_PATTERN.match(values["review_date"]):
            audit.errors.append(f"accepted_notes entry {index} review_date must use YYYY-MM-DD.")
        for field, value in values.items():
            if PLACEHOLDER_PATTERN.search(value):
                audit.errors.append(f"accepted_notes entry {index} field {field} contains placeholder text.")
        if len(values["justification"]) < 30:
            audit.errors.append(f"accepted_notes entry {index} justification is too short for final QC sign-off.")
        audit.accepted_notes.append({"audit": values["audit"].replace("\\", "/"), "item": re.sub(r"\s+", " ", values["item"]).strip()})


def compare_required_and_accepted(audit: Audit) -> None:
    required = {note_key(item["audit"], item["item"]) for item in audit.required_notes}
    accepted = {note_key(item["audit"], item["item"]) for item in audit.accepted_notes}
    missing = sorted(required - accepted)
    extra = sorted(accepted - required)
    for audit_path, item in missing:
        audit.errors.append(f"Non-blocking audit note lacks final QC acceptance: {audit_path}: {item}")
    for audit_path, item in extra:
        audit.warnings.append(f"Accepted QC note no longer appears in current audit output: {audit_path}: {item}")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "required_notes": audit.required_notes,
                "accepted_notes": audit.accepted_notes,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Final QC Acceptance Audit",
        "=========================",
        "",
        f"Passed: {audit.passed}",
        f"Required notes: {len(audit.required_notes)}",
        f"Accepted notes: {len(audit.accepted_notes)}",
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
    collect_required_notes(audit)
    validate_acceptance_entries(audit)
    compare_required_and_accepted(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
