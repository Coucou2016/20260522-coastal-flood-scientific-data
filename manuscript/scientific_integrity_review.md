# 科学真实性、准确性与完整性内部审查文档

**对应稿件：** *Limited concordance between storm-tide magnitude and standardized connected-lowland screening across Northwest Europe*

**审查定位：** code-data-table-figure-manuscript 穿透式内部一致性审计，不冒充独立同行评议

**自动约束状态：** 全部通过

## 1. 审查结论

本轮首先修复会改变空间推断的实现问题，而不是先润色结论。旧 `coastal_sector()` 以经纬度阈值给站点分区，曾把 Fishguard、Holyhead、Cuxhaven 和 Tregde 等站放入不合理海区；它已从统计路径移除。现在 74 个候选站通过 `config/coastal_spatial_blocks_v2.csv` 显式连接到 coastal basin 以及 100、150、250 km 三套版本化空间块。块内 restricted permutation 的双侧概率也改为经验双尾，不再假定受限零分布以 0 为中心。

当前可确认的是：68 站主表、2,960 条地形稳健性记录、三套空间统计、图件和文稿由同一 source-table 体系生成；面积、拓扑和指标分解契约通过。当前证据支持的是 limited rank concordance 和 decision-level disagreement。它不支持“显著负相关定律”“错配异常大于空间随机”“connected terrain 是真实洪水排序”或“二指标组合已经提高预测能力”。

## 2. P0 问题及处理证据

1. **空间错分：已修复并重算。** 经纬度 `if` 规则不再参与推断。地图、块内置换、分块调整关联、块重采样、leave-one-block-out 和 Top-k null 统一读取版本化配置；已知错误映射由自动测试固定。
2. **受限置换双侧概率：已修复并重算。** 当前概率是 `2 * min(P(null <= observed), P(null >= observed))` 的加一校正经验双尾值，允许空间受限零分布偏离 0。
3. **复现入口：已分层。** `python scripts/reproduce.py --mode derived` 从带 SHA-256 的紧凑派生输入重建论文包；`--mode full` 从本地上游原始产品开始。README 不再把 derived rebuild 描述成 raw-to-paper。
4. **审稿包依赖闭包：已重构并设独立门禁。** `src/`、全部 Python 脚本、测试、配置及 figure-source tables 由目录规则纳入，不再依赖易漏项的脚本白名单；最终 ZIP 在包外以临时目录、全新虚拟环境和九个确定性输出哈希独立验收。
5. **运行环境：已补齐。** `pyproject.toml` 声明 xarray、netCDF4、rasterio、pyproj、SciencePlots 与 pytest 等实际依赖；`environment-lock.yml` 记录本轮平台版本。系统全局 pytest 插件可能冲突，因此正式门禁固定 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。

## 3. 数据产品与 mask 审计

| product | release | tile_tag | vertical_reference | release_cap_m | paper_v1_0_cap_m | mask_outside_support_fill | official_255_cells_in_primary_analysis_windows | outside_support_cells_in_primary_analysis_windows | note |
|---|---|---|---|---|---|---|---|---|---|
| DeltaDTM | v1.1.1 | DeltaDTM v1.1.1 / DeltaDTM.jl v1.1.1 | EGM2008 | 30 | 10 | 254 | 0 | 3320 | The 2024 paper documents v1.0; the downloaded v1.1 README documents the 30 m EGM2008 cap. Outside-support fill is kept distinct from class 255 and excluded from all land denominators. |

主流程只允许官方 class 0 land 进入 represented-land denominator；class 1 ocean 是基础 marine seed，class 3 river 仅在与 ocean component 连通时参与水体种子，class 2 lake、class 255 和窗口外 class 254 均排除。这里的 `connected` 是 raster component 分类，不是水动力连通、洪水历时或防洪工程失效判断。

## 4. 自动科学约束

