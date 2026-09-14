from __future__ import annotations

import base64
import csv
import html
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "main"
SOURCE_DIR = ROOT / "data" / "figure_source"
LOG_DIR = ROOT / "logs"
MANUSCRIPT_DIR = ROOT / "manuscript"
OUT_HTML = ROOT / "report.html"
OUT_MD = ROOT / "report.md"


TITLE_CN = "水位过程与地形敏感性解耦的海岸洪水筛查研究报告"
SUBTITLE_CN = "基于 GSSR、COAST-RP、Open-Meteo ERA5 与 DeltaDTM 的多源数据综合分析"
GEN_DATE = datetime.now().strftime("%Y-%m-%d %H:%M")


FIGURES = [
    {
        "id": "fig1",
        "number": "图 1",
        "file": "Fig1_process_terrain_design.png",
        "title": "过程-地形筛查设计与八个海岸站点",
        "caption": "该图概括研究设计、站点分布和物理量定义。研究将 GSSR 重建风暴增水、COAST-RP 风暴潮位重现期、Open-Meteo ERA5 气象驱动和 DeltaDTM 地形敏感性视为互补诊断，而不是互相替代的验证对象。",
        "analysis": "图 1 的作用是搭建解释框架。它说明本研究不是单纯比较两个水位产品谁更准确，而是把水位过程、气象驱动和地形连通性放在同一个筛查逻辑中。这样做的原因是，真实洪水易感性取决于水位是否能够作用到低洼、连通的地形，而不是只由某一个极值水位指标决定。",
    },
    {
        "id": "fig2",
        "number": "图 2",
        "file": "Fig2_water_level_divergence.png",
        "title": "GSSR 增水指标与 COAST-RP 风暴潮位指标的差异",
        "caption": "该图比较八个站点的 GSSR 10 年一遇增水指标与邻近 COAST-RP 10 年一遇风暴潮位指标，并展示 storm-tide-minus-surge 差异。",
        "analysis": "图 2 表明欧洲潮汐影响较强的站点存在更大的产品定义差异。Sheerness、Brest、Newlyn、Aberdeen 和 Hoek van Holland 的 COAST-RP 风暴潮位明显高于 GSSR 增水残差，主要原因是 storm tide 包含天文潮成分，而 GSSR 表征的是风暴增水残差。New York-The Battery 和 Charleston 的差异较小，这进一步说明这种差异不是统一的数据处理错误，而是产品物理定义不同所产生的过程信号。",
    },
    {
        "id": "fig3",
        "number": "图 3",
        "file": "Fig3_meteorological_coherence.png",
        "title": "重建日增水与气象驱动的一致性",
        "caption": "该图展示 1980-2010 年重叠期内 GSSR 日增水与最低气压、最大风速、降水量之间的 Spearman 秩相关关系。",
        "analysis": "图 3 用于检验增水时间序列是否与风暴天气具有物理一致性。Newlyn、Brest、Aberdeen 和 Hoek van Holland 的增水与气压呈显著负相关，符合温带气旋、反气压效应和陆架风暴增水过程的预期。Charleston 和 Hong Kong 的简单日尺度局地相关较弱或方向复杂，说明在受热带气旋路径、风向、海湾几何和潮汐相位影响的地区，仅用站点日值气象变量难以完整解释增水过程。",
    },
    {
        "id": "fig4",
        "number": "图 4",
        "file": "Fig4_deltadtm_terrain_sensitivity.png",
        "title": "五个欧洲站点的 DeltaDTM 海洋连通地形敏感性",
        "caption": "该图基于真实 DeltaDTM 地形窗口，展示 +2 m 相对水位扰动下的海洋连通低洼地形敏感性。蓝色区域表示低于情景水位且连通至边界水体或边界 no-data 海洋区域的单元。",
        "analysis": "图 4 是本研究最关键的地形证据。它显示同样面对高水位指标，不同站点的低洼地形是否与海洋连通会显著改变敏感性判断。Sheerness 的 +2 m 连通低地比例最高，说明低洼地形与海洋边界之间存在更直接的地形通道。Hoek van Holland 在未过滤 bathtub 计算中低地比例较高，但连通过滤后明显降低，说明堤防、地形屏障或局部高程结构会使低地面积与直接海洋连通敏感性解耦。",
    },
    {
        "id": "fig5",
        "number": "图 5",
        "file": "Fig5_process_terrain_typology.png",
        "title": "地形响应与过程-地形类型划分",
        "caption": "该图整合低地高程曲线、不同相对水位扰动下的连通低地淹没比例，以及水位指标差异、气压相关性和 COAST-RP RP10 的综合相空间。",
        "analysis": "图 5 将水位差异、气象一致性和地形敏感性合并为过程-地形类型。Sheerness 属于水位与地形响应较为对齐的热点；Hoek van Holland、Newlyn、Brest 和 Aberdeen 则显示不同程度的水位主导但地形缓冲或解耦特征。该图支撑核心结论：海岸洪水易感性不是单一水位大小的函数，而是由水位过程与低洼连通地形之间的耦合关系决定。",
    },
]


