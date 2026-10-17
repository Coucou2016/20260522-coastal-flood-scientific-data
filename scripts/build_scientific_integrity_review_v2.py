#!/usr/bin/env python3
"""Build the internal scientific-consistency audit and evidence log."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from build_standalone_paper import build_html, chrome_executable


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"
MANUSCRIPT = ROOT / "manuscript"
OUT_MD = MANUSCRIPT / "internal_scientific_consistency_audit.md"
OUT_HTML = MANUSCRIPT / "internal_scientific_consistency_audit.html"
OUT_PDF = MANUSCRIPT / "internal_scientific_consistency_audit.pdf"
LEGACY_OUTPUTS = {
    OUT_MD: MANUSCRIPT / "scientific_integrity_review.md",
    OUT_HTML: MANUSCRIPT / "scientific_integrity_review.html",
    OUT_PDF: MANUSCRIPT / "scientific_integrity_review.pdf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def printable(value: object) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.6g}"
    return str(value).replace("\n", " ").replace("|", "\\|")


def table(frame: pd.DataFrame) -> str:
    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "|" + "|".join(["---"] * len(frame.columns)) + "|",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(printable(v) for v in row) + " |")
    return "\n".join(lines)


def invariant_audit() -> tuple[pd.DataFrame, list[str]]:
    detail = pd.read_csv(SOURCE / "Terrain_robustness_grid_74stations.csv")
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    blocks = pd.read_csv(ROOT / "config" / "coastal_spatial_blocks_v2.csv")
    threshold = pd.read_csv(SOURCE / "Threshold_response_0_3m_68stations.csv")
    topology = pd.read_csv(SOURCE / "Water_land_topology_sensitivity_68stations.csv")
    coastline = pd.read_csv(SOURCE / "Coastline_oriented_window_68stations.csv")
    decision = pd.read_csv(SOURCE / "Decision_instability_station_metrics.csv")
    match_review = pd.read_csv(SOURCE / "COAST_RP_same_coast_match_audit.csv")

    valid = detail.dropna(subset=["below_area_km2", "connected_area_km2"]).copy()
    identity_error = np.abs(
        valid["connected_reference_land_pct"]
        - valid["below_reference_land_pct"] * valid["conditional_connectivity_pct"] / 100.0
    )
    zero = valid[valid["elevation_offset_m"].eq(0.0)]
    keys = ["station_id", "window_width_km", "eta_m", "seed_rule", "elevation_offset_m"]
    pair = zero.pivot_table(index=keys, columns="neighbours", values="connected_area_km2")
    known_blocks = blocks.set_index("station_id")
    known_ok = (
        known_blocks.loc["fishguard-p055-uk", "coastal_basin"] == "Celtic-Irish-Sea"
        and known_blocks.loc["holyhead-p054-uk", "coastal_basin"] == "Irish-Sea"
        and known_blocks.loc["cuxhaven-germany", "coastal_basin"] == "German-Bight"
        and known_blocks.loc["tregde-006-norway", "coastal_basin"] == "Skagerrak"
    )
    checks = [
        ("Robustness-grid rows", len(detail) == 2960, len(detail), "74 stations x 40 configurations"),
        ("Primary stations", len(primary) == 68 and primary["station_id"].nunique() == 68, len(primary), "68 unique matched stations"),
        ("Explicit spatial-block coverage", blocks["station_id"].nunique() == 74 and not blocks.filter(regex=r"spatial_block_").isna().any().any(), blocks["station_id"].nunique(), "74 configured candidates, no missing block"),
        ("Known coastline corrections", bool(known_ok), bool(known_ok), "Fishguard/Holyhead/Cuxhaven/Tregde reviewed mappings"),
        ("Connected area <= below-threshold area", bool((valid["connected_area_km2"] <= valid["below_area_km2"] + 1e-9).all()), int((valid["connected_area_km2"] > valid["below_area_km2"] + 1e-9).sum()), "violations"),
        ("Four-neighbour <= eight-neighbour", bool((pair[4] <= pair[8] + 1e-9).all()), int((pair[4] > pair[8] + 1e-9).sum()), "violations under identical configuration"),
        ("Metric decomposition identity", float(identity_error.max()) < 1e-10, float(identity_error.max()), "maximum absolute percentage-point error"),
        ("Official class 255 in primary windows", int(primary["official_clipped_255_cells"].sum()) == 0, int(primary["official_clipped_255_cells"].sum()), "cells"),
        ("Outside-support sentinel distinct", int(primary["mask_outside_support_cells"].sum()) == 3320, int(primary["mask_outside_support_cells"].sum()), "class-254 cells, excluded"),
        ("Threshold grid complete", len(threshold) == 68 * 13, len(threshold), "68 stations x 13 thresholds from 0 to 3 m"),
        ("Water/land topology grid complete", len(topology) == 68 * 4, len(topology), "68 stations x four explicit topology combinations"),
        ("Coastline-window sensitivity complete", coastline["station_id"].nunique() == 68, coastline["station_id"].nunique(), "stations"),
        ("Decision audit complete", decision["station_id"].nunique() == 68, decision["station_id"].nunique(), "stations"),
        (
            "Coordinate match review complete",
            match_review.loc[
                match_review["included_in_primary_match_sample"].astype(bool),
                "coordinate_connector_review_pass",
            ].astype(bool).all(),
            int(
                match_review.loc[
                    match_review["included_in_primary_match_sample"].astype(bool),
                    "coordinate_connector_review_pass",
                ].astype(bool).sum()
            ),
            "68 included coordinate-plausible pairs; six distance-excluded candidates are not counted",
        ),
    ]
    rows = pd.DataFrame(checks, columns=["Check", "Pass", "Observed", "Criterion or meaning"])
    return rows, rows.loc[~rows["Pass"], "Check"].tolist()


def hash_manifest() -> pd.DataFrame:
    paths = [
        ROOT / "data" / "raw" / "coast_rp" / "COAST-RP.zip",
        ROOT / "data" / "raw" / "gssr" / "metadata" / "eraint.geojson",
        ROOT / "data" / "raw" / "deltadtm" / "index" / "README.md",
        ROOT / "data" / "raw" / "deltadtm" / "zips" / "mask_tiles.zip",
        ROOT / "config" / "coastal_spatial_blocks_v2.csv",
        ROOT / "data" / "upstream_raw_manifest.csv",
        ROOT / "data" / "derived_input_manifest.json",
        SOURCE / "Primary_terrain_components_68stations.csv",
        SOURCE / "Terrain_robustness_grid_74stations.csv",
        SOURCE / "Return_period_sensitivity.csv",
        SOURCE / "Spatial_block_bootstrap_intervals.csv",
        SOURCE / "Topk_spatial_null_curves.csv",
        SOURCE / "Water_land_topology_sensitivity_68stations.csv",
        SOURCE / "Threshold_response_0_3m_68stations.csv",
        SOURCE / "Coastline_oriented_window_68stations.csv",
        SOURCE / "Decision_instability_station_metrics.csv",
        SOURCE / "COAST_RP_same_coast_match_audit.csv",
        SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv",
        ROOT / "scripts" / "reproduce.py",
        ROOT / "scripts" / "rebuild_frozen_primary_analysis.py",
        ROOT / "scripts" / "add_external_review_diagnostics.py",
        ROOT / "scripts" / "make_major_revision_figures.py",
        ROOT / "tests" / "test_scientific_contracts.py",
    ]
    paths.extend(sorted((ROOT / "src" / "coastal_screening").glob("*.py")))
    paths.extend(sorted((ROOT / "data" / "raw" / "local_dtm").glob("*_local_dtm_10m.tif")))
    rows = []
    for path in paths:
        if path.exists():
            rows.append({"File": path.relative_to(ROOT).as_posix(), "Bytes": path.stat().st_size, "SHA-256": sha256(path)})
    output = pd.DataFrame(rows)
    output.to_csv(SOURCE / "Major_revision_evidence_sha256.csv", index=False)
    return output


def figure_audit() -> pd.DataFrame:
    figure_sources = {
        "Fig1_process_terrain_design.png": "Primary_station_spatial_blocks.csv; Primary_sample_flow.csv; coastal_spatial_blocks_v2.csv",
        "Fig2_regional_screening_agreement.png": "Primary_terrain_components_68stations.csv; Return_period_sensitivity.csv; Spatial_block_bootstrap_intervals.csv; Topk_spatial_null_curves.csv; Decision_instability_station_metrics.csv",
        "Fig3_connected_terrain_contrasts.png": "Fig3_predefined_site_selection.csv; Fig3_threshold_response_source.csv; frozen DeltaDTM windows",
        "Fig4_metric_decomposition_robustness.png": "Primary_terrain_components_68stations.csv; Denominator_adjusted_associations.csv; Water_land_topology_summary.csv; Rank_robustness_one_at_a_time.csv; Threshold_integrated_associations.csv; Coastline_window_sensitivity_summary.csv",
        "FigS1_water_level_definition.png": "Fig2_water_level_divergence_with_uncertainty.csv; source-verified tidal metadata",
        "FigS2_process_coherence.png": "Fig3_driver_correlations.csv; event-composite source tables",
        "FigS3_connectivity_gallery.png": "Primary_terrain_components_68stations.csv; frozen DeltaDTM windows",
        "FigS4_elevation_product_datum_sensitivity.png": "TableS_local_dtm_product_datum_crosscheck.csv",
        "FigS5_coastrp_match_audit.png": "Match_distance_audit_74stations.csv; COAST_RP_same_coast_match_audit.csv",
    }
    rows = []
    for name, sources in figure_sources.items():
        path = ROOT / "figures" / "main" / name
        with Image.open(path) as img:
            width, height = img.size
            dpi = img.info.get("dpi", ("not recorded", "not recorded"))
        rows.append({
            "Figure": name,
            "Pixels": f"{width} x {height}",
            "Embedded DPI": f"{dpi[0]:.0f}" if isinstance(dpi[0], (int, float)) else str(dpi[0]),
            "Source data": sources,
            "Visual/data QA": "original-resolution inspection required after each final rebuild; no cell enlargement",
        })
    return pd.DataFrame(rows)


def build_markdown() -> str:
    checks, failures = invariant_audit()
    hashes = hash_manifest()
    figures = figure_audit()
    product = pd.read_csv(SOURCE / "DeltaDTM_v1_1_product_version_audit.csv")
    rp = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    block = pd.read_csv(SOURCE / "Spatial_block_bootstrap_intervals.csv")
    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    topology = pd.read_csv(SOURCE / "Water_land_topology_summary.csv")
    threshold = pd.read_csv(SOURCE / "Threshold_integrated_associations.csv")
    coastline = pd.read_csv(SOURCE / "Coastline_window_sensitivity_summary.csv")
    decision = pd.read_csv(SOURCE / "Decision_instability_station_metrics.csv")
    matching = pd.read_csv(SOURCE / "Match_distance_audit_74stations.csv")
    match_review = pd.read_csv(SOURCE / "COAST_RP_same_coast_match_audit.csv")
    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")

    spatial = rp[
        rp["return_period_years"].eq(10)
        & rp["terrain_metric_label"].isin(["lowland_prevalence", "conditional_connectivity", "connected_lowland_share", "connected_area"])
    ][[
        "terrain_metric", "terrain_metric_label", "block_scale_km", "n_spatial_blocks", "spearman", "kendall",
        "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p",
        "top20_n", "top20_observed_overlap", "sector_stratified_top20_null_q025",
        "sector_stratified_top20_null_q975", "sector_stratified_top20_lower_tail_p",
    ]].merge(
        block[["terrain_metric", "block_scale_km", "spearman_sector_bootstrap_p025", "spearman_sector_bootstrap_p975"]],
        on=["terrain_metric", "block_scale_km"], how="left",
    ).drop(columns="terrain_metric")
    top20 = topk[topk["top_share_pct"].eq(20)][[
        "block_scale_km", "n_spatial_blocks", "top_n", "observed_overlap",
        "sector_stratified_null_q025", "sector_stratified_null_q975", "sector_stratified_lower_tail_p",
    ]]
    decision_summary = pd.DataFrame([
        ("Median absolute rank displacement", float(decision["absolute_rank_displacement"].median())),
        ("Maximum absolute rank displacement", int(decision["absolute_rank_displacement"].max())),
        ("Always terrain Top-20% across eligible configurations", int((decision["terrain_top20_selection_frequency"] == 1).sum())),
        ("Never terrain Top-20% across eligible configurations", int((decision["terrain_top20_selection_frequency"] == 0).sum())),
        ("Pareto-nondominated sites", int(decision["pareto_nondominated"].astype(bool).sum())),
    ], columns=["Decision diagnostic", "Observed"])
    local_summary = local[[
        "station", "delta_connected_2m_reference_land_pct", "local_connected_2m_reference_land_pct",
        "delta_connected_2m_area_km2", "local_connected_2m_area_km2",
        "connected_pixel_iou_after_reprojection", "local_dtm_vertical_datum_note",
    ]]
    residual = pd.DataFrame([
        ("垂向基准统一", "未完成", "DeltaDTM/ODN/NAP 尚未转换到共同 local-MSL reference；S4 只能解释为产品、基准、分辨率和服务重采样的联合敏感性。"),
        ("独立真实洪水基准", "未完成", "检索到的 2026 European total-water-level storms 数据仍是水位过程，不是站点级动态淹没真值；没有用它伪装外部验证。"),
        ("空间块定义", "部分完成", "74 站已由版本化表显式审阅并修正已知错分；100/150/250 km 标签是近似沿岸连续分组，不是精确测得的 shoreline distance。"),
        ("COAST-RP 同岸环境", "部分完成", "坐标和地图审阅通过 68 对匹配并标记 11 个河口/复杂岸线点；这不证明同一沿岸水动力环境，仍需 coastline component/alongshore-distance 数据。"),
        ("独立站点框架", "受限", "68 站来自 GSSR metadata inventory，且英国与爱尔兰占 45 站，不能外推为均匀欧洲海岸样本。"),
        ("公开复现", "计算链已通过", "full 模式已核验 278 个上游文件并完成 raw-to-paper 重建；最终审稿 ZIP 的 clean-room 结果由包外 reviewer_archive_validation_receipt.json 独立记录。"),
        ("作者元数据与 DOI", "待补充", "authors、affiliations、funding、contributions 及正式归档 DOI 尚不能由代码推断。"),
    ], columns=["Risk", "Status", "Evidence boundary"])

    excluded = matching.loc[~matching["included_in_primary_match_sample"].astype(bool), [
        "station", "recomputed_match_dist_km", "coast_rp_source_lon", "coast_rp_source_lat", "match_exclusion_reason"
    ]]
    status = "全部通过" if not failures else "存在失败项: " + ", ".join(failures)
    return f"""# 科学真实性、准确性与完整性内部审查文档

