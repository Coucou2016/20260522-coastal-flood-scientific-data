# Combo 1 数据质量审查报告（真实性审计）

**日期**：2026-05-22  
**范围**：GSSR、COAST-RP、Open-Meteo ERA5、DeltaDTM；8 个 MVP 验潮站 + Sheerness 淹没敏感性  
**结论摘要**：**四类原始数据均已落盘且被流水线实际读取**；此前“效果差”主要来自 **产品物理量不可直接对比** 与 **图表标注不足**，而非伪造数据。经四轮迭代后，图表与 HTML 报告已区分“真实数据 / 预期差异 / 方法局限”。

---

## 1. 各数据层真实性核查

### 1.1 GSSR（ERA5 分支）

| 检查项 | 结果 |
| --- | --- |
| 文件 | 8 个 `data/raw/gssr/era5/*.7z`，解压后 `extracted/*/ *.csv` |
| 变量 | `surge_reconsturcted`（拼写与源站一致）→ 脚本重命名为 `surge_m` |
| 单位 | **米 (m)**；Sheerness 全序列 min≈−0.22，max≈1.55，p99≈0.85 |
| 时间 | 1979-01-03 — 2019-12-31，每站约 14 973 日行 |
| CRS | 站点经纬度在 CSV 内；时间序列非栅格 |

**Sheerness 样本统计（审计脚本实测）**  
- 年最大偏斜潮：0.84–1.55 m（41 年）  
- 经验 RP10（年最大 + Weibull 绘图位置）：**1.33 m**

**判定**：✅ 真实 GSSR 产品；非模拟。

---

### 1.2 COAST-RP

| 检查项 | 结果 |
| --- | --- |
| 文件 | `data/raw/coast_rp/COAST-RP.zip` → `extracted/COAST-RP.nc`（≈2.8 MB） |
| 维度 | `stations` = 23 226 海岸点 |
| 变量 | `storm_tide_rp_0010` 等（**风暴潮位极值，含天文潮贡献**） |
| 全球 RP10 | min 0.031 m，max 9.343 m，mean 1.55 m（合理） |
| 匹配 | 最近邻海岸点；Sheerness 距站 **≈0.56 km**（Haversine 修正后） |

**Sheerness 对应海岸点 RP10**：**5.26 m**（storm tide）

**判定**：✅ 真实 NetCDF；变量选择与 Dullaart et al. (2021) 产品定义一致。

---

### 1.3 Open-Meteo ERA5

| 检查项 | 结果 |
| --- | --- |
| 文件 | 8 个 `*_1980-01-01_2010-12-31_era5.json` + Sheerness 事件窗 JSON |
| 气压 | `pressure_msl` 约 952–1045 → **hPa**，与 ERA5 一致 |
| 聚合 | 日最小气压、日最大风速、日降水累计 |
| 对齐 | 与 GSSR 按 `date`（UTC 日）内连接；每站约 11 323 重叠日 |

**判定**：✅ 真实 API 下载数据；**不提供潮位**，仅作驱动相关分析。

---

### 1.4 DeltaDTM

| 检查项 | 结果 |
| --- | --- |
| 索引 | `data/raw/deltadtm/index/deltadtm_tiles.gpkg` |
| Sheerness bbox 瓦片 | **1 块**：`DeltaDTM_v1_1_N51E000.tif`（≈10.3 MB COG） |
| CRS | EPSG:4326；nodata = **−9999** |
| 分辨率 | ≈0.42″×0.28″（~30 m 量级） |
| 窗口内有效像元 | **45.2%**（其余 nodata/海域掩膜） |
| 有效高程 | min −6.68 m，max 30 m，mean 3.88 m，**median 2.01 m**（EGM2008） |
| 低于 0 m 像元 | **0.68%**（非“整体 Datum 错误”） |

**判定**：✅ 淹没分析使用 **真实 DeltaDTM COG**；`dem_source` 为 `DeltaDTM:DeltaDTM_v1_1_N51E000.tif`。  
仅当瓦片缺失时脚本才回退 `synthetic_coastal_slope`（当前 Sheerness **未触发**）。

---

## 2. 淹没栅格是否使用真实 COG？

**是。** 审计读取与 `inundation_sensitivity.py` 相同路径的 GeoTIFF：

```
rasterio 统计（Sheerness ±0.05° 窗口）
  CRS: EPSG:4326
  nodata: -9999
  elev (valid): min -6.68, max 30.0, mean 3.88 m
  bathtub +2 m（有效像元）: 49.7% 像元水深 > 0
```

**原因说明（非单位 bug）**  
- 公式：`depth = max(0, SLR − DEM)`，+2 m 即“海面相对当前 DEM 抬高 2 m”的静态敏感性。  
- 泰晤士河口窗内 **约一半有效像元高程 < 2 m**（median≈2 m），故 +2 m 时低地像元大量被淹属 **bathtub 与地形共同结果**。  
- 图件已改为：地理坐标 `extent`、nodata 掩膜、**低地掩膜（elev≤15 m）** 分列统计、高程直方图。

**仍属局限（非 bug）**  
- 未做 MSL↔EGM2008 垂直基准转换；SLR 为相对偏移，非业务预报。  
- 无海岸线图层（可后续加 Natural Earth）；单瓦片覆盖 bbox 已足够识别河口台地形态。

