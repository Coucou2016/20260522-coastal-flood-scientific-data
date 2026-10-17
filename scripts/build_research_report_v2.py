#!/usr/bin/env python3
"""Build the detailed Chinese research report from frozen source tables."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pandas as pd

from build_standalone_paper import build_html, chrome_executable, data_uri_for_image
from build_supplementary_information import table


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "figure_source"
OUT_MD = ROOT / "report.md"
OUT_HTML = ROOT / "report.html"
OUT_PDF = ROOT / "report.pdf"
ARCHIVE_DIR = ROOT / "manuscript"


def image(title: str, filename: str) -> str:
    return f"![{title}]({data_uri_for_image(filename)})"


def build_markdown() -> str:
    flow = pd.read_csv(SOURCE / "Primary_sample_flow.csv")
    product = pd.read_csv(SOURCE / "DeltaDTM_v1_1_product_version_audit.csv")
    rank = pd.read_csv(SOURCE / "Rank_robustness_one_at_a_time.csv")
    block = pd.read_csv(SOURCE / "Spatial_block_bootstrap_intervals.csv")
    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    rp = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    moran = pd.read_csv(SOURCE / "Spatial_autocorrelation_moran.csv")
    denominator = pd.read_csv(SOURCE / "Denominator_adjusted_associations.csv")
    topology = pd.read_csv(SOURCE / "Water_land_topology_summary.csv")
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    cases = pd.read_csv(SOURCE / "Fig3_predefined_site_selection.csv")
    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")
    decision = pd.read_csv(SOURCE / "Decision_instability_station_metrics.csv")
    threshold_integrated = pd.read_csv(SOURCE / "Threshold_integrated_associations.csv")
    coastline = pd.read_csv(SOURCE / "Coastline_window_sensitivity_summary.csv")

    base_setting = "primary:10km,2m,4n,adaptive,match<=6km"
    base = rp[
        rp["return_period_years"].eq(10)
        & rp["terrain_metric_label"].isin(
            ["lowland_prevalence", "conditional_connectivity", "connected_lowland_share", "connected_area"]
        )
    ][
        ["terrain_metric", "terrain_metric_label", "n_sites", "block_scale_km", "n_spatial_blocks", "spearman", "kendall", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p", "top20_n", "top20_observed_overlap", "sector_stratified_top20_null_q025", "sector_stratified_top20_null_q975", "sector_stratified_top20_lower_tail_p"]
    ].merge(
        block[["terrain_metric", "block_scale_km", "spearman_sector_bootstrap_p025", "spearman_sector_bootstrap_p975"]],
        on=["terrain_metric", "block_scale_km"],
        how="left",
    ).drop(columns="terrain_metric")
    base.columns = [
        "地形指标",
        "站点数",
        "空间分块尺度(km)",
        "分块数",
        "Spearman rho",
        "Kendall tau",
        "分块调整秩关联",
        "块内经验双侧置换p",
        "Top-set大小",
        "实际重合",
        "块内null 2.5%",
        "块内null 97.5%",
        "块内lower-tail p",
        "分块重采样2.5%",
        "分块重采样97.5%",
    ]

    case_table = cases[
        [
            "station",
            "figure3_role",
            "coast_rp_rp10_m",
            "water_rank",
            "terrain_rank",
            "below_reference_land_pct",
            "conditional_connectivity_pct",
            "connected_reference_land_pct",
            "connected_area_km2",
        ]
    ]
    case_table.columns = ["站点", "图中角色", "RP10 (m)", "水位排名", "地形排名", "低于2m陆地占比(%)", "条件连通率(%)", "连接陆地占比(%)", "连接面积(km2)"]

    local_table = local[
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
    local_table.columns = ["站点", "DeltaDTM连接占比(%)", "地方DTM连接占比(%)", "DeltaDTM连接面积(km2)", "地方DTM连接面积(km2)", "空间IoU", "地方产品原生垂向基准"]

    connected_sens = rank[rank["terrain_metric"].eq("connected_reference_land_pct")][
        ["setting", "n_sites", "spearman", "terrain_rank_spearman_vs_primary", "top20_jaccard_vs_primary", "top20_membership_changes_vs_primary"]
    ]
    connected_sens.columns = ["参数设置", "站点数", "Spearman rho", "与主流程地形排名rho", "Top-20% Jaccard", "Top-20%成员变化数"]

    top20 = topk[topk["top_share_pct"].eq(20) & topk["block_scale_km"].eq(150)].copy()
    rp_summary = rp[
        rp["terrain_metric_label"].isin(["lowland_prevalence", "conditional_connectivity", "connected_lowland_share", "connected_area"])
    ][["return_period_years", "terrain_metric_label", "block_scale_km", "spearman", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p"]].copy()
    rp_summary.columns = ["重现期(年)", "地形指标", "空间块尺度(km)", "Spearman rho", "分块调整秩关联", "块内经验双侧置换p"]

    denominator_table = denominator[
        [
            "terrain_metric_label",
            "raw_spearman_water_vs_metric",
            "partial_spearman_controlling_represented_land_fraction",
            "spearman_metric_vs_represented_land_fraction",
            "spearman_water_vs_represented_land_fraction",
        ]
    ].copy()
    denominator_table.columns = ["地形指标", "原始rho", "控制represented-land比例后的偏rho", "指标与represented-land比例rho", "RP10与represented-land比例rho"]

    topology_table = topology.copy()
    topology_table.columns = ["水体邻域", "陆地邻域", "地形指标", "站点数", "水位-地形rho", "与主流程地形排名rho", "Top-set大小", "Top-set重合", "成员变化数"]

    decision_table = decision[
        ["station", "water_rank", "terrain_rank", "absolute_rank_displacement", "priority_class", "eligible_configurations", "selected_configurations", "terrain_top20_selection_frequency"]
    ].sort_values(["absolute_rank_displacement", "station"], ascending=[False, True]).head(20)
    decision_table.columns = ["站点", "水位排名", "地形排名", "绝对排名位移", "主配置优先类别", "可用配置数", "入选配置数", "地形Top-20%选择频率"]

    threshold_table = threshold_integrated[
        ["terrain_metric", "n_sites", "spearman", "kendall", "interpretation"]
    ].copy()
    threshold_table.columns = ["0-3 m阈值积分指标", "站点数", "Spearman rho", "Kendall tau", "解释边界"]

    coastline_table = coastline[
        [
            "terrain_metric",
            "n_sites",
            "terrain_rank_spearman_oriented_vs_square",
            "water_vs_oriented_spearman",
            "water_vs_square_spearman",
            "top20_overlap_oriented_vs_square",
            "top20_membership_changes",
            "interpretation",
        ]
    ].copy()
    coastline_table.columns = [
        "地形指标",
        "站点数",
        "沿岸窗口与方窗地形排名rho",
        "水位与沿岸窗口rho",
        "水位与方窗rho",
        "Top-20%重合",
        "成员变化数",
        "解释边界",
    ]

    return f"""# Northwest Europe 海岸洪水筛查研究报告