| Check | Pass | Observed | Criterion or meaning |
|---|---|---|---|
| Robustness-grid rows | True | 2960 | 74 stations x 40 configurations |
| Primary stations | True | 68 | 68 unique matched stations |
| Explicit spatial-block coverage | True | 74 | 74 configured candidates, no missing block |
| Known coastline corrections | True | True | Fishguard/Holyhead/Cuxhaven/Tregde reviewed mappings |
| Connected area <= below-threshold area | True | 0 | violations |
| Four-neighbour <= eight-neighbour | True | 0 | violations under identical configuration |
| Metric decomposition identity | True | 1.13687e-12 | maximum absolute percentage-point error |
| Official class 255 in primary windows | True | 0 | cells |
| Outside-support sentinel distinct | True | 3320 | class-254 cells, excluded |
| Threshold grid complete | True | 884 | 68 stations x 13 thresholds from 0 to 3 m |
| Water/land topology grid complete | True | 272 | 68 stations x four explicit topology combinations |
| Coastline-window sensitivity complete | True | 68 | stations |
| Decision audit complete | True | 68 | stations |
| Coordinate match review complete | True | 68 | 68 included coordinate-plausible pairs; six distance-excluded candidates are not counted |

这些检查能证明代码输出满足自身声明的集合、面积与拓扑关系，也能阻止已知回归。它们不能证明输入 DEM 没有系统误差，不能替代共同垂向基准，更不等同于独立洪水观测验证。

## 5. 空间统计证据边界

| terrain_metric_label | block_scale_km | n_spatial_blocks | spearman | kendall | sector_adjusted_rank_association | sector_stratified_permutation_two_sided_p | top20_n | top20_observed_overlap | sector_stratified_top20_null_q025 | sector_stratified_top20_null_q975 | sector_stratified_top20_lower_tail_p | spearman_sector_bootstrap_p025 | spearman_sector_bootstrap_p975 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lowland_prevalence | 100 | 42 | -0.309272 | -0.187884 | -0.395706 | 0.181582 | 14 | 1 | 1 | 1 | 1 | -0.549305 | 0.0332786 |
| lowland_prevalence | 150 | 34 | -0.309272 | -0.187884 | -0.477079 | 0.0219978 | 14 | 1 | 1 | 2 | 0.332667 | -0.548781 | -0.00724409 |
| lowland_prevalence | 250 | 25 | -0.309272 | -0.187884 | -0.41672 | 0.020198 | 14 | 1 | 1 | 2 | 0.331967 | -0.582751 | 0.0704137 |
| conditional_connectivity | 100 | 42 | 0.104533 | 0.06924 | 0.230842 | 0.490151 | 14 | 5 | 4 | 5 | 1 | -0.161064 | 0.330231 |
| conditional_connectivity | 150 | 34 | 0.104533 | 0.06924 | 0.138767 | 0.584742 | 14 | 5 | 3 | 6 | 0.917308 | -0.161052 | 0.315844 |
| conditional_connectivity | 250 | 25 | 0.104533 | 0.06924 | 0.147126 | 0.464154 | 14 | 5 | 2 | 6 | 0.971203 | -0.150571 | 0.326691 |
| connected_lowland_share | 100 | 42 | -0.333168 | -0.210711 | -0.349591 | 0.135186 | 14 | 1 | 1 | 1 | 1 | -0.550994 | -0.0272113 |
| connected_lowland_share | 150 | 34 | -0.333168 | -0.210711 | -0.455223 | 0.0251975 | 14 | 1 | 1 | 2 | 0.332467 | -0.567171 | -0.0273174 |
| connected_lowland_share | 250 | 25 | -0.333168 | -0.210711 | -0.411791 | 0.0119988 | 14 | 1 | 1 | 4 | 0.0985901 | -0.578765 | 0.0163185 |
| connected_area | 100 | 42 | -0.340955 | -0.208077 | -0.401135 | 0.121988 | 14 | 1 | 1 | 1 | 1 | -0.565968 | -0.0190467 |
| connected_area | 150 | 34 | -0.340955 | -0.208077 | -0.481675 | 0.0319968 | 14 | 1 | 1 | 2 | 0.331567 | -0.558951 | -0.0456077 |
| connected_area | 250 | 25 | -0.340955 | -0.208077 | -0.433954 | 0.0129987 | 14 | 1 | 1 | 4 | 0.0977902 | -0.576907 | 0.0158461 |

