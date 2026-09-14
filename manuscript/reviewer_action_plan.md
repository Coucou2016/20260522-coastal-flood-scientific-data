# 审稿人式问题清单与可验收修改目标

生成时间：由当前项目文件、论文正文、研究报告、图件、源表和构建脚本综合审阅形成。

## 总体判断

当前稿件已经从早期的案例报告推进为一个区域尺度的筛查诊断研究。主线已经比较清楚：COAST-RP storm-tide magnitude（风暴潮位幅值）与 DeltaDTM connected-terrain response（连通地形响应）给出的沿海洪水筛查优先级并不完全一致。现有结果可以支持“二者应作为互补筛查信息同时报告”，但还不应写成“真实风险排序被水位指标误排”。

当前最重要的投稿前目标不是继续堆图，而是把证据链闭合到以下标准：数据来源可追溯、地形连通算法可审计、统计解释不过度、图件能直接解释核心问题、复现包可以让审稿人一键重建。

## 高优先级问题与修改目标

### 1. DeltaDTM mask 与 marine seed 审计已完成主流程改造

**当前状态。** 本项已从“最大方法风险”推进为“已完成主流程改造，并已完成七站 local DTM validation 初步交叉验证”的状态。项目已接入官方 `mask_tiles.zip`，并生成 mask-aware terrain metrics、mask class counts、mask-aware rank diagnostics、top-k null envelope 和 mask-seed audit source tables。主文、报告、Figure 3、Figure 4、Supplementary gallery 和 local DTM validation figure 已同步改为 official-mask-aware 主结果；boundary no-data seed proxy 仅作为 sensitivity comparator 保留。

**为什么重要。** connected terrain 的核心问题不是“低地是否低于 2 m”，而是“这个低地是否真的与海洋或潮汐水体连通”。如果湖泊、非潮汐河流、裁剪单元或 tile boundary no-data 被误当成海洋入口，connected fraction 和 connected area 可能被放大或改变排名。

**已落实。**

1. 官方 DeltaDTM `mask_tiles.zip` 已下载并校验，源表记录大小和 MD5。
2. mask class 1 ocean 作为主 seed。
3. class 2 lake 不作为 marine seed。
4. class 3 river 只在与 ocean component 连通时纳入 ocean/tidal-water seed。
5. class 255 clipped cells 不作为 water seed，也不进入低地分母。
6. 每个 station window 已输出 ocean、river、lake、255、valid terrain、connected、unconnected、all-below 的像元数与面积。

**验收条件与证据。**

- 已生成 `data/figure_source/Fig6_mask_class_counts.csv`、`Fig6_mask_aware_terrain_area_metrics.csv`、`Fig6_mask_aware_rank_metrics_fraction_area_samples.csv`、`Fig6_mask_aware_two_sided_permutation_association.csv` 和 `Fig6_deltadtm_mask_seed_audit.csv`。
- Figure 3 和 Supplementary gallery 图例已改为 official ocean/tidal-water seed。
- 主文 Methods 已说明 official DeltaDTM mask-aware primary analysis，并把 boundary no-data 作为 sensitivity/proxy check。
- mask-aware 结果已同步改写摘要、Results、Discussion、图注、报告和自动审计。
- `scripts/audit_current_outputs.py` 已通过 mask-aware source table 和 Figure 3 archetype 一致性检查。

### 2. local DTM validation 已完成七站初步交叉验证

**当前状态。** 已完成 Sheerness、Newlyn、Lowestoft、Immingham、Den Helder、Delfzijl 和 Hoek van Holland 七站 local DTM cross-check。英国四站使用 Environment Agency LiDAR Composite DTM 2 m WCS 并降采样到 10 m 分析网格；荷兰三站使用 PDOK/Rijkswaterstaat AHN DTM 0.5 m WCS 并降采样到 10 m 分析网格。七站均复用同一 official DeltaDTM mask-derived ocean/tidal-water seed 和 class-0 land denominator。

**为什么重要。** Communications Earth & Environment 类期刊会期待至少对关键结论做独立交叉验证。尤其 Hoek van Holland、Delfzijl、Den Helder 等工程低地，DeltaDTM 的连通结果不能直接被解释为真实洪水路径。

**已落实。**

1. 生成 `data/figure_source/TableS_local_dtm_validation.csv`。
2. 生成 `figures/main/FigS_local_dtm_validation.png/pdf` 和 `figures/supplementary/FigS_local_dtm_validation.png/pdf`。
3. Lowestoft 类别稳定：DeltaDTM 16.55%，local DTM 18.36%，connected-pixel IoU 0.781。
4. Delfzijl 类别稳定：DeltaDTM 96.98%，local DTM 93.36%，connected-pixel IoU 0.917。
5. Newlyn 保持低响应：DeltaDTM 6.25%，local DTM 8.97%；Immingham 两种产品下 connected response 均为 0.00%。
6. Sheerness 从 DeltaDTM 46.28% 降至 local DTM 10.33%，Den Helder 从 71.95% 降至 4.96%，Hoek van Holland 从 46.73% 降至 1.63%，类别改变。
7. 主文已同步降调：Sheerness、Den Helder 和 Hoek 不再作为稳定高连通证据，而是作为 validation-sensitive / protected-lowland sensitivity cases。

