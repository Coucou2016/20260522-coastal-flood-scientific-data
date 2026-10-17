# Limited concordance between storm-tide magnitude and standardized connected-lowland screening across Northwest Europe

**Manuscript type:** Article  
**Authors:** 待补充  
**Affiliations:** 待补充  
**Corresponding author:** 待补充

## Abstract

Large-area coastal assessments often rank locations by extreme water level before detailed inundation modelling. Whether such a ranking also identifies coastally connected low terrain has received less attention. We paired COAST-RP storm-tide return levels with a standardized DeltaDTM v1.1.1 terrain screen at 68 Northwest European stations. The terrain calculation used 10 km windows, the official water mask and a 2 m EGM2008 threshold; it did not simulate an event or flood extent. At the 10-year return period, storm-tide magnitude was weakly negatively associated with the connected share of represented land (Spearman rho = -0.33) and connected area (rho = -0.34). Resampling coastline-contiguous blocks produced ranges of -0.55 to -0.03 at 100 km, -0.57 to -0.03 at 150 km and -0.58 to 0.02 at 250 km for connected share, precluding a spatially stable negative regional relationship. The storm-tide and terrain top-20% sets shared one of 14 stations, but this overlap lay within spatially restricted null envelopes. Median absolute displacement between the two rankings was 26 places. The terrain association primarily reflected lowland prevalence rather than conditional raster connectivity and remained similar in threshold-integrated and coastline-oriented sensitivity analyses. Thus, water-level magnitude showed limited concordance with this standardized land-response screen. Neither ranking is treated as observed or dynamically simulated flood hazard.

## Introduction

Extreme-water-level products provide a practical first filter for regional coastal assessment [1-3]. They allow locations to be compared before the data and computational demands of local inundation modelling are met. A water level at the coast, however, is a boundary forcing rather than a measurement of water on land. Terrain, hydraulic pathways, event duration, drainage and flood defences all mediate the land response. Dynamic pan-European modelling and direct land-based observations illustrate the resulting gap between a coastal water-level indicator and flooding at a particular place [4,5].

Elevation-based screening offers another view of the coast, but introduces its own assumptions. Narrow embankments, channels and engineered drainage may be absent from a terrain model with cells tens of metres across [6,7]. Connectivity rules can reduce the familiar bathtub error of filling isolated depressions, yet they do not reproduce hydraulics or the operation of coastal structures [8]. Vertical reference is no less consequential. Coastal land elevation and sea level may have similar numerical values while referring to different surfaces; datum misalignment can materially alter exposure estimates [9]. Product support, water-mask classes, graph topology and vertical reference must therefore be treated as parts of the terrain-screen definition rather than as incidental processing details.

The water-level variable itself also requires a precise definition. COAST-RP combines surge and tide probabilistically to estimate storm-tide return levels [10,11], whereas the Global Storm Surge Reconstruction (GSSR) describes a non-tidal surge residual [12]. Their return quantiles are not physically equivalent, especially on macrotidal coasts where surge timing relative to astronomical tide shapes total sea level [13]. That distinction motivates a supporting product-context analysis here, but the principal comparison is deliberately narrower: storm-tide magnitude versus a separately constructed connected-lowland terrain screen.

We ask whether ranking stations by storm-tide magnitude recovers the ranking obtained from a standardized connected-lowland screen. The analysis includes 68 stations from a sampled Northwest European network with DeltaDTM support, a resolved marine seed and a nearby COAST-RP point (Fig. 1). We separate the terrain screen into lowland prevalence, conditional raster connectivity and absolute connected area; quantify priority displacement and selection stability; and repeat the analysis across return periods, terrain thresholds, window geometries, water and land graph topologies, and three spatial-block scales. Three cases selected by recorded rules show why similar composite values can arise from different terrain mechanisms. Supporting GSSR and tidal analyses are reported separately and do not determine the main result.

## Results

### The sampled station network is spatially clustered

The regional inventory contained 74 stations between 9 degrees W and 9 degrees E and 47 to 61 degrees N. DeltaDTM v1.1.1 elevation support and an official-mask marine seed were available at every location. A pre-specified 6 km limit on the nearest COAST-RP point excluded six Loire estuary stations, leaving 68 stations for the primary comparison (Fig. 1; Supplementary Fig. S5). The greatest retained separation was 2.81 km. The network remained geographically uneven: 45 of the 68 stations were around the British and Irish coasts, whereas the continental North Sea and Skagerrak were represented by six stations.