100、150 和 250 km 方案分别包含 42、34 和 25 个近似沿岸连续块。RP10 与 connected-land share 的原始 Spearman rho 为 -0.333；块内经验双侧 p 随分块尺度为 0.135、0.025 和 0.012，而保持地理组成的块重采样范围为 [-0.551,-0.027]、[-0.567,-0.027] 和 [-0.579,0.016]。两类结果不矛盾：前者问同一组空间块内随机重排后是否常见，后者问换一组被抽到的地理块时估计是否稳定。250 km 范围触及 0，因此稿件不建立空间稳定的负相关定律。

### Top-k 空间零模型

| block_scale_km | n_spatial_blocks | top_n | observed_overlap | sector_stratified_null_q025 | sector_stratified_null_q975 | sector_stratified_lower_tail_p |
|---|---|---|---|---|---|---|
| 100 | 42 | 14 | 1 | 1 | 1 | 1 |
| 150 | 34 | 14 | 1 | 1 | 2 | 0.326667 |
| 250 | 25 | 14 | 1 | 1 | 4 | 0.0982902 |

Top-20% 两表各 14 站，实际只重合 1 站，但该值在三套空间零模型包络内。1/14 是筛查决策的描述性恢复度，不是“低于随机”的显著性证据。

## 6. 指标构念与决策稳定性

connected-land share 被显式拆为 lowland prevalence 乘以 conditional connectivity。主结果中前者与 storm tide 的 rho 为 -0.309，后者为 +0.105；所以低 composite 值不能一概解释为“海洋连通差”。

| Decision diagnostic | Observed |
|---|---|
| Median absolute rank displacement | 26 |
| Maximum absolute rank displacement | 64 |
| Always terrain Top-20% across eligible configurations | 6 |
| Never terrain Top-20% across eligible configurations | 40 |
| Pareto-nondominated sites | 5 |

绝对排名位移中位数为 26。地形 Top-20% 选择频率来自 40 个预设配置中的可用子集，它度量方法选择下的清单稳定性，不是洪水概率。四象限和 Pareto 结果用于说明 costly second-stage modelling 的候选清单如何变化，不把 terrain ranking 当作真值。

### 水体/陆地邻域、阈值与窗口

| water_neighbours | land_neighbours | terrain_metric | n_sites | water_vs_terrain_spearman | terrain_rank_spearman_vs_primary_8water_4land | top20_n | top20_overlap_with_primary | top20_membership_changes |
|---|---|---|---|---|---|---|---|---|
| 4 | 4 | connected_reference_land_pct | 68 | -0.427492 | 0.862007 | 14 | 12 | 4 |
| 4 | 4 | connected_area_km2 | 68 | -0.430927 | 0.862122 | 14 | 12 | 4 |
| 4 | 4 | conditional_connectivity_pct | 68 | 0.0888363 | 0.957201 | 14 | 14 | 0 |
| 4 | 8 | connected_reference_land_pct | 68 | -0.365958 | 0.88785 | 14 | 11 | 6 |
| 4 | 8 | connected_area_km2 | 68 | -0.371493 | 0.896362 | 14 | 11 | 6 |
| 4 | 8 | conditional_connectivity_pct | 68 | 0.012005 | 0.867483 | 14 | 13 | 2 |
| 8 | 4 | connected_reference_land_pct | 68 | -0.333168 | 1 | 14 | 14 | 0 |
| 8 | 4 | connected_area_km2 | 68 | -0.340955 | 1 | 14 | 14 | 0 |
| 8 | 4 | conditional_connectivity_pct | 68 | 0.104533 | 1 | 14 | 14 | 0 |
| 8 | 8 | connected_reference_land_pct | 68 | -0.319846 | 0.961102 | 14 | 11 | 6 |
| 8 | 8 | connected_area_km2 | 68 | -0.329427 | 0.966828 | 14 | 11 | 6 |
| 8 | 8 | conditional_connectivity_pct | 68 | -0.00615544 | 0.900571 | 14 | 13 | 2 |

| terrain_metric | n_sites | spearman | kendall | interpretation |
|---|---|---|---|---|
| connected_share_auc_0_3m_pct | 68 | -0.298202 | -0.187006 | threshold-integrated standardized EGM2008 terrain screen; not a flood probability |
| connected_area_auc_0_3m_km2 | 68 | -0.31328 | -0.186128 | threshold-integrated standardized EGM2008 terrain screen; not a flood probability |
| below_share_auc_0_3m_pct | 68 | -0.289232 | -0.175593 | threshold-integrated standardized EGM2008 terrain screen; not a flood probability |