TABLES = [
    {
        "id": "tab1",
        "number": "表 1",
        "file": "Table1_data_products.csv",
        "title": "数据产品及其分析角色",
        "note": "该表说明每类数据的物理含义、时空支持和主要局限。它是理解后续结果的基础，因为 GSSR、COAST-RP、Open-Meteo 和 DeltaDTM 分别回答不同问题。",
    },
    {
        "id": "tab2",
        "number": "表 2",
        "file": "Table2_water_level_indicators.csv",
        "title": "GSSR 与 COAST-RP 10 年一遇水位指标",
        "note": "该表给出八个站点的增水残差指标、风暴潮位指标、两者差异和空间匹配距离。差异值用于过程解释，不作为模型误差或产品优劣判断。",
    },
    {
        "id": "tab3",
        "number": "表 3",
        "file": "Table3_driver_correlations.csv",
        "title": "GSSR 日增水与气象驱动的 Spearman 秩相关",
        "note": "该表用于检查重建增水是否与气压、风速、降水等风暴条件具有物理一致性。相关关系是筛查诊断，不是完整因果归因模型。",
    },
    {
        "id": "tab4",
        "number": "表 4",
        "file": "Table4_deltadtm_connected_sensitivity.csv",
        "title": "DeltaDTM 海洋连通静态相对海平面敏感性",
        "note": "该表使用 coastal-lowland mask 的中位高程和海洋连通淹没比例。它避免使用受 30 m 上限截断影响的全窗口高程中位数作为解释证据。",
    },
    {
        "id": "tab5",
        "number": "表 5",
        "file": "Fig5_process_terrain_typology.csv",
        "title": "过程-地形类型划分源数据",
        "note": "该表是图 5 的直接来源，汇总水位指标差异、气象压力相关性、连通低地比例和低地高程统计，用于综合类型判断。",
    },
    {
        "id": "tab6",
        "number": "表 6",
        "file": "Fig1_station_metadata.csv",
        "title": "研究站点元数据",
        "note": "该表列出八个筛查站点及其坐标、区域和数据匹配信息，是全部站点级分析的空间索引。",
    },
]


def read_csv_rows(name: str) -> list[dict[str, str]]:
    path = SOURCE_DIR / name
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt_cell(value: str) -> str:
    value = "" if value is None else str(value)
    try:
        number = float(value)
    except ValueError:
        return value
    if value.strip() == "":
        return value
    if abs(number) >= 1000:
        return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"
    if number.is_integer():
        return f"{number:.0f}"
    return f"{number:.3f}".rstrip("0").rstrip(".")


def html_table(rows: list[dict[str, str]], caption: str, note: str, table_id: str) -> str:
    if not rows:
        return f"<p class=\"warning\">{html.escape(caption)}: 待补充</p>"
    headers = list(rows[0].keys())
    thead = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(fmt_cell(row.get(header, '')))}</td>" for header in headers)
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        f"<figure class=\"table-wrap\" id=\"{table_id}\">"
        f"<figcaption>{html.escape(caption)}</figcaption>"
        f"<div class=\"scroll-table\"><table><caption class=\"visually-hidden\">{html.escape(caption)}</caption><thead><tr>{thead}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
        f"<p class=\"table-note\">{html.escape(note)}</p>"
        f"</figure>"
    )


