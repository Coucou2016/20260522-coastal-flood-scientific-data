# 科学真实性、准确性与完整性审查文档

**对应稿件：** *Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network*  
**审查定位：** code-data-table-figure-manuscript 穿透式内部审计  
**自动约束状态：** 全部通过

## 1. 审查结论

本轮大修没有把审稿意见当作文字层面的“解释补丁”，而是重新冻结唯一主流程，并从原始/中间数据重算区域指标。当前 68 站主结果的算术和拓扑约束通过；主要 Spearman、Kendall、岸段内双侧置换、保持岸段结构的 top-k null、Moran's I 和 six-sector resampling 均直接来自当前 source tables。稿件已删除旧 degree-window 数值、15/20 m denominator sensitivity、未定义的 response categories，以及把 top-set mismatch 解释为 beyond-chance discordance 的写法。

现阶段可以确认的是：代码生成的当前表格与图件内部一致，结果支持“两个区域筛查排序不能互相替代”。不能确认、也没有声称的是：静态地形指标等于真实洪水风险，或者七个本地 DTM case 能代表全部 68 站。垂向基准未统一和缺少独立真实洪水基准仍是投稿前的主要外部证据限制。

## 2. 四个 P0 问题的处理证据

1. **DeltaDTM cutoff 与 15 m denominator：已重构。** 当前文件由 GeoTIFF tag 和 v1.1 README 识别为 DeltaDTM v1.1.1，cap 为 30 m EGM2008；2024 论文描述的是 v1.0 的 10 m + MSL 范围。主流程不再使用 15 m 或 20 m lowland denominator，仅用有限 class-0 represented land；正文明确这种比例不是 nominal 10 km square 的全部陆地比例。
2. **旧窗口数值混入 Supplement：已移除。** 新 Supplementary Information 只从 `Primary_terrain_components_68stations.csv` 和 `Terrain_robustness_grid_74stations.csv` 导出。旧 S2/S6、`Fig5_*` 和 degree-window 表不再构成稿件证据。
3. **sector/country 混用：已统一。** 地图、block resampling 和 leave-one-out 使用同一组六个 coastal-sector identifiers；country omission 不再被称为 sector sensitivity。
4. **未定义 response category：已删除。** 正文只报告连续值和绝对面积；Supplementary Figure S4 报告七个诊断站的连续差值和 IoU，不再报告“4/7 category changed”。

## 3. 产品版本与 mask 审计

| product | release | tile_tag | vertical_reference | release_cap_m | paper_v1_0_cap_m | mask_outside_support_fill | official_255_cells_in_primary_analysis_windows | outside_support_cells_in_primary_analysis_windows | note |
|---|---|---|---|---|---|---|---|---|---|
| DeltaDTM | v1.1.1 | DeltaDTM v1.1.1 / DeltaDTM.jl v1.1.1 | EGM2008 | 30 | 10 | 254 | 0 | 3320 | The 2024 paper documents v1.0; the downloaded v1.1 README documents the 30 m EGM2008 cap. Outside-support fill is kept distinct from class 255 and excluded from all land denominators. |

旧代码曾同时用 255 表示 DeltaDTM 官方 clipped class 和 boundless/reprojection fill。新版代码将窗口外支持固定为 254。扫描得到的 72 个 source mask tiles 中未发现官方 255；旧窗口中出现的 255 因而不能解释为真实 clipped land。当前自动门禁要求 254/255 分离，并禁止 lake、outside support、clipped support 或任意 no-data 作为 marine seed。

## 4. 自动科学约束

| Check | Pass | Observed | Criterion or meaning |
|---|---|---|---|
| Robustness-grid rows | True | 2960 | 74 stations x 40 recorded configurations |
| Unique stations | True | 74 | regional candidate inventory |
| Primary stations | True | 68 | COAST-RP match <=6 km |
| Connected area <= below-threshold area | True | 0 | violations |
| Four-neighbour <= eight-neighbour | True | 0 | violations |
| Metric decomposition identity | True | 4.26326e-14 | maximum absolute percentage-point error |
| Official class 255 in primary windows | True | 0 | cells |
| Outside-support sentinel distinct | True | 3320 | class-254 cells recorded and excluded |

这些检查证明当前输出满足代码自身声明的面积与拓扑关系。它们不证明输入产品没有系统误差，也不等同于独立洪水观测验证。

## 5. 统计证据边界

