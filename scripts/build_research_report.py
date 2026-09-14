#!/usr/bin/env python3
"""Build a self-contained Chinese research report HTML, Markdown and PDF."""

from __future__ import annotations

import base64
import html
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures" / "main"
SOURCE_DIR = ROOT / "data" / "figure_source"

OUT_HTML = ROOT / "report.html"
OUT_MD = ROOT / "report.md"
OUT_PDF = ROOT / "report.pdf"

FINAL_HTML = ROOT / "manuscript" / "process_terrain_coastal_flood_research_report.html"
FINAL_MD = ROOT / "manuscript" / "process_terrain_coastal_flood_research_report.md"
FINAL_PDF = ROOT / "manuscript" / "process_terrain_coastal_flood_research_report.pdf"

GENERATED_AT = datetime.now().strftime("%Y-%m-%d %H:%M")

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt(value: object, digits: int = 2) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    if pd.isna(val):
        return "待补充"
    return f"{val:.{digits}f}"


def pct(value: object, digits: int = 1) -> str:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return "" if value is None else str(value)
    if pd.isna(val):
        return "待补充"
    return f"{val:.{digits}f}%"


def table_html(caption: str, headers: list[str], rows: list[list[object]], note: str | None = None) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    note_html = f'<p class="table-note">{esc(note)}</p>' if note else ""
    return f"""
<figure class="table-block">
  <figcaption>{esc(caption)}</figcaption>
  <div class="scroll-table">
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>
        {body}
      </tbody>
    </table>
  </div>
  {note_html}
</figure>
"""