| terrain_metric | n_sites | terrain_rank_spearman_oriented_vs_square | water_vs_oriented_spearman | water_vs_square_spearman | top20_n | top20_overlap_oriented_vs_square | top20_membership_changes | interpretation |
|---|---|---|---|---|---|---|---|---|
| connected_reference_land_pct | 68 | 0.803794 | -0.247662 | -0.333168 | 14 | 11 | 6 | mask-derived window-geometry sensitivity, not an alternative flood model |
| connected_area_km2 | 68 | 0.741535 | -0.254151 | -0.340955 | 14 | 11 | 6 | mask-derived window-geometry sensitivity, not an alternative flood model |
| below_reference_land_pct | 68 | 0.892812 | -0.201779 | -0.309272 | 14 | 14 | 0 | mask-derived window-geometry sensitivity, not an alternative flood model |

主流程是 water-8 / land-4。严格 water-4 / land-4 与主流程地形排名 rho 为 0.86、Top-20% 改变 4 个成员。0-3 m 阈值积分和近似沿岸窗口仍给出有限一致性，但沿岸窗口与方窗仅重合 11/14 个 terrain Top-20% 成员。这些结果支持区域结论的方向，也明确暴露单站优先级的方法依赖性。

## 7. COAST-RP 匹配审计

68 个纳入站点最大 great-circle 匹配距离为 2.811 km；以下 6 站因超过 6 km 预设规则被排除：

| station | recomputed_match_dist_km | coast_rp_source_lon | coast_rp_source_lat | match_exclusion_reason |
|---|---|---|---|---|
| Cordemais France | 22.6474 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Le Pellerin France | 28.388 | -2.014 | 47.014 | excluded_nearest_coast_rp_point_gt6km |
| Nantes Usine Brulee | 39.423 | -2.014 | 47.014 | excluded_nearest_coast_rp_point_gt6km |
| Donges France | 8.27799 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Montoir De Bretagne | 6.89698 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Paimboeuf France | 14.3371 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |

坐标级审阅对 74 个纳入匹配全部给出“地理位置可接受”，其中 11 个标记为河口或半封闭海湾。该审阅没有 coastline component 或沿岸路径距离，字段明确写为 `opposite_bank_flag = not_determined_from_coordinate_review`，不能升级为 hydrodynamic equivalence。

## 8. national/local DTM product-and-datum cross-check

| station | delta_connected_2m_reference_land_pct | local_connected_2m_reference_land_pct | delta_connected_2m_area_km2 | local_connected_2m_area_km2 | connected_pixel_iou_after_reprojection | local_dtm_vertical_datum_note |
|---|---|---|---|---|---|---|
| Sheerness | 42.7002 | 9.62959 | 20.3643 | 4.61207 | 0.214623 | Ordnance Datum Newlyn / EA product native datum |
| Newlyn | 0.44611 | 0.416648 | 0.276293 | 0.259144 | 0.527548 | Ordnance Datum Newlyn / EA product native datum |
| Lowestoft P024 Uk | 1.41616 | 6.16525 | 0.669507 | 2.92848 | 0.110977 | Ordnance Datum Newlyn / EA product native datum |
| Immingham P026 Uk | 0.405551 | 0.078999 | 0.24946 | 0.0487939 | 0.0417246 | Ordnance Datum Newlyn / EA product native datum |
| Denhelder Hel Nl | 71.7296 | 4.36493 | 20.8545 | 1.27433 | 0.0554507 | Normaal Amsterdams Peil / AHN product native datum |
| Delfzijl Del Nl | 96.7041 | 89.7843 | 61.3031 | 57.1869 | 0.925796 | Normaal Amsterdams Peil / AHN product native datum |
| Hoek van Holland | 2.63966 | 1.43861 | 1.41098 | 0.771845 | 0.217064 | Normaal Amsterdams Peil / AHN product native datum |

七站对照记录共同 target grid、transform、mask resampling 和文件 SHA-256，但 DeltaDTM、Ordnance Datum Newlyn 与 Normaal Amsterdams Peil 未统一。因此差异同时包含高程产品、垂向基准、水平分辨率和 provider WCS 重采样；本文只称 diagnostic product-and-datum sensitivity，不称 validation，也不把七站变化比例外推到 68 站。

