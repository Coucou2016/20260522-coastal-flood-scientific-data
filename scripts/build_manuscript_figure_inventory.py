from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOG_DIR = ROOT / "logs"
INVENTORY_JSON = LOG_DIR / "manuscript_figure_inventory.json"
INVENTORY_MD = LOG_DIR / "manuscript_figure_inventory.md"

DOCUMENTS = [
    MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript.md",
    MANUSCRIPT_DIR / "process_terrain_coastal_flood_CEE_manuscript_review.html",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".svg"}


@dataclass
class FigureRecord:
    id: str
    document: str
    reference: str
    kind: str
    path: str | None
    exists: bool
    bytes: int | None
    sha256: str | None
    width: int | None
    height: int | None
    error: str | None = None


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    cursor = 2
    while cursor + 9 < len(data):
        if data[cursor] != 0xFF:
            cursor += 1
            continue
        marker = data[cursor + 1]
        cursor += 2
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if cursor + 2 > len(data):
            return None
        length = int.from_bytes(data[cursor:cursor + 2], "big")
        if length < 2 or cursor + length > len(data):
            return None
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[cursor + 3:cursor + 5], "big")
            width = int.from_bytes(data[cursor + 5:cursor + 7], "big")
            return width, height
        cursor += length
    return None


def webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    if chunk == b"VP8 ":
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if chunk == b"VP8L":
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
    if int.from_bytes(data[2:4], endian) != 42:
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


def dimensions(data: bytes, suffix: str) -> tuple[int, int] | None:
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


def embedded_images(text: str) -> Iterable[tuple[str, bytes, str]]:
    pattern = re.compile(r"""src\s*=\s*["']data:image/([a-zA-Z0-9.+-]+);base64,([^"']+)["']""")
    for index, match in enumerate(pattern.finditer(text), start=1):
        ext = "." + match.group(1).lower().replace("jpeg", "jpg")
        try:
            yield f"embedded-image-{index}{ext}", base64.b64decode(match.group(2), validate=True), ext
        except Exception:
            yield f"embedded-image-{index}{ext}", b"", ext


def local_record(record_id: str, document: Path, ref: str, path: Path) -> FigureRecord:
    if not path.exists():
        return FigureRecord(record_id, rel(document), ref, "local", rel(path), False, None, None, None, None, "missing file")
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return FigureRecord(record_id, rel(document), ref, "local", rel(path), True, None, None, None, None, "unsupported extension")
    try:
        data = path.read_bytes()
    except OSError as exc:
        return FigureRecord(record_id, rel(document), ref, "local", rel(path), True, None, None, None, None, str(exc))
    size = dimensions(data, path.suffix)
    width, height = size if size else (None, None)
    return FigureRecord(record_id, rel(document), ref, "local", rel(path), True, len(data), sha256_bytes(data), width, height)


def embedded_record(record_id: str, document: Path, name: str, data: bytes, suffix: str) -> FigureRecord:
    if not data:
        return FigureRecord(record_id, rel(document), name, "embedded", None, True, None, None, None, None, "embedded image could not be decoded")
    size = dimensions(data, suffix)
    width, height = size if size else (None, None)
    return FigureRecord(record_id, rel(document), name, "embedded", None, True, len(data), sha256_bytes(data), width, height)


def build_inventory() -> list[FigureRecord]:
    records: list[FigureRecord] = []
    for document in DOCUMENTS:
        text = read_text(document)
        for name, data, suffix in embedded_images(text):
            records.append(embedded_record(f"figimg-{len(records) + 1:03d}", document, name, data, suffix))
        for ref in iter_document_image_refs(text):
            path = resolve_image_ref(ref, document.parent)
            if path is None:
                continue
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            records.append(local_record(f"figimg-{len(records) + 1:03d}", document, ref, path))
    return records


def write_inventory(records: list[FigureRecord]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    errors = [record for record in records if record.error]
    payload = {
        "passed": len(records) > 0 and not errors,
        "image_count": len(records),
        "error_count": len(errors),
        "records": [asdict(record) for record in records],
    }
    INVENTORY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "Manuscript Figure Inventory",
        "===========================",
        "",
        f"Passed: {payload['passed']}",
        f"Images: {len(records)}",
        f"Errors: {len(errors)}",
        "",
        "| ID | Document | Kind | Path/Reference | Bytes | Dimensions | SHA256 | Error |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for record in records:
        location = record.path or record.reference
        dims = f"{record.width} x {record.height}" if record.width and record.height else ""
        sha = record.sha256[:16] + "..." if record.sha256 else ""
        lines.append(
            f"| {record.id} | {record.document} | {record.kind} | {location} | "
            f"{record.bytes or ''} | {dims} | {sha} | {record.error or ''} |"
        )
    INVENTORY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    records = build_inventory()
    write_inventory(records)
    print(INVENTORY_MD.relative_to(ROOT))
    return 0 if records and not any(record.error for record in records) else 1


if __name__ == "__main__":
    sys.exit(main())