Both quantities were spatially structured. With symmetric 150 km distance weights, Moran's I was 0.31 for the 10-year storm tide and 0.44 for connected land share. Lowland prevalence was more strongly clustered (I = 0.66), whereas conditional connectivity was not (I = -0.02). We therefore used explicit, coastline-contiguous spatial blocks and report the sensitivity of inference to 100, 150 and 250 km target scales [14].

### Storm-tide and terrain screens selected different stations

At the 10-year return period, COAST-RP magnitude and the connected share of represented DeltaDTM land had a Spearman correlation of -0.33 (Kendall tau = -0.21; Fig. 2a). Connected area gave a similar result (rho = -0.34; tau = -0.21). The two rankings differed by a median of 26 places, and the largest displacement was 64 places. Their top-20% sets each contained 14 stations but shared only Sheerness. Across the 40 archived terrain configurations, six stations entered the terrain top set whenever they were eligible and 40 never entered it; Hoek van Holland entered in 52.5% of its eligible configurations (Fig. 2d). These frequencies describe the stability of the terrain-screen decision, not the probability of flooding.

The small observed top-set overlap was descriptive. At the 100, 150 and 250 km block scales, an overlap of one lay within the corresponding restricted-permutation envelopes; lower-tail probabilities were 1.00, 0.327 and 0.098, respectively (Fig. 2c). Storm-tide magnitude therefore recovered little of the terrain top set, but the disagreement was not unusually large relative to the spatial null. The result establishes limited concordance between these two screens rather than evidence that one ranking is wrong.

### Spatial inference depended on block scale

Resampling whole coastline blocks retained negative median associations but exposed geographic uncertainty (Fig. 2b). For connected share, the 2.5th-97.5th percentile ranges were -0.55 to -0.03 at 100 km, -0.57 to -0.03 at 150 km and -0.58 to 0.02 at 250 km. Connected-area ranges were -0.57 to -0.02, -0.56 to -0.05 and -0.58 to 0.02. The largest block scale therefore admitted a near-zero regional association. Restricted permutations ask a different question, conditional on the observed block composition: empirical two-tail p values for connected share were 0.135, 0.025 and 0.012 at 100, 150 and 250 km. We place greater interpretive weight on the resampling ranges because they show that the pooled association is not stable to the coastal geography represented by this station network.

Changing the COAST-RP return period had little effect on the descriptive association. Spearman rho for connected share ranged from -0.36 at 2 years to -0.32 at 100 years, and connected area ranged from -0.37 to -0.32. Return-period choice was therefore not the main source of ranking disagreement.

### Lowland prevalence and marine connectivity described different terrain mechanisms

Connected land share is the product of the proportion of represented land below the elevation threshold and the proportion of that low land linked to the marine seed. At the 10-year return period, storm-tide magnitude was weakly associated with lowland prevalence (rho = -0.31) but not with conditional connectivity (rho = 0.10). The composite association therefore arose mainly from how much low terrain was present, not from a coast-wide relationship between storm-tide magnitude and raster connectivity.

Three rule-selected cases make this distinction visible (Fig. 3). Delfzijl was the stable terrain-priority case. Its storm tide ranked 26th of 68, while 97.00% of represented land lay below 2 m and 99.69% of that low land belonged to the marine-connected component. The resulting connected share was 96.70% (61.30 km2), the highest in the sample.

Newport represented a water-priority, lowland-limited setting. Its 8.60 m storm tide ranked third, but only 0.164% of represented land lay below 2 m. Although 90.53% of that small lowland footprint was connected, the composite share was 0.148% (0.102 km2), ranking 67th. Immingham showed a different route to a low composite value: 20.14% of represented land was below 2 m, but only 2.01% of that land connected to the marine seed. Its connected share was 0.406% (0.249 km2). Orange areas in Fig. 3c are therefore classified low terrain outside the marine component, not missing blue cells. The explicit -0.5 m and +0.5 m curves further show that some transitions occur rapidly around the standardized 2 m threshold.

### Terrain definition changed individual priorities

The primary calculation used eight-neighbour connectivity for the ocean-river seed and four-neighbour connectivity for land. Requiring four-neighbour connectivity for both graphs yielded a terrain-rank correlation of 0.86 with the primary result and changed four top-20% memberships (Fig. 4c). Allowing eight-neighbour land connectivity changed six memberships. The distinction is consequently minor for the pooled association but material for some station priorities.

Window and threshold definitions also mattered (Fig. 4d). Connected-share correlations with RP10 ranged from -0.42 at a 1 m threshold to -0.30 at 3 m; integrating the terrain response from 0 to 3 m gave rho = -0.30. Five- and 20-km square windows gave -0.41 and -0.39. A mask-derived 10 km alongshore by 5 km landward window produced rho = -0.25, retained 11 of the primary top 14 stations and changed six memberships. These calculations show that the finding is not confined to a single 2 m cross-section or square geometry, while also demonstrating that the identity of priority sites depends on the terrain construct. Uniform vertical offsets of -1 to +1 m retained negative composite associations but are stress tests, not confidence intervals or spatial error models.