## 9. 图件来源与视觉检查

| Figure | Pixels | Embedded DPI | Source data | Visual/data QA |
|---|---|---|---|---|
| Fig1_process_terrain_design.png | 3542 x 2404 | 500 | Primary_station_spatial_blocks.csv; Primary_sample_flow.csv; coastal_spatial_blocks_v2.csv | original-resolution inspection required after each final rebuild; no cell enlargement |
| Fig2_regional_screening_agreement.png | 3719 x 3362 | 500 | Primary_terrain_components_68stations.csv; Return_period_sensitivity.csv; Spatial_block_bootstrap_intervals.csv; Topk_spatial_null_curves.csv; Decision_instability_station_metrics.csv | original-resolution inspection required after each final rebuild; no cell enlargement |
| Fig3_connected_terrain_contrasts.png | 3687 x 3934 | 500 | Fig3_predefined_site_selection.csv; Fig3_threshold_response_source.csv; frozen DeltaDTM windows | original-resolution inspection required after each final rebuild; no cell enlargement |
| Fig4_metric_decomposition_robustness.png | 3816 x 3320 | 500 | Primary_terrain_components_68stations.csv; Denominator_adjusted_associations.csv; Water_land_topology_summary.csv; Rank_robustness_one_at_a_time.csv; Threshold_integrated_associations.csv; Coastline_window_sensitivity_summary.csv | original-resolution inspection required after each final rebuild; no cell enlargement |
| FigS1_water_level_definition.png | 3444 x 1458 | 500 | Fig2_water_level_divergence_with_uncertainty.csv; source-verified tidal metadata | original-resolution inspection required after each final rebuild; no cell enlargement |
| FigS2_process_coherence.png | 5122 x 2354 | 500 | Fig3_driver_correlations.csv; event-composite source tables | original-resolution inspection required after each final rebuild; no cell enlargement |
| FigS3_connectivity_gallery.png | 3462 x 3415 | 500 | Primary_terrain_components_68stations.csv; frozen DeltaDTM windows | original-resolution inspection required after each final rebuild; no cell enlargement |
| FigS4_elevation_product_datum_sensitivity.png | 3591 x 2975 | 500 | TableS_local_dtm_product_datum_crosscheck.csv | original-resolution inspection required after each final rebuild; no cell enlargement |
| FigS5_coastrp_match_audit.png | 3466 x 1591 | 500 | Match_distance_audit_74stations.csv; COAST_RP_same_coast_match_audit.csv | original-resolution inspection required after each final rebuild; no cell enlargement |

Figure 3 的三站由机器可读规则选出。低值站 inset 只放大原像元位置，不增加 connected 面积；9 子图分别展示分类、指标分解和实算阈值曲线。每次最终重建后仍须以原始分辨率检查标签遮挡、图例、字体和颜色，并把像素层面的视觉判断与 source-table 数值核对分开记录。

## 10. 关键文件 SHA-256