**报告性质：** 科研过程、方法、数据、结果与审计证据的完整归档版

**对应论文：** *Limited concordance between storm-tide magnitude and standardized connected-lowland screening across Northwest Europe*

**作者、单位和基金：** 待补充

**使用边界：** 本报告讨论区域筛查指标，不提供局地洪水预报或工程设计水位。

## 目录

1. 摘要  
2. 研究背景与目的  
3. 数据来源与证据边界  
4. 研究过程  
5. 方法  
6. 结果展示与图表解析  
7. 综合分析与讨论  
8. 主要结论  
9. 不足与展望  
10. 复现与验收

## 摘要

本研究考察一个区域海岸筛查中常被忽略的问题：按照极端水位大小排出的优先站点，能否恢复由独立静态地形指标得到的优先站点。研究将 COAST-RP（全球海岸风暴潮位重现期数据集）2、5、10、25、50 和 100 年重现期的 storm tide（风暴增水与天文潮共同构成的总水位统计量）与 DeltaDTM v1.1.1（约 30 m 水平分辨率的全球海岸数字地形模型）配对，在 sampled Northwest European station network 的 68 个站点上计算标准化地形易感性。

区域主流程采用固定 10 km 窗口、官方 water mask、8-neighbour water graph（八邻域水体图，用于保留对角表示的窄水道）、4-neighbour land graph（四邻域陆地图，避免仅以像元角点形成陆地泄漏）和 2 m EGM2008 terrain threshold（地形高程阈值）。这个 2 m 数值不是 COAST-RP 事件水面，也没有与地方平均海平面拼接。10 年重现期 storm tide 与 connected land share 的 Spearman rho 为 -0.33，与 connected area 的 rho 为 -0.34。沿海连续分块的重采样范围在 100 km 为 -0.55 至 -0.03、150 km 为 -0.57 至 -0.03、250 km 为 -0.58 至 0.02；最大尺度触及零，不能据此建立稳定的区域负相关定律。指标拆解显示，关系主要来自 lowland prevalence（rho=-0.31），而 conditional connectivity（rho=0.10）与 storm tide 没有单调关系。