**剩余边界。**

- 当前 local DTM 验证没有完成完整 vertical datum harmonization，因此是 elevation-product sensitivity check，不是绝对洪水水位验证。
- 若正式投稿，建议继续扩展到更多 archetype 并补充垂向基准转换或更明确的本地基准说明。

### 3. top-set mismatch 只能作为决策描述，不能作为显著性证据

**问题。** 全空间 74 站点样本中，top-20% priority sets overlap 为 1/15，描述性 mismatch 为 93%。这个数字很直观，但随机独立列表本来就可能有较低 overlap。现有 top-k null envelope 已经说明 top-set overlap 应作为 decision-oriented description，而不是“显著低于随机”的统计证据。

**为什么重要。** 如果正文把 mismatch 写得过强，统计审稿人会指出 random expected mismatch 已经很高，从而削弱整篇文章的可信度。

**怎么改。**

1. 保留 top-k overlap curve 和 permutation envelope。
2. 主文统计证据以 raw COAST-RP magnitude vs raw connected fraction / area 的 Spearman 和 Kendall 为主。
3. 所有 top-set mismatch 表述都加上“descriptive / decision-oriented”限定。
4. 避免 “distortion”“mis-rank”“true hotspot”等暗示 connected-terrain ranking 是真值基准的措辞。

**验收条件。**

- 摘要、Results、Figure 4 caption、Discussion 均不把 mismatch 写成显著超出随机期望的证据。
- Figure 4 caption 明确：top-k overlap lies within the permutation envelope and is used to contextualize priority-set agreement.
- `scripts/audit_current_outputs.py` 通过 top-k envelope 与 rank arithmetic 检查。

### 4. 74-station all-spatial 样本、46-station GSSR-qualified 样本和 30-station retained subset 必须严格分工

**问题。** 论文现在有三个样本层级：74 个 all-spatial stations、46 个 GSSR-qualified stations、30 个 retained stations。主文已经开始解释，但仍需持续避免读者误解为所有分析都来自同一站点集合。

**为什么重要。** COAST-RP-terrain rank test 不依赖 GSSR 质量，因此 74 站点是主分析。D10 产品定义分析依赖 GSSR，因此应使用 GSSR-qualified 或 30-station retained subset。潮汐解释又只限于 13 个 source-verified tidal stations。

**怎么改。**

1. Figure 1 和 Methods 中保持三层样本定义。
2. 每张表和每个结果句子都说明样本数与样本层级。
3. 报告和论文中潮汐结论只写 “In the 13-station source-verified tidal subset...”。

**验收条件。**

- 全文不存在把 13 个潮汐站点结论外推到 74 个站点的句子。
- report 与 paper 均写明 13 source-verified tidal stations；不再出现 stale eight-station count。
- 每个 rank diagnostic 表都有 sample 和 n_sites 列。

### 5. Figure 3 的任务应是解释核心 rank-discordance，而不是展示“哪里蓝最多”

**问题。** 用户反馈 Figure 3 的直观感受仍然重要：高连通案例不能淹得满到失去层次，低连通案例不能完全看不出响应。新版已改成 Dunkerque、Boulogne-sur-Mer、Lowestoft 的 3 × 3 evidence grid，方向正确，但投稿前还需确保图件在论文尺寸下仍能读懂。

**为什么重要。** Figure 3 是读者理解 Figure 4 区域统计的桥梁。它应回答“为什么水位排名和地形响应排名会分离”，而不是让读者猜地图颜色。

**怎么改。**

1. 保持三列 archetype：高水位/高连通，高水位/低连通，较低水位/较高连通。
2. 每列第一行显示分类地图，第二行显示水位排名与地形排名，第三行显示 threshold-response curve。
3. 图中只保留必要数字：RP10、connected fraction、connected area、water/terrain rank。
4. 低连通案例如果地图响应太小，可用 inset 或边界高亮显示 connected cells，但不得改变数据。

**验收条件。**

- PDF 缩放到期刊双栏宽度时，站点名、核心数字、图例仍可读。
- 三个 archetype 的指标与 `Fig6_archetype_map_selection.csv`、`Fig6_fixed10km_terrain_area_metrics.csv` 完全一致。
- 报告中明确说明图件没有为了美观更改计算结果。

### 6. 潮汐元数据还需补齐，但当前结论边界已可接受

