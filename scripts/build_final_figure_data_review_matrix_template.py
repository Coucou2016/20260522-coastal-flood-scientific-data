"""Build a helper template for the final figure/data review matrix.

The template is derived from available audit logs and package manifests. It is
only a drafting aid: the submission gate audits
`manuscript/final_figure_data_review_matrix.json`, which must still be completed
and signed off by a reviewer.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = ROOT / "manuscript"
LOGS_DIR = ROOT / "logs"

TEMPLATE_PATH = MANUSCRIPT_DIR / "final_figure_data_review_matrix_template.json"
REPORT_MD = LOGS_DIR / "final_figure_data_review_matrix_template.md"
REPORT_JSON = LOGS_DIR / "final_figure_data_review_matrix_template.json"

INPUTS = [
    LOGS_DIR / "manuscript_figure_inventory.json",
    LOGS_DIR / "figure_deliverables_audit.json",
    LOGS_DIR / "figure_data_integrity_audit.json",
    ROOT / "final_archive_manifest.json",
]

ARTIFACT_EXTENSIONS = {
    ".png": "figure",
    ".jpg": "figure",
    ".jpeg": "figure",
    ".svg": "figure",
    ".webp": "figure",
    ".csv": "source_data_table",
    ".tsv": "source_data_table",
    ".tif": "generated_raster",
    ".tiff": "generated_raster",
    ".zip": "package_artifact",
}


def read_json(path: Path) -> object | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def artifact_type_for(value: str) -> str | None:
    suffix = Path(value).suffix.lower()
    return ARTIFACT_EXTENSIONS.get(suffix)


def artifact_id_for(value: str, artifact_type: str, index: int) -> str:
    match = re.search(r"(?:fig(?:ure)?[_\-\s]*)(\d+)", value, flags=re.IGNORECASE)
    if match and artifact_type == "figure":
        return f"Figure {match.group(1)}"
    name = Path(value.replace("\\", "/")).name or f"artifact-{index}"
    return name


def walk_values(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(walk_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(walk_values(item))
    elif isinstance(value, str):
        normalized = normalize_path(value)
        if artifact_type_for(normalized):
            found.append(normalized)
    return found


def build_template() -> dict:
    required: dict[str, dict] = {}
    inputs_seen: list[str] = []
    missing_inputs: list[str] = []

    for source in INPUTS:
        rel = str(source.relative_to(ROOT))
        data = read_json(source)
        if data is None:
            missing_inputs.append(rel)
            continue
        inputs_seen.append(rel)
        for index, value in enumerate(walk_values(data), start=1):
            artifact_type = artifact_type_for(value)
            if not artifact_type:
                continue
            artifact_id = artifact_id_for(value, artifact_type, index)
            key = f"{artifact_type}:{artifact_id}"
            evidence = f"{rel}: {value}"
            if key not in required:
                required[key] = {
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type,
                    "evidence": evidence,
                }
            elif evidence not in required[key]["evidence"]:
                required[key]["evidence"] = f"{required[key]['evidence']}; {evidence}"

    required_artifacts = sorted(required.values(), key=lambda item: (item["artifact_type"], item["artifact_id"], item["evidence"]))

    return {
        "status": "template_only",
        "reviewer": "",
        "review_date": "",
        "scope": {
            "manuscript": "manuscript/process_terrain_coastal_flood_CEE_manuscript.md",
            "review_html": "manuscript/process_terrain_coastal_flood_CEE_manuscript_review.html",
            "artifacts": "template derived from available audit logs; reviewer must confirm completeness",
        },
        "required_artifacts": required_artifacts,
        "rows": [
            {
                "artifact_id": item["artifact_id"],
                "artifact_type": item["artifact_type"],
                "status": "pending",
                "evidence": item["evidence"],
                "caption_matches_rendered_artifact": False,
                "rendered_artifact_checked": False,
                "source_data_checked": False,
                "numeric_sanity_checked": False,
                "visual_quality_checked": False,
                "package_artifact_checked": False,
                "issue_register_cross_checked": False,
                "notes": "",
            }
            for item in required_artifacts
        ],
        "completion_attestation": {
            "status": "pending",
            "evidence": "",
            "notes": "Copy reviewed entries into final_figure_data_review_matrix.json after manual verification.",
        },
        "template_metadata": {
            "inputs_seen": inputs_seen,
            "missing_inputs": missing_inputs,
            "artifact_count": len(required_artifacts),
        },
    }


def write_reports(template: dict) -> None:
    MANUSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = {
        "passed": True,
        "template": str(TEMPLATE_PATH.relative_to(ROOT)),
        "artifact_count": template["template_metadata"]["artifact_count"],
        "inputs_seen": template["template_metadata"]["inputs_seen"],
        "missing_inputs": template["template_metadata"]["missing_inputs"],
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Final Figure/Data Review Matrix Template",
        "",
        f"Passed: {report['passed']}",
        f"Template: `{report['template']}`",
        f"Artifact count: {report['artifact_count']}",
        "",
        "## Inputs Seen",
    ]
    lines.extend(f"- `{item}`" for item in report["inputs_seen"] or ["None"])
    lines.extend(["", "## Missing Inputs"])
    lines.extend(f"- `{item}`" for item in report["missing_inputs"] or ["None"])
    lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    template = build_template()
    write_reports(template)
    print(f"Passed: True")
    print(f"Artifact count: {template['template_metadata']['artifact_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