**对应稿件：** *Limited concordance between storm-tide magnitude and standardized connected-lowland screening across Northwest Europe*

**审查定位：** code-data-table-figure-manuscript 穿透式内部一致性审计，不冒充独立同行评议

**自动约束状态：** {status}

## 1. 审查结论

本轮首先修复会改变空间推断的实现问题，而不是先润色结论。旧 `coastal_sector()` 以经纬度阈值给站点分区，曾把 Fishguard、Holyhead、Cuxhaven 和 Tregde 等站放入不合理海区；它已从统计路径移除。现在 74 个候选站通过 `config/coastal_spatial_blocks_v2.csv` 显式连接到 coastal basin 以及 100、150、250 km 三套版本化空间块。块内 restricted permutation 的双侧概率也改为经验双尾，不再假定受限零分布以 0 为中心。

当前可确认的是：68 站主表、2,960 条地形稳健性记录、三套空间统计、图件和文稿由同一 source-table 体系生成；面积、拓扑和指标分解契约通过。当前证据支持的是 limited rank concordance 和 decision-level disagreement。它不支持“显著负相关定律”“错配异常大于空间随机”“connected terrain 是真实洪水排序”或“二指标组合已经提高预测能力”。

## 2. P0 问题及处理证据

1. **空间错分：已修复并重算。** 经纬度 `if` 规则不再参与推断。地图、块内置换、分块调整关联、块重采样、leave-one-block-out 和 Top-k null 统一读取版本化配置；已知错误映射由自动测试固定。
2. **受限置换双侧概率：已修复并重算。** 当前概率是 `2 * min(P(null <= observed), P(null >= observed))` 的加一校正经验双尾值，允许空间受限零分布偏离 0。
3. **复现入口：已分层。** `python scripts/reproduce.py --mode derived` 从带 SHA-256 的紧凑派生输入重建论文包；`--mode full` 从本地上游原始产品开始。README 不再把 derived rebuild 描述成 raw-to-paper。
4. **审稿包依赖闭包：已重构并设独立门禁。** `src/`、全部 Python 脚本、测试、配置及 figure-source tables 由目录规则纳入，不再依赖易漏项的脚本白名单；最终 ZIP 在包外以临时目录、全新虚拟环境和九个确定性输出哈希独立验收。
5. **运行环境：已补齐。** `pyproject.toml` 声明 xarray、netCDF4、rasterio、pyproj、SciencePlots 与 pytest 等实际依赖；`environment-lock.yml` 记录本轮平台版本。系统全局 pytest 插件可能冲突，因此正式门禁固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。