The finite class-0 land represented within the nominal 10 km windows ranged from approximately 14% to 79%. This geometry did not explain the water-terrain association: RP10 storm tide was uncorrelated with represented-land fraction (rho = 0.003), and adjusting ranks for that fraction changed the connected-share correlation only from -0.33 to -0.34. Expressing connected area as a share of the full nominal window likewise gave rho = -0.34. Recording window support nevertheless remains essential because the connected share and connected area answer different questions.

Seven national or local DTM cases provided an additional, deliberately non-inferential sensitivity check (Supplementary Fig. S4). With four-neighbour connectivity, DeltaDTM and local products remained similar at Delfzijl (96.70% versus 89.78%; intersection-over-union 0.926) but differed strongly at several other sites, including Sheerness (42.70% versus 9.63%) and Den Helder (71.73% versus 4.36%). The surfaces were not transformed to a common vertical datum, and provider resampling also differed. These contrasts therefore diagnose combined product, datum and resampling sensitivity; they do not validate either product against a common flood surface.

### Water-level product context remained secondary

In the 13-station source-verified tidal subset, spring tidal range was strongly associated with COAST-RP 10-year storm-tide magnitude (rho = 0.96) but not with connected land share (rho = -0.21; Supplementary Fig. S1). GSSR metadata and residual-surge calculations were used only to clarify product definitions. The local metadata field `corrn` is a reconstruction-correlation summary; no separate extreme-event skill field was present. Atmospheric predictor comparisons are therefore labelled predictor-consistency diagnostics in the Supplementary Information and are not used to support terrain ranking or causal claims.

## Discussion

Storm-tide magnitude and standardized connected-lowland terrain answer different screening questions. The former describes a coastal water-level forcing; the latter combines the abundance and raster continuity of low land. Their limited rank concordance means that a water-level list did not reproduce the same station priorities as the terrain screen. This is a decision-level comparison, not evidence for a negative physical law between storms and terrain. The 250 km resampling range crossed zero, and the observed top-set overlap was not unusually small under any spatially restricted null.

The metric decomposition is central to that interpretation. A small connected share may indicate little low terrain, as at Newport, or substantial low terrain with little connection to the selected marine component, as at Immingham. These mechanisms lead to different follow-up questions. Lowland prevalence concerns the elevation distribution and the chosen vertical threshold. Conditional connectivity concerns channels, barriers, graph topology and marine-seed definition. Reporting both prevents a composite percentage from being mistaken for a direct measure of hydraulic connection.

The terrain calculation is not a flood map. It imposes no hydrograph, momentum, friction, drainage, river inflow, wave action, defence crest or structure operation. Dynamic pan-European modelling shows that these processes and coastal protection can materially alter flood extent [4]. The present calculation asks a narrower topological question: which represented land cells below a standardized terrain-elevation threshold share a raster component with an explicitly defined marine seed? This inexpensive screen can identify where terrain warrants closer examination, but it cannot replace local hydraulic modelling or observed inundation.

Vertical reference remains the principal barrier to event-level interpretation. DeltaDTM v1.1.1 uses EGM2008 heights, the English local product uses Ordnance Datum Newlyn and the Dutch product uses Normaal Amsterdams Peil. Coastal land and sea-level surfaces are often not aligned in a common vertical reference [9,15]. We therefore did not add COAST-RP storm tides to the terrain threshold or describe connected cells as a storm-tide response. The regional 2 m value is a standardized EGM2008 terrain elevation, not a 2 m local mean-sea-level perturbation. Likewise, the local-DTM comparison remains in the Supplementary Information because native-datum and provider-resampling effects cannot be separated from elevation-product effects.

Spatial sampling places a second limit on generalization. The network is concentrated around Britain, Ireland and the English Channel, and lowland metrics are spatially autocorrelated. The three reviewed block schemes remove the earlier dependence on longitude-latitude cut-offs, but they remain analytical approximations rather than a measured alongshore network. Their scale dependence is informative: restricted permutations and block resampling do not answer the same question, and the latter shows that the estimated regional association changes with coastal composition. A more evenly spaced coastline inventory and block construction from measured alongshore distance would provide a stronger basis for regional inference.