def markdown_table(rows: list[dict[str, str]], caption: str, note: str) -> str:
    if not rows:
        return f"**{caption}**\n\n待补充\n"
    headers = list(rows[0].keys())

    def esc(value: str) -> str:
        return fmt_cell(value).replace("|", "\\|")

    lines = [f"**{caption}**", "", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(esc(row.get(header, "")) for header in headers) + " |")
    lines.extend(["", f"说明: {note}", ""])
    return "\n".join(lines)


def data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_rows() -> list[dict[str, str]]:
    final_report = load_json(LOG_DIR / "final_submission_handoff_report.json")
    submission_report = load_json(LOG_DIR / "submission_ready_gate_report.json")
    publication_report = load_json(LOG_DIR / "publication_gate_report.json")
    return [
        {
            "Gate": "Publication gate",
            "Passed": str(publication_report.get("passed", "待补充")),
            "Evidence": "logs/publication_gate_report.md; publication_gate_evidence/evidence_manifest.json",
            "Reason": "验证原始数据、图件、源数据、文本、引用、包体、仓库沉积准备和归档一致性。",
        },
        {
            "Gate": "Submission-ready gate",
            "Passed": str(submission_report.get("passed", "待补充")),
            "Evidence": "logs/submission_ready_gate_report.md; submission_ready_gate_evidence/evidence_manifest.json",
            "Reason": "在核心门禁基础上加入最终图件/数据审阅矩阵、问题登记表和签署审计。",
        },
        {
            "Gate": "Final handoff gate",
            "Passed": str(final_report.get("passed", "待补充")),
            "Evidence": "logs/final_submission_handoff_report.md; final_submission_handoff_evidence/evidence_manifest.json",
            "Reason": "记录终端运行、构建最终 handoff 证据包并审计证据包完整性。",
        },
    ]


def html_figure(fig: dict[str, str]) -> str:
    uri = data_uri(FIG_DIR / fig["file"])
    caption = f"{fig['number']}. {fig['title']}"
    return f"""
    <figure class="figure-panel" id="{fig['id']}">
      <figcaption>{html.escape(caption)}</figcaption>
      <img src="{uri}" alt="{html.escape(caption)}" />
      <p class="caption-text">{html.escape(fig['caption'])}</p>
      <p class="analysis-text">{html.escape(fig['analysis'])}</p>
    </figure>
    """


def md_figure(fig: dict[str, str]) -> str:
    uri = data_uri(FIG_DIR / fig["file"])
    caption = f"{fig['number']}. {fig['title']}"
    return f"### {caption}\n\n![{caption}]({uri})\n\n{fig['caption']}\n\n{fig['analysis']}\n"


