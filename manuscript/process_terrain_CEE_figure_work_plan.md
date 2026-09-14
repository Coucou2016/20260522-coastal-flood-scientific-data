# 图件制作与投稿工作方案

**对应稿件标题：** Water-level and terrain sensitivity decouple in coastal flood screening  
**目标风格：** Communications Earth & Environment-style research article  
**核心图件策略：** 不把论文包装成“数据融合流程”，而是把图件组织成一个科学论证链：水位指标不等价 → 气象过程可解释 → 地形敏感性不随水位简单同步 → 形成 process-terrain typology。

---

## 1. 投稿图件总体原则

目标期刊风格下，主文图件不宜过多。建议主文控制在 5 个主图和 2-4 个主表。补充材料放更多站点细图、代码审计表、单站水位序列图、DeltaDTM 单站地图和质量控制信息。

主图逻辑应模仿 Dullaart et al. 的写法：每一张图回答一个明确科学问题，而不是展示一个数据处理步骤。Dullaart et al. 的图件顺序大致是：先分过程展示 TC/ETC storm surge，再展示组合后的 storm tide RP，再展示暴露人口结果。你的论文应对应改成：先展示站点和数据物理定义，再展示 surge 与 storm tide 的指标错位，再展示气象过程一致性，再展示地形敏感性，最后用 typology 形成总论点。

---

## 2. 主文图件清单

### Figure 1. Process-terrain screening design across eight coastal sites

**目的：** 让读者第一眼明白这不是 workflow paper，而是一个 process-terrain susceptibility paper。

**推荐版式：** 三联图。

- **Fig. 1a：站点分布图**  
  世界或北大西洋-欧洲-东亚简图，标出 8 个潮位站：Sheerness、Newlyn、Aberdeen、Hoek van Holland、Brest、New York-The Battery、Charleston、Hong Kong。欧洲 5 个有 DeltaDTM 的站点用实心圆，其他 3 个用空心圆。  
  **数据源：** station metadata table。  
  **图上标注：** “DeltaDTM terrain screen available” 和 “water-level and meteorological diagnostics only”。

- **Fig. 1b：物理量定义示意**  
  用一条垂直水位柱表示：astronomical tide、storm surge residual、storm tide、terrain elevation。明确 GSSR 是 residual/skew-surge-like daily reconstruction，COAST-RP 是 storm-tide return level，DeltaDTM 是 terrain elevation。  
  **关键作用：** 预防审稿人误读“你用 GSSR 验证 COAST-RP”。

- **Fig. 1c：论证框架**  
  不要画成普通 workflow，而画成四个诊断维度：water-level indicator divergence、meteorological coherence、terrain sensitivity、process-terrain typology。  
  **关键词：** diagnostic, coupling, decoupling, susceptibility.

**建议图注：**  
“GSSR, COAST-RP, Open-Meteo ERA5-derived drivers and DeltaDTM represent different physical quantities. The analysis therefore treats their combination as a process-terrain diagnostic rather than a direct validation exercise.”

**制作步骤：**

1. 用 `geopandas` 或 `cartopy` 读取站点经纬度。
2. 画世界海岸线和站点点位。
3. 用 `matplotlib.patches` 画水位定义示意图。
4. 用简单箭头连接四个诊断模块。
5. 输出 `figures/main/Fig1_process_terrain_design.pdf` 和 `Fig1_process_terrain_design.png`，分辨率 300-600 dpi。

---

### Figure 2. Surge-based and storm-tide-based indicators diverge by coastal setting

**目的：** 支撑第一个结果：GSSR RP10 和 COAST-RP RP10 在欧洲大潮差/强潮汐背景下明显错位，在美国两个站点差异较小。

**推荐版式：** 三联图。

- **Fig. 2a：paired bar chart**  
  x 轴为 8 个站点，两个柱分别为 GSSR RP10 surge 和 COAST-RP RP10 storm tide。欧洲站点放在左侧，非欧洲站点放在右侧，中间用竖线分组。

- **Fig. 2b：storm-tide-minus-surge divergence**  
  画 `D10 = COAST_RP_RP10 - GSSR_RP10`，按数值从大到小排序。Sheerness 3.93 m、Brest 3.63 m、Newlyn 2.74 m 会自然突出。

- **Fig. 2c：regional contrast 或 small-multiple inset**  
  可以画欧洲组和非欧洲组的均值/范围。注意不要做显著性检验，因为样本量太小；只做 descriptive contrast。

**必须使用的数据：**