Several methodological choices affected individual priorities without making the water and terrain lists converge. The composite association persisted from RP2 to RP100 and was similar for a threshold-integrated metric, but graph topology and window geometry changed top-set membership. The median rank displacement of 26 places and the configuration-specific selection frequencies make that consequence explicit. A priority list should therefore be accompanied by its terrain assumptions and station-level source data, particularly if it is used to allocate expensive local modelling.

An external benchmark remains the decisive next test. The data release accompanying recent pan-European work provides total-water-level storms rather than a station-level dynamic flood-hazard truth set, so it was not treated as validation here. Once terrain and coastal mean sea level are placed on a common reference, storm-tide magnitude, terrain components and their combination could be assessed against observed inundation or dynamic hazard. Such evidence would be needed to claim improved prediction or complementarity. The present analysis instead demonstrates limited agreement between two transparent screening constructs; it does not designate either as truth.

## Methods

### Study design and sample

The primary analysis paired COAST-RP storm-tide return levels with independently calculated DeltaDTM terrain metrics. Candidate locations were drawn from the GSSR station metadata within 9 degrees W to 9 degrees E and 47 to 61 degrees N. This is therefore a sampled Northwest European station network rather than a spatially uniform coastline sample. The inventory contained 74 stations with DeltaDTM support and a resolvable official-mask marine seed. A pre-specified nearest COAST-RP distance of no more than 6 km defined the 68-station primary sample. All retained distances were no greater than 2.81 km; six Loire estuary stations at 6.90-39.42 km were excluded. The threshold is an extraction-quality screen, not a guarantee that a point represents the same along-coast process environment.

A separate GSSR-qualified subset required at least 25 metadata years and a source-metadata reconstruction correlation (`corrn`) of at least 0.55, leaving 44 stations. The local metadata contain no distinct extreme-event skill field, so `corrn` is not interpreted as one. Counts under correlations of 0.45, 0.55 and 0.65 and record lengths of 20, 25 and 30 years are retained as an audit. These filters affect supporting GSSR analyses only and do not define the primary COAST-RP-terrain sample.

Each candidate station was joined by `station_id` to the versioned table `config/coastal_spatial_blocks_v2.csv`. The table assigns a reviewed coastal basin and three nested, approximately coastline-contiguous block schemes with target scales of 100, 150 and 250 km. These labels replace coordinate-threshold sectors that incorrectly grouped geographically distinct coasts. The target scales describe the intended blocking resolution; they are not measurements of exact alongshore distance. The same versioned assignments are used in permutations, block resampling, leave-one-block calculations and figure source data, and an unmapped station causes the workflow to fail.

### COAST-RP storm-tide extraction

COAST-RP provides storm-tide return levels through probabilistic combination of tropical- and extratropical-cyclone surge levels with tidal levels [10,11]. The nearest coastal product point was identified by great-circle distance. Return levels of 2, 5, 10, 25, 50 and 100 years were extracted from the original netCDF variables. The 10-year value was specified as the primary comparison, while all six periods were used to test whether rank concordance depended on return-period choice. Spatial extraction sensitivity was assessed with 1 km and 2 km subsets and an unrestricted 74-station set. Gauge-to-product coordinate connectors were inspected, with estuary, embayment, island and fjord settings flagged in the source table. This is a coordinate and extraction audit: it neither measures alongshore distance nor proves that a product point has the same hydrodynamic setting as a gauge.

### DeltaDTM product version and mask audit

The downloaded elevation tiles identify themselves as DeltaDTM v1.1.1 and DeltaDTM.jl v1.1.1 and reference DOI 10.4121/21997565. The accompanying v1.1 README specifies the compound WGS84/EGM2008 reference and clipping at 30 m EGM2008. This differs from the 10 m plus mean-sea-level extent described for v1.0 in the 2024 paper [6]. The analysis therefore uses the downloaded v1.1.1 product definition rather than transferring the v1.0 cutoff to the newer tiles.

Official mask values were interpreted as land (0), ocean (1), lake (2), river (3) and clipped product support (255). Raster operations used 254 as an internal outside-support fill so that boundless reads and reprojection could never create false class-255 cells. A complete scan of the 72 extracted source mask tiles found no class-255 cells; the primary windows contained 3,320 outside-support cells and no official 255 cells. Only finite class-0 elevation cells entered land denominators. Lakes, clipped cells, outside-support cells and arbitrary no-data boundaries were excluded.

### Static connected-terrain metrics

Terrain was read in station-centred 10 km by 10 km geographic windows. Cell areas were calculated from the latitude-dependent raster geometry and all area totals were weighted by those values. The primary threshold was 2 m in the EGM2008 height reference supplied by DeltaDTM.

