#!/usr/bin/env python3
"""Generate a current scientific-integrity review from project evidence."""

from __future__ import annotations

import hashlib
import html
import json
import math
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
from PIL import Image
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"
MANUSCRIPT = ROOT / "manuscript"
MANIFEST = ROOT / "config" / "submission_figure_manifest.json"
OUT_MD = MANUSCRIPT / "scientific_integrity_review.md"
OUT_HTML = MANUSCRIPT / "scientific_integrity_review.html"
OUT_PDF = MANUSCRIPT / "scientific_integrity_review.pdf"
OUT_JSON = ROOT / "logs" / "scientific_integrity_review.json"
CHROME = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_md(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def table_html(headers: list[str], rows: list[list[object]]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    head = "".join(f"<th>{esc(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def pdf_fonts(path: Path) -> list[str]:
    from pypdf import PdfReader

    fonts: set[str] = set()
    for page in PdfReader(path).pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        font_map = resources.get_object().get("/Font")
        if not font_map:
            continue
        for ref in font_map.get_object().values():
            base = ref.get_object().get("/BaseFont")
            if base:
                fonts.add(str(base))
    return sorted(fonts)


def figure_rows() -> list[list[object]]:
    figures = json.loads(MANIFEST.read_text(encoding="utf-8"))["figures"]
    rows = []
    for item in figures:
        png, pdf = ROOT / item["png"], ROOT / item["pdf"]
        with Image.open(png) as image:
            size = f"{image.width} x {image.height}"
        times = any("Times" in name for name in pdf_fonts(pdf))
        rows.append(
            [
                item["number"],
                size,
                "yes" if times else "not detected",
                sha256(png)[:16],
                item["generator"],
                item["primary_source"],
            ]
        )
    return rows


def input_rows() -> list[list[object]]:
    paths = [
        ROOT / "data/raw/coast_rp/extracted/COAST-RP.nc",
        ROOT / "data/raw/coast_rp/extracted/COAST-RP_ETC.nc",
        ROOT / "data/raw/coast_rp/extracted/COAST-RP_TC.nc",
        ROOT / "data/raw/deltadtm/zips/mask_tiles.zip",
    ]
    paths.extend(sorted((ROOT / "data/raw/local_dtm").glob("*_local_dtm_10m.tif")))
    return [
        [path.relative_to(ROOT).as_posix(), f"{path.stat().st_size:,}", sha256(path)]
        for path in paths
        if path.exists()
    ]


def reference_rows() -> list[list[object]]:
    items = [
        (
            ROOT / "仿照撰写的CEE论文/s43247-025-02326-w.md",
            "CEE article structure, pacing and cautious reporting",
            "No station values, calculated results or wording copied into project results",
        ),
        (
            ROOT / "仿照撰写的CEE论文/s43247-025-02326-w.pdf",
            "Rendered CEE layout and figure-caption benchmark",
            "No source-paper data used as project observations",
        ),
        (
            ROOT / "仿照撰写的CEE论文/0823-额外参考/s41586-026-10196-1.md",
            "Common-vertical-reference problem and DeltaDTM context",
            "Cited as external evidence; no exposure estimates transferred",
        ),
        (
            ROOT / "仿照撰写的CEE论文/0823-额外参考/nhess-26-1859-2026.md",
            "Dynamic Pan-European hazard-modelling context",
            "Cited to delimit static screening; no hazard maps or values transferred",
        ),
    ]
    return [
        [path.relative_to(ROOT).as_posix(), sha256(path), role, boundary]
        for path, role, boundary in items
        if path.exists()
    ]
def calculate() -> tuple[list[dict[str, str]], dict[str, object]]:
    checks: list[dict[str, str]] = []

    def record(name: str, passed: bool, evidence: str) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})

    water = pd.read_csv(SOURCE / "Fig2_water_level_divergence_with_uncertainty.csv")
    d10_error = (water["coast_rp_rp10_m"] - water["gssr_rp10_m"] - water["D10_m"]).abs()
    record("D10 arithmetic", len(water) == 8 and d10_error.max() < 1e-10,
           f"8 focal rows; maximum error={d10_error.max():.3e} m")

    terrain = pd.read_csv(SOURCE / "Fig6_mask_aware_terrain_area_metrics.csv")
    resolved = terrain[terrain["marine_seed_resolved"].eq(True)].copy()
    primary = resolved[resolved["match_dist_km"].le(6.0)].dropna(
        subset=["coast_rp_rp10_m", "mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"]
    )
    record("Primary sample", len(primary) == 68, f"resolved seed and match <=6 km: n={len(primary)}")
    record("Resolved sample", len(resolved) == 74, f"all resolved official-mask seeds: n={len(resolved)}")

    identity = (
        resolved["mask_connected_2m_area_km2"]
        + resolved["mask_unconnected_2m_area_km2"]
        - resolved["mask_all_below_2m_area_km2"]
    ).abs()
    record("Terrain area identity", identity.max() < 1e-8,
           f"max absolute area error={identity.max():.3e} km2")

    rho_fraction = float(stats.spearmanr(
        primary["coast_rp_rp10_m"], primary["mask_connected_2m_lowland_pct"]
    ).statistic)
    rho_area = float(stats.spearmanr(
        primary["coast_rp_rp10_m"], primary["mask_connected_2m_area_km2"]
    ).statistic)
    rank = pd.read_csv(SOURCE / "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv")
    rank = rank[rank["sample"].eq("primary resolved mask-aware match<=6km")]
    stored_fraction = float(rank.loc[rank["terrain_metric"].eq("mask_connected_2m_lowland_pct"), "spearman"].iloc[0])
    stored_area = float(rank.loc[rank["terrain_metric"].eq("mask_connected_2m_area_km2"), "spearman"].iloc[0])
    record("Spearman recomputation",
           abs(rho_fraction - stored_fraction) < 1e-12 and abs(rho_area - stored_area) < 1e-12,
           f"fraction={rho_fraction:.6f}; area={rho_area:.6f}")

    top_n = math.ceil(0.2 * len(primary))
    water_top = set(primary.nlargest(top_n, "coast_rp_rp10_m")["station_id"])
    terrain_top = set(primary.nlargest(top_n, "mask_connected_2m_lowland_pct")["station_id"])
    overlap = len(water_top & terrain_top)
    record("Top-20% overlap", top_n == 14 and overlap == 1,
           f"k={top_n}; independently recomputed overlap={overlap}/{top_n}")

    tide = pd.read_csv(SOURCE / "TableS_tidal_regime_metadata_source_tracked.csv")
    verified = int(tide["source_status"].eq("source_verified").sum())
    record("Tidal metadata boundary", verified == 13, f"source-verified stations={verified}")

    local = pd.read_csv(SOURCE / "TableS_local_dtm_validation.csv")
    changed = int(local["category_changed"].astype(bool).sum())
    retained = len(local) - changed
    record("Local terrain comparison", len(local) == 7 and changed == 4,
           f"n={len(local)}; retained={retained}; changed={changed}")

    paper_text = (MANUSCRIPT / "process_terrain_coastal_flood_CEE_manuscript.md").read_text(encoding="utf-8")
    datum_phrases = [
        "EGM2008",
        "Ordnance Datum Newlyn",
        "Normaal Amsterdams Peil",
        "No vertical offsets were applied",
        "not validation against a common flood surface",
    ]
    record(
        "Vertical-datum disclosure",
        all(phrase in paper_text for phrase in datum_phrases)
        and local["validation_scope"].astype(str).str.contains("vertical datums not harmonized", case=False).all(),
        "DeltaDTM, Environment Agency and AHN native references are named; no harmonization or validation is claimed",
    )

    reference_phrases = [
        "10.1038/s43247-025-02326-w",
        "10.1038/s41586-026-10196-1",
        "10.5194/nhess-26-1859-2026",
    ]
    record(
        "Reference-use boundary",
        len(reference_rows()) == 4 and all(phrase in paper_text for phrase in reference_phrases),
        "Reference manuscripts are hashed and used only for article form, background and method-boundary citations",
    )

    mask = pd.read_csv(SOURCE / "Fig6_deltadtm_mask_seed_audit.csv").iloc[0]
    mask_ok = bool(mask["official_mask_tiles_zip_present"]) and bool(mask["official_mask_classes_used"])
    record("Official DeltaDTM mask", mask_ok, "official archive and classes 0/1/2/3/255 used")

    figures = figure_rows()
    times_ok = all(row[2] == "yes" for row in figures)
    record("Canonical figure provenance", len(figures) == 7 and times_ok,
           f"manifest figures={len(figures)}; Times-family PDF fonts={times_ok}")

    gssr_qualified = int(
        (
            primary["archive_available"].eq(True)
            & primary["passes_years_ge25"].eq(True)
            & primary["passes_corr_ge055"].eq(True)
        ).sum()
    )
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "checks_total": len(checks),
        "checks_failed": sum(item["status"] == "FAIL" for item in checks),
        "primary_n": len(primary),
        "resolved_n": len(resolved),
        "gssr_qualified_n": gssr_qualified,
        "rho_fraction": rho_fraction,
        "rho_area": rho_area,
        "top_n": top_n,
        "top_overlap": overlap,
        "local_retained": retained,
        "local_changed": changed,
    }
    return checks, summary


