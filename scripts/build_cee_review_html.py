#!/usr/bin/env python3
"""Build a self-contained HTML review copy of the process-terrain manuscript."""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript.md"
OUT = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript_review.html"


def inline_format(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def embed_image(path_text: str) -> str:
    match = re.search(r"(figures/main/[A-Za-z0-9_]+\.png)", path_text)
    if not match:
        return ""
    path = ROOT / match.group(1)
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    alt = path.stem
    return f'<figure><img src="data:image/png;base64,{data}" alt="{html.escape(alt)}"></figure>'


def markdown_table_to_html(rows: list[str]) -> str:
    clean = [r.strip() for r in rows if r.strip()]
    if len(clean) < 2:
        return "".join(f"<p>{inline_format(r)}</p>" for r in clean)
    header = [c.strip() for c in clean[0].strip("|").split("|")]
    body = clean[2:]
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{inline_format(c)}</th>" for c in header)
    out.append("</tr></thead><tbody>")
    for row in body:
        cells = [c.strip() for c in row.strip("|").split("|")]
        out.append("<tr>")
        out.extend(f"<td>{inline_format(c)}</td>" for c in cells)
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def convert(md: str) -> str:
    lines = md.splitlines()
    parts: list[str] = []
    table: list[str] = []

    def flush_table() -> None:
        nonlocal table
        if table:
            parts.append(markdown_table_to_html(table))
            table = []

    for line in lines:
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table.append(line)
            continue
        flush_table()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped[level:].strip()
            parts.append(f"<h{level}>{inline_format(text)}</h{level}>")
        elif stripped.startswith("---"):
            parts.append("<hr>")
        elif stripped.startswith("- "):
            parts.append(f"<p class=\"bullet\">&bull; {inline_format(stripped[2:])}</p>")
        else:
            parts.append(f"<p>{inline_format(stripped)}</p>")
            if stripped.startswith("**File:**"):
                img = embed_image(stripped)
                if img:
                    parts.append(img)
    flush_table()
    return "\n".join(parts)


def main() -> int:
    body = convert(MANUSCRIPT.read_text(encoding="utf-8"))
    css = """
body{font-family:Arial,Helvetica,sans-serif;color:#172033;margin:0;background:#f4f6f8;line-height:1.55}
.page{max-width:1120px;margin:0 auto;background:#fff;padding:48px 64px;box-shadow:0 0 30px rgba(15,23,42,.10)}
h1{font-size:30px;line-height:1.15;margin:0 0 18px;color:#0f172a}
h2{font-size:22px;margin:34px 0 12px;border-bottom:2px solid #e2e8f0;padding-bottom:6px;color:#1e293b}
h3{font-size:17px;margin:26px 0 8px;color:#1f3a5f}
h4{font-size:14px;margin:18px 0 8px;color:#334155}
p{font-size:14px;margin:8px 0;text-align:justify}
.bullet{padding-left:18px;text-align:left}
table{width:100%;border-collapse:collapse;margin:14px 0 22px;font-size:12px}
th,td{border:1px solid #d6dee8;padding:7px 8px;vertical-align:top}
th{background:#edf4fb;text-align:left;color:#0f172a}
figure{margin:18px 0 30px;padding:12px;border:1px solid #e2e8f0;background:#fbfdff}
img{width:100%;height:auto;display:block}
code{background:#eef2f7;border-radius:3px;padding:1px 4px}
hr{border:0;border-top:1px solid #e2e8f0;margin:18px 0}
"""
    html_doc = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Process-terrain CEE manuscript review</title><style>{css}</style></head><body><main class=\"page\">{body}</main></body></html>"
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