Ocean class 1 formed the initial marine seed. A river class-3 component was included only if it connected to ocean. When the 10 km crop did not contain class-1 ocean, the mask context was expanded to 25, 50, 100 and 200 km; the ocean-connected water component was then projected back to the station window. Stations remained missing rather than being assigned zero if no marine component could be established. The primary water graph used eight neighbours to retain diagonally represented narrow water channels, whereas the land graph used four neighbours to prevent corner-only leakage into low terrain. This difference is intentional and explicit. All four combinations of four- and eight-neighbour water and land graphs were recalculated as sensitivity tests.

Four quantities were calculated for threshold eta:

**f_low(eta) = A(z <= eta) / A(reference land)**

**p_conn(eta) = A(connected and z <= eta) / A(z <= eta)**

**f_conn(eta) = A(connected and z <= eta) / A(reference land) = f_low(eta) x p_conn(eta)**

**A_conn(eta) = A(connected and z <= eta)**

Here, reference land comprises finite class-0 DeltaDTM cells within the fixed window. Accordingly, f_low and f_conn are shares of represented product land, not shares of every terrestrial cell in the nominal square. Window area, represented-land area, below-threshold area and connected area were retained separately. We also calculated connected area as a share of the nominal window and partial rank associations controlling for represented-land fraction. The principal manuscript maps show marine seed, connected below-threshold land, unconnected below-threshold land, other represented land and excluded water classes separately.

### Sensitivity analysis

The complete 74-station terrain grid contained 40 recorded configurations per station. One-at-a-time alternatives changed the square window to 5 or 20 km, the threshold to 1 or 3 m, the land graph to eight neighbours, the seed to class-1 ocean present within the local crop, the uniform elevation offset to -1, -0.5, +0.5 or +1 m, and COAST-RP matching to 1 km, 2 km or no distance limit. Uniform offsets are product-scale perturbations; they are not confidence intervals or spatially correlated error realizations. We also integrated each terrain response over thresholds from 0 to 3 m at 0.25 m intervals, recalculated all water/land 4/8-neighbour combinations, and compared the square window with a mask-derived 10 km alongshore by 5 km landward support. The oriented window used the local shoreline-cell principal axis and is a geometry sensitivity analysis, not an alternative flood model. For each eligible configuration, deterministic top-20% membership was recorded and tied values were ordered by station identifier.

### Rank and spatial statistics

Spearman rho and Kendall tau were calculated between raw COAST-RP magnitude and each raw terrain metric. Spatially restricted permutation tests held water-level values fixed and reassigned terrain values only among stations in the same spatial block. For each of 10,000 permutations, the empirical two-sided p value was twice the smaller of the lower- and upper-tail probabilities, capped at one. This definition does not assume that a restricted null distribution is centred on zero. Block-adjusted rank associations were obtained by residualizing each rank vector against indicators for the corresponding blocks. All calculations were repeated at 100, 150 and 250 km target scales.

For a sample of n stations and top-set size k = ceiling(0.2n), the observed overlap was calculated at thresholds from 10% to 40%. Its inferential null used the same 10,000 within-block permutations, preserving the distribution of high terrain values among spatial blocks. The exact hypergeometric distribution was retained only as a nonspatial descriptive comparator. Rank displacement was the absolute difference between deterministic descending water and terrain ranks. Terrain-selection frequency was the proportion of a station's eligible archived configurations in which it entered that configuration's top 20%; it is not a probabilistic hazard estimate.

Geographic generalizability was evaluated with 2,000 block-resampling replicates at each target scale. Blocks, rather than stations, were sampled with replacement and all stations in a selected block were retained. Complementary leave-one-block calculations omitted each block in turn. The reported 2.5th-97.5th percentile ranges are resampling sensitivity ranges, not confidence intervals from independent coastal replicates. They answer a different question from restricted permutation by showing sensitivity to the coastal geography represented in the sample.

Spatial autocorrelation was quantified with Moran's I using row-standardized, symmetric binary great-circle weights at 150 and 250 km. An isolated station was linked bidirectionally to its nearest neighbour before row standardization. Significance used 4,999 randomizations. Basin-specific associations were reported where at least four stations were available, and a leave-one-station jackknife recorded the influence of every location. Partial Spearman correlations controlled for the fraction of the nominal window represented by finite land.

### Rule-based map cases

Figure 3 cases were selected by machine-readable rules before visual inspection of their maps. The stable terrain-priority case was the top-20% connected-share station among the seven local-DTM cases with intersection-over-union of at least 0.75 and the smallest absolute local-minus-DeltaDTM share difference. The water-priority lowland-limited case was selected from storm-tide top-20% stations with conditional connectivity of at least 90% by maximizing terrain-minus-water rank displacement, with water rank breaking ties. The connectivity-filtered case was the station with the lowest conditional connectivity among those at or above the sample median below-2 m land share. The updated four-neighbour workflow selected Delfzijl, Newport and Immingham, respectively.

