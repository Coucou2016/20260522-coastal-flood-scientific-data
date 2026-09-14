# Combo 1 结果索引

**更新**：2026-05-22（独立 HTML 完整报告）  
**工作区**：`e:\Projects\20260522-coastal-flood-scientific-data`

---

## 当前进度（一览）

| 维度 | 完成度 | 状态 |
| --- | ---: | --- |
| MVP 流水线（P0–P3：下载 + 处理 + 图表 + HTML） | **100%** | `python scripts/combo1_status.py` 显示全阶段 OK |
| 真实 DeltaDTM 地形淹没 | **100%** | `DeltaDTM_v1_1_N51E000.tif`；Sheerness 使用真实 COG |
| 浏览器 HTML 完整报告 | **100%** | **单文件** `reports/combo1_complete_report.html` |
| Combo 1 综合（MVP） | **~95%** | Methods 文稿仍为剩余项 |

**科学摘要（来自 `combo1_summary.json`）**

- GSSR vs COAST-RP RP10 平均偏差：**−1.95 m**（8 站）
- 淹没 DEM：**DeltaDTM:DeltaDTM_v1_1_N51E000.tif**（真实 30 m COG）
- Sheerness 网格淹没比例（bathtub）：+0.5 m **2.5%**；+1 m **11.7%**；+2 m **49.7%**
- 图表：**5 张** PNG（内嵌于 HTML，非外链）

---

## HTML 报告（推荐入口）

**请直接打开这一份**（无需 Web 服务器、无需 `index.html`、无外部 CSS/图片路径）：

| 文件 | 说明 |
| --- | --- |
| **[`reports/combo1_complete_report.html`](../reports/combo1_complete_report.html)** | **主报告**：执行摘要、数据清单、站匹配表、RP 对比（图+表）、气象驱动、真实 DeltaDTM 淹没、Methods 要点 |

可选分拆（同样 100% 自包含，可离线 `file://` 打开）：

| 文件 | 内容 |
| --- | --- |
| [`reports/combo1_data_report.html`](../reports/combo1_data_report.html) | 仅数据下载与站匹配 |
| [`reports/combo1_analysis_report.html`](../reports/combo1_analysis_report.html) | 仅分析图表与 Methods |
| [`reports/index.html`](../reports/index.html) | 可选索引（列出上述文件名，非必需） |

技术约定：样式在 `<style>` 内联；图片为 `data:image/png;base64,...`；表格由 parquet/json 渲染为 HTML。

**刷新报告**（流水线末尾自动执行，亦可单独运行）：

```powershell
cd e:\Projects\20260522-coastal-flood-scientific-data
python scripts\generate_html_reports.py
python scripts\validate_standalone_html.py
# 或完整重跑（含处理 + 出图 + HTML）
python scripts\run_combo1_pipeline.py
```

---

## 输出目录树

```
e:\Projects\20260522-coastal-flood-scientific-data\
├── reports\
│   ├── combo1_complete_report.html   # ← 主入口（单文件完整版）
│   ├── combo1_data_report.html
│   ├── combo1_analysis_report.html
│   └── index.html                    # 可选
├── figures\                          # PNG 源（生成时读入并 base64 嵌入 HTML）
├── data\processed\
│   ├── combo1_summary.json
│   └── …（parquet / json）
├── data\raw\deltadtm\
│   ├── zips\Europe.zip               # ✅ 完整 ~2.39 GB
│   └── tiles\DeltaDTM_v1_1_N51E000.tif
└── logs\combo1-run-20260522.md
```

---

## 各文件含义与如何查看

### 图表 `figures/`

| 文件 | 含义 |
| --- | --- |
| `combo1_rp10_comparison.png` | 8 站 GSSR vs COAST-RP RP10 |
| `combo1_rp_multi_station.png` | RP10/50/100 分组柱状对比 |
| `combo1_driver_correlation_heatmap.png` | 8 站 Spearman 热力图 |
| `combo1_hydrograph_sheerness.png` | Sheerness GSSR 日序列 |
| `inundation_sensitivity_sheerness-p015-uk.png` | 真实 DEM + SLR +0.5/1/2 m |

### 处理结果 `data/processed/`

| 文件 | 含义 |
| --- | --- |
| `combo1_summary.json` | 总入口（含 `html_report_primary`） |
| `rp_comparison.parquet` | RP 偏差表 |
| `inundation_sensitivity.json` | Sheerness 淹没统计（真实 DEM） |

---

## DeltaDTM / Europe.zip 下载状态

| 项 | 状态 |
| --- | --- |
| `deltadtm_tiles.gpkg` 索引 | ✅ |
| `Europe.zip`（2 386 070 935 B 目标） | ✅ **100%** |
| `tiles/DeltaDTM_v1_1_N51E000.tif` | ✅ 已解压（Sheerness MVP） |
| 淹没 DEM | **DeltaDTM:DeltaDTM_v1_1_N51E000.tif** |

---

## 一键刷新（命令备忘）

```powershell
cd e:\Projects\20260522-coastal-flood-scientific-data
python scripts\combo1_status.py
python scripts\verify_downloads.py --strict
python scripts\run_combo1_pipeline.py
python scripts\generate_html_reports.py
python scripts\validate_standalone_html.py
start reports\combo1_complete_report.html
```

---

## 相关文档

| 文档 | 用途 |
| --- | --- |
| [combo1-progress-report.md](combo1-progress-report.md) | 中文进展报告 |
| [combo1-implementation-guide.md](combo1-implementation-guide.md) | 实施指南（含 HTML 刷新说明） |
| [combo1-product-definitions.md](combo1-product-definitions.md) | GSSR vs COAST-RP Methods |

---

*由 Agent 根据磁盘扫描与全流水线重跑生成；数值以 `combo1_summary.json` 为准。*
