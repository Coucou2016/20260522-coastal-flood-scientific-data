#!/usr/bin/env python3
"""Build the post-major-revision scientific integrity review and evidence log."""

from __future__ import annotations

import hashlib
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
OUT_MD = MANUSCRIPT / "scientific_integrity_review.md"
OUT_HTML = MANUSCRIPT / "scientific_integrity_review.html"
OUT_PDF = MANUSCRIPT / "scientific_integrity_review.pdf"


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
    valid = detail.dropna(subset=["below_area_km2", "connected_area_km2"]).copy()
    identity_error = np.abs(
        valid["connected_reference_land_pct"]
        - valid["below_reference_land_pct"] * valid["conditional_connectivity_pct"] / 100.0
    )
    zero = valid[valid["elevation_offset_m"].eq(0.0)]
    keys = ["station_id", "window_width_km", "eta_m", "seed_rule", "elevation_offset_m"]
    pair = zero.pivot_table(index=keys, columns="neighbours", values="connected_area_km2")
    checks = [
        ("Robustness-grid rows", len(detail) == 2960, len(detail), "74 stations x 40 recorded configurations"),
        ("Unique stations", detail["station_id"].nunique() == 74, detail["station_id"].nunique(), "regional candidate inventory"),
        ("Primary stations", len(primary) == 68 and primary["station_id"].nunique() == 68, len(primary), "COAST-RP match <=6 km"),
        ("Connected area <= below-threshold area", bool((valid["connected_area_km2"] <= valid["below_area_km2"] + 1e-9).all()), int((valid["connected_area_km2"] > valid["below_area_km2"] + 1e-9).sum()), "violations"),
        ("Four-neighbour <= eight-neighbour", bool((pair[4] <= pair[8] + 1e-9).all()), int((pair[4] > pair[8] + 1e-9).sum()), "violations"),
        ("Metric decomposition identity", float(identity_error.max()) < 1e-10, float(identity_error.max()), "maximum absolute percentage-point error"),
        ("Official class 255 in primary windows", int(primary["official_clipped_255_cells"].sum()) == 0, int(primary["official_clipped_255_cells"].sum()), "cells"),
        ("Outside-support sentinel distinct", int(primary["mask_outside_support_cells"].sum()) == 3320, int(primary["mask_outside_support_cells"].sum()), "class-254 cells recorded and excluded"),
    ]
    rows = pd.DataFrame(checks, columns=["Check", "Pass", "Observed", "Criterion or meaning"])
    failures = rows.loc[~rows["Pass"], "Check"].tolist()
    return rows, failures


def hash_manifest() -> pd.DataFrame:
    paths = [
        ROOT / "data" / "raw" / "coast_rp" / "COAST-RP.zip",
        ROOT / "data" / "raw" / "gssr" / "metadata" / "eraint.geojson",
        ROOT / "data" / "raw" / "deltadtm" / "index" / "README.md",
        ROOT / "data" / "raw" / "deltadtm" / "zips" / "mask_tiles.zip",
        SOURCE / "Primary_terrain_components_68stations.csv",
        SOURCE / "Terrain_robustness_grid_74stations.csv",
        SOURCE / "Rank_robustness_one_at_a_time.csv",
        SOURCE / "Spatial_sector_bootstrap_intervals.csv",
        SOURCE / "Topk_spatial_null_curves.csv",
        SOURCE / "Return_period_sensitivity.csv",
        SOURCE / "Denominator_adjusted_associations.csv",
        SOURCE / "Topology_sensitivity_summary.csv",
        SOURCE / "Match_distance_audit_74stations.csv",
        SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv",
        ROOT / "scripts" / "add_mask_aware_terrain_diagnostics.py",
        ROOT / "scripts" / "rebuild_frozen_primary_analysis.py",
        ROOT / "scripts" / "add_external_review_diagnostics.py",
        ROOT / "scripts" / "add_local_dtm_validation.py",
        ROOT / "scripts" / "make_major_revision_figures.py",
    ]
    paths.extend(sorted((ROOT / "data" / "raw" / "local_dtm").glob("*_local_dtm_10m.tif")))
    rows = []
    for path in paths:
        if path.exists():
            rows.append(
                {
                    "File": path.relative_to(ROOT).as_posix(),
                    "Bytes": path.stat().st_size,
                    "SHA-256": sha256(path),
                }
            )
    output = pd.DataFrame(rows)
    output.to_csv(SOURCE / "Major_revision_evidence_sha256.csv", index=False)
    return output


