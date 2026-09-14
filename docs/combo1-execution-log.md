# Combo 1 执行日志

**日期**：2026-05-22  
**工作区**：`e:\Projects\20260522-coastal-flood-scientific-data`  
**执行者**：自动化流水线（Cursor Agent）

---

## 阶段结果总览


| 阶段              | 状态   | 说明                                                                                      |
| --------------- | ---- | --------------------------------------------------------------------------------------- |
| Round 0 环境      | ✅ 成功 | Python 3.13 + requirements 核心包可用；`py7zr` 因 `_lzma` DLL 失败，改用 MATLAB 自带 `7z.exe` 解压 GSSR |
| Round 1 数据获取    | ✅ 成功 | MVP-min 全部通过 `verify_downloads.py --strict`；Open-Meteo 首轮 429 限流，重试后 8 站气候态完成           |
| Round 2 处理流水线   | ✅ 成功 | 新建 6 个脚本 + `combo1_utils.py`；`run_combo1_pipeline.py` 一键运行                              |
| Round 3 分析与 QC  | ✅ 成功 | 汇总 JSON、RP 对比、驱动相关、3 张图                                                                 |
| Round 4 自审（3 轮） | ✅ 完成 | 见下文                                                                                     |


**磁盘占用（约）**：0.27 GB（raw ~276 MB，其中 Open-Meteo ~245 MB）

---

## Round 1：下载明细

```powershell
python scripts\download_combo1.py --tier mvp-min --extract
python scripts\download_open_meteo.py --mode climatology --sleep 5   # 首轮部分 429
# 65s 等待后重试失败站点：
python scripts\download_open_meteo.py --mode climatology --sleep 8 --station-id aberdeen-p038-uk ...
python scripts\verify_downloads.py --strict
```


| 数据集            | 路径                                              | 大小（约）    |
| -------------- | ----------------------------------------------- | -------- |
| COAST-RP       | `data/raw/coast_rp/extracted/COAST-RP.nc`       | 2.8 MB   |
| GSSR ×8        | `data/raw/gssr/era5/*.7z` + `extracted/`        | 15 MB    |
| DeltaDTM 索引    | `data/raw/deltadtm/index/deltadtm_tiles.gpkg`   | 2.9 MB   |
| Open-Meteo 气候态 | `data/raw/open_meteo/hourly/*_1980-2010_*.json` | 8×~31 MB |


**未下载**：`Europe.zip`（2.4 GB）、全球 DeltaDTM（36 GB）— 按 MVP 约束仅用索引 + 合成 DEM 做淹没敏感性。

---

## Round 2–3：流水线产出

```powershell
python scripts\run_combo1_pipeline.py
```


| 产出              | 路径                                                     |
| --------------- | ------------------------------------------------------ |
| 站–COAST-RP 匹配   | `data/processed/coast_rp_nearest.parquet`              |
| GSSR 日序列合并      | `data/processed/gssr_daily_merged.parquet`（119,784 行）  |
| RP 对比表          | `data/processed/rp_comparison.parquet`                 |
| 气象驱动日表          | `data/processed/drivers_daily.parquet`（90,584 行）       |
| 驱动–潮相关          | `data/processed/driver_surge_correlations.parquet`     |
| 淹没敏感性           | `data/processed/inundation_sensitivity.json`           |
| **汇总**          | `data/processed/combo1_summary.json`                   |
| RP10 柱状图        | `figures/combo1_rp10_comparison.png`                   |
| Sheerness 水文过程线 | `figures/combo1_hydrograph_sheerness.png`              |
| 淹没敏感性图          | `figures/inundation_sensitivity_sheerness-p015-uk.png` |
| 运行日志            | `logs/combo1-run-20260522.md`                          |


---

## 关键科学 QC 备注

1. **GSSR vs COAST-RP RP 偏差**：英国/欧洲站 `rp10_bias` 约 −2 至 −4 m。符合预期——GSSR 为**偏斜潮/风暴潮重建**，COAST-RP 为**风暴潮位（含潮）**；对比应作为方法敏感性说明，非直接等同。
2. **US 站（New York、Charleston）**：RP10 偏差 <0.6 m，Pearson RP10 ≈ 0.11（n=8，不显著）。
3. **驱动相关**：欧洲站 `spearman_surge_vs_pressure` 强负相关（−0.72 至 −0.83），与低压–风暴潮物理一致。
4. **DeltaDTM 淹没**：无本地 COG 瓦片时使用 `synthetic_coastal_slope`；Sheerness bbox 内索引瓦片 4 个。要真实地形需 `mvp-terrain` 或按瓦片下载。