storm-tide top-20% 与 connected-land top-20% 各含 14 个站，只重合 1 个；在 150 km 空间分块置换零模型中，该重合仍处于 95% 包络内（lower-tail p = {float(top20.iloc[0]['sector_stratified_lower_tail_p']):.3f}）。两个排序的绝对位移中位数为 26 位。正确结论是二者在当前样本网络中呈 limited concordance（有限一致性），水位清单不能恢复同一套地形优先站点；这不等于“错配显著超过空间随机”，也不证明任一清单是真实洪水排序。

## 研究背景与目的

### 从海上边界水位到独立地形易感性

storm tide 是海岸边界上的水位统计量。它能够告诉我们某个沿岸位置的总水位概率分布，却不能单独告诉我们水会如何进入陆地。真实洪水还受到高程、堤防、河道、潮沟、闸门、排水系统、地表粗糙度、洪水历时和波浪等过程影响。本研究没有把 storm tide 加到 DeltaDTM 高程上，而是把 water-level forcing screen（海岸水位强度筛查）与 standardized terrain-susceptibility screen（标准化地形易感性筛查）并列比较。

本研究检查两个常用于大区域初筛的维度是否给出相同的站点顺序。若水位排名能够恢复地形易感性排名，区域初筛可能只需一个指标；若不能，筛选清单至少要把两类信息并列呈现，再决定哪些站点进入局地水动力分析。

### 为什么必须处理垂向基准

地形高程与海平面必须在共同 vertical datum（垂向基准，规定“零高程”所在物理参考面）下比较。DeltaDTM v1.1.1 使用 EGM2008；英国 Environment Agency 地形使用 Ordnance Datum Newlyn；荷兰 Actueel Hoogtebestand Nederland 使用 Normaal Amsterdams Peil。数值上同为 2 m，并不自动代表相对于当地平均海平面相同的物理高度。因此，本研究把区域主阈值严格称为“2 m EGM2008 地形阈值”，把地方 DTM 结果称为 product-and-datum sensitivity（产品与基准敏感性），不称为验证。

### 具体研究目标

1. 建立可审计的 68 站 COAST-RP 与 DeltaDTM 匹配样本。
2. 将原 composite connected fraction 拆成低地丰度、条件连通率、连接陆地占比和绝对连接面积。
3. 在全部站点上检验 RP2-RP100、窗口、阈值、4/8 邻域、海洋种子、统一高程偏移和 COAST-RP 匹配距离。
4. 用 100、150、250 km 三套版本化沿岸分块的块内置换、区块重采样、Moran's I 和站点 jackknife 约束统计表述。
5. 用七个国家/地方 DTM case 诊断产品、原生垂向基准与服务重采样的混合敏感性。
6. 让每张图都能追溯到机器可读 source table，不通过配色或放大篡改数据含义。