| Station | GSSR RP10 | COAST-RP RP10 | D10 |
|---|---:|---:|---:|
| Sheerness | 1.33 | 5.26 | 3.93 |
| Newlyn | 0.61 | 3.35 | 2.74 |
| Aberdeen | 0.84 | 2.82 | 1.99 |
| Hoek van Holland | 1.50 | 3.37 | 1.87 |
| Brest | 0.68 | 4.31 | 3.63 |
| New York-The Battery | 1.19 | 1.31 | 0.12 |
| Hong Kong | 1.01 | 1.82 | 0.82 |
| Charleston | 0.84 | 1.35 | 0.51 |

**图注一定要写：**  
“GSSR and COAST-RP are not the same physical variable; the plotted difference is used as an indicator of product-definition and process divergence, not as a model-error metric.”

**制作步骤：**

1. 读取 `data/processed/rp_comparison.csv` 或手工整理的 table。
2. 新增列：`D10 = coastrp_rp10 - gssr_rp10`。
3. 对站点排序：欧洲站点在前，非欧洲站点在后；或者按 D10 排序。
4. 用 paired bars 和 horizontal divergence bars。
5. 所有 y 轴单位统一为 m。
6. 图内加一个小文本框：`storm tide = surge + tide; GSSR = surge residual`。

---

### Figure 3. Meteorological coherence of reconstructed daily surge

**目的：** 支撑第二个结果：GSSR 重建 surge 在欧洲温带风暴站点与气压/风速有物理一致性，但对 Charleston/Hong Kong 这类复杂或受热带气旋影响站点，简单日尺度局地气象指标不足。

**推荐版式：** 三联图。

- **Fig. 3a：Spearman correlation heatmap**  
  行为 8 个站点，列为 pressure、wind、precipitation。颜色从负到正，中间为 0。需要标数值。

- **Fig. 3b：Newlyn surge-pressure scatter 或 binned relationship**  
  Newlyn 压力相关最强，rho = -0.831。建议画 hexbin 或分箱中位数，不要画 11,323 个点的普通散点，否则过密。

- **Fig. 3c：Charleston 或 Hong Kong 对照**  
  展示弱相关或异常相关，说明“driver coherence is regime-dependent”。

**必须使用的数据：**

| Station | Surge-pressure | Surge-wind | Surge-precipitation |
|---|---:|---:|---:|
| Aberdeen | -0.724 | 0.422 | 0.252 |
| Brest | -0.796 | 0.442 | 0.585 |
| Charleston | 0.041 | 0.054 | 0.068 |
| Hoek van Holland | -0.539 | 0.610 | 0.486 |
| Hong Kong | 0.159 | 0.331 | -0.079 |
| Newlyn | -0.831 | 0.364 | 0.530 |
| New York-The Battery | -0.261 | 0.175 | 0.355 |
| Sheerness | -0.228 | 0.512 | 0.159 |

**制作步骤：**

1. 读取 `data/processed/driver_correlations.csv`。
2. 固定列顺序：pressure、wind、precipitation。
3. 站点顺序可按 pressure rho 排序，使欧洲强负相关聚在上方。
4. 色标范围固定为 -1 到 +1，避免误导。
5. 热图格子内标数值，保留两位小数。
6. 对 Newlyn 和 Charleston/Hong Kong 的日数据，读取 merged daily table，做分箱图。

**解释重点：**  
不要说 precipitation 代表 compound flooding；只能说 precipitation 是 storm-context indicator。真正 compound flooding 需要 river discharge、runoff、drainage 或 catchment hydrology。

---

### Figure 4. DeltaDTM terrain sensitivity at five European sites

**目的：** 支撑第三个结果：地形敏感性不是 storm-tide level 的简单函数；Sheerness 和 Hoek van Holland 是低地敏感型，Newlyn/Brest/Aberdeen 是地形缓冲型。

**推荐版式：** 如果页面允许，用六联图；如果拥挤，分成主图 + 补充图。

- **Fig. 4a-b：代表性地图**  
  选择 Sheerness 和 Hoek van Holland 两个 aligned hotspots，显示 DeltaDTM elevation 和 +2 m static inundation mask。

- **Fig. 4c-d：对照地图**  
  选择 Brest 或 Newlyn 作为 terrain-buffered site。Aberdeen 可放 Supplementary Figure。

- **Fig. 4e：hypsometry curves**  
  五个站点的低地海拔累积分布曲线。x 轴 elevation，y 轴 cumulative fraction。+0.5、+1.0、+2.0 m 用竖线标出。

- **Fig. 4f：flooded lowland fraction bar chart**  
  每个站点三根柱：+0.5、+1.0、+2.0 m。