| File | Bytes | SHA-256 |
|---|---|---|
| data/raw/coast_rp/COAST-RP.zip | 6798999 | 13242fe8b682230420357dbac202b10590f41dc0c9e378b9c2c69f91962704c9 |
| data/raw/gssr/metadata/eraint.geojson | 307194 | aab77394a0bf87b3ae611131e26b489a7abe9dd67add071aeee0da4b3bab46e6 |
| data/raw/deltadtm/index/README.md | 2326 | 9da10b0576ff4368a756bd5646b091fab6b7c7c7d217a6f758fbe0803f826e00 |
| data/raw/deltadtm/zips/mask_tiles.zip | 428178062 | 3f8c6999f90346359e60cc6c757786d43fd1cb65e4ab13125faaa80606487775 |
| config/coastal_spatial_blocks_v2.csv | 6730 | 05df4af816e3287c6fbf9d7fe9c8ee8ad1b66f3ef2d9533f626e2d008d4e8791 |
| data/upstream_raw_manifest.csv | 77446 | c3567da4627f59e3bb00f40f6957db0770dac691e4c2a01acb8b2ef73f57c620 |
| data/derived_input_manifest.json | 3004 | 9dfa418329cfabec84fe0e2f5abbbeca17bdf05ff8b542a86369da9b6d639154 |
| data/figure_source/Primary_terrain_components_68stations.csv | 35122 | f1e5eef717a36ee71ec82bbef8da9f487a1ae843c9e1cc6e9e3e791bf28c58f2 |
| data/figure_source/Terrain_robustness_grid_74stations.csv | 1481287 | 6142194e3fe7354c8c5cdf48d12c5d95a2d40364b4d97138947d43666b115661 |
| data/figure_source/Return_period_sensitivity.csv | 25437 | 1b5517fc32b1a73413764b647c1449e830d6e7639dd34bba6ff9387d4049f11a |
| data/figure_source/Spatial_block_bootstrap_intervals.csv | 6972 | 6883bc444e5e34edc53325889fd1e57ebc93e0fbee67a06f723d9b99b034b814 |
| data/figure_source/Topk_spatial_null_curves.csv | 19132 | 24ca73f5eca3e5f25318afd65cda2bca53702801e32806d0c5f07ddee16dd8f9 |
| data/figure_source/Water_land_topology_sensitivity_68stations.csv | 72596 | a763ad91307e56be4ca11cb538724bc1d78b7b5d022685922cfd879a0e8a53c8 |
| data/figure_source/Threshold_response_0_3m_68stations.csv | 225103 | 274719124c9f803ae29315d4adba1d7eda94c39aeda88d306b8a9a15b6c47abf |
| data/figure_source/Coastline_oriented_window_68stations.csv | 27461 | 57330dabb4f6bbea9af86c2c484dee117f9bce5d3abea5fa9f7346e3af42ff8c |
| data/figure_source/Decision_instability_station_metrics.csv | 40312 | 427dfdb53466e679b0a89be80bd12dea34d7fead7927ca8efe61e031693e6a41 |
| data/figure_source/COAST_RP_same_coast_match_audit.csv | 66453 | ce2ee8fe792f566cdb1f5203aff73b4ddf1131879096ab3578da6f5260794970 |
| data/figure_source/TableS_local_dtm_product_datum_crosscheck.csv | 9735 | 20a1346c2a15016de6d8f6cc983c296e8728a2a452acb24750df6da7ebb6b597 |
| scripts/reproduce.py | 8137 | ac6df5d8b9aeaf2c314407581e0a3aa83cced98cb8b3da797b7593fb1100ae96 |
| scripts/rebuild_frozen_primary_analysis.py | 25305 | 9c306499e07e25a99cc5b1f75221300ebed755f4ad5a477d9063d517323736c1 |
| scripts/add_external_review_diagnostics.py | 31815 | 22e869b23a08ca1432e940d036133b7d2422f025db764a6a684f06adb97b57c6 |
| scripts/make_major_revision_figures.py | 46635 | 71e9f9484a04d29b7f1544270f67aa73a5ec2e7371771ac3c851d84574ca04f6 |
| tests/test_scientific_contracts.py | 14920 | 7161d27bf4c9710186ac789fc4abecb707e209c20ea5e80c07e6153dd91294c1 |
| src/coastal_screening/__init__.py | 332 | 4ed9dcca6879041b6fb6252d7760c66b7d89ee23e33242eb4bb113b36e8f3500 |
| src/coastal_screening/connectivity.py | 1330 | 9a1eedcdd0aefa3659a25f3df7f0eb6404d2c24ed45855ac71246f4478962199 |
| src/coastal_screening/spatial_blocks.py | 3973 | bc0c1f953c05f6f7b4ce74bb498a9ecc4964946804a1dbc33a5c3a91876ade91 |
| src/coastal_screening/statistics.py | 3122 | 035d10af40bcf808836d47fba87ab401e0c6691adfa94c84b486f2e61977a2b3 |
| data/raw/local_dtm/delfzijl-del-nl_local_dtm_10m.tif | 2204083 | a8b3589a24ca9dbcb00d18e24c916e193d37a9b73034c185bf29fcf80a9cbb35 |
| data/raw/local_dtm/denhelder-hel-nl_local_dtm_10m.tif | 1310648 | b950e177da667509c85bb8a4dc77c4dcbac5b56d85507ea706e968568af15e79 |
| data/raw/local_dtm/hoekvanholla-hvh-nl_local_dtm_10m.tif | 1848802 | e960ac322ae8e703055a75739d6dee6a65c2ee367e9dc0dd8af1c7f6ff600563 |
| data/raw/local_dtm/immingham-p026-uk_local_dtm_10m.tif | 9437675 | 8567cb377b27480b51f3dbee6ff5501784f3eed237e0ec7e8058ff09789ed6e7 |
| data/raw/local_dtm/lowestoft-p024-uk_local_dtm_10m.tif | 6291923 | d95f97c91d4df295e6113b98fccbdab4d3bedac1a35c3751464e0b8e61ab2819 |
| data/raw/local_dtm/newlyn-p001-uk_local_dtm_10m.tif | 9437675 | fef345c91868dd64e5a2e11180ad066b7a1f8ce92305cf26990d70fd0c9e51c2 |
| data/raw/local_dtm/sheerness-p015-uk_local_dtm_10m.tif | 9437675 | 40c81f2a969e0044184d5fb40ebc11728dca5376d2707386e29c90def027cadd |

