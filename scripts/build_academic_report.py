#!/usr/bin/env python3
"""Build portable single-file academic HTML report (report.html) at repo root."""

from __future__ import annotations

import base64
import io
import json
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "report.html"
SUMMARY_PATH = ROOT / "data" / "processed" / "combo1_summary.json"
RP_PARQUET = ROOT / "data" / "processed" / "rp_comparison.parquet"
INUNDATION_JSON = ROOT / "data" / "processed" / "inundation_sensitivity.json"
INUNDATION_ALL_JSON = ROOT / "data" / "processed" / "inundation_sensitivity_all.json"
FIGURES_DIR = ROOT / "figures"

FIGURE_SPECS = [
    ("combo1_rp10_dual_region.png", "欧洲与美国验潮站 GSSR RP10 与 COAST-RP RP10 分组对比"),
    ("combo1_rp10_comparison.png", "八站 GSSR 与 COAST-RP 十年一遇水位对比"),
    ("combo1_rp_multi_station.png", "多站多重现期（RP10/50/100）对比"),
    ("combo1_gssr_coastrp_validation.png", "年均最大偏斜潮与 RP10 散点（跨产品不可比性示意）"),
    ("combo1_hydrograph_sheerness.png", "Sheerness 站 GSSR 日最大偏斜潮时间序列"),
    ("combo1_driver_correlation_heatmap.png", "八站 Open-Meteo 驱动因子与偏斜潮 Spearman 相关热力图"),
    ("inundation_sensitivity_sheerness-p015-uk.png", "Sheerness 邻域 DeltaDTM 静态 SLR 淹没敏感性"),
    ("inundation_sensitivity_newlyn-p001-uk.png", "Newlyn 邻域 DeltaDTM 静态 SLR 淹没敏感性"),
    ("inundation_sensitivity_aberdeen-p038-uk.png", "Aberdeen 邻域 DeltaDTM 静态 SLR 淹没敏感性"),
    ("inundation_sensitivity_hoekvanholla-hvh-nl.png", "Hoek van Holland 邻域 DeltaDTM 静态 SLR 淹没敏感性"),
    ("inundation_sensitivity_brest-france.png", "Brest 邻域 DeltaDTM 静态 SLR 淹没敏感性"),
]

