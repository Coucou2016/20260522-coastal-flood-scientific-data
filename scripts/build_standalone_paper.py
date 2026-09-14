#!/usr/bin/env python3
"""Build standalone paper HTML and Markdown exports with embedded figures."""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_MD = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_manuscript.md"
FIG_DIR = ROOT / "figures" / "main"
OUT_HTML = ROOT / "paper.html"
OUT_MD = ROOT / "paper.md"
OUT_PDF = ROOT / "paper.pdf"
FINAL_HTML = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_final_paper.html"
FINAL_MD = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_final_paper.md"
FINAL_PDF = ROOT / "manuscript" / "process_terrain_coastal_flood_CEE_final_paper.pdf"
SUBMISSION_LINKS = ROOT / "config" / "submission_links.json"

FIGURE_FILES: dict[str, str | list[tuple[str, str]]] = {
    "1": "Fig1_process_terrain_design.png",
    "2": "Fig2_regional_screening_agreement.png",
    "3": "Fig3_connected_terrain_contrasts.png",
    "4": "Fig4_metric_decomposition_robustness.png",
}

SUPPLEMENTARY_FIGURE_FILES: dict[str, str] = {
    "S1": "FigS1_water_level_definition.png",
    "S2": "FigS2_process_coherence.png",
    "S3": "FigS3_connectivity_gallery.png",
    "S4": "FigS4_elevation_product_datum_sensitivity.png",
    "S5": "FigS5_coastrp_match_audit.png",
}


CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def data_uri_for_image(name: str) -> str:
    path = FIG_DIR / name
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def markdown_images_for_figure(number: str, default_title: str) -> list[str]:
    spec = FIGURE_FILES[number]
    if isinstance(spec, str):
        return [f"![Figure {number}. {default_title}]({data_uri_for_image(spec)})"]
    return [f"![{alt}]({data_uri_for_image(name)})" for alt, name in spec]


def markdown_images_for_supplementary_figure(number: str, default_title: str) -> list[str]:
    name = SUPPLEMENTARY_FIGURE_FILES[number]
    return [f"![Supplementary Figure {number}. {default_title}]({data_uri_for_image(name)})"]


def replace_section(markdown: str, header: str, next_header: str, body: str) -> str:
    pattern = rf"({re.escape(header)}\n)(.*?)(?=\n{re.escape(next_header)}\n)"
    replacement = rf"\1\n{body.strip()}\n"
    return re.sub(pattern, replacement, markdown, flags=re.S)


def load_submission_links() -> dict[str, str]:
    if not SUBMISSION_LINKS.exists():
        return {}
    return json.loads(SUBMISSION_LINKS.read_text(encoding="utf-8"))


def clean_link(value: object) -> str:
    return str(value or "").strip()


def availability_link_sentence(kind: str, links: dict[str, str]) -> str:
    data_link = clean_link(links.get("data_repository_url_or_doi"))
    code_link = clean_link(links.get("code_repository_url_or_doi"))
    reviewer_link = clean_link(links.get("private_reviewer_link"))
    if reviewer_link:
        return f"Private reviewer-access repository link: {reviewer_link}."
    if kind == "data" and data_link:
        return f"Processed data and figure-source tables are archived at: {data_link}."
    if kind == "code" and code_link:
        return f"Code and reproducibility workflow are archived at: {code_link}."
    return (
        "Public repository URL and DOI/private reviewer link: 待补充. "
        "The local reproducibility package has been generated but has not yet been deposited in an external reviewer-access repository."
    )


def format_number(value: str, digits: int = 2) -> str:
    number = float(value)
    return f"{number:.{digits}f}"


def normalize_manuscript(markdown: str) -> str:
    return markdown