## 数据来源与证据边界

### 表1 数据产品及其角色

| 数据 | 本研究用途 | 它能说明什么 | 它不能说明什么 |
|---|---|---|---|
| COAST-RP | 2–100 年 storm-tide return levels 和空间匹配 | 区域海岸水位 magnitude screen | 不是观测洪水深度，也不是产品不确定性的完整分布 |
| DeltaDTM v1.1.1 | 10 km 窗口地形和官方水体 mask | 2 m EGM2008 下的静态低地及 raster connectivity | 不含堤防运行、排水、波浪、摩阻和洪水历时 |
| GSSR | surge residual supporting diagnostic | surge-process 定义和重建序列的基础一致性背景 | `corrn` 是站点重建相关指标，不是极端事件技能评分，也不与 COAST-RP 构成等价产品验证 |
| ERA5-derived meteorology | focal surge 的 predictor-consistency check | 日尺度重建 surge 是否保留与基础气象预测因子一致的信号 | 不构成事件归因、因果模型或 flood predictor |
| EA LiDAR / AHN | 七站地方 DTM cross-check | 产品、分辨率、服务重采样与原生 datum 敏感性 | 未统一 datum 前不能计算 DeltaDTM 绝对误差 |

### 表2 样本流

{table(flow)}

68 站并不是 Northwest Europe 海岸线的均匀抽样。候选点来自 GSSR metadata inventory，英国、爱尔兰和 English Channel 站点较密，而 continental North Sea 与 Skagerrak 较少。后续空间不确定性分析必须承认这种网络结构，不能把 68 个点当成完全独立、等代表性的样本。

### 表3 DeltaDTM 版本审计

{table(product)}

2024 DeltaDTM 论文描述 v1.0 的约 10 m + MSL 产品范围，而实际下载 GeoTIFF 与 README 标明 v1.1.1、EGM2008 和 30 m cap。旧稿把文献中的 v1.0 cutoff 直接套到 v1.1.1 上，会造成版本混淆。新流程以实际文件 tag 与 v1.1 README 为准，同时在正文中主动说明两者差别。

## 研究过程

### 第一步：发现并修正 mask 填充值冲突

旧工作流使用 255 作为 boundless read 或 reprojection fill；但 255 同时是 DeltaDTM 官方 clipped class。这样会让“窗口外没有数据”看起来像“产品裁剪地形”。本轮把内部 outside-support sentinel 改为 254，并扫描 72 个已提取官方 mask tile。扫描未发现真实 255。当前 68 个主窗口共记录 3,320 个 254 cells 和 0 个官方 255 cells；所有 254/255、水体和湖泊均不进入陆地分母。

### 第二步：冻结唯一主流程

主流程固定为 10 km 窗口、2 m EGM2008、official adaptive marine seed、water-8/land-4 拓扑以及 COAST-RP match 小于等于 6 km。水体八邻域用于保留官方 ocean-river mask 中以对角像元表达的窄通道；陆地四邻域避免低地仅凭角点接触打开整个 component。water-4/land-4、water-4/land-8 和 water-8/land-8 均作为显式拓扑敏感性。旧 0.03/0.04/0.06 degree windows、15 m denominator 和历史 boundary-no-data seed 结果不再与主结果混用。完整 terrain grid 保存 74 站乘 40 配置，共 2,960 行。

### 第三步：拆解指标

原 connected fraction 不能单独表示“连通性”，因为它同时受低地面积和连通率控制。新流程定义：

**f_low(eta) = A(z <= eta) / A(reference land)**

它表示 represented land 中低于阈值的比例。现实含义是“窗口里到底有多少低地”。

**p_conn(eta) = A(connected and z <= eta) / A(z <= eta)**

它表示已经低于阈值的土地中，有多少属于 ocean-seeded raster component。现实含义是“现有低地在这个静态拓扑规则下有多少接海”。