| terrain_metric | n_sites | spearman | kendall | permutation_two_sided_p | top_n | top_overlap | top_overlap_expected_independent | spearman_sector_bootstrap_p025 | spearman_sector_bootstrap_p975 | sector_adjusted_rank_association | sector_stratified_permutation_two_sided_p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| connected_reference_land_pct | 68 | -0.333168 | -0.210711 | 0.00639936 | 14 | 1 | 2.88235 | -0.647188 | 0.178855 | -0.491883 | 0.00039996 |
| below_reference_land_pct | 68 | -0.309272 | -0.187884 | 0.00859914 | 14 | 1 | 2.88235 | -0.624297 | 0.190665 | -0.45364 | 0.00089991 |
| conditional_connectivity_pct | 68 | 0.108145 | 0.0717274 | 0.378762 | 14 | 5 | 2.88235 | -0.276457 | 0.32199 | 0.198325 | 0.420458 |
| connected_area_km2 | 68 | -0.340955 | -0.208077 | 0.00479952 | 14 | 1 | 2.88235 | -0.626084 | 0.208442 | -0.488862 | 0.00019998 |

station-label permutation 的显著性与 spatial inference 必须分开阅读。connected-land share 和 connected area 的 station-level p 较小，但 six-sector ranges 跨 0。Top-20% overlap 为 1/14，独立随机期望为 2.88；exact lower-tail p = 0.152。因此稿件只写 limited recovery / weak concordance / non-interchangeability，不写 unusual mismatch、distortion、mis-rank 或 proven complementarity。

主推断采用保持岸段组成的空间零模型：RP10 与 connected-land share 的 top-20% overlap 为 1/14，空间零模型 95% 包络为 [0, 4]，lower-tail p=0.257。观察值处在包络内，因此该结果只证明两个清单恢复度有限，不证明错配异常大于空间随机。

指标分解还说明 composite connected share 的负关联主要来自 below-2 m land prevalence；conditional connectivity 的 rho 约为 0。这一结果直接纠正了把低 composite fraction 一概解释为“低连通性”的构念混淆。

### 分母几何与拓扑

| terrain_metric | terrain_metric_label | n_sites | raw_spearman_water_vs_metric | partial_spearman_controlling_represented_land_fraction | spearman_metric_vs_represented_land_fraction | spearman_water_vs_represented_land_fraction |
|---|---|---|---|---|---|---|
| below_reference_land_pct | lowland_prevalence | 68 | -0.309272 | -0.310448 | -0.0976448 | 0.0031683 |
| conditional_connectivity_pct | conditional_connectivity | 68 | 0.104533 | 0.105806 | -0.127793 | 0.0031683 |
| connected_reference_land_pct | connected_lowland_share | 68 | -0.333168 | -0.335911 | -0.137191 | 0.0031683 |
| connected_area_km2 | connected_area | 68 | -0.340955 | -0.341566 | 0.0511509 | 0.0031683 |
| connected_window_pct | connected_window_share | 68 | -0.340955 | -0.341566 | 0.0511509 | 0.0031683 |

| terrain_metric | n_sites | rank_spearman_4n_vs_8n | top20_n | top20_overlap | membership_changes | maximum_eight_minus_four | median_eight_minus_four |
|---|---|---|---|---|---|---|---|
| connected_reference_land_pct | 68 | 0.961102 | 14 | 11 | 6 | 44.0569 | 0.00732171 |
| connected_area_km2 | 68 | 0.966828 | 14 | 11 | 6 | 23.5498 | 0.0038732 |
| conditional_connectivity_pct | 68 | 0.900571 | 14 | 13 | 2 | 91.5269 | 0.581332 |

RP10 与 represented-land fraction 的 rho 接近 0，控制该比例前后主关联几乎不变。4 邻域和 8 邻域在区域排名上高度一致，但 top-20% 仍有站点成员变化，证明站点优先级对拓扑定义比区域总体结论更敏感。

### COAST-RP 匹配审计

68 个纳入站点的最大匹配距离为 2.811 km；下列 6 个站点因超过 6 km 规则被排除，而不是在出图后人工删除：