## 3. 数据产品与 mask 审计

{table(product)}

主流程只允许官方 class 0 land 进入 represented-land denominator；class 1 ocean 是基础 marine seed，class 3 river 仅在与 ocean component 连通时参与水体种子，class 2 lake、class 255 和窗口外 class 254 均排除。这里的 `connected` 是 raster component 分类，不是水动力连通、洪水历时或防洪工程失效判断。

## 4. 自动科学约束

{table(checks)}

这些检查能证明代码输出满足自身声明的集合、面积与拓扑关系，也能阻止已知回归。它们不能证明输入 DEM 没有系统误差，不能替代共同垂向基准，更不等同于独立洪水观测验证。

## 5. 空间统计证据边界

{table(spatial)}

100、150 和 250 km 方案分别包含 42、34 和 25 个近似沿岸连续块。RP10 与 connected-land share 的原始 Spearman rho 为 -0.333；块内经验双侧 p 随分块尺度为 0.135、0.025 和 0.012，而保持地理组成的块重采样范围为 [-0.551,-0.027]、[-0.567,-0.027] 和 [-0.579,0.016]。两类结果不矛盾：前者问同一组空间块内随机重排后是否常见，后者问换一组被抽到的地理块时估计是否稳定。250 km 范围触及 0，因此稿件不建立空间稳定的负相关定律。