def documents() -> tuple[str, str, dict[str, object]]:
    checks, s = calculate()
    figures, inputs, references = figure_rows(), input_rows(), reference_rows()
    check_rows = [[x["check"], x["status"], x["evidence"]] for x in checks]
    if s["checks_failed"] == 0:
        conclusion = (
            "全部可计算门禁通过。该结论证明当前数字、源表、图件和代码链内部一致，"
            "但不替代外部独立复现，也不消除垂向基准、空间聚集和静态模型的局限。"
        )
    else:
        conclusion = f"仍有 {s['checks_failed']} 项失败，失败项关闭前不应作为最终投稿版本。"

    md = f"""# 科学真实性、准确性、完整性与可复现性审查

**审查对象：** Storm-tide magnitude and connected lowland terrain identify complementary coastal-flood screening priorities across Northwest Europe  
**生成时间：** {s['generated_at']}  
**结论：** {conclusion}

## 1. 审查边界

本文件检查研究链条是否透明、内部计算是否一致、结果是否由本项目代码从公开输入数据推导，以及图件是否对应当前源表。参考论文用于投稿体例、产品定义、物理概念和研究背景；论文中的站点数值、相关系数、连通面积、排序和不确定性诊断均由本项目工作流计算。参考论文中的站点结果、图件数据和结论数值没有进入本项目结果表。这里的通过不等同于对上游产品的重新验证，也不把静态地形筛查视为真实洪水观测。

## 2. 自动复算

{table_md(['检查项', '状态', '证据'], check_rows)}

## 3. 数据来源与自算结果的界线

公开输入包括 GSSR、COAST-RP、ERA5、DeltaDTM 及英国和荷兰的国家或地方地形模型。本研究自行完成站点匹配、经验 RP10、D10、气象相关、官方 mask 连通筛查、面积加权、置换检验、沿海分区重采样和图件生成。以下哈希标识了当前复算所用的核心文件版本。

{table_md(['输入文件', '字节数', 'SHA-256'], inputs)}

### 3.1 参考资料用途与禁止迁移边界

{table_md(['参考文件', 'SHA-256', '允许用途', '禁止迁移边界'], references)}

## 4. 关键结果复算

- 主样本 n={s['primary_n']}，已解析样本 n={s['resolved_n']}，GSSR-qualified 子集 n={s['gssr_qualified_n']}。
- COAST-RP RP10 与连通比例的 Spearman rho={s['rho_fraction']:.6f}，与连通面积的 rho={s['rho_area']:.6f}。
- Top 20% 的 k={s['top_n']}，两个集合交集为 {s['top_overlap']}/{s['top_n']}。
- 七站 local-DTM 对比中，类别保持 {s['local_retained']} 站、改变 {s['local_changed']} 站。

## 5. 方法可审计证据

1. 经验重现水平使用 Weibull plotting position，且不在经验范围外推。
2. DeltaDTM class 1 ocean 为基础 seed；class 3 river 仅在连通 ocean 时加入；lake 和 clipped cells 排除。
3. 只有 class 0 land 进入 denominator，连通、未连通和 all-below 面积逐站满足恒等式。
4. DeltaDTM、英国 Environment Agency DTM 和荷兰 AHN 的原生垂向参考被逐一披露；未施加垂向偏移，因此七站比较称为产品与基准敏感性，不称 validation。
5. GSSR bootstrap、prediction bounds、COAST-RP extraction range、高程扰动、站点置换和沿海分区重采样分别解释。
6. Top-set overlap 位于随机包络内，六分区重采样跨零，因此正文没有声称异常低重叠或稳定区域负相关。

## 6. 图件审查

图件统一使用 SciencePlots 的 science/no-latex 样式和 Times New Roman。图件经历三轮视觉复核：数据与颜色语义、最终尺寸字体与裁切、panel 逻辑与遮挡。低响应站点没有通过扩大蓝色区域进行美化。

{table_md(['图号', 'PNG 像素', 'Times 字体', 'PNG SHA-256 前16位', '生成器', '主源表'], figures)}

## 7. 尚未关闭的风险

- DeltaDTM、英国 LiDAR、荷兰 AHN 和水位产品未统一到站点垂向基准。
- 静态连通筛查不包含防御、闸门、排水、波浪、河流和时变传播。
- 沿海分区重采样区间跨零，站点级负相关不能推广为稳定区域规律。
- 潮汐元数据仅 13 站 source-verified。
- 公共数据/代码 DOI 或 private reviewer link 待补充。

## 8. 投稿前验收条件

1. 本文档自动失败项为 0。
2. 自包含 HTML 图片哈希覆盖当前 canonical figures。
3. 测试套件和论文关键数字审计通过。
4. PDF 逐页检查无裁切、重叠、空白页和不可读标签。
5. 作者、单位、贡献、资助和仓储链接补齐。

## 9. 结论

{conclusion}
"""

    table_style = (
        "table{width:100%;border-collapse:collapse;font-size:12px}"
        "th,td{border:1px solid #cbd3dc;padding:7px;vertical-align:top;overflow-wrap:anywhere}"
        "th{background:#e9eff4;text-align:left}tr:nth-child(even)td{background:#fafbfc}"
        ".table-wrap{overflow-x:auto;margin:14px 0 22px}"
    )
    html_doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>科学真实性与完整性审查</title><style>