| station | recomputed_match_dist_km | coast_rp_source_lon | coast_rp_source_lat | match_exclusion_reason |
|---|---|---|---|---|
| Cordemais France | 22.6474 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Le Pellerin France | 28.388 | -2.014 | 47.014 | excluded_nearest_coast_rp_point_gt6km |
| Nantes Usine Brulee | 39.423 | -2.014 | 47.014 | excluded_nearest_coast_rp_point_gt6km |
| Donges France | 8.27799 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Montoir De Bretagne | 6.89698 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |
| Paimboeuf France | 14.3371 | -2.19 | 47.278 | excluded_nearest_coast_rp_point_gt6km |

## 6. 本地 DTM product-and-datum cross-check

| station | delta_connected_2m_reference_land_pct | local_connected_2m_reference_land_pct | delta_connected_2m_area_km2 | local_connected_2m_area_km2 | connected_pixel_iou_after_reprojection | local_dtm_vertical_datum_note |
|---|---|---|---|---|---|---|
| Sheerness | 42.7002 | 9.62959 | 20.3643 | 4.61207 | 0.214623 | Ordnance Datum Newlyn / EA product native datum |
| Newlyn | 0.44611 | 0.416648 | 0.276293 | 0.259144 | 0.527548 | Ordnance Datum Newlyn / EA product native datum |
| Lowestoft P024 Uk | 1.41616 | 6.16525 | 0.669507 | 2.92848 | 0.110977 | Ordnance Datum Newlyn / EA product native datum |
| Immingham P026 Uk | 0.405551 | 0.078999 | 0.24946 | 0.0487939 | 0.0417246 | Ordnance Datum Newlyn / EA product native datum |
| Denhelder Hel Nl | 71.7296 | 4.36493 | 20.8545 | 1.27433 | 0.0554507 | Normaal Amsterdams Peil / AHN product native datum |
| Delfzijl Del Nl | 96.7041 | 89.7843 | 61.3031 | 57.1869 | 0.925796 | Normaal Amsterdams Peil / AHN product native datum |
| Hoek van Holland | 2.63966 | 1.43861 | 1.41098 | 0.771845 | 0.217064 | Normaal Amsterdams Peil / AHN product native datum |

Supplementary Figure S4 的 IoU target grid、grid shape、transform、mask resampling 和文件 SHA-256 全部记录在 `TableS_local_dtm_product_datum_crosscheck.csv`。Environment Agency 和 AHN 数据未与 EGM2008 统一，因此本文不使用 validation 一词，也不把差异归因给 DeltaDTM 单一误差。七站为 diagnostic cases，不把变化比例外推到 68 站总体。

## 7. 图件真实性与视觉检查

| Figure | Pixels | DPI target | Source data | Visual QA |
|---|---|---|---|---|
| Fig1_process_terrain_design.png | 3542 x 2249 | 500 | Primary_station_coastal_sectors.csv; Primary_sample_flow.csv | inspected at original resolution; no deliberate cell enlargement |
| Fig2_regional_screening_agreement.png | 3394 x 3360 | 500 | Primary_terrain_components_68stations.csv; Return_period_sensitivity.csv; Spatial_sector_bootstrap_intervals.csv; Topk_spatial_null_curves.csv | inspected at original resolution; no deliberate cell enlargement |
| Fig3_connected_terrain_contrasts.png | 3669 x 3934 | 500 | Fig3_predefined_site_selection.csv; Fig3_threshold_response_source.csv | inspected at original resolution; no deliberate cell enlargement |
| Fig4_metric_decomposition_robustness.png | 3710 x 3318 | 500 | Primary_terrain_components_68stations.csv; Denominator_adjusted_associations.csv; Topology_sensitivity_summary.csv; Rank_robustness_one_at_a_time.csv | inspected at original resolution; no deliberate cell enlargement |
| FigS1_water_level_definition.png | 3443 x 1456 | 500 | Fig2_water_level_divergence_with_uncertainty.csv; TableS_tidal_regime_metadata_source_tracked.csv | inspected at original resolution; no deliberate cell enlargement |
| FigS2_process_coherence.png | 5122 x 2354 | 500 | Fig3_driver_correlations.csv; event-composite source tables | inspected at original resolution; no deliberate cell enlargement |
| FigS3_connectivity_gallery.png | 3462 x 3415 | 500 | Primary_terrain_components_68stations.csv; frozen DeltaDTM windows | inspected at original resolution; no deliberate cell enlargement |
| FigS4_elevation_product_datum_sensitivity.png | 3574 x 2975 | 500 | TableS_local_dtm_product_datum_crosscheck.csv | inspected at original resolution; no deliberate cell enlargement |
| FigS5_coastrp_match_audit.png | 3466 x 1590 | 500 | Match_distance_audit_74stations.csv; Match_distance_histogram_source.csv | inspected at original resolution; no deliberate cell enlargement |

