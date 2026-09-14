# Combo 1 产品定义说明（Methods 草稿）

**日期**：2026-05-22（审查迭代）  
**用途**：论文 Methods / Supplement 中解释 GSSR 与 COAST-RP 对比、静态淹没局限。

---

## 1. GSSR（Global Storm Surge Reconstruction）

| 项 | 说明 |
| --- | --- |
| 产品 | 验潮站尺度、**日最大偏斜潮/风暴潮重建**（skew surge / storm surge component） |
| 再分析 | 本 MVP 使用 **ERA5** 分支（`erafive/`，1979–2019） |
| 空间 | 离散验潮站（非规则网格） |
| 垂直 | 相对当地平均海平面附近（MSL 量级） |
| 极值 | 本流水线用**年最大序列 + 经验重现期**（Weibull 绘图位置）估计 RP10/50/100 |

**引用**：Tadesse & Wahl, *Scientific Data* 8, 125 (2021).

---

## 2. COAST-RP（Coastal Storm Surge Return Periods）

| 项 | 说明 |
| --- | --- |
| 产品 | **海岸点**（非验潮站）极端**风暴潮位**重现期 |
| 空间 | 全球海岸 1/12° 量级格点，与 GSSR 站**最近邻匹配**（报告 `match_dist_km`） |
| 变量 | `storm_tide_rp_XXXX`（含天文潮贡献的**总风暴潮位**极值统计） |
| 分集 | `COAST-RP.nc`（综合）、`COAST-RP_TC.nc`、`COAST-RP_ETC.nc` |

**引用**：Dullaart et al., *Communications Earth & Environment* 2, 221 (2021).

---

## 3. 为何 GSSR RP10 系统性低于 COAST-RP RP10（英国/欧洲站约 −2 至 −4 m）

以下差异**不应**解释为“某一产品错误”，而应在 Methods 中并列说明：

1. **物理量不同**：GSSR 强调**偏斜潮/风暴潮分量**；COAST-RP 为**风暴潮位（含潮）**极值分布——后者通常更高。
2. **空间代表**：验潮站 vs 最近海岸点（1/12°）；河口/内湾站与离岸海岸点高程与水动力不一致。
3. **统计方法**：GSSR 侧为**有限年数年最大 + 经验分位**；COAST-RP 为**区域极值理论拟合**的全球产品。
4. **样本期**：GSSR ERA5 约 1979–2019；Open-Meteo 气候态窗 1980–2010；COAST-RP 使用其自有极值样本（见原数据 README）。

**建议表述（英文草稿）**：

> We compare GSSR ERA5 skew-surge return levels at tide gauges with COAST-RP storm-tide return levels at the nearest coastal grid point. Systematic negative bias at North Sea stations is expected because the two products differ in surge definition, tidal inclusion, and spatial representativeness. We use the comparison as a **cross-product sensitivity check**, not as mutual validation of absolute elevation.

---

## 4. Open-Meteo ERA5（驱动因子）

- **不提供潮位**；仅 `pressure_msl`、风、降水等。
- 与 GSSR 做 **Spearman 相关**（日最大潮 vs 日最小气压 / 最大风速等），用于复合洪水**统计关联**，非替代水动力模拟。

---

## 5. DeltaDTM 与静态淹没

| 模式 | `dem_source` | 说明 |
| --- | --- | --- |
| 真实 COG | `DeltaDTM:DeltaDTM_v1_1_NxxExxx.tif` | 从 `Europe.zip` 等按 bbox **选择性解压**瓦片 |
| MVP 占位 | `synthetic_coastal_slope` | 简单离岸下坡面；**仅演示 bathtub 流程**，不可用于绝对淹没面积 |

- 垂直：DeltaDTM v1.1 为 **EGM2008** 高程；与 ESL 产品并置时需注明基准一致性。
- 方法：静态 bathtub `max(0, SLR − DEM)`；±0.5 / 1.0 / 2.0 m **相对海平面上升敏感性**，非预报。

**引用**：Pronk et al., *Scientific Data* 11, 273 (2024).

---

## 6. 图表与表格标注清单

| 图/表 | 必注 |
| --- | --- |
| `combo1_rp10_comparison.png` | 两产品定义不同；欧陆站偏差预期 |
| `combo1_hydrograph_sheerness.png` | GSSR 日最大偏斜潮序列 |
| `inundation_sensitivity_*.png` | DEM 来源（真实 / synthetic）；bathtub 非动力 |
| `rp_comparison.parquet` | 含 `match_dist_km`；>25 km 标 `match_flag=long` |

---

*与 `docs/combo1-implementation-guide.md` §2 对齐；流水线产出见 `data/processed/combo1_summary.json`。*