### National and local terrain cross-check

Environment Agency LiDAR Composite DTM was requested for Sheerness, Newlyn, Lowestoft and Immingham in EPSG:27700. The service's 2 m coverage was requested with a scale factor producing a nominal 10 m output; the interpolation kernel was controlled by the provider service and was not specified by the local code. Dutch Actueel Hoogtebestand Nederland DTM was requested for Den Helder, Delfzijl and Hoek van Holland in EPSG:28992 from the 0.5 m coverage, again at nominal 10 m support. The products use Ordnance Datum Newlyn and Normaal Amsterdams Peil, respectively [16,17].

The DeltaDTM official mask and marine seed were reprojected to each local grid with nearest-neighbour resampling, and both elevation products were classified with four-neighbour land connectivity. Connected-mask intersection-over-union was calculated on the local WCS grid after nearest-neighbour reprojection of the DeltaDTM connected mask. Grid shape, transform, coverage identifier, provider URL, file hash and resampling rule were recorded for every case. No vertical transformation was applied among EGM2008, Ordnance Datum Newlyn and Normaal Amsterdams Peil. The comparison is therefore termed a local-DTM product, datum and resampling cross-check, never validation, and is reported in the Supplementary Information.

### Supporting surge and tidal diagnostics

GSSR daily surge residuals were aggregated to annual maxima. For n annual maxima sorted in ascending order, the m-th value was assigned the non-exceedance plotting position F_m = m/(n+1). A target return period T used F = 1 - 1/T, with linear interpolation in F and no extrapolation beyond the empirical support. Bootstrap intervals describe sampling variability; lower and upper GSSR reconstruction bounds were evaluated separately. The descriptive cross-product difference was calculated as D10 = H10(COAST-RP storm tide) - H10(GSSR surge residual). Because the two quantities differ in physical variable, period, extreme-value method and spatial support, D10 was used only as product-definition context and not as model error, tidal contribution or product validation.

Daily GSSR surge was compared with ERA5-derived sea-level pressure, wind and precipitation for 1980-2010 [18]. Because these predictors also contribute to the reconstruction model, the analysis is described only as a predictor-consistency diagnostic. It does not constitute independent atmospheric validation, extreme-event skill evaluation, terrain evidence or causal attribution.

### Reproducibility and quality control

The frozen primary workflow writes all 2,960 station-configuration rows before producing summaries. Automated contracts require connected area not to exceed below-threshold area, four-neighbour connected area not to exceed eight-neighbour area under otherwise identical settings, and f_conn to equal f_low multiplied by p_conn to numerical precision. The workflow uses fixed random seeds. Input versions, mask counts, station coordinates, windows, grid support, source hashes and figure-source tables are retained in the audit package. `python scripts/reproduce.py --mode derived` verifies and rebuilds from compact checksummed station inputs; `--mode full` verifies the separate upstream manifest before running the raw-data chain. These scopes are reported separately.

## Data availability

COAST-RP, GSSR and DeltaDTM are available from the repositories cited in this article [10-12]. The local terrain products are available from the Environment Agency and PDOK/Rijkswaterstaat services [16,17]. The processed 68-station table, 2,960-row robustness grid, figure-source tables, input hashes and compact reproducibility package are publicly available at https://github.com/Coucou2016/20260522-coastal-flood-scientific-data. Upstream raw products are identified by source URL and SHA-256 digest but are not redistributed from this repository; their original provider terms apply. An archival DOI will be added if one is issued for the accepted release.

## Code availability

The Python workflow for product matching, mask-aware terrain classification, statistical analysis, figure generation and standalone document export, together with fixed environment files, is publicly available at https://github.com/Coucou2016/20260522-coastal-flood-scientific-data. The repository distinguishes a compact, checksummed derived-input rebuild from the complete upstream-data workflow. Release archives provide the reviewer package; the Git repository remains the authoritative, inspectable source.

## Acknowledgements

The authors thank the teams responsible for COAST-RP, GSSR, DeltaDTM, ERA5, Environment Agency LiDAR and Actueel Hoogtebestand Nederland data. Author-specific acknowledgements: 待补充.

## Funding

Funding information: 待补充.

## Author contributions

Author contribution statements: 待补充.

## Competing interests

The authors declare no competing interests.

## Figure captions

### Figure 1 | Study region and analytical sample