**f_conn(eta) = f_low(eta) x p_conn(eta)**

它是前两者的乘积，即 connected below-threshold land 占 represented land 的比例。绝对连接面积 A_conn 另行报告，防止小分母产生高比例却对应很小面积。

### 第四步：全样本稳健性与空间推断

所有参数变体都在区域样本上重跑。within-block permutation（空间块内置换）在保持当前沿海组成的情况下检验条件关联；block resampling（空间区块重采样）检验如果抽到的沿海区块构成发生变化，rho 会变化多大。两者回答不同问题：前者针对当前样本组成，后者针对地理可推广性。100、150、250 km 三套块定义全部由 `config/coastal_spatial_blocks_v2.csv` 固定，不再用经纬度 if 条件动态猜测。

Top-k overlap 的主零模型也采用块内置换，使 terrain top values 只在同一空间块站点之间交换。精确 hypergeometric null 仅作为非空间描述对照。68 站、每组 14 站时，非空间独立随机期望重合为 14 x 14 / 68 = 2.88，但论文推断以三套空间约束包络为准。

## 方法

### 海洋种子和连接图

官方 mask class 1 ocean 是基础 seed。class 3 river 只有在其 component 与 ocean 相连时才加入。若 10 km 窗口内没有 ocean，算法逐级扩展到 25、50、100、200 km mask context，找到 ocean-connected water component 后投影回 10 km 窗口。lake、clipped、outside support 和 arbitrary no-data 不可成为海洋入口。

海洋种子和低地传播使用两个独立、显式的邻域参数。主流程先用 water-8 将 class-1 ocean 与 ocean-connected class-3 river 组成 marine seed，再用 land-4 在低于 eta 的 class-0 terrain 上传播。严格 water-4/land-4 与主流程地形排名 rho=0.86，Top-20% 重合 12/14；采用 land-8 的方案则各改变 6 个成员。由此同时报告区域关联方向与站点清单变化，不能只用一个总体 rho 代替拓扑审计。

### 统计量

主文同时报告 raw magnitude-terrain Spearman rho、Kendall tau、10,000 次块内经验双侧置换 p、2,000 次空间块重采样范围、top-10% 到 top-40% spatial null envelope、block-adjusted rank association、Moran's I、terrain rank stability 和 top-20% Jaccard。非空间 station-label p 与 exact hypergeometric 仅保留为审计对照，不能替代空间结果。

## 结果展示与图表解析

### 图1 研究区、显示区域与样本流

{image("图1. Northwest Europe 68站空间分布和样本流", "Fig1_process_terrain_design.png")}

这张图先回答“样本从哪里来、空间上怎么分布”。左图使用真实地图底图，点颜色不是风险等级，而是由 reviewed coastal basins 合并得到的显示区域。黑色三角、方框和星形分别标出 storm-tide top set、terrain top set 和 overlap。颜色仅为读图服务；统计推断使用配置表中另行记录的 100、150、250 km 空间块。图上可以直接看出网络分布不均，而且高水位和高标准化地形响应符号并不集中在同一组点上。

右侧流程图把样本筛选写成可核查数字。74 个区域候选站都有 DeltaDTM support 和 marine seed；COAST-RP 匹配限制后剩 68；GSSR 记录长度与重建相关门槛只用于 supporting subset，剩 44。这里特别强调区域主分析虽从 GSSR station inventory 出发，却不要求每站具有合格 GSSR return level，防止读者误以为主排名是四产品共同交集。

### 图2 区域弱一致性及其统计边界

{image("图2. storm-tide magnitude 与标准化地形易感性的区域弱一致性", "Fig2_regional_screening_agreement.png")}

Panel a 展示原始 COAST-RP magnitude 与 connected land share。纵轴采用普通 logarithmic display，使 0.1%、1%、10% 和 100% 可同时阅读；所有点大小固定，避免读者把视觉面积误认为额外变量，颜色沿用图1岸段。Newport 位于“高水位、极低地形占比”，Delfzijl 位于“中等水位、极高地形占比”。

