# Combo 1 质量迭代日志

**目标**：回应“效果差、是否真实数据”——至少 4 轮审计与修复，直至科学上可辩护。  
**停止条件**：审计文档明确真实/衍生边界；Sheerness 淹没为真实 DeltaDTM；RP 图诚实说明产品差异；无静默单位/CRS 错误；`combo1_summary.json` 与 HTML 同步。

---

## Round 1 — 真实性审计（Truth audit）

**动作**  
- 新增 `scripts/combo1_quality_audit.py`，逐层读盘：GSSR CSV、COAST-RP.nc、Open-Meteo JSON、DeltaDTM GeoTIFF。  
- 撰写 `docs/combo1-quality-audit.md`（本文档姊妹篇，中文完整版）。

**发现**  
1. 四类数据 **全部真实存在**；Sheerness 淹没 **已用** `DeltaDTM_v1_1_N51E000.tif`。  
2. 欧洲 RP10 偏差 −2～−4 m：**产品定义差异**（skew surge vs storm tide），非 m/cm bug。  
3. US 站（NY、Charleston）RP10 偏差 < 0.5 m，反证单位处理基本正确。  
4. +2 m 淹没 ~50%：DEM median≈2 m + bathtub，非合成坡面。  
5. Open-Meteo 气压 952–1045 hPa，单位正确。

---

## Round 2 — 数据处理修复

| 修改 | 文件 |
| --- | --- |
| 匹配距离改 Haversine km | `combo1_utils.py`, `match_stations_to_coastrp.py` |
| 淹没：nodata(−9999) 掩膜、低地统计、DEM 元数据写入 JSON | `inundation_sensitivity.py` |
| 重跑 match / merge / inundation | 终端流水线 |

**未改（刻意）**  
- 不将 COAST-RP 强行换算为 skew surge（避免假一致）。  
- 不下载完整 Europe.zip（2.4 GB）；Sheerness bbox 仅 1 瓦片即覆盖。

---

## Round 3 — 可视化与分析改进

| 产出 | 说明 |
| --- | --- |
| `combo1_rp10_dual_region.png` | 欧洲 vs 美国分组，标注偏差 (m) |
| `combo1_hydrograph_sheerness.png` | 叠加 GSSR RP10 + COAST-RP storm-tide RP10 |
| `combo1_gssr_coastrp_validation.png` | 年均最大 vs RP10 散点（展示不可比性） |
| `inundation_sensitivity_*.png` | 地理 extent、直方图、双列淹没比例 |
| 更新 RP/多 RP 图 Y 轴标签 | `generate_combo1_figures.py` |

---

## Round 4 — HTML 与验证

| 修改 | 结果 |
| --- | --- |
| `generate_html_reports.py` | 新增 Quality audit、Data authenticity（哈希+高程统计） |
| 淹没表 | 分列 all valid / lowland ≤15 m |
| `python scripts/run_combo1_pipeline.py --skip-verify` | 全部步骤 OK |
| `python scripts/validate_standalone_html.py` | 4 个 HTML **OK** |
| `reports/combo1_complete_report.html` | ≈0.86 MB，离线可开 |

**`combo1_summary.json` 更新要点**  
- `inundation_dem_source`: `DeltaDTM:DeltaDTM_v1_1_N51E000.tif`  
- `figures`: 含 `combo1_rp10_dual_region.png`, `combo1_gssr_coastrp_validation.png`  
- `mean_rp10_bias_m`: −1.949 m（未人为篡改，因产品定义未变）

---

## Round 5 — 验收对照

| 验收项 | 状态 |
| --- | --- |
| 审计文档说明真实 vs 衍生 | ✅ `combo1-quality-audit.md` |
| Sheerness 河口可识别地形 | ✅ 真实 COG + lon/lat extent（非 generic slope） |
| RP 图有产品差异说明 | ✅ 双面板 + 完整报告 Methods |
| 无静默单位/CRS bug | ✅ 审计未发现；nodata/CRS 已记录 |
| summary 反映修正指标 | ✅ 含低地淹没分项、新图列表 |

**剩余局限（诚实保留）**  
- 不能做 GSSR⊗COAST-RP 绝对潮位验证。  
- Bathtub 静态淹没非动力预报。  
- SLR 为相对 DEM 偏移，未做 DATUM→MSL 联合改正。  
- 可选：加海岸线矢量、多瓦片拼接扩大图幅。

---

## 建议用户操作

1. 重新打开 **`reports/combo1_complete_report.html`**（`file://` 离线）。  
2. 阅读 **`docs/combo1-quality-audit.md`** 获取中文完整审计。  
3. 若需更好河口离岸对比，可运行（需带宽）：  
   `python scripts/download_deltadtm_tiles.py --station-id sheerness-p015-uk --download`

---

*末次流水线时间见 `data/processed/combo1_summary.json` → `generated_at`。*