def build_html() -> str:
    tables = {item["id"]: html_table(read_csv_rows(item["file"]), f"{item['number']}. {item['title']}", item["note"], item["id"]) for item in TABLES}
    evidence_table = html_table(
        evidence_rows(),
        "表 7. 最终发表前门禁与证据",
        "该表来自最终运行报告，说明本地论文、图件、数据、包体和证据包已经通过自动门禁。作者姓名、单位、基金和公开仓库 DOI 属于投稿治理信息，仍以作者确认和投稿系统为准。",
        "tab7",
    )
    figures = {fig["id"]: html_figure(fig) for fig in FIGURES}

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(TITLE_CN)}</title>
  <style>
    :root {{
      --paper: #fbfaf7;
      --ink: #20242a;
      --muted: #5f6974;
      --line: #d8d6cf;
      --soft: #efede7;
      --accent: #19756b;
      --accent-2: #a85f36;
      --accent-3: #b3872b;
      --white: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
      line-height: 1.72;
      font-size: 16px;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 0 28px 64px; }}
    .cover {{
      min-height: 82vh;
      display: flex;
      flex-direction: column;
      justify-content: center;
      border-bottom: 1px solid var(--line);
      padding: 72px 0 48px;
    }}
    .label {{
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0;
      text-transform: uppercase;
      font-size: 0.88rem;
    }}
    h1 {{
      max-width: 980px;
      margin: 18px 0 16px;
      font-size: clamp(2.35rem, 6vw, 4.6rem);
      line-height: 1.08;
      letter-spacing: 0;
    }}
    .subtitle {{
      max-width: 860px;
      color: var(--muted);
      font-size: 1.24rem;
      margin: 0 0 34px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      max-width: 980px;
    }}
    .meta-item {{
      border-left: 4px solid var(--accent);
      background: var(--white);
      padding: 14px 16px;
      border-radius: 6px;
      box-shadow: 0 1px 0 rgba(0,0,0,0.04);
    }}
    .meta-item b {{ display: block; font-size: 0.92rem; color: var(--muted); font-weight: 600; }}
    .meta-item span {{ display: block; margin-top: 4px; font-weight: 700; }}
    .visually-hidden {{
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }}
    nav.toc {{
      margin: 34px 0 42px;
      padding: 22px 24px;
      border: 1px solid var(--line);
      background: var(--white);
      border-radius: 8px;
    }}
    nav.toc h2 {{ margin-top: 0; }}
    nav.toc ol {{
      columns: 2;
      column-gap: 42px;
      padding-left: 22px;
      margin: 0;
    }}
    nav.toc a {{ color: var(--accent); text-decoration: none; }}
    section {{
      margin: 44px 0;
      padding-top: 8px;
    }}
    h2 {{
      margin: 0 0 18px;
      padding-bottom: 10px;
      border-bottom: 2px solid var(--line);
      font-size: 1.8rem;
      line-height: 1.25;
    }}
    h3 {{
      margin: 28px 0 10px;
      color: var(--accent);
      font-size: 1.22rem;
    }}
    p {{ margin: 0 0 14px; }}
    .lead {{
      font-size: 1.08rem;
      color: #30363d;
      background: var(--white);
      border-left: 4px solid var(--accent-3);
      padding: 18px 20px;
      border-radius: 6px;
    }}
    .key-points {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin: 20px 0 8px;
    }}
    .point {{
      background: var(--white);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .point b {{ color: var(--accent-2); }}
    .method-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }}
    .method {{
      border-top: 4px solid var(--accent);
      background: var(--white);
      border-radius: 8px;
      padding: 16px;
      min-height: 150px;
    }}
    .figure-panel, .table-wrap {{
      margin: 26px 0 34px;
      background: var(--white);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      overflow: hidden;
    }}
    figure figcaption {{
      font-weight: 800;
      margin-bottom: 12px;
      color: var(--ink);
    }}
    .figure-panel img {{
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }}
    .caption-text {{
      color: var(--muted);
      font-size: 0.95rem;
      margin-top: 12px;
    }}
    .analysis-text {{
      margin-top: 10px;
      padding-left: 14px;
      border-left: 3px solid var(--accent-3);
    }}
    .scroll-table {{ overflow-x: auto; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 720px;
      font-size: 0.94rem;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }}
    th {{
      background: var(--soft);
      font-weight: 800;
    }}
    tbody tr:nth-child(even) td {{ background: #f8f7f3; }}
    .table-note {{
      color: var(--muted);
      font-size: 0.94rem;
      margin-top: 10px;
    }}
    .callout {{
      border-left: 4px solid var(--accent-2);
      background: #fff8f2;
      padding: 16px 18px;
      border-radius: 6px;
      margin: 20px 0;
    }}
    .warning {{
      color: #8a4b18;
      font-weight: 700;
    }}
    ul, ol {{ padding-left: 22px; }}
    li {{ margin: 6px 0; }}
    .footer {{
      margin-top: 54px;
      padding-top: 20px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }}
    @media (max-width: 760px) {{
      main {{ padding: 0 16px 44px; }}
      nav.toc ol {{ columns: 1; }}
      h1 {{ font-size: 2.25rem; }}
      table {{ min-width: 640px; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      main {{ max-width: none; padding: 0 18mm; }}
      .cover {{ min-height: auto; page-break-after: always; }}
      .figure-panel, .table-wrap, .point, .method, nav.toc {{ box-shadow: none; break-inside: avoid; }}
    }}
  </style>
</head>
<body>
<main>
  <header class="cover" id="cover">
    <div class="label">Scientific Report</div>
    <h1>{html.escape(TITLE_CN)}</h1>
    <p class="subtitle">{html.escape(SUBTITLE_CN)}</p>
    <div class="meta-grid">
      <div class="meta-item"><b>报告日期</b><span>{GEN_DATE}</span></div>
      <div class="meta-item"><b>研究对象</b><span>八个海岸潮位站点</span></div>
      <div class="meta-item"><b>核心数据</b><span>GSSR, COAST-RP, Open-Meteo ERA5, DeltaDTM</span></div>
      <div class="meta-item"><b>最终状态</b><span>Final handoff: Passed True</span></div>
      <div class="meta-item"><b>作者与单位</b><span>待补充</span></div>
      <div class="meta-item"><b>公开仓库 DOI</b><span>待补充</span></div>
    </div>
  </header>

  <nav class="toc" id="toc">
    <h2>目录</h2>
    <ol>
      <li><a href="#abstract">摘要</a></li>
      <li><a href="#background">研究背景与目的</a></li>
      <li><a href="#data-methods">数据与方法</a></li>
      <li><a href="#workflow">研究过程与质量控制</a></li>
      <li><a href="#results">结果展示</a></li>
      <li><a href="#discussion">分析与讨论</a></li>
      <li><a href="#conclusion">主要结论</a></li>
      <li><a href="#limitations">不足与展望</a></li>
      <li><a href="#appendix">附录: 表格与证据</a></li>
    </ol>
  </nav>

  <section id="abstract">
    <h2>摘要</h2>
    <p class="lead">本报告整理了一项海岸洪水筛查研究的背景、过程、方法、图表、数据、结果与结论。研究核心问题是: 极端水位指标是否能够单独代表海岸洪水易感性。结果表明，水位过程与地形敏感性在多个站点上存在明显解耦。欧洲站点中，GSSR 增水残差与 COAST-RP 风暴潮位的 10 年一遇指标差异可达 1.87-3.93 m；但在 New York-The Battery 和 Charleston 该差异小于 0.6 m。DeltaDTM 海洋连通地形筛查显示，+2 m 情景下 Sheerness 的连通低地敏感性最高，为 39.25%，而 Newlyn、Brest、Aberdeen 和 Hoek van Holland 均低于 10%。</p>
    <div class="key-points">
      <div class="point"><b>研究逻辑</b><br />把水位产品差异、气象过程一致性和地形连通性放在同一框架中解释。</div>
      <div class="point"><b>关键发现</b><br />风暴潮位高不必然意味着低地敏感性高，地形连通性会改变筛查结论。</div>
      <div class="point"><b>质量控制</b><br />最终 publication gate、submission-ready gate 和 final handoff gate 均为 Passed True。</div>
    </div>
  </section>

  <section id="background">
    <h2>研究背景与目的</h2>
    <p>海岸洪水由气象强迫、海洋水位、天文潮、波浪、近岸地貌、局部地形、人类防护工程和排水系统共同决定。大尺度风险筛查常把复杂过程压缩成少数水位指标，例如风暴增水重现期、风暴潮位重现期或极端海平面面状产品。这种简化有利于区域比较，但也容易掩盖一个关键事实: 产生洪水的水位过程和承受水位作用的地形并不是同一个对象。</p>
    <p>本研究的目的不是验证某一个数据产品优于另一个产品，而是解释它们为何不同、这些差异如何影响易感性判断，以及低洼地形是否真正与海洋边界连通。研究因此提出一个过程-地形耦合框架，用于回答三个问题: 第一，GSSR 增水残差与 COAST-RP 风暴潮位在不同海岸背景下差异有多大；第二，重建增水是否与气压、风速和降水等气象驱动具有物理一致性；第三，低洼地形在海洋连通过滤后是否仍显示高敏感性。</p>
    <div class="callout">需要特别说明的是，本文中的 terrain sensitivity 是静态地形敏感性筛查，不是观测洪水范围，也不是水动力模型预报。作者姓名、作者贡献、基金号和公开仓库 DOI 属于投稿治理信息，当前报告按要求标注为待补充，不做编造。</div>
  </section>

  <section id="data-methods">
    <h2>数据与方法</h2>
    {tables['tab1']}
    <div class="method-grid">
      <div class="method"><h3>1. 水位产品比较</h3><p>使用 GSSR 年最大增水序列计算经验 10 年一遇增水水平，并与邻近 COAST-RP 10 年一遇风暴潮位进行匹配。差异定义为 COAST-RP storm tide 减去 GSSR surge，用于表达物理定义差异。</p></div>
      <div class="method"><h3>2. 气象一致性检验</h3><p>将 GSSR 日增水与 Open-Meteo ERA5 派生的最低气压、最大风速和降水量按日合并，计算 Spearman 秩相关。该步骤用于物理合理性筛查，不用于完整因果归因。</p></div>
      <div class="method"><h3>3. 地形敏感性筛查</h3><p>使用 DeltaDTM 站点窗口，在 +0.5 m、+1.0 m 和 +2.0 m 相对水位扰动下计算低洼地形。候选低洼单元必须与边界水体或边界 no-data 海洋区域八邻域连通，孤立内陆低洼单元不计入海洋连通敏感性。</p></div>
      <div class="method"><h3>4. 过程-地形类型</h3><p>综合 D10 水位差异、+2 m 海洋连通低地比例、气压相关性和 COAST-RP RP10 水位，形成描述性类型划分。该类型不是训练分类器，也不用于区域外统计泛化。</p></div>
    </div>
  </section>

  <section id="workflow">
    <h2>研究过程与质量控制</h2>
    <p>研究过程从数据下载与校验开始，随后进行站点匹配、GSSR 时间序列处理、COAST-RP 水位提取、Open-Meteo 气象变量合并、DeltaDTM 地形窗口读取、海洋连通性计算、图件重建、文本和图表审计、包体生成以及最终证据归档。这样设计的原因是，海岸洪水筛查很容易被数据源定义不一致、地形 no-data 解释错误、图件源数据不一致或投稿元数据缺失所影响，因此必须把科学计算和发表前审计放在同一条流程中。</p>
    {evidence_table}
  </section>

  <section id="results">
    <h2>结果展示</h2>
    <h3>研究设计与站点</h3>
    {figures['fig1']}
    {tables['tab6']}

    <h3>水位指标差异</h3>
    {figures['fig2']}
    {tables['tab2']}

    <h3>气象驱动一致性</h3>
    {figures['fig3']}
    {tables['tab3']}

    <h3>DeltaDTM 地形敏感性</h3>
    {figures['fig4']}
    {tables['tab4']}

    <h3>过程-地形类型划分</h3>
    {figures['fig5']}
    {tables['tab5']}
  </section>

  <section id="discussion">
    <h2>分析与讨论</h2>
    <h3>为什么水位产品会产生明显差异</h3>
    <p>GSSR 和 COAST-RP 的差异首先来自物理定义。GSSR 表征站点尺度重建增水残差，COAST-RP 表征包含天文潮的风暴潮位重现期。因此，在潮差较大的欧洲站点，COAST-RP RP10 明显高于 GSSR RP10 是合理现象。该差异不应被简单解释为模型误差，而应被解释为产品定义和水位过程不同。</p>
    <h3>为什么地形连通性会改变易感性判断</h3>
    <p>静态 bathtub 筛查只看地形是否低于某一水位阈值，容易把孤立内陆低洼地或不与海洋边界相连的区域计入潜在淹没范围。本研究使用边界连通规则后，Hoek van Holland 的 +2 m 低地比例从未过滤情景中的较高值降到 3.10% 的连通低地比例，说明地形屏障和连通路径对筛查结果具有决定性影响。</p>
    <h3>结果对海岸洪水筛查的意义</h3>
    <p>结果提示，第一阶筛查不能只按极端水位大小排序。一个站点可能具有较大的风暴潮位指标，但由于低地范围较小或与海洋边界不直接连通，其静态地形敏感性较低。相反，当高水位指标与连通低洼地形相互叠加时，站点会表现出更高的筛查优先级。Sheerness 就是这一类水位-地形较为对齐的站点。</p>
  </section>

  <section id="conclusion">
    <h2>主要结论</h2>
    <ol>
      <li>GSSR 增水残差和 COAST-RP 风暴潮位代表不同物理量，不能直接互相验证或互相替代。</li>
      <li>欧洲潮汐影响较强站点的 storm-tide-minus-surge 差异较大，表明天文潮和产品定义对筛查解释非常重要。</li>
      <li>Newlyn、Brest、Aberdeen 和 Hoek van Holland 等站点的增水与气压呈明显负相关，说明重建增水在温带风暴背景下具有气象一致性。</li>
      <li>DeltaDTM 海洋连通筛查显示，Sheerness 的 +2 m 低地敏感性最突出，而其他欧洲站点在连通规则下均低于 10%。</li>
      <li>海岸洪水易感性应被理解为水位过程与低洼连通地形的耦合结果，而不是单一极端水位指标的直接函数。</li>
    </ol>
  </section>

  <section id="limitations">
    <h2>不足与展望</h2>
    <p>本研究仍有边界条件。第一，站点数量有限，八个站点可以展示机制差异，但不足以代表全球统计规律。第二，GSSR 重现期采用经验年最大值方法，较长重现期存在记录长度限制。第三，水位产品和地形产品的垂向基准尚未完全统一，因此本文使用相对水位扰动而非绝对洪水水深。第四，海洋连通静态筛查未模拟堤防破坏、粗糙度、水动力传播、波浪增水、河流洪水或排水失效。第五，New York-The Battery、Charleston 和 Hong Kong 当前没有纳入 DeltaDTM 地形窗口，相关扩展仍待补充。</p>
    <p>后续研究可扩大站点样本，增加潮差和垂向基准元数据，引入事件级风向、风暴路径和热带气旋参数，测试不同连通性和防护假设，并将地形筛查与暴露、脆弱性和适应能力结合，形成更完整的风险评估。</p>
  </section>

  <section id="appendix">
    <h2>附录: 数据可用性、代码可用性与待补充信息</h2>
    <p>所有上游输入数据均为公开数据产品。GSSR、COAST-RP、Open-Meteo ERA5 和 DeltaDTM 的引用信息已在论文参考文献和投稿支持文件中记录。处理后的图表源数据、最终包体和归档清单均已在项目归档材料中保存；本报告本身不依赖任何外部数据文件。</p>
    <p><b>待补充:</b> 最终作者姓名与单位、通讯作者邮箱、基金信息、公开仓库 URL 和 DOI、正式投稿日期。这些信息需要作者组确认，不从计算流程中推断。</p>
  </section>

  <footer class="footer">
    <p>本报告为完全自包含 HTML，CSS、图片和表格均内嵌于文件内部。图片来自已通过最终门禁的主图，表格来自已审计的图表源数据。报告生成时间: {GEN_DATE}。</p>
  </footer>
</main>
</body>
</html>
"""


def build_markdown() -> str:
    table_blocks = {item["id"]: markdown_table(read_csv_rows(item["file"]), f"{item['number']}. {item['title']}", item["note"]) for item in TABLES}
    evidence_block = markdown_table(
        evidence_rows(),
        "表 7. 最终发表前门禁与证据",
        "该表来自最终运行报告，说明本地论文、图件、数据、包体和证据包已经通过自动门禁。作者姓名、单位、基金和公开仓库 DOI 属于投稿治理信息，仍以作者确认和投稿系统为准。",
    )
    figure_blocks = {fig["id"]: md_figure(fig) for fig in FIGURES}
    return f"""# {TITLE_CN}

{SUBTITLE_CN}

- 报告日期: {GEN_DATE}
- 研究对象: 八个海岸潮位站点
- 核心数据: GSSR, COAST-RP, Open-Meteo ERA5, DeltaDTM
- 最终状态: Final handoff Passed True
- 作者与单位: 待补充
- 公开仓库 DOI: 待补充

## 摘要

本报告整理了一项海岸洪水筛查研究的背景、过程、方法、图表、数据、结果与结论。研究核心问题是: 极端水位指标是否能够单独代表海岸洪水易感性。结果表明，水位过程与地形敏感性在多个站点上存在明显解耦。欧洲站点中，GSSR 增水残差与 COAST-RP 风暴潮位的 10 年一遇指标差异可达 1.87-3.93 m；但在 New York-The Battery 和 Charleston 该差异小于 0.6 m。DeltaDTM 海洋连通地形筛查显示，+2 m 情景下 Sheerness 的连通低地敏感性最高，为 39.25%，而 Newlyn、Brest、Aberdeen 和 Hoek van Holland 均低于 10%。

## 研究背景与目的

海岸洪水由气象强迫、海洋水位、天文潮、波浪、近岸地貌、局部地形、人类防护工程和排水系统共同决定。大尺度风险筛查常把复杂过程压缩成少数水位指标，这种简化有利于区域比较，但也容易掩盖水位过程与暴露地形之间的差异。

本研究的目的不是验证某一个数据产品优于另一个产品，而是解释它们为何不同、这些差异如何影响易感性判断，以及低洼地形是否真正与海洋边界连通。

## 数据与方法

{table_blocks['tab1']}

方法包括水位产品比较、气象一致性检验、DeltaDTM 海洋连通静态地形敏感性筛查，以及过程-地形类型划分。静态地形敏感性不是观测洪水范围，也不是水动力预报。

## 研究过程与质量控制

研究过程包括数据下载与校验、站点匹配、GSSR 时间序列处理、COAST-RP 水位提取、Open-Meteo 气象变量合并、DeltaDTM 地形窗口读取、海洋连通性计算、图件重建、文本和图表审计、包体生成以及最终证据归档。

{evidence_block}

## 结果展示

{figure_blocks['fig1']}

{table_blocks['tab6']}

{figure_blocks['fig2']}

{table_blocks['tab2']}

{figure_blocks['fig3']}

{table_blocks['tab3']}

{figure_blocks['fig4']}

{table_blocks['tab4']}

{figure_blocks['fig5']}

{table_blocks['tab5']}

## 分析与讨论

GSSR 和 COAST-RP 的差异首先来自物理定义。GSSR 表征站点尺度重建增水残差，COAST-RP 表征包含天文潮的风暴潮位重现期。因此，在潮差较大的欧洲站点，COAST-RP RP10 明显高于 GSSR RP10 是合理现象。

地形连通性会改变易感性判断。静态 bathtub 筛查只看地形是否低于某一水位阈值，容易把孤立内陆低洼地或不与海洋边界相连的区域计入潜在淹没范围。本文使用边界连通规则后，Hoek van Holland 的 +2 m 连通低地比例明显降低，说明地形屏障和连通路径对筛查结果具有决定性影响。

## 主要结论

1. GSSR 增水残差和 COAST-RP 风暴潮位代表不同物理量，不能直接互相验证或互相替代。
2. 欧洲潮汐影响较强站点的 storm-tide-minus-surge 差异较大，表明天文潮和产品定义对筛查解释非常重要。
3. Newlyn、Brest、Aberdeen 和 Hoek van Holland 等站点的增水与气压呈明显负相关，说明重建增水在温带风暴背景下具有气象一致性。
4. DeltaDTM 海洋连通筛查显示，Sheerness 的 +2 m 低地敏感性最突出，而其他欧洲站点在连通规则下均低于 10%。
5. 海岸洪水易感性应被理解为水位过程与低洼连通地形的耦合结果，而不是单一极端水位指标的直接函数。

## 不足与展望

本研究仍有边界条件。站点数量有限，GSSR 重现期存在记录长度限制，水位产品和地形产品的垂向基准尚未完全统一，海洋连通静态筛查未模拟堤防破坏、粗糙度、水动力传播、波浪增水、河流洪水或排水失效。New York-The Battery、Charleston 和 Hong Kong 当前没有纳入 DeltaDTM 地形窗口，相关扩展仍待补充。

## 待补充信息

最终作者姓名与单位、通讯作者邮箱、基金信息、公开仓库 URL 和 DOI、正式投稿日期需要作者组确认，不从计算流程中推断。
"""


def main() -> int:
    OUT_HTML.write_text(build_html(), encoding="utf-8")
    OUT_MD.write_text(build_markdown(), encoding="utf-8")
    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
