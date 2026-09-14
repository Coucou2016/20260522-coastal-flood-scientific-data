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
    block = pd.read_csv(SOURCE / "Spatial_sector_bootstrap_intervals.csv")
    topk = pd.read_csv(SOURCE / "Topk_spatial_null_curves.csv")
    rp = pd.read_csv(SOURCE / "Return_period_sensitivity.csv")
    moran = pd.read_csv(SOURCE / "Spatial_autocorrelation_moran.csv")
    denominator = pd.read_csv(SOURCE / "Denominator_adjusted_associations.csv")
    topology = pd.read_csv(SOURCE / "Topology_sensitivity_summary.csv")
    primary = pd.read_csv(SOURCE / "Primary_terrain_components_68stations.csv")
    cases = pd.read_csv(SOURCE / "Fig3_predefined_site_selection.csv")
    local = pd.read_csv(SOURCE / "TableS_local_dtm_product_datum_crosscheck.csv")

    base_setting = "primary:10km,2m,4n,adaptive,match<=6km"
    base = rank[rank["setting"].eq(base_setting)][
        ["terrain_metric", "n_sites", "spearman", "kendall", "permutation_two_sided_p", "top_n", "top_overlap", "top_overlap_expected_independent"]
    ].merge(
        block[["terrain_metric", "spearman_sector_bootstrap_p025", "spearman_sector_bootstrap_p975"]],
        on="terrain_metric",
    ).merge(
        rp[rp["return_period_years"].eq(10)][
            ["terrain_metric", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p"]
        ],
        on="terrain_metric",
    )
    base.columns = [
        "地形指标",
        "站点数",
        "Spearman rho",
        "Kendall tau",
        "非空间站点置换 p（审计）",
        "Top-set 大小",
        "实际重合",
        "独立随机期望重合",
        "六岸段区间 2.5%",
        "六岸段区间 97.5%",
        "岸段调整秩关联",
        "岸段内置换 p",
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

    top20 = topk[topk["top_share_pct"].eq(20)].copy()
    rp_summary = rp[
        rp["terrain_metric_label"].isin(["lowland_prevalence", "conditional_connectivity", "connected_lowland_share", "connected_area"])
    ][["return_period_years", "terrain_metric_label", "spearman", "sector_adjusted_rank_association", "sector_stratified_permutation_two_sided_p"]]

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
    topology_table.columns = ["地形指标", "站点数", "4n与8n排名rho", "Top-set大小", "Top-set重合", "成员变化数", "最大8n-4n差值", "中位8n-4n差值"]

    return f"""# Northwest Europe 海岸洪水筛查研究报告

**报告性质：** 科研过程、方法、数据、结果与审计证据的完整归档版  
**对应论文：** *Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network*  
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

区域主流程采用固定 10 km 窗口、官方 water mask、4-neighbour graph（四邻域图，像元只能通过公共边相连）和 2 m EGM2008 terrain threshold（地形高程阈值）。这个 2 m 数值不是 COAST-RP 事件水面，也没有与地方平均海平面拼接。10 年重现期 storm tide 与 connected land share 的 Spearman rho 为 -0.33，与 connected area 的 rho 为 -0.34；但按六个岸段进行 block resampling 后，95% 范围均跨 0。指标拆解显示，关系主要来自 lowland prevalence（rho=-0.31），而 conditional connectivity（rho=0.10）与 storm tide 没有单调关系。

storm-tide top-20% 与 connected-land top-20% 各含 14 个站，只重合 1 个；在保持岸段结构的置换零模型中，该重合仍处于 95% 包络内（lower-tail p = {float(top20.iloc[0]['sector_stratified_lower_tail_p']):.3f}）。从 RP2 到 RP100，复合地形指标相关约为 -0.36 至 -0.32。正确结论是两个透明筛查维度在当前样本网络中 non-interchangeable（不可互换），而不是“错配显著超过空间随机”或“两个指标已经被证明能预测真实洪水”。

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
4. 用岸段内置换、岸段区块重采样、Moran's I 和站点 jackknife 约束统计表述。
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

68 站并不是 Northwest Europe 海岸线的均匀抽样。候选点来自 GSSR metadata inventory，英国、English Channel 与 southern North Sea 站点较密，Denmark-Norway 岸段只有 2 站。后续空间不确定性分析必须承认这种网络结构，不能把 68 个点当成完全独立、等代表性的样本。

### 表3 DeltaDTM 版本审计

{table(product)}

2024 DeltaDTM 论文描述 v1.0 的约 10 m + MSL 产品范围，而实际下载 GeoTIFF 与 README 标明 v1.1.1、EGM2008 和 30 m cap。旧稿把文献中的 v1.0 cutoff 直接套到 v1.1.1 上，会造成版本混淆。新流程以实际文件 tag 与 v1.1 README 为准，同时在正文中主动说明两者差别。

## 研究过程

### 第一步：发现并修正 mask 填充值冲突

旧工作流使用 255 作为 boundless read 或 reprojection fill；但 255 同时是 DeltaDTM 官方 clipped class。这样会让“窗口外没有数据”看起来像“产品裁剪地形”。本轮把内部 outside-support sentinel 改为 254，并扫描 72 个已提取官方 mask tile。扫描未发现真实 255。当前 68 个主窗口共记录 3,320 个 254 cells 和 0 个官方 255 cells；所有 254/255、水体和湖泊均不进入陆地分母。

### 第二步：冻结唯一主流程

主流程固定为 10 km 窗口、2 m EGM2008、4-neighbour、official adaptive marine seed、COAST-RP match 小于等于 6 km。四邻域避免只在角点接触的像元打开整片低地；8-neighbour 仅作为拓扑敏感性。旧 0.03/0.04/0.06 degree windows、15 m denominator 和历史 boundary-no-data seed 结果不再与主结果混用。完整 terrain grid 保存 74 站乘 40 配置，共 2,960 行。

### 第三步：拆解指标

原 connected fraction 不能单独表示“连通性”，因为它同时受低地面积和连通率控制。新流程定义：

**f_low(eta) = A(z <= eta) / A(reference land)**

它表示 represented land 中低于阈值的比例。现实含义是“窗口里到底有多少低地”。

**p_conn(eta) = A(connected and z <= eta) / A(z <= eta)**

它表示已经低于阈值的土地中，有多少属于 ocean-seeded raster component。现实含义是“现有低地在这个静态拓扑规则下有多少接海”。

**f_conn(eta) = f_low(eta) x p_conn(eta)**

它是前两者的乘积，即 connected below-threshold land 占 represented land 的比例。绝对连接面积 A_conn 另行报告，防止小分母产生高比例却对应很小面积。

### 第四步：全样本稳健性与空间推断

所有参数变体都在区域样本上重跑。within-sector permutation（岸段内置换）在保持岸段组成的情况下检验条件关联；six-sector block bootstrap（六岸段区块重采样）检验如果抽到的地理岸段构成发生变化，rho 会变化多大。两者回答不同问题：前者针对当前空间组成，后者针对区域可推广性。

Top-k overlap 的主零模型也采用岸段内置换，使 terrain top values 只在同岸段站点之间交换。精确 hypergeometric null 仅作为非空间描述对照。68 站、每组 14 站时，非空间独立随机期望重合为 14 x 14 / 68 = 2.88，但论文推断以空间约束包络为准。

## 方法

### 海洋种子和连接图

官方 mask class 1 ocean 是基础 seed。class 3 river 只有在其 component 与 ocean 相连时才加入。若 10 km 窗口内没有 ocean，算法逐级扩展到 25、50、100、200 km mask context，找到 ocean-connected water component 后投影回 10 km 窗口。lake、clipped、outside support 和 arbitrary no-data 不可成为海洋入口。

对低于 eta 的 class-0 land 使用 4-neighbour 图进行主计算；8-neighbour 作为灵敏度检验。8-neighbour 允许角点接触，可能打开 narrow diagonal path。实算显示两种拓扑的地形排名 rho=0.96，但 top-20% 有 6 次成员变化，因此论文同时报告区域稳定性和站点级变化。

### 统计量

主文同时报告 raw magnitude-terrain Spearman rho、Kendall tau、10,000 次岸段内双侧置换 p、2,000 次六岸段 bootstrap range、top-10% 到 top-40% spatial null envelope、sector-adjusted rank association、Moran's I、terrain rank stability 和 top-20% Jaccard。非空间 station-label p 与 exact hypergeometric 仅保留为审计对照，不能替代空间结果。

## 结果展示与图表解析

### 图1 研究区、岸段与样本流

{image("图1. Northwest Europe 68站空间分布和样本流", "Fig1_process_terrain_design.png")}

这张图的作用是先回答“样本从哪里来、空间上怎么分布”。左图使用真实地图底图，点颜色不是风险等级，而是 six coastal sectors。黑色三角、方框和星形分别标出 storm-tide top set、terrain top set 和 overlap。它让读者一眼看到两点：第一，网络空间分布不均；第二，高水位和高标准化地形易感性符号并不集中在同一组点上。

右侧流程图把样本筛选写成可核查数字。74 个区域候选站都有 DeltaDTM support 和 marine seed；COAST-RP 匹配限制后剩 68；GSSR 记录长度与重建相关门槛只用于 supporting subset，剩 44。这里特别强调区域主分析虽从 GSSR station inventory 出发，却不要求每站具有合格 GSSR return level，防止读者误以为主排名是四产品共同交集。

### 图2 区域弱一致性及其统计边界

{image("图2. storm-tide magnitude 与标准化地形易感性的区域弱一致性", "Fig2_regional_screening_agreement.png")}

Panel a 展示原始 COAST-RP magnitude 与 connected land share。纵轴采用普通 logarithmic display，使 0.1%、1%、10% 和 100% 可同时阅读；所有点大小固定，避免读者把视觉面积误认为额外变量，颜色沿用图1岸段。Newport 位于“高水位、极低地形占比”，Delfzijl 位于“中等水位、极高地形占比”。

Panel b 是本研究最重要的统计解释。connected share、below-2 m share 和 connected area 的站点 rho 大约为 -0.31 到 -0.34，岸段内置换 p 小于 0.001；但灰色 six-sector block range 全部跨 0。conditional connection 的点估计为 0.10，岸段内置换 p=0.420。通俗地说：当前网络内部存在负斜率，但改变岸段构成后关系不够稳定，不能写成普遍区域定律。

Panel c 检查“1/14 重合”是否真的异常。蓝线始终位于灰色 95% within-sector null envelope 内，所以正确表述是 water-level list 不能恢复 terrain list，而不是 observed mismatch 显著超出空间随机。Panel d 显示 RP2-RP100：复合地形占比和面积的 rho 约为 -0.36 至 -0.32，conditional connectivity 始终约 0.10。重现期选择不是主要不确定性来源。

### 表4 主统计结果

{table(base)}

### 表5 重现期与空间约束稳健性

{table(rp_summary)}

Moran's I 结果显示 150 km 邻域下 storm tide 为 0.30、lowland prevalence 为 0.76、connected land share 为 0.55，而 conditional connectivity 为 -0.02。前几项具有明显空间聚集，解释了为什么必须同时呈现岸段内置换与岸段区块区间。

### 表6 分母覆盖诊断

{table(denominator_table)}

RP10 与窗口内 represented-land 比例几乎无关（rho=0.003）。控制这一比例后，connected-land share 的 rho 由 -0.333 变为 -0.336，说明当前负关联并不是由不同站点窗口中“可用陆地占比”机械制造出来的。不过，该诊断不能消除高程产品和垂向基准误差，只能排除一个具体的分母几何混杂来源。

### 表7 4/8 邻域拓扑诊断

{table(topology_table)}

4 邻域与 8 邻域的区域排名总体接近，但 connected-land share 的 top-20% 仍有 6 次成员变化，单站差值最高为 44.1 个百分点。这说明“区域总体关联的符号相近”不等于“每个站点优先级都稳定”，所以主文采用更严格的 4 邻域，并公开 8 邻域结果作为敏感性而非替代主结果。

### 图3 三种机制而不是三个“好看案例”

{image("图3. Delfzijl、Newport 与 Immingham 的9子图机制解释", "Fig3_connected_terrain_contrasts.png")}

Figure 3 使用 3 x 3 结构，但每一行承担固定任务。第一行是实际 raster classification；第二行拆成 f_low、p_conn 和 f_conn；第三行显示 threshold response。这样设计是为了解决旧图“一个站全蓝、另一个几乎看不到蓝色”的读图问题，同时不改变像元分类。

Delfzijl 是稳定的 terrain-priority case。97.00% represented land 低于 2 m，其中 99.69% 属于海洋种子连通 component，所以 connected share 为 96.70%（61.30 km2）。它的水位排名为 26/68、地形排名为 1/68。主图大面积蓝色是原始分类结果；地方 DTM 的四邻域 cross-check 仍为 89.78%，因此没有为了视觉平衡缩小蓝色面积。

Newport 是 high-water, lowland-limited case。它的 RP10 为 8.60 m、排名 3/68，但低于 2 m 的 represented land 只有 0.164%。条件连通率为 90.53%；最终 connected share 只有 0.148%，是因为低地少，不是因为海洋连通差。主地图保持原始小面积，inset 只放大原像元位置，不扩大面积。

Immingham 是 connectivity-filtered case。低于 2 m 的 represented land 有 20.14%，但条件连通率仅 2.01%，因此图中橙色未连接低地很多，蓝色连接面积很少。它与 Newport 的最终 connected share 都低，但物理原因相反。这正是指标拆解的必要性。第三行不再画类似置信区间的阴影，而是分别给出 baseline、DEM -0.5 m 和 DEM +0.5 m 三条实算曲线。

### 表8 Figure 3 数据

{table(case_table)}

### 图4 指标分解、窗口支持与方法敏感性

{image("图4. 标准化地形指标的分解与全样本稳健性", "Fig4_metric_decomposition_robustness.png")}

Panel a 将 lowland prevalence 与 conditional connectivity 放在同一相空间中，说明两个分量可以独立变化。Panel b 检查窗口中 represented land 的比例是否机械驱动主关联；调整这一比例后，connected-share rho 仅从 -0.33 变为 -0.34。Panel c 比较 4-neighbour 主值和 8-neighbour 灵敏度：整体排名 rho=0.96，但 top-20% 有 6 次成员变化，最大站点差异达到 44.1 个百分点。Panel d 汇总窗口、阈值、邻域、seed、±0.5/±1 m 和匹配距离的完整单因素网格。

图4把论文核心稳健性放在主文，而将七站地方 DTM 对照降到 Supplementary Figure S4。后者仍然重要，但其差异同时包含 elevation product、native datum、horizontal resolution 和 provider WCS resampling；未统一 EGM2008、ODN 和 NAP 前，不能承担主结论或建立绝对准确性排名。

### 表9 七站交叉检查（补充敏感性）

{table(local_table)}

### 表10 connected land share 全样本敏感性

{table(connected_sens)}

## 综合分析与讨论

### 不同不等于已经证明互补

两个排序不同，可能因为它们代表不同而有用的物理维度，也可能因为其中一个受产品误差影响，还可能只是统计上低相关。当前没有独立真实洪水 outcome，不能证明把二者组合后 predictive prioritization 一定提高。因此论文采用 non-interchangeability，而不使用 proven complementarity、distortion 或 mis-rank。

### 静态连通不等于真实淹没

蓝色 connected cells 只表示在指定 raster、seed、threshold 和邻域下共享一个连通 component。它没有模拟水量是否足够、洪水需要多久到达、堤防是否失效、排水是否反向、闸门是否关闭或波浪是否越顶。低地深处出现蓝色可以是河道连通，也可以是 DEM 对 barrier 表达不足；必须结合 seed audit、4/8-neighbour 和 local terrain 检查。

### 为什么报告比例和面积

比例高不一定面积大，面积大也不一定占窗口土地比例高。connected share 更接近“represented landscape 中响应有多普遍”，A_conn 更接近“绝对潜在面积”。两者均给出相似站点层面负关联，但空间区间均跨 0，所以不会选其中一个作为唯一真值。

## 主要结论

1. 在 68 个 Northwest Europe 站点中，COAST-RP storm-tide magnitude 没有稳定恢复 DeltaDTM standardized terrain-susceptibility ranking。
2. composite connected share 的区域变化主要由 lowland prevalence 驱动；conditional connectivity 与 storm tide 基本无单调关系。
3. 1/14 top-set overlap 是描述性差异，但没有低于保持岸段结构的 spatial null envelope。
4. 窗口、阈值和 4/8-neighbour 会改变部分站点排名，因此区域结论与站点优先级的稳健性必须分开报告。
5. national/local DTM cross-check 显示产品和垂向基准可大幅改变多个站点结果；未统一 datum 前不能称为 validation。
6. 最合理的应用是并列报告 water-level screen 与分解后的 terrain components，再决定哪些站点进入局地水动力建模。

## 不足与展望

### 表11 投稿前不足、目标与验收条件

| 事项 | 当前状态 | 可验收目标 |
|---|---|---|
| 垂向基准 | DeltaDTM/ODN/NAP 未统一 | 至少 3 个英国和 3 个荷兰 case 转换到共同 local-MSL reference，记录 offset 来源、公式和不确定性并重算 Supplementary Figure S4 |
| 独立真值 | 没有 observed/dynamic flood outcome | 预先定义评价指标，对 water-only、terrain-only、combined screen 做外部 benchmark；完成前不声称 predictive complementarity |
| 样本代表性 | GSSR inventory 派生且空间聚集 | 使用独立 coastal inventory 或 shoreline sample，公开全部候选、排除理由和 spacing/sector coverage |
| 地方DTM服务 | WCS 插值核由服务端控制 | 获取 native-resolution tiles 或可声明 kernel 的本地重采样流程，固定 target grid、origin 和 CRS |
| 公开复现 | GitHub 公开仓库已建立，发布包通过凭据扫描 | 从公开仓库的新克隆执行一条命令，重建 source tables、figures 和文档；正式归档 DOI 尚待版本冻结后生成 |
| 作者元数据 | 待补充 | HTML、MD、PDF 中 authors、affiliations、funding、contributions 无占位符 |

## 复现与验收

主重算入口为 `python scripts/rebuild_frozen_primary_analysis.py`，地方地形交叉检查为 `python scripts/add_local_dtm_validation.py`，主图为 `python scripts/make_major_revision_figures.py`。科学约束测试要求 2,960 行完整、connected area 不超过 below area、4-neighbour 不超过 8-neighbour、f_conn 恒等式误差小于 1e-10。所有图的 source tables、input hashes 和当前剩余风险记录在 `manuscript/scientific_integrity_review.md`。
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