def build_markdown_export(source_markdown: str) -> str:
    lines = normalize_manuscript(source_markdown).splitlines()
    output: list[str] = []
    current_figure: str | None = None
    current_title = ""

    for line in lines:
        heading_match = re.match(r"^### Figure\s+(\d+)(?:\.|\s+\|)\s*(.+)$", line.strip())
        supp_heading_match = re.match(r"^### Supplementary Figure\s+(S\d+)(?:\.|\s+\|)\s*(.+)$", line.strip())
        if heading_match:
            current_figure = heading_match.group(1)
            current_title = heading_match.group(2)
            continue
        if supp_heading_match:
            current_figure = supp_heading_match.group(1)
            current_title = supp_heading_match.group(2)
            continue

        if current_figure and line.strip().startswith("**File:**"):
            output.append("")
            if current_figure.startswith("S"):
                output.extend(markdown_images_for_supplementary_figure(current_figure, current_title))
            else:
                output.extend(markdown_images_for_figure(current_figure, current_title))
            continue

        output.append(line)

    return "\n".join(output).rstrip() + "\n"


def math_html(raw: str) -> str:
    text = raw.strip()
    replacements = {
        r"\mathrm{COAST}": "COAST",
        r"\mathrm{GSSR}": "GSSR",
        r"\eta": "η",
        r"\max": "max",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    escaped = html.escape(text)
    escaped = re.sub(r"_\{([^{}]+)\}", r"<sub>\1</sub>", escaped)
    escaped = re.sub(r"\^\{([^{}]+)\}", r"<sup>\1</sup>", escaped)
    escaped = escaped.replace("\\", "")
    return escaped


def inline_format(text: str) -> str:
    placeholders: list[str] = []

    def stash_math(match: re.Match[str]) -> str:
        placeholders.append(f'<span class="math">{math_html(match.group(1))}</span>')
        return f"@@MATH{len(placeholders) - 1}@@"

    text = re.sub(r"\\\((.+?)\\\)", stash_math, text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", escaped)
    for index, value in enumerate(placeholders):
        escaped = escaped.replace(f"@@MATH{index}@@", value)
    return escaped


def markdown_table_to_html(rows: list[str], caption: str | None) -> str:
    clean = [row.strip() for row in rows if row.strip()]
    if len(clean) < 2:
        return "".join(f"<p>{inline_format(row)}</p>" for row in clean)

    headers = [cell.strip() for cell in clean[0].strip("|").split("|")]
    body_rows = clean[2:]
    thead = "".join(f"<th>{inline_format(header)}</th>" for header in headers)
    body_html: list[str] = []
    for row in body_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        body_html.append("<tr>" + "".join(f"<td>{inline_format(cell)}</td>" for cell in cells) + "</tr>")

    table = (
        "<div class=\"scroll-table\"><table>"
        + (f"<caption>{inline_format(caption)}</caption>" if caption else "")
        + f"<thead><tr>{thead}</tr></thead><tbody>{''.join(body_html)}</tbody></table></div>"
    )
    if caption:
        return f'<figure class="table-block"><figcaption>{inline_format(caption)}</figcaption>{table}</figure>'
    return table


def image_markdown_to_html(line: str) -> str | None:
    match = re.match(r"^!\[(.*?)\]\((data:image/png;base64,[^)]+)\)$", line.strip())
    if not match:
        return None
    alt = match.group(1)
    uri = match.group(2)
    return (
        '<figure class="figure-block">'
        f'<figcaption>{inline_format(alt)}</figcaption>'
        f'<img src="{uri}" alt="{html.escape(alt)}" />'
        "</figure>"
    )


def markdown_to_html(markdown: str) -> str:
    parts: list[str] = []
    table_rows: list[str] = []
    pending_table_caption: str | None = None
    in_equation = False
    equation_lines: list[str] = []

    def flush_table() -> None:
        nonlocal table_rows, pending_table_caption
        if table_rows:
            parts.append(markdown_table_to_html(table_rows, pending_table_caption))
            table_rows = []
            pending_table_caption = None

    def flush_pending_caption_if_needed(next_is_table: bool) -> None:
        nonlocal pending_table_caption
        if pending_table_caption and not next_is_table:
            parts.append(f"<p><strong>{inline_format(pending_table_caption)}</strong></p>")
            pending_table_caption = None

    for line in markdown.splitlines():
        stripped = line.strip()
        is_table_line = stripped.startswith("|") and stripped.endswith("|")
        if is_table_line:
            table_rows.append(line)
            continue

        flush_table()

        if in_equation:
            if stripped == r"\]":
                parts.append(f'<div class="equation">{math_html(" ".join(equation_lines))}</div>')
                equation_lines = []
                in_equation = False
            elif stripped:
                equation_lines.append(stripped)
            continue

        if stripped == r"\[":
            flush_pending_caption_if_needed(False)
            in_equation = True
            equation_lines = []
            continue

        if not stripped:
            continue

        table_caption_match = re.match(r"^\*\*(Table\s+\d+\..+?)\*\*$", stripped)
        if table_caption_match:
            flush_pending_caption_if_needed(False)
            pending_table_caption = table_caption_match.group(1)
            continue

        flush_pending_caption_if_needed(False)

        image_html = image_markdown_to_html(stripped)
        if image_html:
            parts.append(image_html)
            continue

        if stripped.startswith("---"):
            parts.append("<hr />")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = min(len(heading_match.group(1)), 4)
            text = heading_match.group(2)
            anchor = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            parts.append(f'<h{level} id="{html.escape(anchor)}">{inline_format(text)}</h{level}>')
            continue

        if stripped.startswith("- "):
            parts.append(f'<p class="bullet">• {inline_format(stripped[2:])}</p>')
            continue

        parts.append(f"<p>{inline_format(stripped)}</p>")

    flush_table()
    return "\n".join(parts)


def build_html(markdown: str) -> str:
    body = markdown_to_html(markdown)
    title_match = re.search(r"^#\s+(.+)$", markdown, flags=re.M)
    title = title_match.group(1) if title_match else "Standalone paper"
    css = """
:root {
  --paper: #ffffff;
  --page: #ffffff;
  --ink: #1b2430;
  --muted: #5f6b78;
  --line: #d9dde3;
  --soft: #eef3f6;
  --accent: #1b2430;
  --accent-2: #1b2430;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background: #ffffff;
  font-family: Georgia, "Times New Roman", "Noto Serif CJK SC", "Source Han Serif SC", "Microsoft YaHei", serif;
  line-height: 1.68;
  font-size: 16px;
}
.page {
  max-width: 1060px;
  margin: 0 auto;
  background: var(--page);
  padding: 56px 72px 72px;
  box-shadow: none;
}
h1 {
  margin: 0 0 18px;
  font-size: 2.35rem;
  line-height: 1.12;
  letter-spacing: 0;
}
h2 {
  margin: 38px 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
  font-size: 1.55rem;
  line-height: 1.25;
}
h3 {
  margin: 28px 0 10px;
  color: var(--accent);
  font-size: 1.17rem;
}
h4 {
  margin: 22px 0 8px;
  color: var(--accent-2);
  font-size: 1rem;
}
p {
  margin: 0 0 12px;
  text-align: justify;
}
strong { font-weight: 700; }
em { font-style: italic; }
code {
  padding: 1px 4px;
  border-radius: 4px;
  background: #f0f2f4;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
}
hr {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 22px 0;
}
.bullet {
  padding-left: 18px;
  text-align: left;
}
.figure-block {
  margin: 18px 0 28px;
  padding: 0;
  border: 0;
  background: #ffffff;
  break-inside: avoid;
}
.figure-block figcaption {
  margin: 0 0 10px;
  color: var(--ink);
  font-weight: 700;
  line-height: 1.35;
  text-align: left;
}
.figure-block img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid #e5e8ec;
  background: #fff;
}
.table-block {
  margin: 18px 0 28px;
}
.table-block figcaption {
  margin: 0 0 8px;
  font-weight: 700;
}
.scroll-table {
  width: 100%;
  overflow-x: auto;
}
table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 0.9rem;
}
caption {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
th, td {
  border: 1px solid var(--line);
  padding: 7px 9px;
  vertical-align: top;
  text-align: left;
}
th {
  background: var(--soft);
  font-weight: 700;
}
tbody tr:nth-child(even) td {
  background: #fafafa;
}
.math, .equation {
  font-family: "Cambria Math", "Times New Roman", serif;
}
.equation {
  margin: 14px 0 16px;
  padding: 10px 14px;
  text-align: center;
  background: #fbfcfd;
  border: 1px solid var(--line);
}
@media (max-width: 760px) {
  .page {
    padding: 28px 18px 42px;
    box-shadow: none;
  }
  h1 { font-size: 1.85rem; }
  table { font-size: 0.84rem; }
}
@media print {
  @page {
    size: A4;
    margin: 16mm 15mm 18mm;
  }
  body { background: #fff; }
  .page {
    max-width: none;
    box-shadow: none;
    padding: 0;
  }
  h1, h2, h3, h4 { break-after: avoid; }
  .figure-block, .table-block, table { break-inside: avoid; }
  .figure-block {
    margin: 12px 0 20px;
    padding: 8px;
  }
  .figure-block img {
    max-height: 235mm;
    object-fit: contain;
  }
  .scroll-table {
    overflow: visible;
  }
  table {
    width: 100%;
    min-width: 0;
    table-layout: fixed;
    font-size: 7.2pt;
  }
  th, td {
    padding: 3px 4px;
    overflow-wrap: anywhere;
    word-break: normal;
  }
}
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
{css}
  </style>
</head>
<body>
<main class="page">
{body}
</main>
</body>
</html>
"""


def chrome_executable() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    found = shutil.which("chrome") or shutil.which("chrome.exe") or shutil.which("msedge") or shutil.which("msedge.exe")
    if found:
        return Path(found)
    raise RuntimeError("No Chrome/Edge executable found for PDF export.")


def html_file_url(path: Path) -> str:
    return path.resolve().as_uri()


def build_pdf_from_html() -> None:
    chrome = chrome_executable()
    if OUT_PDF.exists():
        OUT_PDF.unlink()
    command = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=10000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={OUT_PDF}",
        html_file_url(OUT_HTML),
    ]
    subprocess.run(command, cwd=ROOT, check=True, timeout=180)
    if not OUT_PDF.exists() or OUT_PDF.stat().st_size < 100_000:
        raise RuntimeError(f"PDF export failed or produced a suspiciously small file: {OUT_PDF}")
    shutil.copyfile(OUT_PDF, FINAL_PDF)


def main() -> int:
    source_markdown = SRC_MD.read_text(encoding="utf-8")
    links = load_submission_links()
    data_sentence = availability_link_sentence("data", links)
    code_sentence = availability_link_sentence("code", links)
    source_markdown = replace_section(
        source_markdown,
        "## Data availability",
        "## Code availability",
        (
            "COAST-RP, GSSR and DeltaDTM are available from the repositories cited in this article [9-11]. "
            "The local terrain products are available from the Environment Agency and PDOK/Rijkswaterstaat "
            "services [13,14]. The processed 68-station table, 2,960-row robustness grid, figure-source tables, "
            "input hashes and compact reproducibility package are retained for independent review. "
            f"{data_sentence} Upstream raw products are identified by source URL and SHA-256 digest but are not "
            "redistributed from this repository; their original provider terms apply."
        ),
    )
    source_markdown = replace_section(
        source_markdown,
        "## Code availability",
        "## Acknowledgements",
        (
            "The Python workflow for product matching, mask-aware terrain classification, statistical analysis, "
            "figure generation and standalone document export is retained with fixed environment files and a "
            f"one-command rebuild gate. {code_sentence}"
        ),
    )
    paper_markdown = build_markdown_export(source_markdown)
    OUT_MD.write_text(paper_markdown, encoding="utf-8")
    paper_html = build_html(paper_markdown)
    OUT_HTML.write_text(paper_html, encoding="utf-8")
    FINAL_MD.write_text(paper_markdown, encoding="utf-8")
    FINAL_HTML.write_text(paper_html, encoding="utf-8")
    build_pdf_from_html()
    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_PDF}")
    print(f"Wrote {FINAL_HTML}")
    print(f"Wrote {FINAL_MD}")
    print(f"Wrote {FINAL_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