Figure 3 的三个站由机器可读规则选出。低值站点只对原始 connected cells 做局部放大，不改变主地图中的像元面积；high/low 视觉平衡通过指标分解和三条实算 threshold curves 实现，而不是调数值。Figure 4 取消离散类别，Figure 2 明确区分 raw station estimate、sector range 和 spatially constrained top-k null。

## 8. 关键文件 SHA-256

| File | Bytes | SHA-256 |
|---|---|---|
| data/raw/coast_rp/COAST-RP.zip | 6798999 | 13242fe8b682230420357dbac202b10590f41dc0c9e378b9c2c69f91962704c9 |
| data/raw/gssr/metadata/eraint.geojson | 307194 | aab77394a0bf87b3ae611131e26b489a7abe9dd67add071aeee0da4b3bab46e6 |
| data/raw/deltadtm/index/README.md | 2326 | 9da10b0576ff4368a756bd5646b091fab6b7c7c7d217a6f758fbe0803f826e00 |
| data/raw/deltadtm/zips/mask_tiles.zip | 428178062 | 3f8c6999f90346359e60cc6c757786d43fd1cb65e4ab13125faaa80606487775 |
| data/figure_source/Primary_terrain_components_68stations.csv | 31386 | c516a97298a87ddd8d1746d8975e23afff94043a2a030c2e8eee6707c6c6893e |
| data/figure_source/Terrain_robustness_grid_74stations.csv | 1321599 | 5708031c3492aa47f2bf456d52df5dcbe1d22ac427e5dc7e5d168723b56539af |
| data/figure_source/Rank_robustness_one_at_a_time.csv | 35926 | dc43ead84439e0d72c1f71ddf9bde1cca9334fdbf399e2385a020b3f3b5e2b2d |
| data/figure_source/Spatial_sector_bootstrap_intervals.csv | 1316 | 2e73a799fcb280cb37daab1a6d7347b632c546b0a4a9bc4d70512d1055e93124 |
| data/figure_source/Topk_spatial_null_curves.csv | 5811 | ea385515afb10a2448160909057daf2e4e6f2b5356f76d1d6349b9331ee16042 |
| data/figure_source/Return_period_sensitivity.csv | 8146 | 51397a192a4e7e413c0f22d1afb044d17eaca7c956f234c09c00fc49629e8a3b |
| data/figure_source/Denominator_adjusted_associations.csv | 884 | 0f8dea8b42895a42fa1d672edfe2a022dae900643d6d93c2316633de802a2823 |
| data/figure_source/Topology_sensitivity_summary.csv | 422 | 85f7263bc4da748e07eb96bf6231c94ffe4072d62aa8294743b91ea62916602b |
| data/figure_source/Match_distance_audit_74stations.csv | 37578 | d255f5fa00644be1d371c8df1a789c307bbe89f7d463842f151b046203380df0 |
| data/figure_source/TableS_local_dtm_product_datum_crosscheck.csv | 9733 | 6b9c4656676341d87c2ea8b0a84c307c984ed1e04439dca7b3e0563329ae9928 |
| scripts/add_mask_aware_terrain_diagnostics.py | 32421 | aa8e38aaf0eedfac3628eabd84270fcdbb2c279e1a1fbd8c1afbdb7ef1cf5e16 |
| scripts/rebuild_frozen_primary_analysis.py | 21686 | 057e8bbd4011cac63bfedc58a85c94981eaa1aaa4dd1726b87b7f4f5ca7389cc |
| scripts/add_external_review_diagnostics.py | 28100 | b9bb20e4a29c0961500d7961b4a1c7f8e70b70285750b5812e2742f03d312e21 |
| scripts/add_local_dtm_validation.py | 20251 | f4320a331c77492aa95f1216bc6e12301a5d2ce76a49b46914cff3d636c8a3ef |
| scripts/make_major_revision_figures.py | 41950 | 4e1c09d6362481d8b283ee1e40b848f52f16c47014381198938db2ece8c2c006 |
| data/raw/local_dtm/delfzijl-del-nl_local_dtm_10m.tif | 2204083 | a8b3589a24ca9dbcb00d18e24c916e193d37a9b73034c185bf29fcf80a9cbb35 |
| data/raw/local_dtm/denhelder-hel-nl_local_dtm_10m.tif | 1310648 | b950e177da667509c85bb8a4dc77c4dcbac5b56d85507ea706e968568af15e79 |
| data/raw/local_dtm/hoekvanholla-hvh-nl_local_dtm_10m.tif | 1848802 | e960ac322ae8e703055a75739d6dee6a65c2ee367e9dc0dd8af1c7f6ff600563 |
| data/raw/local_dtm/immingham-p026-uk_local_dtm_10m.tif | 9437675 | 8567cb377b27480b51f3dbee6ff5501784f3eed237e0ec7e8058ff09789ed6e7 |
| data/raw/local_dtm/lowestoft-p024-uk_local_dtm_10m.tif | 6291923 | d95f97c91d4df295e6113b98fccbdab4d3bedac1a35c3751464e0b8e61ab2819 |
| data/raw/local_dtm/newlyn-p001-uk_local_dtm_10m.tif | 9437675 | fef345c91868dd64e5a2e11180ad066b7a1f8ce92305cf26990d70fd0c9e51c2 |
| data/raw/local_dtm/sheerness-p015-uk_local_dtm_10m.tif | 9437675 | 40c81f2a969e0044184d5fb40ebc11728dca5376d2707386e29c90def027cadd |