**问题。** 30-station retained subset 中只有 13 个 source-verified tidal metadata，2 个 context-only，15 个 missing。当前主文已限制在 13 个站点解释 tidal range 与 D10 的关系，这一处理是稳妥的，但投稿前最好补齐法国、荷兰、德国等站点。

**为什么重要。** D10 大小与潮差关系强是物理预期，但如果 source-verified metadata 覆盖不足，审稿人会要求证明这不是英国站点驱动的局部现象。

**怎么改。**

1. 补齐 SHOM/REFMAR、Rijkswaterstaat、BSH、Danish/Norwegian 官方潮汐调和或大潮差数据。
2. 对所有可验证站点重新计算 tidal range vs D10 和 tidal range vs connected terrain。
3. 对 context-only 数据继续明确标注，不混入主文推断。

**验收条件。**

- source-tracked tidal table 覆盖率显著高于当前 13/30。
- 主文报告 source-verified subset 和 all-available context check 两套结果。
- 如果补齐后相关性变化，图 2c 和 Results 需相应更新。

### 7. 本地复现包已生成，DOI 或 reviewer link 仍是投前硬门槛

**当前状态。** 本地复现包已经生成：`reproducibility_package/` 和 `reproducibility_package.zip`。其中包含 processed station master table、figure source tables、raw-file hashes、station coordinates、COAST-RP match distances、terrain window definitions、official mask-aware seed rules、package versions、当前 paper/report 输出、验证脚本和 one-command rebuild workflow。仍未完成的是把该复现包发布到公共仓储或审稿私有仓储，并在 Data availability / Code availability 中填入 DOI 或 private reviewer link。

**为什么重要。** 论文的强项是透明、可复现、多数据源诊断；如果缺少可运行复现包，强项会变成弱点。

**怎么改。**

1. 保持本地复现包随 paper/report 重建同步刷新。
2. 发布包含本地复现包内容的公共或 private reviewer-access 仓储。
3. 用 `scripts/set_submission_links.py` 将 DOI 或 private reviewer link 写入 `config/submission_links.json`，不要手工修改导出的 paper 文件。
4. 重新运行 paper/report/package 构建脚本，并用 `scripts/audit_submission_readiness.py` 确认最终投稿门槛通过。

**验收条件。**

- 本地 `reproducibility_package/` 和 `reproducibility_package.zip` 存在，并包含 `README_reproducibility.md`、source-data manifest、raw-file hash manifest、package versions 和 one-command rebuild 脚本。
- `scripts/audit_current_outputs.py` 运行通过。
- `config/submission_links.json` 中填入真实 DOI 或 private reviewer link，Data availability 和 Code availability 自动写入该链接。
- `scripts/audit_submission_readiness.py` 运行通过。

## 本轮已执行或已加入自动检查的事项

1. 报告脚本中的 source-verified tidal station 计数改为从 Northwest Europe source-tracked table 读取，避免把八个 focal station 表误当成区域潮汐样本。
2. 新增并更新 `scripts/audit_current_outputs.py`，用于检查 standalone HTML、图片嵌入、潮汐计数、D10 算术、mask-aware rank arithmetic、Figure 3 archetype 源表一致性、official DeltaDTM mask 接入状态和 terrain boundary 表述。
3. 已接入官方 DeltaDTM mask-aware terrain workflow，生成 74 个 all-spatial stations 的 mask class counts、connected/unconnected/all-below 面积和像元统计。
4. 论文和报告已同步重建：`paper.html/md/pdf`、`report.html/md/pdf` 以及 manuscript 目录中的最终副本均已更新。
5. 本地复现包已生成并加入自动审计：`reproducibility_package/`、`reproducibility_package.zip`、74-row master table、raw-file hashes、package versions 和 one-command rebuild workflow。
6. 已完成七站 local DTM validation，并据此降调 Sheerness、Den Helder 与 Hoek van Holland 的稳定性表述，同时保留 Lowestoft 和 Delfzijl 作为较稳定交叉验证案例。
7. 已新增 `config/submission_links.json`、`scripts/set_submission_links.py`、`scripts/audit_submission_readiness.py` 和 `manuscript/repository_deposit_instructions.md`，将外部仓储链接变成可配置、可审计的最终门槛。
8. 当前仍明确保留 “Data/Code DOI 或 private reviewer link 待补充” 和 “local DTM validation 仍需基准统一” 的边界，不把 connected-terrain screen 写成真实洪水范围。

## 投稿前优先级

1. **必须完成：** 复现包 DOI 或 reviewer link。
2. **强烈建议：** 对已扩展的七站 local DTM validation 继续做垂向基准统一；补齐更多 source-verified tidal metadata；对 Figure 3 做最终期刊尺寸检查；保留 top-k null-envelope 解释。
3. **可以作为后续研究：** 全球尺度扩展、完整水动力模拟、工程防洪系统显式建模、非平稳极值建模。