**File:** `figures/main/Fig1_process_terrain_design.png`  
**Caption:** **a**, Locations of the 68 primary stations on a real basemap, coloured by display regions derived from the reviewed coastal-basin table. Open outlines denote membership of the storm-tide top 20%, connected-land-share top 20%, or both. Spatial inference uses the separately recorded 100, 150 and 250 km coastline-block identifiers rather than the display colours. **b**, Sample flow from 74 regional candidate locations to the 68-station primary analysis and 44-station GSSR-qualified supporting subset. The station inventory originates from GSSR metadata, but the principal COAST-RP-terrain comparison does not require a GSSR return-level estimate.

### Figure 2 | Limited agreement between storm-tide and terrain priorities

**File:** `figures/main/Fig2_regional_screening_agreement.png`  
**Caption:** **a**, COAST-RP 10-year storm tide versus the connected share of finite class-0 DeltaDTM land below 2 m EGM2008. The primary water and land graphs use eight and four neighbours, respectively; colour denotes display region and the vertical axis is logarithmic. **b**, Raw station-level Spearman estimates and 2.5th-97.5th percentile ranges from resampling coastline-contiguous blocks at 100, 150 and 250 km target scales. **c**, Observed top-set overlap and restricted-permutation median and 95% envelopes at the same scales. The observed curve remains inside the spatial null envelopes. **d**, Frequency with which each station enters the terrain top 20% across its eligible prespecified configurations, plotted against storm-tide rank. Colours identify the primary top-set classification; frequency is a sensitivity measure, not a flood probability.

### Figure 3 | Three mechanisms behind a high or low connected-land share

**File:** `figures/main/Fig3_connected_terrain_contrasts.png`  
**Caption:** **a-c**, Static 10 km DeltaDTM classifications at Delfzijl, Newport and Immingham, selected by the recorded rules in Methods. Coordinates are kilometres east and north of the gauge, and each map includes a 2 km scale bar. Blue denotes represented land below 2 m EGM2008 connected to the marine seed by a four-neighbour graph; orange denotes below-threshold land outside that component. Insets magnify original connected cells at low-share sites without enlarging their area in the main map. **d-f**, Decomposition into below-threshold land share, conditional connectivity and their product, the connected share of represented land. **g-i**, Threshold responses from 0 to 3 m. Solid lines are baseline calculations; dashed and dotted lines are explicit uniform -0.5 m and +0.5 m elevation-offset calculations. The horizontal values are standardized terrain elevations, not event-specific water levels, and the maps are not simulated flood extents.

### Figure 4 | Terrain-metric decomposition and analysis sensitivity

**File:** `figures/main/Fig4_metric_decomposition_robustness.png`  
**Caption:** **a**, Joint distribution of lowland prevalence and conditional connectivity, the two components of connected land share. **b**, Connected share versus the percentage of the nominal 10 km window represented by finite class-0 land. **c**, Primary topology (eight-neighbour water seed and four-neighbour land graph) versus the strict four-neighbour water and land alternative. Orange symbols identify stations whose top-20% membership changes; the dashed line denotes equality. **d**, Spearman estimates under prespecified alternatives in window, elevation threshold, graph topology, marine seed, uniform elevation offset and COAST-RP match distance, together with coastline-oriented and threshold-integrated analyses. `NA` marks a component not defined for that summary rather than a missing calculation.

### Supplementary Figure S1 | Source-verified tidal context

**File:** `figures/main/FigS1_water_level_definition.png`  
**Caption:** All 13 stations with source-verified spring tidal range plotted against **a**, COAST-RP 10-year storm tide and **b**, connected share of represented land. The plotted count and station identities are retained in `FigS1_tidal_source_audit.csv`. This subset is exploratory and is not used to infer the 68-station terrain association.

### Supplementary Figure S2 | Predictor-consistency diagnostic for focal GSSR series

**File:** `figures/main/FigS2_process_coherence.png`  
**Caption:** Daily rank correlations and annual-maximum composites comparing reconstructed GSSR residuals with atmospheric predictors also used by the reconstruction framework. The panel is a predictor-consistency diagnostic, not independent validation, extreme-event skill assessment, terrain evidence or causal attribution.

### Supplementary Figure S3 | Standardized static terrain gallery

**File:** `figures/main/FigS3_connectivity_gallery.png`  
**Caption:** Nine 10 km DeltaDTM v1.1.1 classifications using the same 2 m EGM2008 threshold, official-mask seed and colour key as Fig. 3. The gallery includes stable, lowland-limited and product-sensitive examples. Panels are terrain screens rather than flood maps.

### Supplementary Figure S4 | Local-DTM product, datum and resampling sensitivity