def table_md(caption: str, headers: list[str], rows: list[list[object]], note: str | None = None) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    lines = [f"**{caption}**", ""]
    lines.append("| " + " | ".join(cell(h) for h in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(cell(c) for c in row) + " |")
    if note:
        lines.extend(["", f"注：{note}"])
    return "\n".join(lines)


def paras_html(paragraphs: list[str]) -> str:
    return "\n".join(f"<p>{p}</p>" for p in paragraphs)


def paras_md(paragraphs: list[str]) -> str:
    return "\n\n".join(re.sub(r"<[^>]+>", "", p) for p in paragraphs)


def figure_html(number: str, title: str, file_name: str, paragraphs: list[str]) -> str:
    uri = data_uri(FIG_DIR / file_name)
    return f"""
<figure class="figure-block" id="fig-{number}">
  <figcaption>图 {number}. {esc(title)}</figcaption>
  <img src="{uri}" alt="图 {number}. {esc(title)}" />
</figure>
<div class="figure-explain">
  {paras_html(paragraphs)}
</div>
"""


def figure_md(number: str, title: str, file_name: str, paragraphs: list[str]) -> str:
    uri = data_uri(FIG_DIR / file_name)
    return "\n".join(
        [
            f"**图 {number}. {title}**",
            "",
            f"![图 {number}. {title}]({uri})",
            "",
            paras_md(paragraphs),
        ]
    )


def section_html(anchor: str, title: str, body: str) -> str:
    return f'<section id="{anchor}">\n<h2>{esc(title)}</h2>\n{body}\n</section>'


def section_md(title: str, body: str) -> str:
    return f"## {title}\n\n{body}"


def load_report_tables() -> dict[str, tuple[list[str], list[list[object]], str | None]]:
    water = pd.read_csv(SOURCE_DIR / "Fig2_water_level_divergence_with_uncertainty.csv")
    rank = pd.read_csv(SOURCE_DIR / "Fig6_mask_aware_rank_metrics_fraction_area_samples.csv")
    assoc = pd.read_csv(SOURCE_DIR / "Fig6_mask_aware_two_sided_permutation_association.csv")
    block = pd.read_csv(SOURCE_DIR / "Fig6_mask_aware_sector_block_bootstrap.csv")
    arche = pd.read_csv(SOURCE_DIR / "Fig6_archetype_map_selection.csv")
    drivers = pd.read_csv(SOURCE_DIR / "Fig3_driver_correlations.csv")
    mask = pd.read_csv(SOURCE_DIR / "Fig6_deltadtm_mask_seed_audit.csv")
    fixed = pd.read_csv(SOURCE_DIR / "Fig6_mask_aware_terrain_area_metrics.csv")
    local_validation = pd.read_csv(SOURCE_DIR / "TableS_local_dtm_validation.csv")
    tidal_tracked = pd.read_csv(SOURCE_DIR / "TableS_tidal_regime_metadata_source_tracked.csv")
    primary_fixed = fixed[
        fixed["marine_seed_resolved"].eq(True)
        & fixed["match_dist_km"].le(6.0)
    ].dropna(subset=["coast_rp_rp10_m", "mask_connected_2m_lowland_pct"])
    spatial_n = int(primary_fixed.shape[0])
    gssr_qualified_n = int(
        primary_fixed[
            primary_fixed["archive_available"]
            & primary_fixed["passes_years_ge25"]
            & primary_fixed["passes_corr_ge055"]
        ].shape[0]
    )
    source_verified_tidal_n = int(tidal_tracked["source_status"].eq("source_verified").sum())
    local_station_names = {
        "sheerness-p015-uk": "Sheerness",
        "newlyn-p001-uk": "Newlyn",
        "lowestoft-p024-uk": "Lowestoft",
        "immingham-p026-uk": "Immingham",
        "denhelder-hel-nl": "Den Helder",
        "delfzijl-del-nl": "Delfzijl",
        "hoekvanholla-hvh-nl": "Hoek van Holland",
    }

    data_product_rows = [
        [
            "全球风暴潮重建",
            "Global Storm Surge Reconstruction（全球风暴潮重建，简称 GSSR；这里使用 ERA5 再分析驱动的逐日重建风暴增水序列）",
            "逐日重建的 surge residual（风暴残差水位，即去除天文潮后主要由气象强迫引起的水位异常）",
            "用于描述水位过程侧的风暴增水信号，并估计 10 年一遇经验重现水位。",
            "它不是总水位，不直接包含天文潮。",
        ],
        [
            "COAST-RP",
            "COAST-RP（全球沿海 storm tide return period 数据集；storm tide 指风暴增水与天文潮共同形成的总风暴潮位）",
            "10 年一遇 storm-tide return level（风暴潮位重现水位）",
            "用于代表大尺度沿岸极端总水位筛查指标。",
            "与 GSSR 的 residual surge 不是同一物理量，不能直接当作相互验证。",
        ],
        [
            "ERA5 气象诊断",
            "ERA5-derived meteorological variables（由 ERA5 再分析衍生的气压、风速、降水等日尺度气象变量）",
            "气压、风速、降水及事件合成指标",
            "用于检查 GSSR 重建风暴增水在若干站点是否保留合理的气象过程一致性。",
            "只是过程一致性检查，不是因果归因模型，也不是淹没预测模型。",
        ],
        [
            "DeltaDTM",
            "DeltaDTM（全球沿海数字地形模型，约 30 m 水平分辨率；用于近似 bare-earth 地形）",
            "地形高程、静态低地连通性",
            "用于计算低于 2 m 地形阈值且与官方 ocean/tidal-water mask 种子相连的低地区域。",
            "当前主流程已接入官方 mask_tiles.zip：ocean class 1 为主种子，river class 3 仅在与 ocean 连通时加入，lake class 2 和 255 clipped cells 不作为海洋种子。",
        ],
    ]

    water_rows = []
    for _, r in water.iterrows():
        water_rows.append(
            [
                r["full_label"],
                r["region"],
                f"{fmt(r['gssr_rp10_m'])} m",
                f"{fmt(r['coast_rp_rp10_m'])} m",
                f"{fmt(r['D10_m'])} m",
                fmt(r.get("spring_tidal_range_m")),
                r["source_status"],
            ]
        )

    rank_rows = []
    for _, r in rank[rank["terrain_metric"].isin(["mask_connected_2m_lowland_pct", "mask_connected_2m_area_km2"])].iterrows():
        p_match = assoc[
            (assoc["sample"].eq(r["sample"])) & (assoc["terrain_metric"].eq(r["terrain_metric"]))
        ]
        p_value = p_match.iloc[0]["spearman_two_sided_p"] if not p_match.empty else None
        block_match = block[
            (block["sample"].eq(r["sample"])) & (block["terrain_metric"].eq(r["terrain_metric"]))
        ]
        block_range = (
            f"{fmt(block_match.iloc[0]['spearman_block_p025'])} to "
            f"{fmt(block_match.iloc[0]['spearman_block_p975'])}"
            if not block_match.empty
            else "not calculated"
        )
        metric_label = "官方 mask 连通低地比例" if r["terrain_metric"] == "mask_connected_2m_lowland_pct" else "官方 mask 连通面积"
        rank_rows.append(
            [
                r["sample"],
                metric_label,
                int(r["n_sites"]),
                int(r["top_overlap"]),
                int(r["top_n"]),
                pct(100 * float(r["top_mismatch"]), 0),
                fmt(r["spearman"]),
                fmt(p_value, 3),
                block_range,
            ]
        )

    arche_rows = []
    label_map = {
        "aligned high storm-tide / high connected-terrain": "高水位 / 高连通地形响应",
        "high storm-tide / lower connected-terrain": "高水位 / 较低连通地形响应",
        "lower storm-tide / high connected-terrain": "较低水位 / 较高连通比例响应",
    }
    for _, r in arche.iterrows():
        arche_rows.append(
            [
                label_map.get(r["archetype"], r["archetype"]),
                r["station"],
                f"{fmt(r['coast_rp_rp10_m'])} m",
                pct(r["connected_2m_lowland_pct"]),
                f"{fmt(r['connected_2m_area_km2'])} km²",
                f"{int(r['water_rank'])}/{spatial_n}",
                f"{int(r['terrain_rank'])}/{spatial_n}",
            ]
        )

    driver_rows = []
    for _, r in drivers.iterrows():
        driver_rows.append(
            [
                r["label"],
                int(r["n_days"]),
                fmt(r["pressure"], 3),
                fmt(r["wind"], 3),
                fmt(r["precipitation"], 3),
                r["coherence_role"],
            ]
        )

    mask_row = mask.iloc[0]
    data_readiness_rows = [
        [
            "GSSR 风暴增水序列",
            f"已读取真实 GSSR 站点时间序列，并形成 {gssr_qualified_n} 个 GSSR-qualified Northwest Europe 站点子集。",
            "支持 surge residual 过程侧诊断、经验 RP10、bootstrap、GEV 点估计和 prediction-envelope 检查。",
            "不代表总水位，不直接包含天文潮；当前仍是筛查级极值处理。",
            "公开原始文件来源、处理脚本、随机种子、版本信息和 RP10 源表。",
        ],
        [
            "COAST-RP 风暴潮位",
            f"已完成 Northwest Europe 空间匹配，主地形排序使用 {spatial_n} 个同时具备 COAST-RP 和 DeltaDTM 支持的站点。",
            "支持 storm-tide magnitude 排名和 COAST-RP-terrain rank diagnostic。",
            "nearest-neighbour / nearest-three / within-5 km 只能说明提取敏感性，不等于完整产品不确定性。",
            "在复现包中保留 NetCDF 文件哈希、匹配距离、组件文件和提取源表。",
        ],
        [
            "DeltaDTM 地形高程",
            "已使用 Europe.zip 高程瓦片、官方 mask_tiles.zip 和固定约 10 x 10 km 窗口计算 mask-aware connected fraction 与 connected area。",
            "支持标准化静态 terrain-screening sensitivity，即低于 2 m EGM2008-referenced threshold 且与官方 ocean/tidal-water seed 连通的低地响应。",
            "官方 mask 仍不能表达堤防、水闸、涵洞、排水系统和局部水动力传播，因此结果仍是筛查指标，不是真实洪水边界。",
            "复现包保留每个窗口的 ocean、river、lake、255 clipped cells、connected/unconnected/all-below 像元数和面积。",
        ],
        [
            "潮汐元数据",
            f"当前正式潮汐解释限制在 {source_verified_tidal_n} 个 source-verified tidal stations。",
            "支持解释 D10 在大潮差地区较大的物理合理性。",
            "尚不能声称潮汐元数据覆盖全部区域站点；context-only 站点只作背景说明。",
            "补齐 SHOM/REFMAR、荷兰及其他官方站点潮汐调和或大潮差数据。",
        ],
        [
            "图表与中间源表",
            "paper.html 和 report.html 均嵌入 Base64 PNG；图件哈希已与 figures/main 中当前 PNG 一致。",
            "支持报告和论文在脱离本地图片路径后完整显示，也支持审稿人追溯图件来源。",
            "当前本地复现包已经生成，位置为 reproducibility_package/ 和 reproducibility_package.zip；尚未发布 DOI 或 private reviewer link，仍是本地可审计状态。",
            "投稿前需要把包含 figure source tables、图件哈希、脚本入口、环境信息和一键重建说明的复现包发布到公开或审稿私有仓储。",
        ],
        [
            "本地高精度地形交叉检查",
            "已完成 Sheerness、Newlyn、Lowestoft、Immingham、Den Helder、Delfzijl 和 Hoek van Holland 七站 local DTM cross-check。",
            "支持 Newlyn、Lowestoft 与 Delfzijl 的连通响应类别；显示 Sheerness、Immingham、Den Helder 与 Hoek 在本地 DTM 下类别改变。",
            "由于 local DTM 与 DeltaDTM 垂向基准尚未统一，不能把 cross-check 解释为绝对洪水水位验证。",
            "下一步应进行 datum harmonization 或更明确的本地基准转换，并继续补充关键 archetype 的独立地形产品检查。",
        ],
    ]

    limitation_rows = [
        [
            "DeltaDTM 官方 mask",
            f"已接入官方 mask_tiles.zip（{mask_row['official_mask_tiles_zip_size_bytes']} bytes，MD5 {mask_row['official_mask_tiles_zip_md5_expected']}），主流程使用 {mask_row['marine_seed_rule']}。",
            "boundary no-data seed proxy 仅作为敏感性/历史对照保留；七站 local-DTM cross-check 已完成，但还需垂向基准统一。",
        ],
        [
            "本地地形交叉检查",
            "已用英国 Environment Agency LiDAR Composite DTM 和荷兰 PDOK/Rijkswaterstaat AHN DTM 完成七站产品与基准敏感性检查。",
            "交叉检查显示 Newlyn、Lowestoft 与 Delfzijl 类别保持，Sheerness、Immingham、Den Helder 与 Hoek van Holland 类别改变；因此主文已降调这些地点的稳定性表述。",
        ],
        [
            "潮汐元数据",
            "主文只对 13 个 source-verified tidal stations 作正式潮汐解释，部分站点仍是 context-only。",
            "补齐 SHOM/REFMAR、荷兰及其他官方站点的潮汐调和或大潮差数据。",
        ],
        [
            "统计解释",
            "top-set mismatch 是筛查优先级描述，不是证明 overlap 显著低于随机的证据。",
            "继续保留 two-sided permutation 和 top-k null envelope；避免使用暗示真实基准或单一真值排序的过强措辞。",
        ],
    ]
    target_rows = [
        [
            "总目标",
            "把当前稿件优化为“数据边界清楚、图件可读、指标可审计、结论不过度外推”的区域沿海洪水筛查论文。",
            "论文和报告均明确：本研究比较 storm-tide magnitude 与 connected-terrain response 的筛查优先级，不声称模拟真实洪水范围。",
        ],
        [
            "数据闭环",
            "每个核心数值都能追溯到公开输入数据、处理脚本、中间源表和最终图表。",
            "复现包包含 processed station master table、figure source data、raw-file hashes、环境版本、随机种子和一键重建命令。",
        ],
        [
            "地形审计",
            "官方 DeltaDTM mask classes 已替代 boundary no-data seed proxy 成为主分析，并保留旧 proxy 作为 sensitivity comparator。",
            "每个地形窗口输出 ocean、river、lake、255 clipped cells、valid terrain、connected/unconnected cells 的数量和面积。",
        ],
        [
            "本地交叉检查",
            "把已完成的七站 local DTM cross-check 纳入论文和复现包，并将其作为地形产品敏感性边界写清楚。",
            "已完成七站验收；下一步若要正式投稿，应继续做垂向基准统一和必要的关键站点交叉验证。",
        ],
        [
            "写作收束",
            "把 Discussion 中的结论固定为“limited recovery / complementary screening priorities”，避免暗示某一个筛查排序就是真实洪水基准的措辞。",
            "摘要、图注、结论和报告均使用同一套术语和边界说明。",
        ],
    ]

    return {
        "data_products": (
            ["数据源", "全称与含义", "主要变量", "在本研究中的作用", "主要限制"],
            data_product_rows,
            "这些数据源对应水位过程、气象过程和地形响应三个层面；报告不把它们相互替代，而是把它们作为互补筛查信息。",
        ),
        "data_readiness": (
            ["数据层", "当前真实数据基础", "当前可以支持的结论", "当前不能支持的结论", "下一步验收要求"],
            data_readiness_rows,
            "这张表把“数据真实”和“结果可信”的边界拆开：已有数据足以支持区域筛查诊断，但还不足以声称真实洪水范围或完整工程风险评估。",
        ),
        "water": (
            ["站点", "区域", "GSSR 10 年一遇", "COAST-RP 10 年一遇", "D10 差值", "潮差背景", "来源状态"],
            water_rows,
            "D10 = COAST-RP 10 年一遇 storm-tide return level - GSSR 10 年一遇 surge return level。该差值不是误差，而是两个物理定义不同的指标之间的分离程度。",
        ),
        "rank": (
            ["样本", "地形响应指标", "站点数", "Top overlap", "Top set", "描述性 mismatch", "Spearman rho", "双侧置换 p", "六沿海分区 block 95% 范围"],
            rank_rows,
            "Top-set mismatch 是决策层面的描述性结果。普通站点置换检验不处理沿海站点的空间聚集；主样本还报告六沿海分区 block-bootstrap 范围，该范围跨零，因此不能声称稳定的区域负相关。",
        ),
        "archetypes": (
            ["类型", "代表站点", "COAST-RP RP10", "连通低地比例", "连通面积", "水位排名", "地形排名"],
            arche_rows,
            "三个 archetype 是为了帮助读者理解为什么水位优先级和地形优先级会分离，不是为了声称这三个站点代表所有海岸类型。",
        ),
        "drivers": (
            ["站点", "样本天数", "气压相关", "风速相关", "降水相关", "解释角色"],
            driver_rows,
            "相关系数为 Spearman rank correlation，表示两个变量排序是否同向或反向变化；它不是因果模型。",
        ),
        "limitations": (
            ["事项", "当前状态", "下一步验收条件"],
            limitation_rows,
            "这些不是推翻当前报告的缺陷，而是将报告从筛查研究推进到正式投稿版本所需的补强项。",
        ),
        "target": (
            ["层级", "具体目标", "验收条件"],
            target_rows,
            "下一轮优化的目标不是让结论更夸张，而是让每一条结论都有清楚的数据边界、复现路径和审稿可检查证据。",
        ),
        "local_validation": (
            [
                "站点",
                "本地 DTM 来源",
                "DeltaDTM 连通比例",
                "本地 DTM 连通比例",
                "DeltaDTM 连通面积",
                "本地 DTM 连通面积",
                "类别是否改变",
                "交并比",
            ],
            [
                [
                    local_station_names.get(row["station_id"], row["station"]),
                    row["local_dtm_source"],
                    pct(row["delta_connected_2m_fraction_pct"], 2),
                    pct(row["local_connected_2m_fraction_pct"], 2),
                    f"{fmt(row['delta_connected_2m_area_km2'], 2)} km²",
                    f"{fmt(row['local_connected_2m_area_km2'], 2)} km²",
                    "是" if bool(row["category_changed"]) else "否",
                    fmt(row["connected_pixel_iou_after_reprojection"], 3),
                ]
                for _, row in local_validation.iterrows()
            ],
            "本表使用本地 DTM 原生垂向基准下的 2 m 阈值进行筛查交叉验证，尚未做完整垂向基准统一；因此它用于判断 DeltaDTM 结果是否对地形产品敏感，而不是用于给出真实洪水边界。",
        ),
    }


def build_report() -> tuple[str, str]:
    tables = load_report_tables()
    figures = [
        (
            "1",
            "研究设计、站点覆盖和数据角色",
            "Fig1_process_terrain_design.png",
            [
                "这张图回答的是“研究到底在比较什么”。整项研究不是从单一水位产品直接推断沿海洪水风险，而是把问题拆成三个层面：水位过程、气象过程一致性和地形连通响应。图中的站点用于说明不同数据层级怎样叠加：有些站点只用于水位和气象诊断，有些站点还进入 DeltaDTM 地形筛查。",
                "通俗地说，如果只看一个极端水位数字，就像只知道一场雨下得很大，却不知道城市地势、排水系统和河道连通性。图 1 的作用就是把“海边水位有多高”和“低地是否能从海洋方向连通”分开。报告先给出 68 站区域证据，再用三个站点解释排序为什么分离，随后检查地形产品和垂向基准敏感性；水位定义与气象过程诊断放在后面作为解释性证据。",
                "需要特别注意的是，图 1 不是风险地图，也不是洪水淹没图。它是一张研究框架图，用来告诉读者哪些数据用于哪个问题。这样的图在正式汇报中很重要，因为它防止读者一开始就把 storm tide、storm surge 和 terrain response 混为一谈。",
            ],
        ),
        (
            "2",
            "区域尺度水位排名与地形响应排名的统计关系",
            "Fig2_regional_screening_agreement.png",
            [
                "图 2 直接展示论文的核心区域证据。主样本包含 68 个官方海洋种子已经解析、且 COAST-RP 最近点距离不超过 6 km 的站点。它比较的是 storm-tide magnitude（风暴潮位幅值）与 connected-terrain response（连通地形响应），不是两个相同物理量之间的验证。",
                "主样本中，COAST-RP RP10 与 +2 m 连通比例的 Spearman rho 为 -0.36，普通站点置换 p=0.003；与连通面积的 rho 为 -0.33，p=0.006。但按六个沿海分区整体重采样后，两组范围都跨过零。因此结果不能包装成稳定的区域负相关定律，只能说明在当前站点样本中，水位幅值对地形响应排序的恢复能力有限。",
                "图 2b 进一步把 top-k overlap（前 k% 集合重叠）与随机置换包络并列。主样本前 20% 集合只重叠 1/14，但该重叠仍在随机包络内。它是实际优先级列表差异的描述，而不是超出随机期望的显著性证据。图 2c 和 2d 则说明比例、面积、样本定义和空间聚集都会改变关联强度。",
            ],
        ),
        (
            "3",
            "为什么水位优先级和连通地形优先级会分离",
            "Fig3_connected_terrain_contrasts.png",
            [
                "图 3 是本报告最关键的“解释图”。它不再试图一次性展示所有站点，而是把问题浓缩成三类典型情形。每一列是一类 archetype（原型案例；这里指为了说明机制而选出的典型排序组合，不代表所有海岸都属于这三类）。每一列从上到下读：第一行看空间分类，第二行看水位与地形排序证据，第三行看这个判断是否只依赖 +2 m 这个阈值。",
                "地图中的深蓝边界只描出已经被算法判定为 connected 的像元轮廓，目的在于让 Newport 仅占 0.2% 的狭窄连通足迹在期刊缩图中仍然可见。这个边界没有膨胀像元、没有增加淹没面积，也没有改变源表数值；它是可读性标记，不是结果平衡处理。",
                "新版 Figure 3 的案例由明确规则从主样本自动选择，不再手工指定站点：种子必须可解析、COAST-RP 匹配必须不超过 6 km，并要求至少 0.05 km² 连通面积保证地图可读。每类再按相应的排名位移选择案例。",
                "第一列 Sheerness 是高水位/高地形响应案例：COAST-RP RP10 为 5.26 m，连通低地比例 46.5%，连通面积 20.65 km²，水位和地形排名分别为 14/68 和 6/68。它说明两个指标有时会共同给出较高优先级，但本地 LiDAR 交叉检查把其连通比例降至 10.69%，因此不能视为已验证洪水范围。",
                "第二列 Newport 是高水位/较低地形响应案例：RP10 为 8.60 m，水位排名 3/68，而连通比例仅 0.21%、面积 0.11 km²、地形排名 68/68。地图并非完全没有蓝色，而是蓝色主要沿狭窄潮汐水道出现，这正是低连通响应的空间含义。",
                "第三列 Den Helder 是较低水位/高地形响应案例：RP10 为 2.64 m，水位排名 58/68，但 DeltaDTM 连通比例 72.0%、面积 20.89 km²、地形排名 2/68。AHN 本地地形检查只有 4.96%，所以这列同时是方法敏感性警示。",
                "第三行 threshold-response curves（阈值响应曲线）说明这些对比如何随 0-3 m 地形阈值变化。浅色带是 ±0.5 m 地形扰动范围，不是置信区间。Figure 3 解释的是标准化地形响应，不是实际淹没预测。",
            ],
        ),
        (
            "4",
            "地形产品与垂向基准敏感性",
            "Fig4_elevation_product_datum_sensitivity.png",
            [
                "图 4 是本轮投稿修改中最重要的方法边界图。它比较七个站点使用 DeltaDTM 与 national/local DTM 后的连通比例，并计算重投影后的连通像元交并比。水体种子和 class-0 陆地掩膜保持不变，因此主要变化来自地形高程栅格。",
                "Newlyn、Lowestoft 和 Delfzijl 的响应类别保持不变；Sheerness、Immingham、Den Helder 和 Hoek van Holland 的类别改变。图中的差异没有被隐藏，因为它们直接说明区域筛查在工程化或低平海岸可能对高程产品高度敏感。",
                "需要特别强调，DeltaDTM 使用 EGM2008，英国 Environment Agency 地形使用 Ordnance Datum Newlyn，荷兰 AHN 使用 Normaal Amsterdams Peil。本项目没有把三者转换到共同垂直参考系，所以图 4 只能解释为 elevation-product and datum sensitivity（地形产品与垂向基准敏感性），不能称为误差验证或真实洪水水位验证。",
                "这一限制与 Seeger and Minderhoud (2026) 对沿海评估中陆地高程和海平面必须共享垂直参考系的警示直接对应。图 4 因而不是附带的免责声明，而是对主指标可解释范围的实证检查：四个站点类别改变，说明站点层面的绝对判断需要先完成基准统一。",
            ],
        ),
        (
            "5",
            "残差风暴增水与总风暴潮位指标的分离",
            "FigS1_water_level_definition.png",
            [
                "图 5 是水位定义的支持性证据。GSSR 描述 surge residual（剔除天文潮后的重建风暴残差），COAST-RP 描述 storm tide return level（包含天文潮贡献的总风暴潮位重现值）。二者都用米表示，却不是等价物理量。",
                "Sheerness 的 GSSR RP10 为 1.36 m，COAST-RP RP10 为 5.26 m，D10 为 3.89 m；Brest、Newlyn 等大潮差站点也有较大分离。13 个来源核实站点中，潮差与 D10 的 rho 为 0.95，说明这一分离主要提供潮汐与产品定义背景，而不是产品误差证据。",
                "因此这张图不再承担论文主发现。它解释为什么区域筛查必须保留 water-level indicator 的物理标签，但真正的新结果仍是 Figure 2 至 Figure 4 展示的水位优先级、连通地形优先级及其地形产品敏感性。",
            ],
        ),
        (
            "6",
            "GSSR 重建风暴增水的气象过程一致性检查",
            "FigS2_process_coherence.png",
            [
                "图 6 是质量控制，不是全文主发现。它检查 GSSR 的逐日 surge residual 在选定站点上是否保留合理的气压和风场信号。Newlyn、Brest、Aberdeen 和 Hoek van Holland 的 surge-pressure 相关为明显负值，年度最大增水日前后也出现低压与较强风速。",
                "这项分析不是在证明“风暴潮由气象驱动”这一常识，也不用于预测地形响应。Charleston 和 Hong Kong 的局地日尺度关系较弱，说明单点气象序列不能完整代表气旋路径、风向旋转、潮汐相位和海岸几何。它只支持把 GSSR 用作若干欧洲站点的过程背景。",
            ],
        ),
        (
            "7",
            "标准化连通地形图库与案例充分性检查",
            "FigS3_connectivity_gallery.png",
            [
                "图 7 用完全相同的 10 x 10 km 窗口、颜色和官方 mask 规则展示九个站点，用来检查 Figure 3 的三个原型是否只是孤立案例。",
                "图库显示连通响应在不同海岸间存在连续变化：有些站点形成大面积连通低地，有些只沿港池或潮汐水道形成狭窄连接，还有一些包含大量低于阈值但未与海洋种子连通的陆地。蓝色面积没有为了视觉平衡而放大。",
                "这些图仍然只是标准化地形分类。它们不包含传播时间、波浪、排水、防御或共同垂直基准，不能作为真实洪水范围使用。",
            ],
        ),
    ]

    html_sections: list[str] = []
    md_sections: list[str] = []

    toc_items = [
        ("abstract", "摘要"),
        ("background", "研究背景与目的"),
        ("terms", "术语、符号与公式说明"),
        ("data-methods", "数据与方法"),
        ("process", "研究过程"),
        ("results", "结果展示与图表解析"),
        ("discussion", "分析与讨论"),
        ("conclusion", "主要结论"),
        ("limits", "不足与展望"),
    ]
    toc_html = '<nav class="toc"><h2>目录</h2><ol>' + "".join(
        f'<li><a href="#{a}">{esc(t)}</a></li>' for a, t in toc_items
    ) + "</ol></nav>"
    toc_md = "## 目录\n\n" + "\n".join(f"- [{t}](#{a})" for a, t in toc_items)

    abstract = [
        "本报告与论文稿并行产出，目标不是替代论文，而是把研究背景、数据来源、方法链条、图表结果和不确定性解释整理成一份便于汇报、存档和发送给合作者阅读的中文科研报告。报告围绕一个核心问题展开：在 Northwest Europe（西北欧洲）沿海筛查中，storm-tide magnitude（风暴潮位幅值，即风暴增水与天文潮叠加后的极端总水位大小）能否代表 connected-lowland terrain response（连通低地地形响应，即低于指定地形阈值并与边界水体种子相连的低地区域响应）？",
        "当前结果显示，二者不能简单等同。68 站主样本的站点级相关为负，但沿海分区块 bootstrap 跨过零；top-20% 重叠也位于随机包络内。因此报告把结论限定为两个指标提供互补筛查信息，而不是宣称稳定负相关、错误排序或实际洪水风险差异。",
        "报告特别强调边界：当前 DeltaDTM 地形连通性主结果已接入 official DeltaDTM mask（官方 DeltaDTM 掩膜，即 mask_tiles.zip 中提供的 ocean、lake、river 和 clipped classes），使用 ocean class 1（海洋单元）和与 ocean 连通的 river class 3（河流单元）作为 ocean/tidal-water seed，只有 land class 0（陆地单元）进入低地分母，lake class 2（湖泊单元）、river/ocean 水体单元和 255 clipped cells（被裁剪或未解析单元）不作为候选陆地响应。boundary no-data seed proxy（边界无数据种子代理）只作为敏感性对照保留。七站 local-DTM cross-check 已完成，但 EGM2008、Ordnance Datum Newlyn 和 Normaal Amsterdams Peil 尚未转换到共同垂直参考，因此当前结果只能解释为透明、可审计的 elevation-product and datum sensitivity（高程产品与基准敏感性）。",
    ]
    html_sections.append(section_html("abstract", "摘要", paras_html(abstract)))
    md_sections.append(section_md("摘要", paras_md(abstract)))

    background = [
        "沿海洪水并不是单一水位数字造成的。现实中的沿海洪水由气象强迫、天文潮、海岸形态、局部地形、河流输入、排水系统和防洪工程共同决定。大尺度筛查研究常常必须简化问题，因为全球或区域尺度上不可能对每一个站点都立即运行高分辨率水动力模型。常见做法是按极端水位指标排序，例如某站点的 10 年一遇、50 年一遇或 100 年一遇水位。但这种做法会隐藏一个关键事实：水位很高不等于低地一定广泛连通，水位较低也不等于地形响应一定小。",
        "本研究的目的就是把这个被简化掉的环节重新拆开。第一步问：GSSR 和 COAST-RP 的水位指标是不是同一类物理量？第二步问：GSSR 重建的逐日风暴增水在若干站点上是否保留合理的气象过程信号？第三步问：把水位阈值投到 DeltaDTM 地形上之后，哪些低地真正通过当前连通性规则与边界水体相连？第四步问：水位排序和地形响应排序是否给出相同的站点优先级？",
        "这个研究问题的意义在于筛查优先级。如果管理者只看 storm-tide magnitude，可能优先关注总水位高的站点；如果同时看 connected-lowland response，优先级可能改变。报告不声称 connected terrain ranking 是真实洪水风险的唯一标准，而是说明它提供了水位指标之外的互补筛查信息。",
    ]
    html_sections.append(section_html("background", "研究背景与目的", paras_html(background)))
    md_sections.append(section_md("研究背景与目的", paras_md(background)))

    term_body = paras_html(
        [
            "<strong>Storm surge（风暴增水或风暴潮残差）</strong>：指由气压降低、风应力和风暴环流等气象强迫造成的非天文潮水位异常。它在观测总水位中通常表现为 residual（残差；即从总水位中扣除可预测天文潮后剩余的异常部分）。在方程意义上，可以把观测水位近似理解为“天文潮 + 气象残差 + 其他局地过程”，storm surge 位于气象残差这一项。引入它是为了单独分析风暴过程，而不是把潮汐和风暴效应混在一起。",
            "<strong>Storm tide（风暴潮位或风暴总潮位）</strong>：指 storm surge 与 astronomical tide（天文潮；由月球、太阳引潮力和地球自转共同导致的周期性海面升降）叠加后的总水位。它更接近实际岸边会遇到的总水位，但不等于单纯气象残差。COAST-RP 给出的主要是 storm-tide return level，因此在潮差大的地区会显著高于 GSSR 的 surge residual。",
            "<strong>Return period / RP10（重现期 / 10 年一遇）</strong>：RP10 不是说事件每 10 年必然发生一次，而是统计意义上年超越概率约为 1/10 的水位水平。它来自极值统计框架，用于把多年最大值或概率模型转化为可比较的设计水位。本报告使用 RP10 主要是因为它相对较少受有限记录长度影响。",
            "<strong>D10 = H10_COAST - H10_GSSR</strong>：D10 是 COAST-RP 10 年一遇风暴潮位与 GSSR 10 年一遇风暴增水之间的差值。它不是误差项，而是产品定义差异的诊断量。若 D10 很大，首先应想到 storm tide 包含天文潮，而 surge residual 不包含完整天文潮，而不是直接判断某个数据产品错误。",
            "<strong>h = max(0, η - z)</strong>：这是静态地形筛查中的候选水深公式。η（eta，给定的地形阈值或水位筛查面）减去 z（terrain elevation，地形高程）后，如果结果为正，表示该单元格低于阈值；如果为负，则记为 0。这里的 h 不是水动力模型中的真实流动水深，因为它没有模拟流速、摩擦、堤防、排水和时间传播。",
            "<strong>Connected-lowland response（连通低地响应）</strong>：指低于阈值且通过当前连通性规则与边界水体种子相连的低地单元格。它的物理直觉是：孤立洼地即使低于某个水位，也不应自动被判为海水可达；只有与海洋、河口或边界水体连通的低地才进入 connected metric。",
            "<strong>Spearman rho（斯皮尔曼等级相关系数）</strong>：衡量两个变量的排序是否单调一致。它不要求线性关系，适合本研究这种“站点排序”问题。rho 接近 +1 表示一个变量高时另一个也高，接近 -1 表示一个变量高时另一个低，接近 0 表示没有明显单调关系。",
            "<strong>Permutation test（置换检验）</strong>：把一个变量序列固定，随机打乱另一个变量，重复很多次，形成“如果二者没有关系会出现什么结果”的零分布。本报告使用双侧置换 p 值来评估 raw COAST-RP magnitude 与 raw terrain response 的相关是否偏离随机排列。",
        ]
    )
    html_sections.append(section_html("terms", "术语、符号与公式说明", term_body))
    md_sections.append(section_md("术语、符号与公式说明", paras_md([term_body])))

    data_methods_body = (
        paras_html(
            [
                "研究数据由四类开放数据构成：水位残差信号、总风暴潮位、气象过程诊断和地形筛查。它们不是同一个层面的数据，因此报告中的方法不是简单拼接，而是逐层追问：水位指标定义是否不同、气象过程是否合理、地形响应是否连通、排序优先级是否一致。",
                "地形部分使用 DeltaDTM elevation tiles（DeltaDTM 高程瓦片）和 official DeltaDTM mask（官方 DeltaDTM 掩膜，也就是 official mask_tiles.zip）。连通性算法现在把 ocean class 1 作为基础海洋种子，并只把与海洋连通的 river class 3 纳入 tidal-water access；只有 land class 0 进入低地分母，lake class 2、river/ocean 水体单元和 255 clipped cells 不作为候选陆地响应。这一点很关键，因为它减少了内陆湖泊、非潮汐河流、海面像元或裁剪边界被误认为陆地淹没响应的风险。",
                "为了让数据内容更清楚，报告把数据分为两层：第一层是“已经真实读取并用于计算的数据”，第二层是“投稿前仍需继续扩展或统一基准的数据”。前者足以支撑当前的 screening diagnostic（筛查诊断；即用于发现优先级不一致的透明指标），后者决定论文能否进一步升级为更强的 submission-ready manuscript（投稿级稿件；即数据审计链、复现包和方法边界都足够清楚的版本）。",
            ]
        )
        + table_html("表 1. 数据产品、变量和研究角色", *tables["data_products"])
        + table_html("表 2. 数据真实性、可复现性和解释边界", *tables["data_readiness"])
    )
    html_sections.append(section_html("data-methods", "数据与方法", data_methods_body))
    md_sections.append(
        section_md(
            "数据与方法",
            paras_md(
                [
                    "研究数据由四类开放数据构成：水位残差信号、总风暴潮位、气象过程诊断和地形筛查。它们不是同一个层面的数据，因此报告中的方法不是简单拼接，而是逐层追问：水位指标定义是否不同、气象过程是否合理、地形响应是否连通、排序优先级是否一致。",
                    "地形部分使用 DeltaDTM elevation tiles（DeltaDTM 高程瓦片）和 official DeltaDTM mask（官方 DeltaDTM 掩膜，也就是 official mask_tiles.zip）。连通性算法现在把 ocean class 1 作为基础海洋种子，并只把与海洋连通的 river class 3 纳入 tidal-water access；只有 land class 0 进入低地分母，lake class 2、river/ocean 水体单元和 255 clipped cells 不作为候选陆地响应。这一点很关键，因为它减少了内陆湖泊、非潮汐河流、海面像元或裁剪边界被误认为陆地淹没响应的风险。",
                    "为了让数据内容更清楚，报告把数据分为两层：第一层是“已经真实读取并用于计算的数据”，第二层是“投稿前仍需继续扩展或统一基准的数据”。前者足以支撑当前的 screening diagnostic（筛查诊断；即用于发现优先级不一致的透明指标），后者决定论文能否进一步升级为更强的 submission-ready manuscript（投稿级稿件；即数据审计链、复现包和方法边界都足够清楚的版本）。",
                ]
            )
            + "\n\n"
            + table_md("表 1. 数据产品、变量和研究角色", *tables["data_products"])
            + "\n\n"
            + table_md("表 2. 数据真实性、可复现性和解释边界", *tables["data_readiness"]),
        )
    )

    process_body = (
        paras_html(
            [
                "研究过程可以理解为从“水位数字”走向“地形响应”的审计链。第一步整理八个 focal tide-gauge sites（重点验潮站点），用于检查 GSSR 与 COAST-RP 的产品定义差异。第二步加入潮差背景，判断 D10 是否主要由潮汐环境解释。第三步对 GSSR 逐日风暴增水与气压、风速、降水做过程一致性检查，确认它在若干欧洲温带风暴站点上保留合理气象信号。",
                "第四步进入地形筛查：对 Northwest Europe 的空间合格站点建立约 10 x 10 km 固定窗口，计算低于 2 m 阈值且与官方 ocean/tidal-water seed 相连的低地比例和面积。第五步将 COAST-RP RP10 排名与 connected-terrain response 排名对照，并通过置换检验、top-k overlap envelope、不同样本定义和 fraction/area 双指标来避免过度解释。",
                "最后一步是图件重构。早期 Figure 3 同时放地图、曲线和面积/比例摘要，读者难以抓住主语。新版 Figure 3 改成 3 x 3 evidence grid：每一列代表一个筛查 archetype，每一行代表一种证据层。这一改动使图件从“看起来哪里蓝多”转为“解释水位排名与地形排名为什么会分离”。",
            ]
        )
    )
    html_sections.append(section_html("process", "研究过程", process_body))
    md_sections.append(section_md("研究过程", paras_md([
        "研究过程可以理解为从“水位数字”走向“地形响应”的审计链。第一步整理八个 focal tide-gauge sites（重点验潮站点），用于检查 GSSR 与 COAST-RP 的产品定义差异。第二步加入潮差背景，判断 D10 是否主要由潮汐环境解释。第三步对 GSSR 逐日风暴增水与气压、风速、降水做过程一致性检查，确认它在若干欧洲温带风暴站点上保留合理气象信号。",
        "第四步进入地形筛查：对 Northwest Europe 的空间合格站点建立约 10 x 10 km 固定窗口，计算低于 2 m 阈值且与官方 ocean/tidal-water seed 相连的低地比例和面积。第五步将 COAST-RP RP10 排名与 connected-terrain response 排名对照，并通过置换检验、top-k overlap envelope、不同样本定义和 fraction/area 双指标来避免过度解释。",
        "最后一步是图件重构。早期 Figure 3 同时放地图、曲线和面积/比例摘要，读者难以抓住主语。新版 Figure 3 改成 3 x 3 evidence grid：每一列代表一个筛查 archetype，每一行代表一种证据层。这一改动使图件从“看起来哪里蓝多”转为“解释水位排名与地形排名为什么会分离”。",
    ])))

    results_html_parts = []
    results_md_parts = []
    for fig in figures:
        results_html_parts.append(figure_html(*fig))
        results_md_parts.append(figure_md(*fig))
        if fig[0] == "2":
            results_html_parts.append(table_html("表 3. 八个重点站点的水位指标与 D10 诊断", *tables["water"]))
            results_md_parts.append(table_md("表 3. 八个重点站点的水位指标与 D10 诊断", *tables["water"]))
        if fig[0] == "3":
            results_html_parts.append(table_html("表 4. Figure 3 三类 archetype 的数值证据", *tables["archetypes"]))
            results_md_parts.append(table_md("表 4. Figure 3 三类 archetype 的数值证据", *tables["archetypes"]))
        if fig[0] == "4":
            results_html_parts.append(table_html("表 5. 区域样本水位排序与地形响应排序诊断", *tables["rank"]))
            results_md_parts.append(table_md("表 5. 区域样本水位排序与地形响应排序诊断", *tables["rank"]))
        if fig[0] == "5":
            results_html_parts.append(table_html("表 6. GSSR 重建风暴增水与气象变量的过程一致性检查", *tables["drivers"]))
            results_md_parts.append(table_md("表 6. GSSR 重建风暴增水与气象变量的过程一致性检查", *tables["drivers"]))
        if fig[0] == "7":
            results_html_parts.append(table_html("表 7. 本地 DTM 交叉验证结果", *tables["local_validation"]))
            results_md_parts.append(table_md("表 7. 本地 DTM 交叉验证结果", *tables["local_validation"]))
    html_sections.append(section_html("results", "结果展示与图表解析", "\n".join(results_html_parts)))
    md_sections.append(section_md("结果展示与图表解析", "\n\n".join(results_md_parts)))

    discussion = [
        "综合所有结果，报告最重要的判断是：水位指标和地形响应指标提供的是互补信息，而不是可以互相替代的同一指标。GSSR 与 COAST-RP 的差异首先来自物理定义；当潮汐很强时，总风暴潮位自然会显著高于风暴残差水位。真正需要进一步筛查的是：总水位高的地方是否同时存在大面积、低高程、与水体连通的低地。",
        "Figure 2 和 Figure 3 共同回答这个问题。Figure 2 给出 68 站主样本并辅以 74 站距离敏感性，Figure 3 用三个按规则选择的案例解释指标差异。主样本 fraction rho=-0.36、area rho=-0.33，但六分区块区间均跨零，说明效应方向仍受空间聚集影响。Figure 4 进一步说明地形排序受高程产品和垂向基准影响。",
        "这里的 connected-terrain response 仍是静态筛查量，不是动力洪水模拟。Cotrim et al. (2026) 的泛欧洲研究显式处理风暴过程、防御和水动力传播；本研究有意停留在更早的筛选阶段，用于识别哪些地点值得进入这种高成本模拟，而不能替代后者。",
        "这里需要避免两个过度解释。第一，不能把 top-set mismatch 当作超过随机期望的强统计证据，因为随机列表本来也可能有较低重叠。第二，不能把 connected-terrain ranking 当作真实洪水风险基准，因为当前方法不包含堤防、排水、波浪、河流、摩擦和水动力传播。更稳健的表述是：storm-tide magnitude 与 connected-terrain response 会给出不同筛查优先级，二者应该同时报告。",
    ]
    html_sections.append(section_html("discussion", "分析与讨论", paras_html(discussion)))
    md_sections.append(section_md("分析与讨论", paras_md(discussion)))

    conclusions = [
        "第一，GSSR 的风暴残差水位和 COAST-RP 的总风暴潮位不是同一物理量。第二，来源已核实的潮汐子集中，D10 与潮差高度相关。第三，68 站主样本显示站点级负相关，但沿海分区块区间跨零，不能声称稳定的区域负相关。",
        "第四，Sheerness、Newport 和 Den Helder 是按公开规则选择的三个地形筛查案例；其中 Sheerness 和 Den Helder 的本地 DTM 类别改变。第五，地形指标必须同时报告比例、面积、匹配距离、海洋种子状态和地形产品敏感性。",
        "最终结论是：沿海洪水筛查不应只按极端水位幅值排序。更透明的筛查框架应同时报告水位定义、气象过程一致性、地形连通响应、面积/比例差异和关键不确定性。",
    ]
    html_sections.append(section_html("conclusion", "主要结论", paras_html(conclusions)))
    md_sections.append(section_md("主要结论", paras_md(conclusions)))

    limits_body = (
        paras_html(
            [
                "当前报告已经能作为内部汇报、归档和合作者沟通材料使用，但若目标是直接投稿 Communications Earth & Environment，还需要继续补强。最重要的不是再堆图，而是补齐方法审计链中仍缺的环节：七站 local-DTM cross-check 的垂向基准统一、潮汐元数据补齐，以及复现包的 DOI 或 private reviewer link。官方 mask-aware rerun、七站地形产品/基准敏感性检查和本地复现包已完成。",
                "下面的验收条件把“还需要做什么”具体化。完成这些条件后，论文的证据链会更接近正式投稿要求：既能说明新认识，也能证明数据处理和不确定性追踪足够透明。",
            ]
        )
        + table_html("表 8. 投稿前不足、补充目标和验收条件", *tables["limitations"])
        + table_html("表 9. 下一轮论文优化的具体目标", *tables["target"])
    )
    html_sections.append(section_html("limits", "不足与展望", limits_body))
    md_sections.append(
        section_md(
            "不足与展望",
            paras_md(
                [
                    "当前报告已经能作为内部汇报、归档和合作者沟通材料使用，但若目标是直接投稿 Communications Earth & Environment，还需要继续补强。最重要的不是再堆图，而是补齐方法审计链中仍缺的环节：七站 local-DTM cross-check 的垂向基准统一、潮汐元数据补齐，以及复现包的 DOI 或 private reviewer link。官方 mask-aware rerun、七站地形产品/基准敏感性检查和本地复现包已完成。",
                    "下面的验收条件把“还需要做什么”具体化。完成这些条件后，论文的证据链会更接近正式投稿要求：既能说明新认识，也能证明数据处理和不确定性追踪足够透明。",
                ]
            )
            + "\n\n"
            + table_md("表 8. 投稿前不足、补充目标和验收条件", *tables["limitations"])
            + "\n\n"
            + table_md("表 9. 下一轮论文优化的具体目标", *tables["target"]),
        )
    )

    html_doc = build_html_document(toc_html + "\n".join(html_sections))
    md_doc = "\n\n".join(
        [
            "# 沿海洪水筛查中风暴潮位幅值与连通低地响应的差异：科研报告",
            f"生成时间：{GENERATED_AT}",
            toc_md,
            *md_sections,
        ]
    )
    return html_doc, md_doc


def build_html_document(body: str) -> str:
    css = """
:root {
  --bg: #eef2f4;
  --paper: #ffffff;
  --ink: #17202a;
  --muted: #526170;
  --line: #d8dee6;
  --soft: #f3f7fa;
  --accent: #0f6b73;
  --accent2: #8a5a23;
  --blue: #0ea5e9;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
  line-height: 1.75;
  font-size: 16px;
}
.page {
  max-width: 1120px;
  margin: 0 auto;
  background: var(--paper);
  min-height: 100vh;
  padding: 54px 70px 82px;
  box-shadow: 0 18px 44px rgba(20, 30, 45, 0.14);
}
.cover {
  padding: 34px 0 36px;
  border-bottom: 4px solid var(--accent);
  margin-bottom: 26px;
}
.kicker {
  color: var(--accent);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 14px;
}
h1 {
  margin: 0 0 16px;
  font-size: 2.35rem;
  line-height: 1.18;
  letter-spacing: 0;
}
.subtitle {
  color: var(--muted);
  font-size: 1.05rem;
  max-width: 860px;
}
.meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 24px;
}
.meta div, .callout {
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
}
.meta strong {
  display: block;
  color: var(--accent);
  margin-bottom: 4px;
}
.toc {
  margin: 26px 0 32px;
  padding: 18px 22px;
  background: #fbfcfd;
  border: 1px solid var(--line);
  border-radius: 8px;
}
.toc h2 { margin-top: 0; border: 0; padding: 0; }
.toc a { color: var(--accent); text-decoration: none; }
h2 {
  margin: 42px 0 14px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--line);
  color: #0f2935;
  font-size: 1.55rem;
}
h3 {
  margin: 28px 0 10px;
  color: var(--accent);
  font-size: 1.18rem;
}
p {
  margin: 0 0 13px;
  text-align: justify;
}
strong { font-weight: 700; }
.figure-block {
  margin: 22px 0 12px;
  padding: 14px;
  border: 1px solid var(--line);
  background: #fbfcfd;
  border-radius: 8px;
  break-inside: avoid;
}
.figure-block figcaption {
  margin: 0 0 10px;
  font-weight: 700;
  color: #0f2935;
}
.figure-block img {
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid #e4e9ef;
  background: #fff;
}
.figure-explain {
  margin: 0 0 26px;
  padding: 14px 18px;
  border-left: 4px solid var(--blue);
  background: #f8fbfd;
}
.table-block {
  margin: 22px 0 30px;
  break-inside: avoid;
}
.table-block figcaption {
  margin-bottom: 8px;
  font-weight: 700;
}
.scroll-table { overflow-x: auto; width: 100%; }
table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  font-size: 0.9rem;
}
th, td {
  border: 1px solid var(--line);
  padding: 8px 9px;
  vertical-align: top;
  text-align: left;
}
th {
  background: #eaf2f5;
  color: #102733;
}
tbody tr:nth-child(even) td { background: #fafafa; }
.table-note {
  color: var(--muted);
  font-size: 0.92rem;
  margin-top: 8px;
}
@media print {
  body { background: #fff; }
  .page { box-shadow: none; padding: 30px 40px; max-width: none; }
  .figure-block, .table-block { break-inside: avoid; }
  .scroll-table { overflow: visible; }
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
@media (max-width: 760px) {
  .page { padding: 28px 20px 44px; }
  h1 { font-size: 1.75rem; }
  .meta { grid-template-columns: 1fr; }
}
"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>沿海洪水筛查科研报告</title>
  <style>
{css}
  </style>
</head>
<body>
  <main class="page">
    <section class="cover">
      <div class="kicker">Research Report</div>
      <h1>沿海洪水筛查中风暴潮位幅值与连通低地响应的差异</h1>
      <p class="subtitle">一份与论文并行的中文科研报告：完整梳理研究背景、研究过程、数据与方法、图表结果、分析讨论、结论和投稿前补强目标。</p>
      <div class="meta">
        <div><strong>研究区域</strong>Northwest Europe（西北欧洲）及八个重点验潮站点</div>
        <div><strong>核心问题</strong>水位排序能否代表连通低地地形响应排序</div>
        <div><strong>生成时间</strong>{esc(GENERATED_AT)}</div>
      </div>
    </section>
    {body}
  </main>
</body>
</html>
"""


def write_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = next((p for p in CHROME_CANDIDATES if p.exists()), None)
    if browser is None:
        print("WARN: Chrome/Edge not found; PDF not generated")
        return
    subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            str(html_path),
        ],
        check=True,
        cwd=ROOT,
    )


def main() -> int:
    html_doc, md_doc = build_report()
    OUT_HTML.write_text(html_doc, encoding="utf-8")
    OUT_MD.write_text(md_doc, encoding="utf-8")
    write_pdf(OUT_HTML.resolve(), OUT_PDF)

    FINAL_HTML.write_text(html_doc, encoding="utf-8")
    FINAL_MD.write_text(md_doc, encoding="utf-8")
    if OUT_PDF.exists():
        FINAL_PDF.write_bytes(OUT_PDF.read_bytes())

    print(f"Wrote {OUT_HTML}")
    print(f"Wrote {OUT_MD}")
    if OUT_PDF.exists():
        print(f"Wrote {OUT_PDF}")
    print(f"Wrote {FINAL_HTML}")
    print(f"Wrote {FINAL_MD}")
    if FINAL_PDF.exists():
        print(f"Wrote {FINAL_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