大体积上游数据不能凭文件名认定相同。full 模式在计算前核验 `data/upstream_raw_manifest.csv`；derived 模式核验 `data/derived_input_manifest.json`。本表用于确认论文、报告和发布包是否来自同一输入与代码基线。

## 11. 尚未消除的风险

| Risk | Status | Evidence boundary |
|---|---|---|
| 垂向基准统一 | 未完成 | DeltaDTM/ODN/NAP 尚未转换到共同 local-MSL reference；S4 只能解释为产品、基准、分辨率和服务重采样的联合敏感性。 |
| 独立真实洪水基准 | 未完成 | 检索到的 2026 European total-water-level storms 数据仍是水位过程，不是站点级动态淹没真值；没有用它伪装外部验证。 |
| 空间块定义 | 部分完成 | 74 站已由版本化表显式审阅并修正已知错分；100/150/250 km 标签是近似沿岸连续分组，不是精确测得的 shoreline distance。 |
| COAST-RP 同岸环境 | 部分完成 | 坐标和地图审阅通过 68 对匹配并标记 11 个河口/复杂岸线点；这不证明同一沿岸水动力环境，仍需 coastline component/alongshore-distance 数据。 |
| 独立站点框架 | 受限 | 68 站来自 GSSR metadata inventory，且英国与爱尔兰占 45 站，不能外推为均匀欧洲海岸样本。 |
| 公开复现 | 计算链已通过 | full 模式已核验 278 个上游文件并完成 raw-to-paper 重建；最终审稿 ZIP 的 clean-room 结果由包外 reviewer_archive_validation_receipt.json 独立记录。 |
| 作者元数据与 DOI | 待补充 | authors、affiliations、funding、contributions 及正式归档 DOI 尚不能由代码推断。 |

## 12. 可验收的后续目标

1. **共同垂向基准：** 至少 3 个英国和 3 个荷兰 case 转换到明确共同 coastal-MSL reference，记录 offset 来源、公式、不确定性和重算结果；否则 S4 永久保持 sensitivity 定位。
2. **独立 outcome：** 只在存在站点可匹配的 observed 或 dynamic flood-hazard outcome 后，预先定义并比较 water-only、terrain-only、combined screen；完成前不使用 predictive complementarity。
3. **独立海岸样本：** 用不依赖 GSSR inventory 的 station/shoreline inventory 重算，公开全部候选、排除原因和沿岸采样覆盖。
4. **同岸匹配：** 计算 coastline component 与 alongshore distance，逐站固定 opposite-bank/estuary 判定；当前坐标审阅不得替代这一工作。
5. **发布复现：** 在全新临时目录解压 reviewer ZIP，安装项目、运行 derived reproduction、测试并比较确定性科学输出哈希；记录 release tag、commit 与 ZIP SHA-256。
6. **投稿元数据：** 补齐 authors、affiliations、funding、contributions 和正式归档 DOI；HTML、Markdown、PDF 中不留“待补充”。

## 13. 复现入口

- 审稿人快速复现：`python scripts/reproduce.py --mode derived`
- 上游文件预检：`python scripts/reproduce.py --mode full --verify-only`
- 完整 raw-to-paper：`python scripts/reproduce.py --mode full`
- 科学合同：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`
- 发布门禁：`python scripts/run_major_revision_rebuild.py`
