from __future__ import annotations

import base64
from io import BytesIO
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
INVENTORY_JSON = LOG_DIR / "manuscript_figure_inventory.json"
REPORT_TXT = LOG_DIR / "figure_visual_quality_audit.txt"
REPORT_JSON = LOG_DIR / "figure_visual_quality_audit.json"


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors and not self.warnings


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_inventory(audit: Audit) -> list[dict[str, Any]]:
    try:
        data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    except FileNotFoundError:
        audit.errors.append(f"Missing figure inventory: {rel(INVENTORY_JSON)}")
        return []
    except json.JSONDecodeError as exc:
        audit.errors.append(f"Invalid JSON in {rel(INVENTORY_JSON)}: {exc}")
        return []
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list) or not records:
        audit.errors.append("Figure inventory has no image records.")
        return []
    return [record for record in records if isinstance(record, dict)]


def local_image_path(record: dict[str, Any]) -> Path | None:
    path_value = record.get("path")
    if not path_value:
        return None
    path = Path(str(path_value))
    return path if path.is_absolute() else ROOT / path


def image_basename(record: dict[str, Any]) -> str:
    return str(record.get("path") or record.get("reference") or record.get("id") or "unknown")


def embedded_image_bytes(record: dict[str, Any]) -> bytes | None:
    if record.get("kind") != "embedded":
        return None
    document_value = record.get("document")
    reference = str(record.get("reference") or "")
    match = re.match(r"embedded-image-([0-9]+)\.", reference)
    if not document_value or not match:
        return None
    document = Path(str(document_value))
    if not document.is_absolute():
        document = ROOT / document
    try:
        text = document.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    pattern = re.compile(r"""src\s*=\s*["']data:image/[a-zA-Z0-9.+-]+;base64,([^"']+)["']""")
    index = int(match.group(1))
    matches = list(pattern.finditer(text))
    if index < 1 or index > len(matches):
        return None
    try:
        return base64.b64decode(matches[index - 1].group(1), validate=True)
    except Exception:
        return None


def sample_stride(width: int, height: int, target: int = 250_000) -> int:
    pixels = max(width * height, 1)
    return max(1, int(math.sqrt(pixels / target)))


def luminance(pixel: tuple[int, ...]) -> float:
    r, g, b = pixel[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def edge_band_values(gray: list[list[float]], band: int) -> list[float]:
    if not gray:
        return []
    height = len(gray)
    width = len(gray[0])
    values: list[float] = []
    for y in range(height):
        for x in range(width):
            if x < band or y < band or x >= width - band or y >= height - band:
                values.append(gray[y][x])
    return values


def fraction_near_white(values: list[float]) -> float:
    return sum(value >= 248 for value in values) / len(values) if values else 0.0


def fraction_near_black(values: list[float]) -> float:
    return sum(value <= 7 for value in values) / len(values) if values else 0.0


def dynamic_range(values: list[float]) -> float:
    return max(values) - min(values) if values else 0.0


def analyze_image_bytes(data: bytes) -> dict[str, Any]:
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(f"Pillow is required for visual-quality audit: {exc}") from exc

    with Image.open(BytesIO(data)) as image:
        rgba = image.convert("RGBA")
        width, height = rgba.size
        stride = sample_stride(width, height)
        values: list[float] = []
        alpha_values: list[int] = []
        gray_grid: list[list[float]] = []
        for y in range(0, height, stride):
            row: list[float] = []
            for x in range(0, width, stride):
                pixel = rgba.getpixel((x, y))
                values.append(luminance(pixel))
                alpha_values.append(pixel[3])
                row.append(luminance(pixel))
            gray_grid.append(row)

    edge_band = max(1, min(12, min(len(gray_grid), len(gray_grid[0]) if gray_grid else 1) // 20))
    edge_values = edge_band_values(gray_grid, edge_band)
    return {
        "width": width,
        "height": height,
        "sample_stride": stride,
        "sampled_pixels": len(values),
        "dynamic_range": round(dynamic_range(values), 3),
        "near_white_fraction": round(fraction_near_white(values), 4),
        "near_black_fraction": round(fraction_near_black(values), 4),
        "transparent_fraction": round(sum(alpha < 250 for alpha in alpha_values) / len(alpha_values), 4) if alpha_values else 0.0,
        "edge_near_white_fraction": round(fraction_near_white(edge_values), 4),
        "edge_near_black_fraction": round(fraction_near_black(edge_values), 4),
    }


def analyze_image(path: Path) -> dict[str, Any]:
    return analyze_image_bytes(path.read_bytes())


def audit_record(record: dict[str, Any], audit: Audit) -> None:
    label = image_basename(record)
    path = local_image_path(record)
    if path is None:
        data = embedded_image_bytes(record)
        if data is None:
            audit.errors.append(f"{label}: embedded image cannot be decoded for visual-quality audit.")
            return
        try:
            metrics = analyze_image_bytes(data)
        except Exception as exc:
            audit.errors.append(f"{label}: cannot analyze embedded visual quality: {exc}")
            return
        output_path = None
    else:
        if not path.exists():
            audit.errors.append(f"{label}: image file is missing.")
            return
        if path.suffix.lower() == ".svg":
            audit.notes.append(f"{label}: SVG requires manual visual review because raster pixel audit is not applicable.")
            return
        try:
            metrics = analyze_image(path)
        except Exception as exc:
            audit.errors.append(f"{label}: cannot analyze visual quality: {exc}")
            return
        output_path = rel(path)

    problems: list[str] = []
    if metrics["width"] < 1200 or metrics["height"] < 700:
        problems.append(f"low resolution {metrics['width']} x {metrics['height']}")
    if metrics["dynamic_range"] < 8:
        problems.append(f"very low luminance dynamic range {metrics['dynamic_range']}")
    if metrics["near_white_fraction"] > 0.96:
        problems.append(f"mostly white pixels ({metrics['near_white_fraction']:.1%})")
    if metrics["near_black_fraction"] > 0.96:
        problems.append(f"mostly black pixels ({metrics['near_black_fraction']:.1%})")
    if metrics["transparent_fraction"] > 0.5:
        problems.append(f"mostly transparent pixels ({metrics['transparent_fraction']:.1%})")
    notes: list[str] = []
    if metrics["edge_near_white_fraction"] < 0.05 and metrics["edge_near_black_fraction"] < 0.05:
        notes.append("image content reaches the canvas edge; visually confirm it is intentional and not clipped")

    output = {"label": label, "path": output_path, **metrics, "problems": problems, "notes": notes}
    audit.records.append(output)
    for problem in problems:
        audit.warnings.append(f"{label}: {problem}.")
    for note in notes:
        audit.notes.append(f"{label}: {note}.")
    if path is None:
        return


def write_reports(audit: Audit) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "passed": audit.passed,
                "errors": audit.errors,
                "warnings": audit.warnings,
                "notes": audit.notes,
                "records": audit.records,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "Figure Visual Quality Audit",
        "===========================",
        "",
        f"Passed: {audit.passed}",
        f"Images analyzed: {len(audit.records)}",
        f"Errors: {len(audit.errors)}",
        f"Warnings: {len(audit.warnings)}",
        f"Notes: {len(audit.notes)}",
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
    for record in load_inventory(audit):
        if record.get("error"):
            audit.errors.append(f"{image_basename(record)}: inventory reports error {record.get('error')}.")
            continue
        audit_record(record, audit)
    write_reports(audit)
    print(REPORT_TXT.relative_to(ROOT))
    return 0 if audit.passed else 1


if __name__ == "__main__":
    sys.exit(main())