**必须使用的数据：**

| Station | Median elevation | +0.5 m | +1.0 m | +2.0 m |
|---|---:|---:|---:|---:|
| Sheerness | 2.47 | 2.13% | 10.18% | 42.78% |
| Hoek van Holland | 3.85 | 5.15% | 15.67% | 34.72% |
| Newlyn | 30.00 | 2.52% | 4.19% | 8.26% |
| Brest | 30.00 | 3.67% | 5.22% | 7.63% |
| Aberdeen | 22.46 | 2.39% | 3.77% | 7.24% |

**制作步骤：**

1. 读取 DeltaDTM GeoTIFF tiles：
   - Sheerness: `DeltaDTM_v1_1_N51E000.tif`
   - Newlyn: `DeltaDTM_v1_1_N50W006.tif`
   - Aberdeen: `DeltaDTM_v1_1_N57W003.tif`
   - Hoek van Holland: `DeltaDTM_v1_1_N51E004.tif` and `DeltaDTM_v1_1_N52E004.tif`
   - Brest: `DeltaDTM_v1_1_N48W005.tif`
2. 用 `rasterio` 读取 station-centred window。
3. mask nodata。
4. 建立 coastal-lowland mask，与现有处理保持一致。
5. 对每个 perturbation 计算 `depth = max(0, eta - DEM)`。
6. 地图上不要用“flood risk”字样，用 “static terrain sensitivity”。
7. 荷兰站点必须在图注中说明未考虑 flood defenses。

---

### Figure 5. Process-terrain typology of coastal flood susceptibility

**目的：** 这是全文 synthesis figure，把论文从“多个结果”收束成一个科学结论。

**推荐版式：** 两联图。

- **Fig. 5a：diagnostic scatter**  
  x 轴：`D10 = COAST-RP RP10 - GSSR RP10`。  
  y 轴：`+2.0 m flooded lowland fraction`。  
  点颜色：surge-pressure correlation，越负说明 extratropical storm coherence 越强。  
  只放 5 个有 DeltaDTM 的欧洲站点，但可以在旁边用灰色注释列出 non-terrain sites 的 D10。

- **Fig. 5b：typology diagram**  
  三类：
  1. water-level-terrain aligned hotspots：Sheerness、Hoek van Holland；
  2. water-level-dominated but terrain-buffered sites：Brest、Newlyn、Aberdeen；
  3. process-diagnostic comparison sites：New York-The Battery、Charleston、Hong Kong。

**解释重点：**  
这张图必须对应论文主结论：Extreme water-level magnitude alone incompletely identifies coastal flood susceptibility because water-level process and lowland terrain can be decoupled.

**制作步骤：**

1. 合并 RP10 table、correlation table、terrain sensitivity table。
2. 只保留有 terrain 的五个站点用于主 scatter。
3. x 轴不需要从 0 开始，但建议从 1.5 到 4.2 m，避免空间浪费。
4. y 轴用百分比 0-50%。
5. 标注每个点名。
6. 加半透明区域：high terrain sensitivity、terrain-buffered 等。
7. 输出为 vector PDF，并另存 PNG 用于预览。

---

## 3. 表格安排

### Main Table 1：Data products and physical definitions

这张表必须保留在主文，因为它能防止审稿人误解。列包括：Product、Variable、Spatial support、Time/RP support、Role、Limitation。

### Main Table 2：Water-level indicators and divergence

保留 8 个站点 RP10 比较。建议增加 `D10 = COAST - GSSR`，比只写负 bias 更直观。

### Main Table 3：Process-terrain typology

这张表可以替代部分文字，列包括：Station、D10、pressure rho、+2 m lowland sensitivity、typology class、interpretation。

### Supplementary Tables

- Supplementary Table 1：station coordinates and COAST-RP match distance。
- Supplementary Table 2：GSSR RP10/RP50/RP100 empirical values。
- Supplementary Table 3：Open-Meteo variables and time coverage。
- Supplementary Table 4：DeltaDTM tile names, valid-cell fractions, nodata statistics。
- Supplementary Table 5：all-valid-cell vs coastal-lowland flooded fractions。

---

## 4. 代码实现建议

### Recommended script structure

```text
scripts/
  make_fig1_design_map.py
  make_fig2_water_level_divergence.py
  make_fig3_meteorological_coherence.py
  make_fig4_deltadtm_terrain_sensitivity.py
  make_fig5_process_terrain_typology.py
  build_main_tables.py
```

### Recommended output structure