### Top-k 空间零模型

{table(top20)}

Top-20% 两表各 14 站，实际只重合 1 站，但该值在三套空间零模型包络内。1/14 是筛查决策的描述性恢复度，不是“低于随机”的显著性证据。

## 6. 指标构念与决策稳定性

connected-land share 被显式拆为 lowland prevalence 乘以 conditional connectivity。主结果中前者与 storm tide 的 rho 为 -0.309，后者为 +0.105；所以低 composite 值不能一概解释为“海洋连通差”。

{table(decision_summary)}

绝对排名位移中位数为 26。地形 Top-20% 选择频率来自 40 个预设配置中的可用子集，它度量方法选择下的清单稳定性，不是洪水概率。四象限和 Pareto 结果用于说明 costly second-stage modelling 的候选清单如何变化，不把 terrain ranking 当作真值。

### 水体/陆地邻域、阈值与窗口

{table(topology)}

{table(threshold)}

{table(coastline)}

主流程是 water-8 / land-4。严格 water-4 / land-4 与主流程地形排名 rho 为 0.86、Top-20% 改变 4 个成员。0-3 m 阈值积分和近似沿岸窗口仍给出有限一致性，但沿岸窗口与方窗仅重合 11/14 个 terrain Top-20% 成员。这些结果支持区域结论的方向，也明确暴露单站优先级的方法依赖性。