此清单用于确认后续 manuscript、report 或 publication package 是否仍由同一基线生成。大体积上游数据不应凭文件名认定相同，必须复核 hash 或上游 DOI/version。

## 9. 仍未消除的风险

| Risk | Status | Evidence boundary |
|---|---|---|
| 垂向基准统一 | 未完成 | DeltaDTM/ODN/NAP 尚未转换到共同 local-MSL reference；Supplementary Figure S4 只能解释为 combined product/datum/provider-resampling sensitivity。 |
| 独立真实洪水基准 | 未完成 | 没有 observed or dynamic flood-hazard truth dataset，因此不能声称 connected-terrain ranking 是真实优先级。 |
| 样本代表性 | 受限 | 68 站来自 GSSR metadata inventory，且岸段分布不均；Denmark-Norway 仅 2 站。 |
| 本地 DTM 服务重采样 | 受限 | WCS scaleFactor 生成 nominal 10 m；连续高程插值核由服务端控制。 |
| 公开审稿仓库 | 已完成 | 代码、派生数据、图表源数据、文稿和审查证据已发布至 https://github.com/Coucou2016/20260522-coastal-flood-scientific-data；上游原始文件以来源和 SHA-256 清单追踪。正式归档 DOI 尚待版本冻结。 |
| 潮汐元数据 | 部分完成 | 正式 cross-product return-level difference 的潮汐语境限制在 13 个 source-verified sites；Brest 和 Hoek 仍不得进入正式 tidal inference。 |

## 10. 可验收的投稿前目标

1. **共同垂向基准：** 至少将 3 个英国和 3 个荷兰 case 的 terrain 与 coastal MSL 转换到明确共同参考；验收为方法给出 offset 来源、公式和不确定性，重算后的 source table/figure 可一键复现。若无法完成，则 Supplementary Figure S4 保持 sensitivity 定位。
2. **独立结果基准：** 在可匹配站点上引入 observed 或 dynamic hazard outcome；验收为预先定义评价指标并分别比较 water-only、terrain-only 和 combined screen。完成前不使用 predictive complementarity。
3. **独立站点框架：** 用不依赖 GSSR inventory 的 coastal station/shoreline sample 重算主关系；验收为 sample-flow 记录全部候选、排除原因和 coastal-spacing/sector coverage。
4. **公开复现入口：** GitHub 公开入口已经建立；下一项验收是在独立临时目录中克隆仓库并运行不依赖上游大文件的合同测试，再记录 release tag、commit 和 archive hashes。正式投稿版本冻结后可再生成归档 DOI。
5. **投稿元数据：** 补齐 authors、affiliations、funding、contributions；验收为 HTML、Markdown 和 PDF 中无“待补充”占位。

## 11. 复现入口

核心重算命令为 `python scripts/rebuild_frozen_primary_analysis.py`。本地 DTM 交叉检查为 `python scripts/add_local_dtm_validation.py`，主图为 `python scripts/make_major_revision_figures.py`，论文和补充材料分别由 `python scripts/build_standalone_paper.py` 与 `python scripts/build_supplementary_information.py` 生成。自动科学合同使用 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q --import-mode=importlib`。