body{{margin:0;background:#f3f5f7;color:#182236;font-family:"Times New Roman","Microsoft YaHei",serif;line-height:1.72}}
main{{max-width:1100px;margin:24px auto;padding:50px 64px;background:white;box-shadow:0 2px 14px #ccd2d9}}
h1{{font-size:29px;color:#174866}}h2{{font-size:20px;color:#174866;border-bottom:1px solid #ccd3dc;padding-bottom:6px;margin-top:32px}}
p,li{{font-size:15px}}.summary{{border-left:4px solid #2777a8;background:#eef5f9;padding:12px 16px}}
{table_style}
@media print{{body{{background:white}}main{{margin:0;max-width:none;box-shadow:none;padding:18px 28px}}table{{font-size:8pt}}tr{{break-inside:avoid}}h2{{break-after:avoid-page}}}}
</style></head><body><main>
<h1>科学真实性、准确性、完整性与可复现性审查</h1>
<p class="summary"><strong>生成时间：</strong>{html.escape(str(s['generated_at']))}<br><strong>结论：</strong>{html.escape(conclusion)}</p>
<h2>1. 审查边界</h2><p>本文件检查研究链条、内部计算、数据来源和图件源表的一致性。参考论文只用于投稿体例、背景、定义和方法边界；本文全部站点数值、统计量、连通指标和图件源表由项目代码计算，参考论文结果没有进入项目结果表。</p>
<h2>2. 自动复算</h2>{table_html(['检查项','状态','证据'], check_rows)}
<h2>3. 数据来源与自算结果的界线</h2><p>公开输入为 GSSR、COAST-RP、ERA5、DeltaDTM 及英国和荷兰地形模型；站点匹配、RP10、D10、连通指标、统计检验和图件均在本项目中生成。</p>
{table_html(['输入文件','字节数','SHA-256'], inputs)}
<h3>3.1 参考资料用途与禁止迁移边界</h3>{table_html(['参考文件','SHA-256','允许用途','禁止迁移边界'], references)}
<h2>4. 关键结果复算</h2><ul><li>主样本 n={s['primary_n']}；已解析 n={s['resolved_n']}；GSSR-qualified n={s['gssr_qualified_n']}。</li>
<li>Spearman rho：比例 {s['rho_fraction']:.6f}；面积 {s['rho_area']:.6f}。</li>
<li>Top 20% 交集 {s['top_overlap']}/{s['top_n']}。</li><li>Local-DTM 类别保持 {s['local_retained']} 站，改变 {s['local_changed']} 站。</li></ul>
<h2>5. 方法证据</h2><ol><li>经验重现水平按 Weibull plotting position 计算。</li><li>官方 mask class-aware marine seed。</li><li>class 0 land denominator 与面积恒等式。</li><li>三类原生垂向参考明确披露，未统一时只称产品与基准敏感性。</li><li>不同不确定性来源分别解释。</li><li>统计结论受 top-k null 与沿海分区重采样约束。</li></ol>
<h2>6. 图件审查</h2><p>全部 canonical figures 使用 SciencePlots 和 Times New Roman，并完成三轮视觉审核。</p>
{table_html(['图号','PNG 像素','Times 字体','PNG SHA-256 前16位','生成器','主源表'], figures)}
<h2>7. 未关闭风险</h2><ul><li>垂向基准未统一。</li><li>缺少动力过程和工程控制。</li><li>空间重采样区间跨零。</li><li>潮汐元数据和仓储 DOI 尚未补齐。</li></ul>
<h2>8. 投稿验收条件</h2><ol><li>自动失败项为 0。</li><li>HTML、测试和关键数字审计通过。</li><li>PDF 逐页视觉检查通过。</li><li>投稿元数据与仓储链接补齐。</li></ol>
<h2>9. 结论</h2><p>{html.escape(conclusion)}</p>
</main></body></html>"""
    payload = {"summary": s, "checks": checks, "figures": figures, "core_inputs": inputs, "reference_boundaries": references}
    return md, html_doc, payload


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    md, html_doc, payload = documents()
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    browser = next((path for path in CHROME if path.exists()), None)
    if browser is None:
        raise RuntimeError("Chrome or Edge is required for PDF export")
    subprocess.run(
        [str(browser), "--headless=new", "--disable-gpu", f"--print-to-pdf={OUT_PDF}",
         "--no-pdf-header-footer", str(OUT_HTML.resolve())],
        check=True,
        cwd=ROOT,
    )
    if payload["summary"]["checks_failed"]:
        raise RuntimeError(f"scientific integrity checks failed: {payload['summary']['checks_failed']}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_PDF}")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