## 7. COAST-RP 匹配审计

68 个纳入站点最大 great-circle 匹配距离为 {float(matching.loc[matching['included_in_primary_match_sample'].astype(bool), 'recomputed_match_dist_km'].max()):.3f} km；以下 6 站因超过 6 km 预设规则被排除：

{table(excluded)}

坐标级审阅对 {len(match_review)} 个纳入匹配全部给出“地理位置可接受”，其中 {int(match_review['estuary_or_embayment_flag'].astype(bool).sum())} 个标记为河口或半封闭海湾。该审阅没有 coastline component 或沿岸路径距离，字段明确写为 `opposite_bank_flag = not_determined_from_coordinate_review`，不能升级为 hydrodynamic equivalence。

## 8. national/local DTM product-and-datum cross-check

{table(local_summary)}

七站对照记录共同 target grid、transform、mask resampling 和文件 SHA-256，但 DeltaDTM、Ordnance Datum Newlyn 与 Normaal Amsterdams Peil 未统一。因此差异同时包含高程产品、垂向基准、水平分辨率和 provider WCS 重采样；本文只称 diagnostic product-and-datum sensitivity，不称 validation，也不把七站变化比例外推到 68 站。

## 9. 图件来源与视觉检查

{table(figures)}

Figure 3 的三站由机器可读规则选出。低值站 inset 只放大原像元位置，不增加 connected 面积；9 子图分别展示分类、指标分解和实算阈值曲线。每次最终重建后仍须以原始分辨率检查标签遮挡、图例、字体和颜色，并把像素层面的视觉判断与 source-table 数值核对分开记录。