ALLOWED_PREFIXES = ("data:", "#", "mailto:", "javascript:")
ATTR_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
FORBIDDEN_EXT = re.compile(
    r"\.(?:css|png|jpe?g|gif|svg|webp|js|json|parquet|html|ico|woff2?|ttf)(?:\?|#|$)",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def png_to_data_uri(path: Path, max_kb: int = 500) -> str:
    raw = path.read_bytes()
    if len(raw) > max_kb * 1024:
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(raw))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"
        except ImportError:
            pass
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def fmt_num(x: float | None, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "待补充"
    return f"{float(x):.{digits}f}"


def df_to_html_table(df: pd.DataFrame, float_fmt: str = ".3f") -> str:
    rows = []
    rows.append("<thead><tr>" + "".join(f"<th>{escape(str(c))}</th>" for c in df.columns) + "</tr></thead>")
    body = []
    for _, row in df.iterrows():
        cells = []
        for c, v in row.items():
            if isinstance(v, float):
                cells.append(f"<td>{escape(format(v, float_fmt))}</td>")
            else:
                cells.append(f"<td>{escape(str(v))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    rows.append("<tbody>" + "".join(body) + "</tbody>")
    return "<table class=\"data-table\">" + "".join(rows) + "</table>"


def build_driver_svg(correlations: list[dict]) -> str:
    """Inline SVG: mean |Spearman| by variable across stations."""
    if not correlations:
        return "<p>待补充</p>"
    vars_ = [
        ("气压", "spearman_surge_vs_pressure"),
        ("风速", "spearman_surge_vs_wind"),
        ("降水", "spearman_surge_vs_precip"),
    ]
    means = []
    for label, key in vars_:
        vals = [abs(r[key]) for r in correlations if key in r]
        means.append((label, sum(vals) / len(vals) if vals else 0.0))
    w, h, pad = 420, 160, 36
    max_v = max(m[1] for m in means) or 1.0
    bar_w = 70
    bars = []
    for i, (label, val) in enumerate(means):
        x = pad + i * (bar_w + 40)
        bh = int((val / max_v) * (h - 2 * pad - 24))
        y = h - pad - bh
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="#2c5282" opacity="0.85"/>'
            f'<text x="{x + bar_w/2}" y="{h - 8}" text-anchor="middle" font-size="11">{escape(label)}</text>'
            f'<text x="{x + bar_w/2}" y="{y - 4}" text-anchor="middle" font-size="10">{val:.2f}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'class="inline-chart" role="img" aria-label="驱动因子平均绝对Spearman相关">'
        f'<text x="{pad}" y="18" font-size="12" fill="#333">八站平均 |Spearman|（示意）</text>'
        + "".join(bars)
        + "</svg>"
    )


def validate_html(text: str) -> list[str]:
    issues: list[str] = []
    if '<link rel="stylesheet"' in text.lower() or '<link href=' in text.lower():
        issues.append("contains <link> stylesheet reference")
    if re.search(r'<script[^>]+src\s*=', text, re.I):
        issues.append("contains external <script src>")
    for m in ATTR_RE.finditer(text):
        url = m.group(1).strip()
        if not url or url.startswith(ALLOWED_PREFIXES):
            continue
        if url.startswith(("http://", "https://", "//")):
            issues.append(f"external URL: {url[:80]}")
        elif FORBIDDEN_EXT.search(url):
            issues.append(f"relative asset: {url[:80]}")
        elif url.startswith(("assets/", "figures/", "../", "./")):
            issues.append(f"relative path: {url[:80]}")
    return issues


def build_report() -> tuple[Path, int, int, int, list[str]]:
    """Clean build without template hack for section 2."""
    summary = load_json(SUMMARY_PATH)
    inundation = load_json(INUNDATION_JSON) if INUNDATION_JSON.exists() else {}
    inundation_all: list[dict] = []
    if INUNDATION_ALL_JSON.exists():
        inundation_all = json.loads(INUNDATION_ALL_JSON.read_text(encoding="utf-8"))
    elif inundation:
        inundation_all = [inundation]
    rp_df = pd.read_parquet(RP_PARQUET)

    rp_display = rp_df.copy()
    rp_display.columns = [
        "站点ID",
        "GSSR RP10 (m)",
        "GSSR RP50 (m)",
        "GSSR RP100 (m)",
        "COAST-RP RP10 (m)",
        "COAST-RP RP50 (m)",
        "COAST-RP RP100 (m)",
        "匹配距离 (km)",
        "匹配标记",
        "GSSR 序列最大 (m)",
        "GSSR p99 (m)",
        "RP10 偏差 (m)",
        "RP100 偏差 (m)",
    ]

    met_rows = [
        {
            "站点ID": r["station_id"],
            "重叠日数": r["n_days"],
            "潮位–气压 Spearman": r["spearman_surge_vs_pressure"],
            "潮位–风速 Spearman": r["spearman_surge_vs_wind"],
            "潮位–降水 Spearman": r["spearman_surge_vs_precip"],
        }
        for r in summary.get("met_driver_correlations", [])
    ]
    met_df = pd.DataFrame(met_rows)
    out_table = pd.DataFrame([{"产出文件": k, "记录数/行数": v} for k, v in sorted(summary.get("outputs", {}).items())])

    slr_rows = []
    for inv in inundation_all:
        for slr in inv.get("slr_levels_m", [0.5, 1.0, 2.0]):
            sk = float(slr)
            slr_rows.append(
                {
                    "站点": inv.get("station_name", inv.get("station_id", "待补充")),
                    "SLR 偏移 (m)": sk,
                    "全有效像元淹没比例": inv.get("flooded_fraction_all_valid", {}).get(str(slr)),
                    "低地(≤15 m)淹没比例": inv.get("flooded_fraction_coastal_lowland", {}).get(str(slr)),
                    "DEM 来源": inv.get("dem_source", "待补充"),
                }
            )
    inund_df = pd.DataFrame(slr_rows)

    rp_meta = summary.get("rp_comparison", {})
    gen_at = summary.get("generated_at", "待补充")
    dem_src = summary.get("inundation_dem_source", "待补充")
    dem_stats = inundation.get("dem_stats") or {}

    tables_parts: list[str] = []
    table_count = 0

    def add_table(caption: str, table_html: str, prose: str) -> None:
        nonlocal table_count
        table_count += 1
        tables_parts.append(
            f'<div class="table-block" id="tab{table_count}">'
            f'<p class="table-caption"><strong>表{table_count}</strong> {escape(caption)}</p>'
            f"{table_html}<p class=\"table-note\">{prose}</p></div>"
        )

    add_table(
        "Combo 1 流水线主要中间产出规模",
        df_to_html_table(out_table, ".0f"),
        "表列出行级规模，用于说明四类数据源均已进入融合流水线；完整校验见质量审计文档。",
    )
    add_table(
        "八验潮站 GSSR 与 COAST-RP 重现期水位对比",
        df_to_html_table(rp_display),
        "偏差列为 GSSR 减 COAST-RP（m）。欧洲站负偏差约 −1.9～−3.9 m，与美国站（纽约、查尔斯顿 &lt;0.5 m）形成对照，"
        "反映偏斜潮与风暴潮位（含潮）产品定义差异，而非单位换算错误。",
    )
    add_table(
        "Open-Meteo ERA5 日尺度驱动因子与 GSSR 偏斜潮 Spearman 相关",
        df_to_html_table(met_df),
        "Open-Meteo 不提供潮位；相关分析仅作复合洪水统计关联。英国—西北欧站气压相关可达 −0.5～−0.8，"
        "Charleston 接近 0，可能与区域风暴机制有关。",
    )
    if not inund_df.empty:
        n_st = inundation_df["站点"].nunique() if (inundation_df := inund_df).shape[0] else 0
        add_table(
            f"DeltaDTM 静态 bathtub 淹没敏感性（{n_st} 个验潮站邻域）",
            df_to_html_table(inund_df),
            f"共 {len(inundation_all)} 站使用真实 DeltaDTM 瓦片（无瓦片则跳过）。"
            "SLR 为相对 DEM 偏移；属静态筛查，非动力预报。",
        )

    table1_html = tables_parts[0] if tables_parts else ""
    tables_rest = "".join(tables_parts[1:])

    figure_specs = list(FIGURE_SPECS)
    known = {f for f, _ in figure_specs}
    for p in sorted(FIGURES_DIR.glob("inundation_sensitivity_*.png")):
        if p.name not in known:
            sid = p.stem.replace("inundation_sensitivity_", "")
            figure_specs.append((p.name, f"{sid} 邻域 DeltaDTM 静态 SLR 淹没敏感性"))

    figures_html = []
    figure_count = 0
    for fname, caption in figure_specs:
        fpath = FIGURES_DIR / fname
        if not fpath.exists():
            continue
        figure_count += 1
        data_uri = png_to_data_uri(fpath)
        figures_html.append(
            f'<figure id="fig{figure_count}" class="figure-block">'
            f'<figcaption><strong>图{figure_count}</strong> {escape(caption)}</figcaption>'
            f'<img src="{data_uri}" alt="{escape(caption)}"/>'
            f"</figure>"
        )
    fig_body = "\n".join(figures_html)
    driver_svg = build_driver_svg(summary.get("met_driver_correlations", []))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>海岸洪水多源开放数据融合研究报告（Combo 1）</title>
<style>
:root {{ --text:#1a202c; --muted:#4a5568; --accent:#2b6cb0; --border:#e2e8f0; --bg:#f7fafc; --paper:#fff; }}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; font-family:"Source Han Serif SC","Noto Serif SC","SimSun",Georgia,serif; font-size:11.5pt; line-height:1.75; color:var(--text); background:var(--bg); }}
.wrap {{ max-width:920px; margin:0 auto; padding:2.5rem 2rem 4rem; background:var(--paper); box-shadow:0 0 24px rgba(0,0,0,.06); }}
.cover {{ text-align:center; padding:3rem 1rem 2.5rem; border-bottom:2px solid var(--accent); margin-bottom:2rem; }}
.cover h1 {{ font-size:1.65rem; font-weight:700; margin:0 0 .75rem; line-height:1.4; }}
.cover .subtitle {{ font-size:1.05rem; color:var(--muted); margin-bottom:1.5rem; }}
.cover .meta {{ font-size:.95rem; color:var(--muted); }}
h2 {{ font-size:1.25rem; color:var(--accent); border-left:4px solid var(--accent); padding-left:.6rem; margin:2.2rem 0 1rem; }}
h3 {{ font-size:1.05rem; margin:1.4rem 0 .6rem; }}
p {{ margin:0 0 .85rem; text-align:justify; }}
.toc {{ background:#edf2f7; padding:1.2rem 1.5rem; border-radius:6px; margin-bottom:2rem; }}
.toc ul {{ margin:.5rem 0 0; padding-left:1.2rem; }}
.toc a {{ color:var(--accent); text-decoration:none; }}
.abstract {{ background:#f0fff4; border:1px solid #c6f6d5; padding:1rem 1.2rem; border-radius:6px; }}
.keywords {{ font-size:.95rem; color:var(--muted); margin-top:.5rem; }}
.figure-block,.table-block {{ margin:1.8rem 0; }}
.figure-block img {{ width:100%; height:auto; border:1px solid var(--border); border-radius:4px; }}
figcaption,.table-caption {{ font-size:.95rem; color:var(--muted); margin:.5rem 0 .75rem; text-align:center; }}
.table-note {{ font-size:.9rem; color:var(--muted); margin-top:.5rem; }}
.data-table {{ width:100%; border-collapse:collapse; font-size:.88rem; font-family:"Segoe UI","Microsoft YaHei",sans-serif; }}
.data-table th,.data-table td {{ border:1px solid var(--border); padding:.45rem .55rem; text-align:center; }}
.data-table th {{ background:#ebf8ff; font-weight:600; }}
.data-table tr:nth-child(even) {{ background:#f8fafc; }}
.inline-chart {{ width:100%; max-width:420px; display:block; margin:1rem auto; }}
.ref-list {{ font-size:.92rem; padding-left:1.4rem; }}
.ref-list li {{ margin-bottom:.45rem; }}
@media print {{ body {{ background:white; }} .wrap {{ box-shadow:none; max-width:100%; }} }}
</style>
</head>
<body>
<div class="wrap">
<section class="cover" id="cover">
  <h1>面向海岸洪水危害的可复现多源融合框架</h1>
  <p class="subtitle">Combo 1：GSSR · COAST-RP · Open-Meteo ERA5 · DeltaDTM<br/>交叉敏感性、驱动相关与静态淹没筛查</p>
  <p class="meta">项目：coastal-flood-scientific-data<br/>流水线生成时间：{escape(str(gen_at))}<br/>报告日期：2026-05-22</p>
</section>
<nav class="toc" id="toc"><strong>目录</strong><ul>
<li><a href="#abstract">摘要</a></li>
<li><a href="#sec1">1 研究背景与目的</a></li>
<li><a href="#sec2">2 数据与方法</a></li>
<li><a href="#sec3">3 研究过程</a></li>
<li><a href="#sec4">4 结果展示</a></li>
<li><a href="#sec5">5 分析与讨论</a></li>
<li><a href="#sec6">6 主要结论</a></li>
<li><a href="#sec7">7 不足与展望</a></li>
<li><a href="#refs">参考文献</a></li>
</ul></nav>
<section id="abstract" class="abstract">
<h2>摘要</h2>
<p>本研究构建 Combo 1 可复现流水线，联结 GSSR（ERA5）日最大偏斜潮、COAST-RP 风暴潮位重现期、Open-Meteo ERA5 驱动与 DeltaDTM 海岸地形，在 <strong>8</strong> 个验潮站开展 RP 敏感性对比与驱动相关分析，并以 Sheerness 真实 COG 瓦片开展静态 SLR 淹没筛查。</p>
<p>八站 RP10 平均偏差（GSSR−COAST-RP）为 <strong>{fmt_num(rp_meta.get('mean_rp10_bias_m'))} m</strong>；RP100 平均偏差 <strong>{fmt_num(rp_meta.get('mean_rp100_bias_m'))} m</strong>；
Pearson（RP10）<strong>{fmt_num(rp_meta.get('pearson_rp10'))}</strong>。美国站偏差 &lt;0.5 m，欧洲站约 −2～−4 m。Sheerness 在 +2 m SLR 下有效像元淹没比例约 <strong>{fmt_num((inundation.get('flooded_fraction_all_valid') or {{}}).get(2.0, 0) * 100, 1)}%</strong>（低地掩膜约 {fmt_num((inundation.get('flooded_fraction_coastal_lowland') or {{}}).get(2.0, 0) * 100, 1)}%）。</p>
<p class="keywords"><strong>关键词</strong>：海岸洪水；多源融合；风暴潮；重现期；Open-Meteo；DeltaDTM</p>
</section>
<section id="sec1"><h2>1 研究背景与目的</h2>
<p>现有 Scientific Data 数据集分别提供水位重建、地形与事件档案，但缺少在统一开源框架下对「重建潮—极值重现期—30 m DTM—再分析风压」的交叉验证。本仓库优先实施<strong>组合 1</strong>（GSSR + COAST-RP + Open-Meteo + DeltaDTM），目标为建立可审计流水线、量化跨产品偏差分异、开展静态淹没敏感性并披露方法局限，<strong>不</strong>将结果表述为业务预报或互验绝对潮位。</p>
</section>
<section id="sec2"><h2>2 数据与方法</h2>
<h3>2.1 数据源</h3>
<p><strong>GSSR</strong>：验潮站日最大偏斜潮（ERA5 分支，约 1979–2019）；RP 由年最大 + Weibull 绘图位置估计。<strong>COAST-RP</strong>：海岸点 <code>storm_tide_rp_*</code>（含潮风暴潮位极值），最近邻匹配（Haversine km）。<strong>Open-Meteo</strong>：ERA5 日最小气压、日最大风速、日降水（1980–2010），不提供潮位。<strong>DeltaDTM</strong>：EGM2008，Sheerness 瓦片 {escape(dem_src)}。</p>
<h3>2.2 方法要点</h3>
<p>UTC 日对齐；Spearman 驱动相关；bathtub <code>max(0, SLR−DEM)</code>。垂直基准联合改正：<strong>待补充</strong>。</p>
{table1_html}
</section>
<section id="sec3"><h2>3 研究过程</h2>
<p>经四轮质量迭代：（1）真实性审计确认四源落盘；（2）Haversine 匹配与 nodata 掩膜修复；（3）双区域 RP 图、水文叠加与淹没 extent；（4）HTML 离线验证。主脚本：<code>run_combo1_pipeline.py</code>、<code>combo1_quality_audit.py</code>。</p>
</section>
<section id="sec4"><h2>4 结果展示</h2>
<p>图 1 以欧洲/美国分组展示 RP10 产品差异；图 2–3 给出八站 RP 对比；图 4 示意跨产品散点不宜作验证；图 5 为 Sheerness 偏斜潮序列（典型 −0.2～1.6 m，RP10≈1.33 m）；图 6 为驱动相关；图 7 为 DeltaDTM 淹没敏感性（真实 COG，非合成坡面）。</p>
{fig_body}
<h3>4.2 表格</h3>
{tables_rest}
<h3>4.3 驱动相关汇总（内嵌 SVG）</h3>
{driver_svg}
</section>
<section id="sec5"><h2>5 分析与讨论</h2>
<h3>5.1 产品错配</h3>
<p>偏斜潮分量 vs 含潮风暴潮位解释欧洲站 −2～−4 m 偏差（表 2）；Pearson≈{fmt_num(rp_meta.get('pearson_rp10'))} 仅说明不可直接比（图 4）。</p>
<h3>5.2 美国 vs 欧洲</h3>
<p>纽约、查尔斯顿接近 0 偏差，支持无单位错误；河口站与海岸格点空间错位放大欧陆差异（图 1）。</p>
<h3>5.3 Bathtub 局限</h3>
<p>图 7：median elev≈{fmt_num(dem_stats.get('elev_median_m'))} m，+2 m 约淹 {fmt_num((inundation.get('flooded_fraction_all_valid') or {{}}).get(2.0, 0) * 100, 1)}% 有效像元；无动力、无岸线矢量。</p>
<h3>5.4 气象驱动</h3>
<p>西北欧气压负相关 −0.5～−0.8（表 3、图 6）；Charleston 近 0，机制解释<strong>待补充</strong>。</p>
</section>
<section id="sec6"><h2>6 主要结论</h2>
<ol>
<li>四源真实对齐的可复现 Combo 1 MVP 已建立（表 1）。</li>
<li>RP 对比应定位为敏感性检查：平均 RP10 偏差 {fmt_num(rp_meta.get('mean_rp10_bias_m'))} m。</li>
<li>真实 DeltaDTM 支持河口 SLR 静态筛查，须标注 bathtub 与基准局限。</li>
<li>Open-Meteo 可作驱动统计关联，不能替代潮位模拟。</li>
</ol>
</section>
<section id="sec7"><h2>7 不足与展望</h2>
<ul>
<li>组合 2/3（US-CoastEX、WNP、SurgeWatch、PCCFR）：<strong>待补充</strong></li>
<li>GESLA3 观测验证、CoDEC 第三产品、垂直基准统一：<strong>待补充</strong></li>
<li>多瓦片 DEM、海岸线、动力淹没与投稿归档：<strong>待补充</strong></li>
</ul>
</section>
<section id="refs"><h2>参考文献</h2>
<ol class="ref-list">
<li>Tadesse &amp; Wahl (2021). <em>Scientific Data</em> <strong>8</strong>, 125. DOI: 10.1038/s41597-021-00906-x</li>
<li>Dullaart et al. (2021). <em>Communications Earth &amp; Environment</em> <strong>2</strong>, 221. DOI: 10.1038/s43247-021-00204-9</li>
<li>Pronk et al. (2024). <em>Scientific Data</em> <strong>11</strong>, 273. DOI: 10.1038/s41597-024-03091-9</li>
<li>Dang et al. (2024). <em>Scientific Data</em> <strong>11</strong>, 405. DOI: 10.1038/s41597-024-03249-5</li>
<li>Morim et al. (2025). <em>Scientific Data</em> <strong>12</strong>, 1395. DOI: 10.1038/s41597-025-05730-1</li>
<li>Haigh et al. (2015, 2017). DOI: 10.1038/sdata201521; 10.1038/sdata2017100</li>
<li>Muis et al. (2016). <em>Nature Communications</em> <strong>7</strong>, 11969. DOI: 10.1038/ncomms11969</li>
<li>Dullaart et al. (2023). <em>NHESS</em> <strong>23</strong>, 1847–1862. DOI: 10.5194/nhess-23-1847-2023</li>
<li>Open-Meteo ERA5 API 文档。版本锁定记录：<strong>待补充</strong>。</li>
</ol>
</section>
</div>
</body>
</html>"""

    issues = validate_html(html)
    REPORT_PATH.write_text(html, encoding="utf-8")
    return REPORT_PATH, figure_count, table_count, len(html), issues


def main() -> int:
    path, n_fig, n_tab, nbytes, issues = build_report()
    size_mb = nbytes / (1024 * 1024)

    round_num = 1
    while issues and round_num < 3:
        print(f"Validation round {round_num} FAILED:", file=sys.stderr)
        for i in issues:
            print(f"  - {i}", file=sys.stderr)
        round_num += 1
        path, n_fig, n_tab, nbytes, issues = build_report()

    status = "PASS" if not issues else "FAIL"
    print(f"Report: {path}")
    print(f"Size: {size_mb:.2f} MB ({nbytes} bytes)")
    print(f"Figures embedded: {n_fig}")
    print(f"Tables embedded: {n_tab}")
    print(f"Validation: {status}")
    if issues:
        for i in issues:
            print(f"  - {i}")

    # Also run standalone validator
    import subprocess

    val_script = ROOT / "scripts" / "validate_standalone_html.py"
    if val_script.exists():
        r = subprocess.run(
            [sys.executable, str(val_script), str(path)],
            capture_output=True,
            text=True,
        )
        print(r.stdout.strip())
        if r.returncode != 0:
            print(r.stderr.strip(), file=sys.stderr)
            return 1

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