```text
figures/main/
  Fig1_process_terrain_design.pdf
  Fig1_process_terrain_design.png
  Fig2_water_level_divergence.pdf
  Fig2_water_level_divergence.png
  Fig3_meteorological_coherence.pdf
  Fig3_meteorological_coherence.png
  Fig4_deltadtm_terrain_sensitivity.pdf
  Fig4_deltadtm_terrain_sensitivity.png
  Fig5_process_terrain_typology.pdf
  Fig5_process_terrain_typology.png

figures/supplementary/
  FigS1_sheerness_hydrograph.pdf
  FigS2_gssr_return_levels_all_sites.pdf
  FigS3_each_deltadtm_site_map.pdf
  FigS4_quality_audit_schematic.pdf

data/figure_source/
  Fig2_water_level_divergence.csv
  Fig3_driver_correlations.csv
  Fig4_terrain_sensitivity.csv
  Fig5_process_terrain_typology.csv
```

---

## 5. 每张图对应的论文段落

| 图 | 对应 Results 小节 | 核心句 |
|---|---|---|
| Fig. 1 | Introduction / first Results paragraph | The analysis treats open datasets as physically distinct indicators of process-terrain susceptibility. |
| Fig. 2 | Surge and storm-tide indicators diverge across coastal settings | Surge-based and storm-tide-based indicators diverge most strongly at European sites. |
| Fig. 3 | Reconstructed surges are meteorologically coherent at extratropical European sites | Pressure and wind correlations support extratropical storm coherence in several European reconstructions. |
| Fig. 4 | Lowland terrain sensitivity does not simply follow storm-tide magnitude | Static DeltaDTM sensitivity is concentrated at Sheerness and Hoek van Holland. |
| Fig. 5 | Process-terrain typology | Coastal flood susceptibility depends on the coupling between water-level process and lowland terrain. |

---

## 6. 补充材料建议

### Supplementary Figure S1：Sheerness GSSR hydrograph

展示 daily surge series、GSSR empirical thresholds、COAST-RP RP10 reference line。图注必须写：COAST-RP line is not the same physical variable as the GSSR daily series。

### Supplementary Figure S2：GSSR empirical return levels

8 个站点 RP10、RP50、RP100 的 empirical values。若 RP50/RP100 等于 record maximum，要在图注中说明 empirical estimates are constrained by record length。

### Supplementary Figure S3：单站 DeltaDTM maps

把 Aberdeen、Newlyn、Brest、Sheerness、Hoek van Holland 的完整地图都放进去，主文只放代表性地图。

### Supplementary Note 1：Product-definition audit

专门解释 storm surge、skew surge、storm tide、extreme sea level、terrain elevation、vertical datum 的区别。

### Supplementary Note 2：Static terrain-screen limitations

专门解释 no connectivity、no defenses、no wave setup、no datum transformation、no river discharge。

---

## 7. 投稿前必须补齐的事项

1. **作者、单位、通讯作者邮箱。** 目标期刊格式需要完整作者和单位信息。
2. **公开数据和代码 DOI。** Communications Earth & Environment 对 Data availability 和 Code availability 要求较明确。建议用 Zenodo 或 OSF 归档 processed tables、figure source data 和 code snapshot。
3. **Figure source data。** 每个主图都要有对应 CSV 或 Parquet。
4. **Supplementary Information PDF。** 把补充图、补充表、产品定义审计、质量控制、额外站点图放进去。
5. **英文润色。** 目标期刊不进行深度 copy-edit，投稿前最好统一术语和图注风格。
6. **限制语句。** 所有 static inundation 图都要标注 sensitivity screen, not flood forecast。
7. **标题控制。** 目标标题 `Water-level and terrain sensitivity decouple in coastal flood screening` 少于 15 个词，符合该期刊对简洁标题的偏好。

---

## 8. 论文成败关键

这篇论文最容易被审稿人质疑的地方不是数据真实性，而是“你到底证明了什么”。所以所有图都必须服务于一句话：

> Coastal flood susceptibility is governed by the coupling between flood-generating water-level processes and lowland terrain, and this coupling can be misaligned across coastal settings.

不要让图件看起来像“我把四个数据源接起来了”。图件要让读者看到：

1. GSSR 和 COAST-RP 的差异是物理定义差异，不是坏结果；
2. 欧洲站点 surge 与 pressure/wind 有过程一致性；
3. Sheerness 和 Hoek van Holland 的地形低地敏感性明显更强；
4. Brest/Newlyn 等高 storm-tide 指标站点不一定是最高地形敏感站点；
5. 因此，单一 extreme water-level 指标不足以识别 coastal flood susceptibility。
