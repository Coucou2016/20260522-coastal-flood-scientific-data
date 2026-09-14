from __future__ import annotations

import argparse
import base64
import csv
import json
import math
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
REPORT_TXT = LOG_DIR / "figure_data_integrity_audit.txt"
REPORT_JSON = LOG_DIR / "figure_data_integrity_audit.json"

DOCUMENTS = [
    MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md",
    MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript_review.html",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".svg"}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "publication_package",
    "venv",
    ".venv",
}


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    image_records: list[dict[str, object]] = field(default_factory=list)
    table_records: list[dict[str, object]] = field(default_factory=list)

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
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        audit.error(f"Cannot read {rel(path)}: {exc}")
        return ""


def iter_document_image_refs(text: str) -> Iterable[str]:
    src_pattern = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
    md_pattern = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
    for match in src_pattern.finditer(text):
        yield match.group(1).strip()
    for match in md_pattern.finditer(text):
        yield match.group(1).strip()


def resolve_image_ref(ref: str, base: Path) -> Path | None:
    if not ref or ref.startswith("#") or ref.startswith("data:"):
        return None
    parsed = urlparse(ref)
    if parsed.scheme in {"http", "https", "mailto"}:
        return None
    if parsed.scheme == "file":
        return Path(unquote(parsed.path.lstrip("/"))) if re.match(r"^/[A-Za-z]:/", parsed.path) else Path(unquote(parsed.path))
    clean = unquote(ref.split("#", 1)[0].split("?", 1)[0])
    path = Path(clean)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def decode_embedded_images(text: str, audit: Audit) -> list[tuple[str, bytes]]:
    pattern = re.compile(r"""src\s*=\s*["']data:image/([a-zA-Z0-9.+-]+);base64,([^"']+)["']""")
    decoded: list[tuple[str, bytes]] = []
    for index, match in enumerate(pattern.finditer(text), start=1):
        ext = match.group(1).lower()
        try:
            decoded.append((f"embedded-image-{index}.{ext}", base64.b64decode(match.group(2), validate=True)))
        except Exception as exc:
            audit.error(f"Embedded image {index} cannot be decoded: {exc}")
    return decoded


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            return None
        length = int.from_bytes(data[index:index + 2], "big")
        if length < 2 or index + length > len(data):
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return width, height
        index += length
    return None


def webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8 " and len(data) >= 30:
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if chunk == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def tiff_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 8:
        return None
    if data[:2] == b"II":
        endian = "little"
    elif data[:2] == b"MM":
        endian = "big"
    else:
        return None
    magic = int.from_bytes(data[2:4], endian)
    if magic != 42:
        return None
    ifd_offset = int.from_bytes(data[4:8], endian)
    if ifd_offset + 2 > len(data):
        return None
    count = int.from_bytes(data[ifd_offset:ifd_offset + 2], endian)
    width: int | None = None
    height: int | None = None
    cursor = ifd_offset + 2
    for _ in range(count):
        if cursor + 12 > len(data):
            break
        tag = int.from_bytes(data[cursor:cursor + 2], endian)
        field_type = int.from_bytes(data[cursor + 2:cursor + 4], endian)
        field_count = int.from_bytes(data[cursor + 4:cursor + 8], endian)
        raw_value = data[cursor + 8:cursor + 12]
        value: int | None = None
        if field_count == 1 and field_type == 3:
            value = int.from_bytes(raw_value[:2], endian)
        elif field_count == 1 and field_type == 4:
            value = int.from_bytes(raw_value, endian)
        if tag == 256:
            width = value
        elif tag == 257:
            height = value
        cursor += 12
    if width is not None and height is not None:
        return width, height
    return None


def svg_dimensions(data: bytes) -> tuple[int, int] | None:
    text = data[:4096].decode("utf-8", errors="ignore")
    width = re.search(r"""\bwidth\s*=\s*["']([0-9.]+)""", text)
    height = re.search(r"""\bheight\s*=\s*["']([0-9.]+)""", text)
    if width and height:
        return int(float(width.group(1))), int(float(height.group(1)))
    viewbox = re.search(r"""\bviewBox\s*=\s*["']\s*[-0-9.]+\s+[-0-9.]+\s+([0-9.]+)\s+([0-9.]+)\s*["']""", text)
    if viewbox:
        return int(float(viewbox.group(1))), int(float(viewbox.group(2)))
    return None


def image_dimensions(data: bytes, suffix: str) -> tuple[int, int] | None:
    suffix = suffix.lower()
    if suffix == ".png":
        return png_dimensions(data)
    if suffix in {".jpg", ".jpeg"}:
        return jpeg_dimensions(data)
    if suffix == ".webp":
        return webp_dimensions(data)
    if suffix in {".tif", ".tiff"}:
        return tiff_dimensions(data)
    if suffix == ".svg":
        return svg_dimensions(data)
    return png_dimensions(data) or jpeg_dimensions(data) or webp_dimensions(data) or tiff_dimensions(data) or svg_dimensions(data)