**File:** `figures/main/FigS4_elevation_product_datum_sensitivity.png`  
**Caption:** **a,b**, Connected land share and area from DeltaDTM v1.1.1 and national or local terrain products at the same numerical 2 m threshold using four-neighbour connectivity. **c**, Connected-mask intersection-over-union after nearest-neighbour reprojection to the local grid. **d**, Changes in lowland prevalence and conditional connectivity. EGM2008, Ordnance Datum Newlyn and Normaal Amsterdams Peil were not harmonized, and provider resampling contributes to the comparison. The figure is a combined workflow-sensitivity diagnostic, not product validation.

### Supplementary Figure S5 | COAST-RP nearest-point matching audit

**File:** `figures/main/FigS5_coastrp_match_audit.png`  
**Caption:** **a**, Distribution of nearest-product distances for all 74 candidate stations and the pre-specified 6 km extraction screen. **b**, Gauge-to-product pairs; 68 stations were retained and six Loire estuary stations were excluded. The audit verifies extraction distance but does not establish along-coast process equivalence.

## References

1. Muis, S., Verlaan, M., Winsemius, H. C., Aerts, J. C. J. H. & Ward, P. J. A global reanalysis of storm surges and extreme sea levels. *Nature Communications* **7**, 11969 (2016). https://doi.org/10.1038/ncomms11969
2. Vousdoukas, M. I. et al. Developments in large-scale coastal flood hazard mapping. *Natural Hazards and Earth System Sciences* **16**, 1841-1853 (2016). https://doi.org/10.5194/nhess-16-1841-2016
3. Kirezci, E. et al. Projections of global-scale extreme sea levels and resulting episodic coastal flooding over the 21st century. *Scientific Reports* **10**, 11629 (2020). https://doi.org/10.1038/s41598-020-67736-6
4. Cotrim, C., Toimil, A., Losada, I. J., Novo, S. & Suarez, I. Pan-European assessment of coastal flood hazards. *Natural Hazards and Earth System Sciences* **26**, 1859-1881 (2026). https://doi.org/10.5194/nhess-26-1859-2026
5. Hino, M. et al. Land-based sensors reveal high frequency of coastal flooding. *Communications Earth & Environment* **6**, 404 (2025). https://doi.org/10.1038/s43247-025-02326-w
6. Pronk, M. et al. DeltaDTM: A global coastal digital terrain model. *Scientific Data* **11**, 273 (2024). https://doi.org/10.1038/s41597-024-03091-9
7. Kulp, S. A. & Strauss, B. H. New elevation data triple estimates of global vulnerability to sea-level rise and coastal flooding. *Nature Communications* **10**, 4844 (2019). https://doi.org/10.1038/s41467-019-12808-z
8. Gesch, D. B. et al. Best practices for elevation-based assessments of sea-level rise and coastal flooding exposure. *Frontiers in Earth Science* **6**, 230 (2018). https://doi.org/10.3389/feart.2018.00230
9. Seeger, K. & Minderhoud, P. S. J. Sea level much higher than assumed in most coastal hazard assessments. *Nature* **652**, 667-674 (2026). https://doi.org/10.1038/s41586-026-10196-1
10. Dullaart, J. C. M. et al. Accounting for tropical cyclones more than doubles the global population exposed to low-probability coastal flooding. *Communications Earth & Environment* **2**, 135 (2021). https://doi.org/10.1038/s43247-021-00204-9
11. Dullaart, J. C. M. et al. COAST-RP: A global COastal dAtaset of Storm Tide Return Periods. 4TU.ResearchData (2022). https://doi.org/10.4121/13392314
12. Tadesse, M. G. & Wahl, T. A database of global storm surge reconstructions. *Scientific Data* **8**, 125 (2021). https://doi.org/10.1038/s41597-021-00906-x
13. Haigh, I. D. et al. Spatial and temporal analysis of extreme sea level and storm surge events around the coastline of the UK. *Scientific Data* **3**, 160107 (2016). https://doi.org/10.1038/sdata.2016.107
14. Roberts, D. R. et al. Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* **40**, 913-929 (2017). https://doi.org/10.1111/ecog.02881
15. Seeger, K. & Minderhoud, P. S. J. Addendum: Sea level much higher than assumed in most coastal hazard assessments. *Nature* (2026). https://doi.org/10.1038/s41586-026-11017-1
16. Environment Agency. LiDAR Composite Digital Terrain Model. https://environment.data.gov.uk/dataset/ce8fe7e7-bed0-4889-8825-19b042e128d2
17. Rijkswaterstaat. Actueel Hoogtebestand Nederland data room. https://www.ahn.nl/dataroom
18. Hersbach, H. et al. The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society* **146**, 1999-2049 (2020). https://doi.org/10.1002/qj.3803