## 10. 关键文件 SHA-256

{table(hashes)}

大体积上游数据不能凭文件名认定相同。full 模式在计算前核验 `data/upstream_raw_manifest.csv`；derived 模式核验 `data/derived_input_manifest.json`。本表用于确认论文、报告和发布包是否来自同一输入与代码基线。

## 11. 尚未消除的风险

{table(residual)}

## 12. 可验收的后续目标

1. **共同垂向基准：** 至少 3 个英国和 3 个荷兰 case 转换到明确共同 coastal-MSL reference，记录 offset 来源、公式、不确定性和重算结果；否则 S4 永久保持 sensitivity 定位。
2. **独立 outcome：** 只在存在站点可匹配的 observed 或 dynamic flood-hazard outcome 后，预先定义并比较 water-only、terrain-only、combined screen；完成前不使用 predictive complementarity。
3. **独立海岸样本：** 用不依赖 GSSR inventory 的 station/shoreline inventory 重算，公开全部候选、排除原因和沿岸采样覆盖。
4. **同岸匹配：** 计算 coastline component 与 alongshore distance，逐站固定 opposite-bank/estuary 判定；当前坐标审阅不得替代这一工作。
5. **发布复现：** 在全新临时目录解压 reviewer ZIP，安装项目、运行 derived reproduction、测试并比较确定性科学输出哈希；记录 release tag、commit 与 ZIP SHA-256。
6. **投稿元数据：** 补齐 authors、affiliations、funding、contributions 和正式归档 DOI；HTML、Markdown、PDF 中不留“待补充”。

## 13. 复现入口

- 审稿人快速复现：`python scripts/reproduce.py --mode derived`
- 上游文件预检：`python scripts/reproduce.py --mode full --verify-only`
- 完整 raw-to-paper：`python scripts/reproduce.py --mode full`
- 科学合同：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`
- 发布门禁：`python scripts/run_major_revision_rebuild.py`
"""


def render_pdf() -> None:
    chrome = chrome_executable()
    if OUT_PDF.exists():
        OUT_PDF.unlink()
    subprocess.run(
        [
            str(chrome), "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000", "--no-pdf-header-footer",
            f"--print-to-pdf={OUT_PDF}", OUT_HTML.resolve().as_uri(),
        ],
        cwd=ROOT,
        check=True,
        timeout=180,
    )
    if not OUT_PDF.exists() or OUT_PDF.stat().st_size < 100_000:
        raise RuntimeError(f"Suspicious PDF output: {OUT_PDF}")


def main() -> int:
    markdown = build_markdown()
    OUT_MD.write_text(markdown, encoding="utf-8")
    OUT_HTML.write_text(build_html(markdown), encoding="utf-8")
    render_pdf()
    for preferred, legacy in LEGACY_OUTPUTS.items():
        shutil.copy2(preferred, legacy)
    print(f"Wrote {OUT_MD}, {OUT_HTML}, and {OUT_PDF} (plus compatibility copies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