def image_is_probably_blank(data: bytes, suffix: str) -> bool | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as image:
            extrema = image.convert("RGBA").getextrema()
            return all(low == high for low, high in extrema)
    except Exception:
        return None


def audit_image_bytes(name: str, data: bytes, suffix: str, audit: Audit) -> None:
    dims = image_dimensions(data, suffix)
    record: dict[str, object] = {"name": name, "bytes": len(data)}
    if dims:
        width, height = dims
        record["width"] = width
        record["height"] = height
        if width < 1200 or height < 700:
            audit.warn(f"{name} is low resolution for a main manuscript figure ({width} x {height}).")
    else:
        audit.warn(f"{name} dimensions could not be determined.")
    if len(data) < 10_000 and suffix.lower() != ".svg":
        audit.warn(f"{name} is very small ({len(data)} bytes), which can indicate a failed export.")
    blank = image_is_probably_blank(data, suffix)
    if blank is True:
        audit.error(f"{name} appears to be a single-color or blank raster image.")
    elif blank is None and suffix.lower() != ".svg":
        audit.note(f"{name} blank-image pixel check skipped because Pillow is unavailable.")
    audit.image_records.append(record)


def audit_document_images(audit: Audit) -> None:
    seen: set[Path] = set()
    found_refs = 0
    for document in DOCUMENTS:
        if not document.exists():
            audit.error(f"Missing manuscript document: {rel(document)}")
            continue
        text = read_text(document, audit)
        for name, data in decode_embedded_images(text, audit):
            found_refs += 1
            audit_image_bytes(f"{rel(document)}:{name}", data, Path(name).suffix, audit)
        for ref in iter_document_image_refs(text):
            path = resolve_image_ref(ref, document.parent)
            if path is None:
                continue
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            found_refs += 1
            if path in seen:
                continue
            seen.add(path)
            if not path.exists():
                audit.error(f"Referenced image does not exist: {ref} in {rel(document)}")
                continue
            try:
                audit_image_bytes(rel(path), path.read_bytes(), path.suffix, audit)
            except OSError as exc:
                audit.error(f"Cannot read referenced image {rel(path)}: {exc}")
    if found_refs == 0:
        audit.error("No local or embedded images were found in the manuscript Markdown/HTML.")


def iter_candidate_csvs() -> Iterable[Path]:
    for path in ROOT.rglob("*.csv"):
        parts = set(path.relative_to(ROOT).parts[:-1])
        if parts & EXCLUDED_DIRS:
            continue
        lowered = path.as_posix().lower()
        if any(token in lowered for token in ("source", "figure", "/fig", "\\fig", "table", "audit")):
            yield path


def parse_number(value: str) -> float | None:
    clean = value.strip().replace(",", "")
    if clean == "" or clean.lower() in {"na", "n/a", "null", "none"}:
        return None
    try:
        number = float(clean)
    except ValueError:
        return None
    return number


def matching_columns(fieldnames: Iterable[str], *needles: str) -> list[str]:
    columns = []
    for name in fieldnames:
        if not name:
            continue
        lowered = name.lower()
        if "connected" in needles and "disconnected" in lowered:
            continue
        if all(needle in lowered for needle in needles):
            columns.append(name)
    return columns


def scenario_level_key(column: str) -> str | None:
    normalized = column.lower().replace(" ", "")
    match = re.search(r"\+?([0-9]+(?:\.[0-9]+)?)m", normalized)
    if not match:
        return None
    return f"{float(match.group(1)):g}m"


def check_range(audit: Audit, csv_path: Path, column: str, row_index: int, value: float, low: float, high: float) -> None:
    if value < low or value > high:
        audit.error(f"{rel(csv_path)} row {row_index} column {column} has value {value}, outside [{low}, {high}].")