Panel b 是本研究最重要的统计边界。connected share、below-2 m share 和 connected area 的站点 rho 大约为 -0.31 到 -0.34。空间块重采样结果随尺度变化：connected share 在 100 和 150 km 范围上限略低于零，在 250 km 则跨零。块内经验双侧置换 p 也从 0.135 变化到 0.025 和 0.012。两类统计量回答的问题不同；综合解释是当前样本有负斜率，但它对沿海组成和分块尺度敏感，不能写成普遍区域定律。

Panel c 检查“1/14 重合”是否真的异常。黑线位于三套 95% within-block null envelope 内，所以正确表述是 water-level list 对 terrain list 的恢复度有限，而不是 observed mismatch 显著超出空间随机。Panel d 不再重复重现期曲线，而是显示每站在其可用预设配置中进入 terrain top-20% 的频率。Sheerness 在可用配置中始终入选，Hoek van Holland 只有 52.5%，Avonmouth 从不入选；这说明筛选决策的稳定程度因站而异，但这些频率绝不是洪水概率。

### 表4 主统计结果

{table(base)}

### 表5 重现期与空间约束稳健性

{table(rp_summary)}

Moran's I 结果显示 150 km 对称邻接下 storm tide 为 0.31、lowland prevalence 为 0.66、connected land share 为 0.44，而 conditional connectivity 为 -0.02。前几项具有明显空间聚集，解释了为什么必须同时呈现块内置换与空间块重采样区间。

### 表6 分母覆盖诊断

{table(denominator_table)}

RP10 与窗口内 represented-land 比例几乎无关（rho=0.003）。控制这一比例后，connected-land share 的 rho 由 -0.333 变为 -0.336，说明当前负关联并不是由不同站点窗口中“可用陆地占比”机械制造出来的。不过，该诊断不能消除高程产品和垂向基准误差，只能排除一个具体的分母几何混杂来源。

### 表7 水体图与陆地图的 4/8 邻域拓扑诊断

{table(topology_table)}

主流程有意采用“水体 8 邻域、陆地 4 邻域”：前者允许官方河流/海洋 mask 中以对角像元表示的窄水道接入海洋种子，后者不允许低地仅凭角点接触传播。严格的“水体 4 邻域、陆地 4 邻域”将水位与 connected-land share 的 rho 从 -0.33 改为 -0.43；两套地形排名的 rho 为 0.86，Top-20% 重合 12/14，即有 4 个成员改变。采用陆地 8 邻域的两套方案各改变 6 个 Top-20% 成员。可见区域层面的 limited concordance 仍在，但单站优先级对栅格拓扑选择并非完全稳定。

### 表8 决策稳定性最高的排名位移案例

{table(decision_table)}

每个站点的“选择频率”是它在自身可用的预设地形配置中进入 terrain Top-20% 的比例；配置包括阈值、窗口、邻域、海洋种子、高程整体偏移和匹配距离等已记录方案。这个频率不是洪水概率。它回答的是一个更贴近筛查决策的问题：若分析者在合理而预先记录的方法选项之间切换，哪些站点仍会反复进入第二阶段建模清单，哪些站点的入选依赖某一特定配置。

### 表9 0-3 m 阈值积分诊断

{table(threshold_table)}

阈值积分把 0-3 m EGM2008 范围内每 0.25 m 的实算响应曲线汇总为面积平均值，从而检查主结论是否只由 +2 m 这一截面造成。connected-share 与 connected-area 的阈值积分 rho 分别为 -0.30 和 -0.31，接近但略弱于 +2 m 主结果。它仍是标准化静态地形指标，不是概率，也没有解决 local mean sea level 的基准统一问题。

### 表10 沿岸方向窗口诊断

{table(coastline_table)}

