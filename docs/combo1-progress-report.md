# Combo 1 进展报告（中文）

**更新日期**：2026-05-22（真实 DEM + HTML 报告系统）  
**工作区**：`e:\Projects\20260522-coastal-flood-scientific-data`

---

## 进展摘要

| 维度 | 完成度 | 说明 |
| --- | ---: | --- |
| MVP 数据下载（P0–P1） | **100%** | COAST-RP、8 站 GSSR、DeltaDTM 索引、Open-Meteo、**Europe.zip 完整** |
| 处理与分析流水线（P2–P3） | **100%** | `run_combo1_pipeline.py` 全绿；5 张图 + `combo1_summary.json` |
| 真实 DeltaDTM 淹没 | **100%** | `DeltaDTM_v1_1_N51E000.tif`；修复瓦片路径匹配后重跑 |
| 浏览器 HTML 报告 | **100%** | `reports/index.html` + 6 阶段页；流水线末尾自动再生 |
| 论文 Methods 文稿 | **~40%** | `combo1-product-definitions.md` 已就绪 |
| **综合（Combo 1 MVP）** | **~95%** | 文稿与可选验证集为剩余项 |

---

## 已完成

### 数据

- COAST-RP NetCDF（解压后 ~2.8 MB）
- GSSR ERA5：8 站 `.7z` + CSV（7-Zip CLI 解压，`py7zr`/lzma 已绕过）
- Open-Meteo：8 站 × 1980–2010 气候态（~245 MB）
- DeltaDTM：`deltadtm_tiles.gpkg` 索引

### 处理产出（`data/processed/`）

| 文件 | 说明 |
| --- | --- |
| `coast_rp_nearest.parquet` | 8 站最近邻 COAST-RP；含 `match_dist_km`、`match_flag` |
| `gssr_daily_merged.parquet` | 119,784 行日最大偏斜潮 |
| `rp_comparison.parquet` | GSSR vs COAST-RP RP10/100 偏差 |
| `drivers_daily.parquet` | 90,584 行气象驱动日表 |
| `driver_surge_correlations.parquet` | 8 站 Spearman 相关 |
| `inundation_sensitivity.json` | Sheerness 静态淹没（**真实 DeltaDTM COG**） |
| `combo1_summary.json` | 流水线汇总（含 `html_reports` 列表） |

### HTML 报告（`reports/`）

| 文件 | 用途 |
| --- | --- |
| `index.html` | 主索引 + 最后更新时间 |
| `stage0` … `stage4_*.html` | 各阶段表格与嵌入图 |
| `combo1_full_summary.html` | 执行摘要 |

浏览器打开：`start reports\index.html`（无需服务器）。

### 图表（`figures/`）

| 图 | 用途 |
| --- | --- |
| `combo1_rp10_comparison.png` | GSSR vs COAST-RP RP10 |
| `combo1_rp_multi_station.png` | RP10/50/100 多站对比 |
| `combo1_driver_correlation_heatmap.png` | 驱动–潮 Spearman 热力图 |
| `combo1_hydrograph_sheerness.png` | Sheerness GSSR 日序列 |
| `inundation_sensitivity_sheerness-p015-uk.png` | 真实 DEM + SLR +0.5/1/2 m |

### 本轮改进（审查迭代）

1. 新增 `scripts/download_deltadtm_tiles.py` — 按站点 bbox 列出/解压瓦片（避免下载全球 36 GB）
2. 新增 `scripts/combo1_status.py` — 一屏进度看板
3. 强化 `run_combo1_pipeline.py` 日志（逐步耗时、错误尾部）
4. 新增 `docs/combo1-product-definitions.md` — GSSR vs COAST-RP Methods 说明
5. 淹没图与 RP 图增加科学免责声明
6. 站匹配增加 `match_flag`（>25 km 告警；当前 8 站均为 `ok`）
7. 新增 `scripts/generate_html_reports.py` — 7 个独立 HTML + `style.css`
8. 修复 `inundation_sensitivity.py` 瓦片 glob（索引列为完整 `.tif` 文件名）
9. 扩展 `generate_combo1_figures.py`：多 RP 对比、驱动相关热力图

---

## 待办 / 阻塞

| 优先级 | 项 | 操作 |
| --- | --- | --- |
| 中 | GSSR–COAST-RP 定义差 | 写作时引用 `docs/combo1-product-definitions.md` |
| 低 | `py7zr` / `_lzma` | 保持 7-Zip 在 PATH 即可 |
| 低 | Open-Meteo 429 | 批量下载用 `--sleep 8` |
| 可选 | CoDEC/GESLA 验证 | 非 Combo 1 MVP |

---

## 关键科学结论（当前数据）

- **RP10 平均偏差**：约 **−1.95 m**（GSSR 低于 COAST-RP）；英荷站约 −2 至 −4 m，符合“偏斜潮 vs 含潮风暴潮位”预期。
- **Pearson RP10（8 站）**：约 **0.11**（不显著）；不宜作为绝对水位互验。
- **驱动相关**：北海/欧洲站气压–潮 Spearman **−0.72 至 −0.83**；美东/香港相关弱。
- **淹没（真实 DeltaDTM）**：Sheerness +0.5 m **2.5%**、+1 m **11.7%**、+2 m **49.7%** 网格淹没（bathtub，非动力）。

---

## 下一步命令

```powershell
cd e:\Projects\20260522-coastal-flood-scientific-data

# 一屏进度
python scripts\combo1_status.py

# 全流水线（处理 + 5 图 + HTML 报告）
python scripts\run_combo1_pipeline.py

# 仅刷新 HTML（不改处理结果时）
python scripts\generate_html_reports.py

# 浏览器打开报告索引
start reports\index.html
```

---

## 文档索引

| 文档 | 内容 |
| --- | --- |
| `docs/combo1-execution-log.md` | 执行日志 + 审查迭代 |
| `docs/combo1-implementation-guide.md` | 实施指南 |
| `docs/combo1-product-definitions.md` | 产品定义（Methods） |
| `logs/combo1-run-20260522.md` | 最近一次流水线逐步耗时 |

---

*由自动化审查生成；复现以 `python scripts\run_combo1_pipeline.py` 为准。*
