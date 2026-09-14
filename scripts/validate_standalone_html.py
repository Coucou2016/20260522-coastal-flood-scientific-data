#!/usr/bin/env python3
"""Validate HTML reports have no external or relative asset dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

# Values that cannot load a separate asset.
ALLOWED_PREFIXES = ("data:", "#", "mailto:")

# Relative file extensions that must not appear (except data: URIs)
FORBIDDEN_EXT = re.compile(
    r"\.(?:css|png|jpe?g|gif|svg|webp|js|json|parquet|html|ico|woff2?|ttf)(?:\?|#|$)",
    re.IGNORECASE,
)

CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)


def _check_url(url: str, context: str) -> list[str]:
    url = url.strip()
    if not url or url.startswith(ALLOWED_PREFIXES):
        return []
    if url.lower().startswith("javascript:"):
        return [f"active javascript URL in {context}"]
    if url.startswith(("http://", "https://", "//")):
        return [f"external URL in {context}: {url[:80]}"]
    if FORBIDDEN_EXT.search(url) or url.startswith(("assets/", "figures/", "../", "./")):
        return [f"relative asset path in {context}: {url[:80]}"]
    return []


class StandaloneHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.issues: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag in {"iframe", "object", "embed"}:
            self.issues.append(f"contains unsupported active resource element <{tag}>")
        if tag == "link" and attr_map.get("rel", "").lower() in {"stylesheet", "preload", "modulepreload"}:
            self.issues.append(f"contains external-resource <link rel={attr_map.get('rel')!r}>")
        if tag == "script" and attr_map.get("src"):
            self.issues.extend(_check_url(attr_map["src"], "script src"))
        for name in ("src", "href", "poster", "data"):
            if attr_map.get(name):
                self.issues.extend(_check_url(attr_map[name], f"<{tag}> {name}"))
        if attr_map.get("srcset"):
            for candidate in attr_map["srcset"].split(","):
                self.issues.extend(_check_url(candidate.strip().split()[0], f"<{tag}> srcset"))
        if attr_map.get("style"):
            for match in CSS_URL_RE.finditer(attr_map["style"]):
                self.issues.extend(_check_url(match.group(2), f"<{tag}> style"))
        self.in_style = tag == "style"

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            for match in CSS_URL_RE.finditer(data):
                self.issues.extend(_check_url(match.group(2), "<style>"))


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parser = StandaloneHTMLParser()
    parser.feed(text)
    parser.close()
    return list(dict.fromkeys(parser.issues))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate standalone HTML reports")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="HTML files to check (default: reports/*.html)",
    )
    args = parser.parse_args()
    targets = args.paths or sorted(REPORTS.glob("*.html"))
    if not targets:
        print("No HTML files found.", file=sys.stderr)
        return 1

    failed = False
    for path in targets:
        if not path.exists():
            print(f"FAIL missing: {path}")
            failed = True
            continue
        issues = check_file(path)
        if issues:
            failed = True
            print(f"FAIL {path}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"OK   {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