该敏感性用海岸 mask 的局部主方向构造约 10 km 沿岸 x 5 km 向陆支持区，再与 10 km 站点中心方窗比较。两种几何下 connected-share 排名 rho 为 0.80，Top-20% 重合 11/14；水位与沿岸窗口地形的 rho 为 -0.25。这个近似窗口不能替代精确海岸线或水动力域，但说明方窗几何会改变部分站点，而 limited concordance 并非只存在于方窗设定。

### 图3 三种机制而不是三个“好看案例”

{image("图3. Delfzijl、Newport 与 Immingham 的9子图机制解释", "Fig3_connected_terrain_contrasts.png")}

Figure 3 使用 3 x 3 结构，但每一行承担固定任务。第一行是实际 raster classification；第二行拆成 f_low、p_conn 和 f_conn；第三行显示 threshold response。这样设计是为了解决旧图“一个站全蓝、另一个几乎看不到蓝色”的读图问题，同时不改变像元分类。

Delfzijl 是稳定的 terrain-priority case。97.00% represented land 低于 2 m，其中 99.69% 属于海洋种子连通 component，所以 connected share 为 96.70%（61.30 km2）。它的水位排名为 26/68、地形排名为 1/68。主图大面积蓝色是原始分类结果；地方 DTM 的四邻域 cross-check 仍为 89.78%，因此没有为了视觉平衡缩小蓝色面积。

Newport 是 high-water, lowland-limited case。它的 RP10 为 8.60 m、排名 3/68，但低于 2 m 的 represented land 只有 0.164%。条件连通率为 90.53%；最终 connected share 只有 0.148%，是因为低地少，不是因为海洋连通差。主地图保持原始小面积，inset 只放大原像元位置，不扩大面积。

Immingham 是 connectivity-filtered case。低于 2 m 的 represented land 有 20.14%，但条件连通率仅 2.01%，因此图中橙色未连接低地很多，蓝色连接面积很少。它与 Newport 的最终 connected share 都低，但物理原因相反。这正是指标拆解的必要性。第三行不再画类似置信区间的阴影，而是分别给出 baseline、DEM -0.5 m 和 DEM +0.5 m 三条实算曲线。

### 表11 Figure 3 数据

{table(case_table)}

### 图4 指标分解、窗口支持与方法敏感性

{image("图4. 标准化地形指标的分解与全样本稳健性", "Fig4_metric_decomposition_robustness.png")}

图4把论文核心稳健性放在主文。Panel c 明确比较主流程“水体8邻域、陆地4邻域”与严格“水体4邻域、陆地4邻域”；两套地形排名 rho 为 0.86，但 top-20% 仍有 4 个成员变化。Panel d 还纳入 0-3 m threshold-integrated metric 和 10 km x 5 km coastline-oriented window。前者 connected-share rho 为 -0.30，后者为 -0.25；这些结果说明结论不只依赖单一 2 m 截面，同时也提醒个别站点排序会随地形定义改变。七站地方 DTM 对照仍放在 Supplementary Figure S4，因为差异同时包含 elevation product、native datum、horizontal resolution 和 provider WCS resampling；未统一 EGM2008、ODN 和 NAP 前，不能承担主结论或建立绝对准确性排名。

### 表12 七站交叉检查（补充敏感性）

{table(local_table)}

### 表13 connected land share 全样本敏感性

{table(connected_sens)}

## 综合分析与讨论

### 不同不等于已经证明互补

两个排序不同，可能因为它们代表不同而有用的物理维度，也可能因为其中一个受产品误差影响，还可能只是统计上低相关。当前没有独立真实洪水 outcome，不能证明把二者组合后 predictive prioritization 一定提高。因此论文采用 limited concordance 和 different screening priorities，不使用 proven complementarity、distortion 或 mis-rank。

### 静态连通不等于真实淹没

蓝色 connected cells 只表示在指定 raster、seed、threshold 和邻域下共享一个连通 component。它没有模拟水量是否足够、洪水需要多久到达、堤防是否失效、排水是否反向、闸门是否关闭或波浪是否越顶。低地深处出现蓝色可以是河道连通，也可以是 DEM 对 barrier 表达不足；必须结合 seed audit、4/8-neighbour 和 local terrain 检查。