---

## 3. RP10 对比“很差”（欧洲站 −2～−4 m）— bug 还是产品差异？

### 3.1 实测偏差（GSSR − COAST-RP，单位 m）

| 站点 | GSSR RP10 | COAST-RP RP10 | 偏差 |
| --- | ---: | ---: | ---: |
| Sheerness | 1.33 | 5.26 | **−3.93** |
| Newlyn | 0.61 | 3.35 | −2.74 |
| Aberdeen | 0.84 | 2.82 | −1.99 |
| Hoek v.H. | 1.50 | 3.37 | −1.87 |
| Brest | 0.68 | 4.31 | −3.63 |
| New York | 1.19 | 1.31 | **−0.12** |
| Hong Kong | 1.01 | 1.82 | −0.82 |
| Charleston | 0.84 | 1.35 | −0.51 |

### 3.2 根因（文献/产品定义，非 cm↔m 错误）

1. **物理量**：GSSR = **偏斜潮/风暴潮分量**；COAST-RP = **风暴潮位（含潮）** 重现期极值。  
2. **空间**：验潮站 vs 1/12° 海岸点（河口站与离岸点潮差不同）。  
3. **统计**：GSSR 侧 41 年年最大 + 经验分位；COAST-RP 为全球极值拟合产品。  
4. **美国站接近**：NY、Charleston 偏差 < 0.5 m，说明流水线 **无系统性单位错误**；欧洲站大偏差符合“不可直接验证”的预期。

**判定**：❌ 不是 RP 列号或 return period 取错；✅ 是 **产品不可比** + 原图未说明。  
**处理**：双区域 RP 图、水文过程线叠加 COAST-RP 阈值、验证散点图、HTML/Methods 诚实标注。

---

## 4. 图表合理性检查

### 4.1 Sheerness 水文过程线（GSSR）

- 日最大偏斜潮典型范围约 **−0.2～1.6 m**（非天文潮全水位 4–6 m）。  
- 与 GSSR 产品定义一致；99 分位 ≈ 0.85 m，RP10 ≈ 1.33 m。  
- 迭代后叠加：GSSR RP10、COAST-RP storm-tide RP10（紫色虚线，**不可与序列直接比高低**）。

### 4.2 淹没 +2 m → ~50% 像元

| 假设 | 是否成立 |
| --- | --- |
| DEM 垂直基准全错 | ❌ 仅 0.7% 像元 < 0 m |
| 掩膜错误 | ⚠️ 45% nodata；已掩膜，不再把 nodata 当陆地 |
| bathtub + 低洼河口平原 | ✅ 主因；median elev≈2 m |
| 用合成坡面 | ❌ 当前为真实 COG |

### 4.3 气象驱动相关

- 英国/荷兰/法国站：气压与潮位 Spearman **−0.5～−0.8**（物理合理）。  
- Charleston：相关接近 0（可能区域/风暴机制不同，非数据假）。

---

## 5. 具体问题清单：Bug vs 预期科学

| 类型 | 问题 | 状态 |
| --- | --- | --- |
| **预期科学** | GSSR skew surge vs COAST-RP storm tide 不可直接比 | 已用分区域图与文案说明 |
| **预期科学** | 静态 bathtub 高估连通淹没 | Methods 已标注 |
| **预期科学** | Pearson RP10≈0.11（跨产品） | 不作为验证指标 |
| **已修复** | 匹配距离用 deg×111 近似 | → Haversine km |
| **已修复** | 淹没图无坐标/extent、无 nodata | → extent + 掩膜 + 直方图 |
| **已修复** | RP/水文图 Y 轴标签误导 | → 区分 skew surge / storm tide |
| **已修复** | HTML 无真实性证明 | → 哈希表 + 审计章节 |
| **非 bug** | 欧洲站 RP 大负偏差 | 产品差异 |
| **局限** | 单瓦片、无海岸线矢量 | 可扩展下载，非阻塞 |

---

## 6. 数据真实性证明（摘要表）

| 资产 | 路径 | 规模/统计 |
| --- | --- | --- |
| GSSR Sheerness | `sheerness_p015_uk.7z` | 409 263 B；sha256(head)=eec0b411958455a7 |
| COAST-RP | `COAST-RP.nc` | 2 817 029 B |
| Open-Meteo | `sheerness-p015-uk_1980-..._era5.json` | pressure 952–1045 hPa |
| DeltaDTM | `DeltaDTM_v1_1_N51E000.tif` | 10 258 832 B；median elev 2.01 m |

完整表见 `reports/combo1_complete_report.html` 章节 **Quality audit / Data authenticity**。

---

## 7. 审查结论

1. **数据是真实的**——四类源数据均来自公开产品且文件哈希/统计可复现。  
2. **“效果差”的主要原因**是跨产品对比与静态淹没方法未在图中充分披露，而非随机/假数据。  
3. 经修复后，成果可用于 **交叉敏感性、驱动相关、河口地形静态 SLR 筛查**；**不可**用于“GSSR 验证 COAST-RP 绝对潮位”或“业务淹没预报”。

*审计脚本：`scripts/combo1_quality_audit.py`；流水线：`scripts/run_combo1_pipeline.py`。*