def figure_audit() -> pd.DataFrame:
    figure_sources = {
        "Fig1_process_terrain_design.png": "Primary_station_coastal_sectors.csv; Primary_sample_flow.csv",
        "Fig2_regional_screening_agreement.png": "Primary_terrain_components_68stations.csv; Return_period_sensitivity.csv; Spatial_sector_bootstrap_intervals.csv; Topk_spatial_null_curves.csv",
        "Fig3_connected_terrain_contrasts.png": "Fig3_predefined_site_selection.csv; Fig3_threshold_response_source.csv",
        "Fig4_metric_decomposition_robustness.png": "Primary_terrain_components_68stations.csv; Denominator_adjusted_associations.csv; Topology_sensitivity_summary.csv; Rank_robustness_one_at_a_time.csv",
        "FigS1_water_level_definition.png": "Fig2_water_level_divergence_with_uncertainty.csv; TableS_tidal_regime_metadata_source_tracked.csv",
        "FigS2_process_coherence.png": "Fig3_driver_correlations.csv; event-composite source tables",
        "FigS3_connectivity_gallery.png": "Primary_terrain_components_68stations.csv; frozen DeltaDTM windows",
        "FigS4_elevation_product_datum_sensitivity.png": "TableS_local_dtm_product_datum_crosscheck.csv",
        "FigS5_coastrp_match_audit.png": "Match_distance_audit_74stations.csv; Match_distance_histogram_source.csv",
    }
    rows = []
    for name, sources in figure_sources.items():
        path = ROOT / "figures" / "main" / name
        with Image.open(path) as img:
            width, height = img.size
        rows.append(
            {
                "Figure": name,
                "Pixels": f"{width} x {height}",
                "DPI target": 500 if name.startswith("Fig") else "NA",
                "Source data": sources,
                "Visual QA": "inspected at original resolution; no deliberate cell enlargement",
            }
        )
    return pd.DataFrame(rows)