### 为什么报告比例和面积

比例高不一定面积大，面积大也不一定占窗口土地比例高。connected share 更接近“represented landscape 中响应有多普遍”，A_conn 更接近“绝对潜在面积”。两者均给出相似站点层面负关联，但空间区间均跨 0，所以不会选其中一个作为唯一真值。

## 主要结论

1. 在 68 个 Northwest Europe 站点中，COAST-RP storm-tide magnitude 没有稳定恢复 DeltaDTM standardized terrain-susceptibility ranking。
2. composite connected share 的区域变化主要由 lowland prevalence 驱动；conditional connectivity 与 storm tide 基本无单调关系。
3. 1/14 top-set overlap 是描述性差异，但没有低于三套空间分块的 spatial null envelope。
4. 窗口、阈值和 4/8-neighbour 会改变部分站点排名，因此区域结论与站点优先级的稳健性必须分开报告。
5. national/local DTM cross-check 显示产品和垂向基准可大幅改变多个站点结果；未统一 datum 前不能称为 validation。
6. 最合理的应用是并列报告 water-level screen 与分解后的 terrain components，再决定哪些站点进入局地水动力建模。

## 不足与展望

### 表14 投稿前不足、目标与验收条件

| 事项 | 当前状态 | 可验收目标 |
|---|---|---|
| 垂向基准 | DeltaDTM/ODN/NAP 未统一 | 至少 3 个英国和 3 个荷兰 case 转换到共同 local-MSL reference，记录 offset 来源、公式和不确定性并重算 Supplementary Figure S4 |
| 独立真值 | 没有 observed/dynamic flood outcome | 预先定义评价指标，对 water-only、terrain-only、combined screen 做外部 benchmark；完成前不声称 predictive complementarity |
| 样本代表性 | GSSR inventory 派生且空间聚集 | 使用独立 coastal inventory 或 shoreline sample，公开全部候选、排除理由及沿岸间距/空间分块覆盖 |
| 地方DTM服务 | WCS 插值核由服务端控制 | 获取 native-resolution tiles 或可声明 kernel 的本地重采样流程，固定 target grid、origin 和 CRS |
| 公开复现 | GitHub 公开仓库已建立，发布包通过凭据扫描 | 从公开仓库的新克隆执行一条命令，重建 source tables、figures 和文档；正式归档 DOI 尚待版本冻结后生成 |
| 作者元数据 | 待补充 | HTML、MD、PDF 中 authors、affiliations、funding、contributions 无占位符 |

## 复现与验收

审稿人快速复现入口为 `python scripts/reproduce.py --mode derived`：它先核验带 SHA-256 的紧凑派生输入，再重建主统计、图件、论文、补充材料、报告和审查文档。真正的上游全链条入口是 `python scripts/reproduce.py --mode full`，执行前可用 `--verify-only` 检查本地原始产品是否与 `data/upstream_raw_manifest.csv` 一致。科学约束测试要求 2,960 行完整、connected area 不超过 below area、四邻域结果不超过相同条件下的八邻域结果、指标分解恒等式误差小于 1e-10，并检查空间分块、经验双尾置换、确定性 Top-k 和水/陆拓扑定义。所有图源、输入哈希和剩余风险记录在 `manuscript/internal_scientific_consistency_audit.md`。
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
    html = build_html(markdown).replace('<html lang="en">', '<html lang="zh-CN">')
    OUT_MD.write_text(markdown, encoding="utf-8")
    OUT_HTML.write_text(html, encoding="utf-8")
    render_pdf()
    ARCHIVE_DIR.joinpath("research_report.md").write_text(markdown, encoding="utf-8")
    ARCHIVE_DIR.joinpath("research_report.html").write_text(html, encoding="utf-8")
    shutil.copyfile(OUT_PDF, ARCHIVE_DIR / "research_report.pdf")
    print(f"Wrote {OUT_MD}, {OUT_HTML}, and {OUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
