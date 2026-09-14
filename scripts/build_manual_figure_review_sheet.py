from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
INVENTORY_JSON = LOG_DIR / "manuscript_figure_inventory.json"
VISUAL_AUDIT_JSON = LOG_DIR / "figure_visual_quality_audit.json"
DELIVERABLES_JSON = LOG_DIR / "figure_deliverables_audit.json"
REPORT_MD = LOG_DIR / "manual_figure_review_sheet.md"
REPORT_JSON = LOG_DIR / "manual_figure_review_sheet.json"


@dataclass
class ReviewItem:
    figure: int | None
    label: str
    path: str | None
    document: str | None
    width: int | None
    height: int | None
    bytes: int | None
    sha256: str | None
    visual_problems: list[str] = field(default_factory=list)
    visual_notes: list[str] = field(default_factory=list)
    inferred_mapping: bool = False


@dataclass
class Sheet:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    items: list[ReviewItem] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path, sheet: Sheet, required: bool = True) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if required:
            sheet.errors.append(f"Missing required JSON file: {rel(path)}")
    except json.JSONDecodeError as exc:
        sheet.errors.append(f"Invalid JSON in {rel(path)}: {exc}")
    except OSError as exc:
        sheet.errors.append(f"Cannot read {rel(path)}: {exc}")
    return None


def figure_from_text(text: str) -> int | None:
    patterns = [
        r"\bfig(?:ure)?[_ -]?0*([0-9]+)\b",
        r"\bfigure[_ -]?0*([0-9]+)\b",
        r"\bmain[_ -]?0*([0-9]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def visual_lookup(sheet: Sheet) -> dict[str, dict[str, Any]]:
    data = load_json(VISUAL_AUDIT_JSON, sheet, required=False)
    records = data.get("records") if isinstance(data, dict) else []
    lookup: dict[str, dict[str, Any]] = {}
    if not isinstance(records, list):
        return lookup
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in [record.get("path"), record.get("label")]:
            if key:
                lookup[str(key)] = record
    return lookup


def inferred_labels(sheet: Sheet) -> set[str]:
    data = load_json(DELIVERABLES_JSON, sheet, required=False)
    figures = data.get("figures") if isinstance(data, dict) else []
    labels: set[str] = set()
    if not isinstance(figures, list):
        return labels
    for figure in figures:
        if not isinstance(figure, dict):
            continue
        for key in ["inferred_image_records", "inferred_source_tables"]:
            values = figure.get(key) or []
            if isinstance(values, list):
                labels.update(str(value) for value in values)
    return labels


def build_sheet() -> Sheet:
    sheet = Sheet()
    inventory = load_json(INVENTORY_JSON, sheet)
    records = inventory.get("records") if isinstance(inventory, dict) else None
    if not isinstance(records, list) or not records:
        sheet.errors.append("Manuscript figure inventory has no records.")
        return sheet

    visual = visual_lookup(sheet)
    inferred = inferred_labels(sheet)
    for record in records:
        if not isinstance(record, dict):
            sheet.warnings.append("Skipping non-object figure inventory record.")
            continue
        label = str(record.get("path") or record.get("reference") or record.get("id") or "unknown")
        visual_record = visual.get(label) or visual.get(str(record.get("path") or "")) or visual.get(str(record.get("reference") or ""))
        problems = []
        notes = []
        if isinstance(visual_record, dict):
            problems = [str(item) for item in visual_record.get("problems") or []]
            notes = [str(item) for item in visual_record.get("notes") or []]
        text_for_number = " ".join(str(record.get(key) or "") for key in ["id", "reference", "path", "document"])
        sheet.items.append(
            ReviewItem(
                figure=figure_from_text(text_for_number),
                label=label,
                path=record.get("path"),
                document=record.get("document"),
                width=record.get("width"),
                height=record.get("height"),
                bytes=record.get("bytes"),
                sha256=record.get("sha256"),
                visual_problems=problems,
                visual_notes=notes,
                inferred_mapping=label in inferred,
            )
        )
    return sheet


def write_sheet(sheet: Sheet) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": sheet.passed,
                "errors": sheet.errors,
                "warnings": sheet.warnings,
                "items": [
                    {
                        "figure": item.figure,
                        "label": item.label,
                        "path": item.path,
                        "document": item.document,
                        "width": item.width,
                        "height": item.height,
                        "bytes": item.bytes,
                        "sha256": item.sha256,
                        "visual_problems": item.visual_problems,
                        "visual_notes": item.visual_notes,
                        "inferred_mapping": item.inferred_mapping,
                    }
                    for item in sheet.items
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Manual Figure Review Sheet",
        "==========================",
        "",
        "This sheet supports human review of manuscript figures. It is not a substitute for the automated publication gate.",
        "",
        f"Passed: {sheet.passed}",
        f"Items: {len(sheet.items)}",
        f"Errors: {len(sheet.errors)}",
        f"Warnings: {len(sheet.warnings)}",
        "",
        "| Figure | Label | Size | Bytes | Problems | Notes | Inferred |",
        "| ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in sheet.items:
        size = f"{item.width} x {item.height}" if item.width and item.height else ""
        problems = "; ".join(item.visual_problems)
        notes = "; ".join(item.visual_notes)
        lines.append(
            f"| {item.figure or ''} | {item.label} | {size} | {item.bytes or ''} | "
            f"{problems} | {notes} | {item.inferred_mapping} |"
        )
    lines.extend(["", "Reviewer Sign-Off", "-----------------"])
    lines.extend(
        [
            "- Reviewer:",
            "- Review date:",
            "- All figures inspected in rendered manuscript:",
            "- All visual notes accepted or resolved:",
            "- All inferred mappings checked against source-data dictionary:",
        ]
    )
    lines.extend(["", "Errors", "------"])
    lines.extend(f"- {item}" for item in sheet.errors)
    lines.extend(["", "Warnings", "--------"])
    lines.extend(f"- {item}" for item in sheet.warnings)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    sheet = build_sheet()
    write_sheet(sheet)
    print(REPORT_MD.relative_to(ROOT))
    return 0 if sheet.passed else 1


if __name__ == "__main__":
    sys.exit(main())