def audit_csv(path: Path, audit: Audit) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except UnicodeDecodeError:
        with path.open("r", encoding="latin-1", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        audit.error(f"Cannot parse CSV {rel(path)}: {exc}")
        return

    if not rows:
        audit.error(f"CSV source table is empty: {rel(path)}")
        return

    normalized_rows = [tuple((key, (value or "").strip()) for key, value in sorted(row.items()) if key) for row in rows]
    duplicate_count = len(normalized_rows) - len(set(normalized_rows))
    if duplicate_count:
        audit.warn(f"{rel(path)} contains {duplicate_count} duplicate data row(s).")

    fieldnames = [name for name in rows[0].keys() if name]
    if not fieldnames:
        audit.error(f"CSV source table has no header: {rel(path)}")
        return

    numeric_values: dict[str, list[float]] = {column: [] for column in fieldnames}
    for row_index, row in enumerate(rows, start=2):
        for column, raw in row.items():
            if not column:
                audit.warn(f"{rel(path)} row {row_index} has extra values beyond the declared CSV header.")
                continue
            if raw is None:
                continue
            lowered = raw.strip().lower()
            if lowered in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
                audit.error(f"{rel(path)} row {row_index} column {column} contains non-finite value {raw!r}.")
                continue
            value = parse_number(raw)
            if value is None:
                continue
            if not math.isfinite(value):
                audit.error(f"{rel(path)} row {row_index} column {column} contains non-finite numeric value {raw!r}.")
                continue
            numeric_values.setdefault(column, []).append(value)
            lowered_column = column.lower()
            if any(token in lowered_column for token in ("fraction", "percent", "percentage", "share", "ratio")):
                upper = 100.0 if any(token in lowered_column for token in ("percent", "percentage")) else 1.0
                check_range(audit, path, column, row_index, value, 0.0, upper)
            if lowered_column in {"r", "rho", "pearson_r", "spearman_r"} or "correlation" in lowered_column:
                check_range(audit, path, column, row_index, value, -1.0, 1.0)
            if lowered_column in {"p", "p_value", "pvalue"} or "p_value" in lowered_column:
                check_range(audit, path, column, row_index, value, 0.0, 1.0)
            if any(token in lowered_column for token in ("area", "count", "pixels", "n_cells", "cell_count")):
                if value < 0:
                    audit.error(f"{rel(path)} row {row_index} column {column} is negative ({value}).")
            if "elev" in lowered_column and ("median" in lowered_column or "lowland" in lowered_column):
                check_range(audit, path, column, row_index, value, -10.0, 40.0)

    for column, values in numeric_values.items():
        if len(values) >= 4 and len(set(values)) == 1:
            lowered = column.lower()
            if not any(token in lowered for token in ("scenario", "year", "threshold", "level", "id", "day")):
                audit.warn(f"{rel(path)} column {column} is constant across {len(values)} rows.")
        if len(values) >= 4 and set(values) == {0.0}:
            lowered = column.lower()
            if not any(token in lowered for token in ("baseline", "offset", "zero", "id")):
                audit.warn(f"{rel(path)} column {column} is all zeros across {len(values)} rows.")

    connected_cols = matching_columns(fieldnames, "connected")
    bathtub_cols = matching_columns(fieldnames, "bathtub")
    if connected_cols and bathtub_cols:
        for row_index, row in enumerate(rows, start=2):
            for connected_col in connected_cols:
                connected = parse_number(row.get(connected_col, ""))
                if connected is None:
                    continue
                connected_level = scenario_level_key(connected_col)
                for bathtub_col in bathtub_cols:
                    bathtub_level = scenario_level_key(bathtub_col)
                    if connected_level is not None and bathtub_level is not None and connected_level != bathtub_level:
                        continue
                    bathtub = parse_number(row.get(bathtub_col, ""))
                    if bathtub is None:
                        continue
                    if connected > bathtub + max(1e-9, abs(bathtub) * 1e-9):
                        audit.error(
                            f"{rel(path)} row {row_index}: {connected_col} ({connected}) exceeds "
                            f"{bathtub_col} ({bathtub})."
                        )

    low_cols = matching_columns(fieldnames, "d10") + matching_columns(fieldnames, "p10")
    med_cols = matching_columns(fieldnames, "median") + matching_columns(fieldnames, "p50")
    high_cols = matching_columns(fieldnames, "d90") + matching_columns(fieldnames, "p90")
    if low_cols and med_cols and high_cols:
        for row_index, row in enumerate(rows, start=2):
            low = parse_number(row.get(low_cols[0], ""))
            med = parse_number(row.get(med_cols[0], ""))
            high = parse_number(row.get(high_cols[0], ""))
            if None not in (low, med, high) and not (low <= med <= high):
                audit.error(f"{rel(path)} row {row_index}: quantiles are not monotonic ({low}, {med}, {high}).")

    audit.table_records.append({"path": rel(path), "rows": len(rows), "columns": len(fieldnames)})


def audit_source_tables(audit: Audit) -> None:
    csv_paths = sorted(set(iter_candidate_csvs()))
    if not csv_paths:
        audit.error("No candidate figure/source CSV files were found.")
        return
    for path in csv_paths:
        audit_csv(path, audit)


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "Figure and data integrity audit",
        "================================",
        "",
        f"Images checked: {len(audit.image_records)}",
        f"CSV source tables checked: {len(audit.table_records)}",
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
    REPORT_JSON.write_text(
        json.dumps(
            {
                "errors": audit.errors,
                "warnings": audit.warnings,
                "notes": audit.notes,
                "images": audit.image_records,
                "tables": audit.table_records,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit manuscript figure files and figure source data.")
    parser.add_argument("--strict", action="store_true", help="Return a nonzero exit code when warnings are present.")
    args = parser.parse_args()

    audit = Audit()
    audit_document_images(audit)
    audit_source_tables(audit)
    write_reports(audit)

    print(REPORT_TXT.relative_to(ROOT))
    if audit.errors:
        return 1
    if args.strict and audit.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