---

## 三轮自审记录

### Pass 1（首次全流水线）

- `merge_gssr_coastrp.py`：`surge.dt.year` 在 Series 上报错 → 已修复为按 `date` 列分组。
- Open-Meteo 默认 `--sleep 1` 触发 429 → 改为 5s + urllib3 重试。
- `py7zr`/`lzma` 在 Windows 上不可用 → `combo1_utils.extract_gssr_archive` 回退 7-Zip CLI。

### Pass 2（匹配 / CRS）

- 核实 COAST-RP `station_x_coordinate`/`station_y_coordinate` 为 lon/lat（WGS84）；最近邻距离 UK 站 <2 km。
- KDTree 查询顺序 `[lon, lat]` 与数据集一致。

### Pass 3（性能 / 磁盘）

- 未下载 Europe.zip；淹没脚本仅读 bbox 相交瓦片路径，缺失时用合成 DEM。
- Open-Meteo 按站单文件 ~31 MB（31 年逐时），共 ~245 MB；可改为按年分块以减峰值内存（未实施，留作扩展）。

---

## 阻塞项与需用户操作


| 项                 | 严重性   | 建议                                                                        |
| ----------------- | ----- | ------------------------------------------------------------------------- |
| `py7zr` / `_lzma` | 低     | 安装完整 Python lzma 支持，或保持 7-Zip 在 PATH                                      |
| 真实 DeltaDTM 淹没    | 中     | `python scripts\download_combo1.py --tier mvp-terrain --extract`（+2.4 GB） |
| GSSR–COAST-RP 定义差 | 中（科学） | 论文 Methods 中明确产品定义与偏差解释                                                   |
| Open-Meteo 速率     | 低     | 批量下载时 `--sleep 8` 或更大                                                     |


---

## 下一步

1. 可选：`mvp-terrain` 下载后重跑 `inundation_sensitivity.py` 使用真实 COG。
2. 扩展 `match_stations_to_coastrp.py`：报告匹配距离 >25 km 的站为 flagged。
3. 将 RP 对比与驱动相关写入论文 Fig.4 / Suppl. 模板。

---

## 审查迭代（2026-05-22 第二轮）

### 迭代 1 — 状态审计

- **MVP 流水线**：P0–P3 约 **85%**（数据+处理+图表完成；真实 DTM 与文稿未齐）
- **可用**：GSSR 合并、COAST-RP 匹配、驱动相关、RP 对比、合成 DEM 淹没敏感性
- **占位/弱项**：`synthetic_coastal_slope` 淹没图；GSSR–COAST-RP 不可直接等同；无 CoDEC/GESLA

### 迭代 2 — 高影响修补

| 改动 | 说明 |
| --- | --- |
| `scripts/download_deltadtm_tiles.py` | 按站点 bbox 从 `Europe.zip` **选择性解压**（Sheerness 仅需 `DeltaDTM_v1_1_N51E000.tif`） |
| `download_combo1.py --tiles-station` | 同上入口 |
| `docs/combo1-product-definitions.md` | Methods：GSSR 偏斜潮 vs COAST-RP 含潮风暴潮位 |
| `match_stations_to_coastrp.py` | 新增 `match_flag`（>25 km → `long`）；当前 8 站均 <6 km |
| 图表 | RP/淹没图增加产品定义与 SYNTHETIC 标注 |

**DeltaDTM 下载**：已后台启动 `Europe.zip`（~2.4 GB）；完成后执行 `inundation_sensitivity.py` 重跑。

### 迭代 3 — 流水线加固

- `run_combo1_pipeline.py`：逐步耗时表、捕获 stderr 尾部、`inundation_dem_source` 写入 summary
- `scripts/combo1_status.py`：一屏进度看板
- **复跑结果**：`verify_downloads --strict` 全绿；5 步处理 **全部 OK**（~46 s）

### 迭代 4 — 文档

- 本段「审查迭代」
- 中文报告：`docs/combo1-progress-report.md`

---

*本日志由自动化执行生成；复现请运行 `python scripts\run_combo1_pipeline.py`；进度看板：`python scripts\combo1_status.py`。*