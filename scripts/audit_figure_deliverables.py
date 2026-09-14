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
REPORT_TXT = LOG_DIR / "figure_deliverables_audit.txt"
REPORT_JSON = LOG_DIR / "figure_deliverables_audit.json"

MAIN_MANUSCRIPT = MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md"
FIGURE_INVENTORY = LOG_DIR / "manuscript_figure_inventory.json"

SOURCE_TABLE_DIR_CANDIDATES = [
    ROOT / "source_data",
    ROOT / "figures" / "source_data",
    MANUSCRIPT_DIR / "source_data",
    MANUSCRIPT_DIR / "figures" / "source_data",
]


@dataclass
class FigureDeliverable:
    figure: int
    caption_present: bool = False
    image_records: list[str] = field(default_factory=list)
    source_tables: list[str] = field(default_factory=list)
    inferred_image_records: list[str] = field(default_factory=list)
    inferred_source_tables: list[str] = field(default_factory=list)


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    figures: list[FigureDeliverable] = field(default_factory=list)

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
        audit.errors.append(f"Missing manuscript file: {rel(path)}")
    except OSError as exc:
        audit.errors.append(f"Cannot read {rel(path)}: {exc}")
    return ""


def load_inventory(audit: Audit) -> list[dict[str, Any]]:
    try:
        data = json.loads(FIGURE_INVENTORY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        audit.errors.append(f"Missing figure inventory: {rel(FIGURE_INVENTORY)}")
        return []
    except json.JSONDecodeError as exc:
        audit.errors.append(f"Invalid JSON in {rel(FIGURE_INVENTORY)}: {exc}")
        return []
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        audit.errors.append(f"Figure inventory has no records list: {rel(FIGURE_INVENTORY)}")
        return []
    return [record for record in records if isinstance(record, dict)]


def referenced_figures(text: str) -> set[int]:
    return {int(value) for value in re.findall(r"\b(?:Figure|Fig\.?)\s+([0-9]+)\b", text, flags=re.IGNORECASE)}


def caption_figures(text: str) -> set[int]:
    caption_patterns = [
        r"^(?:#+\s*)?(?:\*\*)?(?:Figure|Fig\.?)\s+([0-9]+)[.:\s]",
        r"^<figcaption[^>]*>\s*(?:<[^>]+>\s*)?(?:Figure|Fig\.?)\s+([0-9]+)[.:\s]",
    ]
    found: set[int] = set()
    for pattern in caption_patterns:
        found.update(int(value) for value in re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))
    return found


def figure_number_from_record(record: dict[str, Any]) -> int | None:
    text = " ".join(str(record.get(key) or "") for key in ["id", "reference", "path", "document"])
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


def candidate_source_tables() -> list[Path]:
    tables: list[Path] = []
    for directory in SOURCE_TABLE_DIR_CANDIDATES:
        if directory.exists():
            tables.extend(sorted(directory.rglob("*.csv")))
            tables.extend(sorted(directory.rglob("*.xlsx")))
    for path in ROOT.rglob("*"):
        if path.suffix.lower() not in {".csv", ".xlsx"}:
            continue
        lowered = path.as_posix().lower()
        if "source" in lowered and ("fig" in lowered or "figure" in lowered):
            tables.append(path)
    return sorted(set(tables))


def figure_number_from_source_table(path: Path) -> int | None:
    text = path.as_posix()
    patterns = [
        r"\bfig(?:ure)?[_ -]?0*([0-9]+)\b",
        r"\bsource[_ -]?data[_ -]?0*([0-9]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def audit_deliverables(audit: Audit) -> None:
    text = read_text(MAIN_MANUSCRIPT, audit)
    if not text:
        return
    referenced = referenced_figures(text)
    captions = caption_figures(text)
    if not referenced:
        audit.errors.append("No numbered main figures are referenced in the manuscript.")
        return
    expected = set(range(1, max(referenced) + 1))
    if referenced != expected:
        audit.errors.append(f"Main figure references are not contiguous from Figure 1: {sorted(referenced)}")

    inventory = load_inventory(audit)
    image_map: dict[int, list[str]] = {}
    inferred_image_map: dict[int, list[str]] = {}
    unmatched_images: list[str] = []
    seen_unmatched: set[str] = set()
    for record in inventory:
        label = str(record.get("path") or record.get("reference") or record.get("id"))
        number = figure_number_from_record(record)
        if number is None:
            if label and label not in seen_unmatched:
                unmatched_images.append(label)
                seen_unmatched.add(label)
            continue
        image_map.setdefault(number, []).append(label)

    missing_image_figures = [figure for figure in sorted(expected) if not image_map.get(figure)]
    if missing_image_figures and len(unmatched_images) >= len(missing_image_figures):
        for figure, label in zip(missing_image_figures, unmatched_images):
            image_map.setdefault(figure, []).append(label)
            inferred_image_map.setdefault(figure, []).append(label)

    source_map: dict[int, list[str]] = {}
    inferred_source_map: dict[int, list[str]] = {}
    unmatched_source_tables: list[str] = []
    seen_source_tables: set[str] = set()
    for table in candidate_source_tables():
        label = rel(table)
        number = figure_number_from_source_table(table)
        if number is None:
            if label not in seen_source_tables:
                unmatched_source_tables.append(label)
                seen_source_tables.add(label)
            continue
        source_map.setdefault(number, []).append(label)

    missing_source_figures = [figure for figure in sorted(expected) if not source_map.get(figure)]
    if missing_source_figures and len(unmatched_source_tables) >= len(missing_source_figures):
        for figure, label in zip(missing_source_figures, unmatched_source_tables):
            source_map.setdefault(figure, []).append(label)
            inferred_source_map.setdefault(figure, []).append(label)

    for figure in sorted(expected):
        item = FigureDeliverable(
            figure=figure,
            caption_present=figure in captions,
            image_records=image_map.get(figure, []),
            source_tables=source_map.get(figure, []),
            inferred_image_records=inferred_image_map.get(figure, []),
            inferred_source_tables=inferred_source_map.get(figure, []),
        )
        audit.figures.append(item)
        if not item.caption_present:
            audit.errors.append(f"Figure {figure} has no detected caption in the main manuscript.")
        if not item.image_records:
            audit.warnings.append(f"Figure {figure} has no image inventory record with a recognizable figure number.")
        if not item.source_tables:
            audit.warnings.append(f"Figure {figure} has no detected figure source-data table.")


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "figures": [
                    {
                        "figure": item.figure,
                        "caption_present": item.caption_present,
                        "image_records": item.image_records,
                        "source_tables": item.source_tables,
                        "inferred_image_records": item.inferred_image_records,
                        "inferred_source_tables": item.inferred_source_tables,
                    }
                    for item in audit.figures
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Figure Deliverables Audit",
        "=========================",
        "",
        f"Passed: {audit.passed}",
        f"Figures checked: {len(audit.figures)}",
        f"Errors: {len(audit.errors)}",
        f"Warnings: {len(audit.warnings)}",
        "",
        "| Figure | Caption | Images | Inferred images | Source tables | Inferred source tables |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in audit.figures:
        lines.append(
            f"| {item.figure} | {item.caption_present} | {len(item.image_records)} | "
            f"{len(item.inferred_image_records)} | {len(item.source_tables)} | {len(item.inferred_source_tables)} |"
        )
    lines.extend(["", "Errors", "------"])
    lines.extend(f"- {item}" for item in audit.errors)
    lines.extend(["", "Warnings", "--------"])
    lines.extend(f"- {item}" for item in audit.warnings)
    REPORT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    audit = Audit()
    audit_deliverables(audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