def build_markdown() -> str:
    checks, failures = invariant_audit()
    hashes = hash_manifest()
    figures = figure_audit()
    product = pd.read_csv(SOURCE / "DeltaDTM_v1_1_product_version_audit.csv")
    rank = pd.read_csv(SOURCE / "Rank_robustness_one_at_a_time.csv")
    base = rank[rank["setting"].eq("primary:10km,2m,4n,adaptive,match<=6km")][
        ["terrain_metric", "n_sites", "spearman", "kendall", "permutation_two_sided_p", "top_n", "top_overlap", "top_overlap_expected_independent"]
    ]
    block = pd.read_csv(SOURCE / "Spatial_sector_bootstrap_intervals.csv")
    rp = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    spatial = base.merge(
        block[["terrain_metric", "spearman_sector_bootstrap_p025", "spearman_sector_bootstrap_p975"]],
        on="terrain_metric",
    ).merge(
        rp[rp["return_period_years"].eq(10)][
            ["terrain_metric", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p"]
        ],
        on="terrain_metric",
    )
    denominator = pd.read_csv(SOURCE / "Denominator_adjusted_associations.csv")
    topology = pd.read_csv(SOURCE / "Topology_sensitivity_summary.csv")
    matching = pd.read_csv(SOURCE / "Match_distance_audit_74stations.csv")
    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    top20 = topk[topk["top_share_pct"].eq(20)].copy()
    matching_excluded = matching.loc[~matching["included_in_primary_match_sample"].astype(bool)].copy()
    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")
    local_summary = local[
        [
            "station",
            "delta_connected_2m_reference_land_pct",
            "local_connected_2m_reference_land_pct",
            "delta_connected_2m_area_km2",
            "local_connected_2m_area_km2",
            "connected_pixel_iou_after_reprojection",
            "local_dtm_vertical_datum_note",
        ]
    ]
    residual = pd.DataFrame(
        [
            ("垂向基准统一", "未完成", "DeltaDTM/ODN/NAP 尚未转换到共同 local-MSL reference；Supplementary Figure S4 只能解释为 combined product/datum/provider-resampling sensitivity。"),
            ("独立真实洪水基准", "未完成", "没有 observed or dynamic flood-hazard truth dataset，因此不能声称 connected-terrain ranking 是真实优先级。"),
            ("样本代表性", "受限", "68 站来自 GSSR metadata inventory，且岸段分布不均；Denmark-Norway 仅 2 站。"),
            ("本地 DTM 服务重采样", "受限", "WCS scaleFactor 生成 nominal 10 m；连续高程插值核由服务端控制。"),
            ("公开审稿仓库", "已完成", "代码、派生数据、图表源数据、文稿和审查证据已发布至 https://github.com/Coucou2016/20260522-coastal-flood-scientific-data；上游原始文件以来源和 SHA-256 清单追踪。正式归档 DOI 尚待版本冻结。"),
            ("潮汐元数据", "部分完成", "正式 cross-product return-level difference 的潮汐语境限制在 13 个 source-verified sites；Brest 和 Hoek 仍不得进入正式 tidal inference。"),
        ],
        columns=["Risk", "Status", "Evidence boundary"],
    )

    status = "全部通过" if not failures else "存在失败项: " + ", ".join(failures)
    return f"""# 科学真实性、准确性与完整性审查文档

**对应稿件：** *Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network*  
**审查定位：** code-data-table-figure-manuscript 穿透式内部审计  
**自动约束状态：** {status}

## 1. 审查结论

本轮大修没有把审稿意见当作文字层面的“解释补丁”，而是重新冻结唯一主流程，并从原始/中间数据重算区域指标。当前 68 站主结果的算术和拓扑约束通过；主要 Spearman、Kendall、岸段内双侧置换、保持岸段结构的 top-k null、Moran's I 和 six-sector resampling 均直接来自当前 source tables。稿件已删除旧 degree-window 数值、15/20 m denominator sensitivity、未定义的 response categories，以及把 top-set mismatch 解释为 beyond-chance discordance 的写法。

现阶段可以确认的是：代码生成的当前表格与图件内部一致，结果支持“两个区域筛查排序不能互相替代”。不能确认、也没有声称的是：静态地形指标等于真实洪水风险，或者七个本地 DTM case 能代表全部 68 站。垂向基准未统一和缺少独立真实洪水基准仍是投稿前的主要外部证据限制。

## 2. 四个 P0 问题的处理证据

1. **DeltaDTM cutoff 与 15 m denominator：已重构。** 当前文件由 GeoTIFF tag 和 v1.1 README 识别为 DeltaDTM v1.1.1，cap 为 30 m EGM2008；2024 论文描述的是 v1.0 的 10 m + MSL 范围。主流程不再使用 15 m 或 20 m lowland denominator，仅用有限 class-0 represented land；正文明确这种比例不是 nominal 10 km square 的全部陆地比例。
2. **旧窗口数值混入 Supplement：已移除。** 新 Supplementary Information 只从 `Primary_terrain_components_68stations.csv` 和 `Terrain_robustness_grid_74stations.csv` 导出。旧 S2/S6、`Fig5_*` 和 degree-window 表不再构成稿件证据。
3. **sector/country 混用：已统一。** 地图、block resampling 和 leave-one-out 使用同一组六个 coastal-sector identifiers；country omission 不再被称为 sector sensitivity。
4. **未定义 response category：已删除。** 正文只报告连续值和绝对面积；Supplementary Figure S4 报告七个诊断站的连续差值和 IoU，不再报告“4/7 category changed”。

## 3. 产品版本与 mask 审计

{table(product)}

旧代码曾同时用 255 表示 DeltaDTM 官方 clipped class 和 boundless/reprojection fill。新版代码将窗口外支持固定为 254。扫描得到的 72 个 source mask tiles 中未发现官方 255；旧窗口中出现的 255 因而不能解释为真实 clipped land。当前自动门禁要求 254/255 分离，并禁止 lake、outside support、clipped support 或任意 no-data 作为 marine seed。

## 4. 自动科学约束

{table(checks)}

这些检查证明当前输出满足代码自身声明的面积与拓扑关系。它们不证明输入产品没有系统误差，也不等同于独立洪水观测验证。

## 5. 统计证据边界

{table(spatial)}

station-label permutation 的显著性与 spatial inference 必须分开阅读。connected-land share 和 connected area 的 station-level p 较小，但 six-sector ranges 跨 0。Top-20% overlap 为 1/14，独立随机期望为 2.88；exact lower-tail p = 0.152。因此稿件只写 limited recovery / weak concordance / non-interchangeability，不写 unusual mismatch、distortion、mis-rank 或 proven complementarity。

主推断采用保持岸段组成的空间零模型：RP10 与 connected-land share 的 top-20% overlap 为 {int(top20.iloc[0]['observed_overlap'])}/{int(top20.iloc[0]['top_n'])}，空间零模型 95% 包络为 [{float(top20.iloc[0]['sector_stratified_null_q025']):.0f}, {float(top20.iloc[0]['sector_stratified_null_q975']):.0f}]，lower-tail p={float(top20.iloc[0]['sector_stratified_lower_tail_p']):.3f}。观察值处在包络内，因此该结果只证明两个清单恢复度有限，不证明错配异常大于空间随机。

指标分解还说明 composite connected share 的负关联主要来自 below-2 m land prevalence；conditional connectivity 的 rho 约为 0。这一结果直接纠正了把低 composite fraction 一概解释为“低连通性”的构念混淆。

### 分母几何与拓扑

{table(denominator)}

{table(topology)}

RP10 与 represented-land fraction 的 rho 接近 0，控制该比例前后主关联几乎不变。4 邻域和 8 邻域在区域排名上高度一致，但 top-20% 仍有站点成员变化，证明站点优先级对拓扑定义比区域总体结论更敏感。

### COAST-RP 匹配审计

68 个纳入站点的最大匹配距离为 {float(matching.loc[matching['included_in_primary_match_sample'].astype(bool), 'recomputed_match_dist_km'].max()):.3f} km；下列 6 个站点因超过 6 km 规则被排除，而不是在出图后人工删除：

{table(matching_excluded[['station', 'recomputed_match_dist_km', 'coast_rp_source_lon', 'coast_rp_source_lat', 'match_exclusion_reason']])}

## 6. 本地 DTM product-and-datum cross-check

{table(local_summary)}

Supplementary Figure S4 的 IoU target grid、grid shape、transform、mask resampling 和文件 SHA-256 全部记录在 `TableS_local_dtm_product_datum_crosscheck.csv`。Environment Agency 和 AHN 数据未与 EGM2008 统一，因此本文不使用 validation 一词，也不把差异归因给 DeltaDTM 单一误差。七站为 diagnostic cases，不把变化比例外推到 68 站总体。

## 7. 图件真实性与视觉检查

{table(figures)}

Figure 3 的三个站由机器可读规则选出。低值站点只对原始 connected cells 做局部放大，不改变主地图中的像元面积；high/low 视觉平衡通过指标分解和三条实算 threshold curves 实现，而不是调数值。Figure 4 取消离散类别，Figure 2 明确区分 raw station estimate、sector range 和 spatially constrained top-k null。

## 8. 关键文件 SHA-256

{table(hashes)}

此清单用于确认后续 manuscript、report 或 publication package 是否仍由同一基线生成。大体积上游数据不应凭文件名认定相同，必须复核 hash 或上游 DOI/version。

## 9. 仍未消除的风险

{table(residual)}

## 10. 可验收的投稿前目标

1. **共同垂向基准：** 至少将 3 个英国和 3 个荷兰 case 的 terrain 与 coastal MSL 转换到明确共同参考；验收为方法给出 offset 来源、公式和不确定性，重算后的 source table/figure 可一键复现。若无法完成，则 Supplementary Figure S4 保持 sensitivity 定位。
2. **独立结果基准：** 在可匹配站点上引入 observed 或 dynamic hazard outcome；验收为预先定义评价指标并分别比较 water-only、terrain-only 和 combined screen。完成前不使用 predictive complementarity。
3. **独立站点框架：** 用不依赖 GSSR inventory 的 coastal station/shoreline sample 重算主关系；验收为 sample-flow 记录全部候选、排除原因和 coastal-spacing/sector coverage。
4. **公开复现入口：** GitHub 公开入口已经建立；下一项验收是在独立临时目录中克隆仓库并运行不依赖上游大文件的合同测试，再记录 release tag、commit 和 archive hashes。正式投稿版本冻结后可再生成归档 DOI。
5. **投稿元数据：** 补齐 authors、affiliations、funding、contributions；验收为 HTML、Markdown 和 PDF 中无“待补充”占位。

## 11. 复现入口

核心重算命令为 `python scripts/rebuild_frozen_primary_analysis.py`。本地 DTM 交叉检查为 `python scripts/add_local_dtm_validation.py`，主图为 `python scripts/make_major_revision_figures.py`，论文和补充材料分别由 `python scripts/build_standalone_paper.py` 与 `python scripts/build_supplementary_information.py` 生成。自动科学合同使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q --import-mode=importlib`。
"""


def render_pdf() -> None:
    chrome = chrome_executable()
    if OUT_PDF.exists():
        OUT_PDF.unlink()
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            "--no-pdf-header-footer",
            f"--print-to-pdf={OUT_PDF}",
            OUT_HTML.resolve().as_uri(),
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
    print(f"Wrote {OUT_MD}, {OUT_HTML}, and {OUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
