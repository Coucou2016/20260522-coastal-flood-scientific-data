# Storm-tide magnitude and standardized connected terrain yield non-interchangeable coastal screening priorities in a Northwest European station network

**Manuscript type:** Article  
**Authors:** 待补充  
**Affiliations:** 待补充  
**Corresponding author:** 待补充

## Abstract

Regional coastal screening commonly begins with an extreme water-level ranking, whereas the amount and spatial continuity of low terrain are separate properties. We compared COAST-RP storm-tide return levels with an independently defined DeltaDTM v1.1.1 terrain-susceptibility screen at 68 stations in a sampled Northwest European network. The terrain calculation used fixed 10 km windows, the official water mask, four-neighbour connectivity and a standardized 2 m EGM2008 elevation threshold; it was not an event-specific flood surface. At the 10-year return period, storm-tide magnitude was weakly negatively associated with the connected share of represented land (Spearman rho = -0.33) and connected area (rho = -0.34), but sector-block 95% ranges crossed zero. The association arose mainly from lowland prevalence (rho = -0.31), not conditional connectivity (rho = 0.10). Storm-tide and terrain top-20% lists shared one of 14 stations, an overlap within a coastal-sector-constrained null envelope. Results were similar from 2- to 100-year return periods, although window, threshold and neighbourhood choices altered individual priorities. Storm-tide magnitude therefore did not recover the standardized connected-terrain ranking. The two screens provide non-interchangeable regional information, but neither is treated as observed or dynamically simulated flood hazard.

## Introduction

Extreme coastal water levels provide a practical first filter for large-area hazard assessment. Global and continental products now describe storm surge, storm tide and extreme sea level at thousands of coastal locations [1-3]. Such products make regional comparison possible before the data and computational demands of detailed inundation modelling are incurred. Yet a coastal water level is a boundary condition rather than an observation of flooding on land. Flood extent also depends on terrain, hydraulic pathways, event duration, surface roughness, drainage and defence performance. Recent pan-European dynamic modelling and land-based observations both demonstrate that water-level indicators alone do not determine where, or how often, flooding occurs [4,5].

Topographic screening introduces a different set of assumptions. Coastal digital terrain models have improved the representation of low-lying land, but narrow embankments, channels and engineered drainage remain difficult to resolve at tens-of-metres scale [6,7]. Vertical reference is equally important. Terrain elevation and coastal water level can carry similar numerical values while referring to different physical surfaces, and systematic datum offsets can materially change exposure estimates [8]. A static terrain classification is consequently interpretable only when its product support, marine seed, graph topology and vertical reference are stated explicitly.

The distinction between water-level products adds further context. COAST-RP probabilistically combines surge and tide to estimate storm-tide return levels [9,10], whereas the Global Storm Surge Reconstruction (GSSR) describes the non-tidal surge residual [11]. Their return quantiles cannot be read as equivalent physical quantities, particularly around macrotidal coasts where surge timing relative to astronomical tide affects total sea level [12]. This product distinction explains why a single number cannot stand for every aspect of coastal forcing, but it does not establish whether a water-level ranking represents low-lying terrain.

The unresolved question is therefore one of rank concordance: does a regional storm-tide ranking recover the sites prioritized by an independently defined connected-terrain screen? We address this question at 68 stations drawn from a sampled Northwest European GSSR station network with DeltaDTM support, an auditable marine seed and a nearby COAST-RP point (Fig. 1). The terrain metric is decomposed into lowland prevalence, conditional marine connectivity and absolute connected area. Concordance is then examined across six storm-tide return periods, spatially constrained null models, coastal-sector resampling, station influence tests and a common grid of terrain assumptions. Three rule-selected cases illustrate the distinct mechanisms that can produce similar composite values. Tidal and GSSR analyses are retained in the Supplementary Information as product-context checks rather than as evidence for the principal terrain comparison.

## Results

### The sampled station network is spatially clustered

The regional inventory contained 74 stations between 9 degrees W and 9 degrees E and 47 to 61 degrees N. DeltaDTM v1.1.1 elevation support and an official-mask marine seed were available at all locations. A pre-specified maximum nearest-point distance of 6 km excluded six Loire estuary stations and left 68 stations for the primary comparison (Fig. 1; Supplementary Fig. S5). The largest retained distance was 2.81 km. Sampling was uneven across the six coastal sectors: 21 stations were in the western English Channel, 19 on the British North Sea coast, 12 in the Atlantic-Celtic sector, 10 in the eastern Channel and southern North Sea, four in the Dutch-German Bight and two in Denmark-Norway.

Both sides of the comparison were spatially structured. At a 150 km neighbourhood distance, Moran's I was 0.30 for the 10-year storm tide and 0.55 for connected land share; lowland prevalence was more strongly clustered (I = 0.76), whereas conditional connectivity was not (I = -0.02). These patterns motivated sector-constrained inference and limit extrapolation beyond the sampled station network.

### Storm-tide magnitude and connected-terrain susceptibility were weakly concordant

At the 10-year return period, larger COAST-RP storm tides tended to occur at stations with smaller connected shares of represented DeltaDTM land (Spearman rho = -0.33; Kendall tau = -0.21; Fig. 2a,b). Connected area gave a similar association (rho = -0.34; tau = -0.21). Within-sector permutations placed both estimates in the lower tail of their conditional null distributions (two-sided p < 0.001). This conditional result did not remove geographic uncertainty: resampling whole coastal sectors produced 95% ranges of -0.65 to 0.18 for connected land share and -0.63 to 0.21 for connected area. The association was therefore evident within the observed spatial composition but was not stable to resampling the sectors represented by the network.

The direction and magnitude changed little across the COAST-RP return periods. Spearman rho for connected land share ranged from -0.36 at 2 years to -0.32 at 100 years; connected area ranged from -0.37 to -0.32 (Fig. 2d). Return-period choice was consequently not the main source of disagreement between the two screens.

The top-set comparison was descriptive rather than evidence of an unusually small overlap. The storm-tide and connected-land top 20% lists each contained 14 stations but shared only Sheerness. Under permutations constrained within coastal sector, an overlap of one had a lower-tail probability of 0.257. The observed overlap curve remained inside the corresponding 95% null envelope across top-set sizes of 10-40% (Fig. 2c). Storm-tide magnitude thus had limited ability to recover the same priority set, but the observed overlap was not smaller than expected under this spatial null.

### Lowland prevalence and marine connectivity described different terrain mechanisms

Connected land share is a product of two quantities: the proportion of represented land below the threshold and the proportion of that low land connected to the marine seed. At the 10-year return period, storm-tide magnitude was associated with lowland prevalence (rho = -0.31) but not with conditional connectivity (rho = 0.10; within-sector permutation p = 0.420). The composite connected share therefore inherited most of its regional association from the abundance of low terrain rather than from a coast-wide relation between storm-tide magnitude and raster connectivity.

Three rule-selected cases make this distinction visible (Fig. 3). Delfzijl was the stable terrain-priority case. Its storm tide ranked 26th of 68, while 97.00% of represented land lay below 2 m and 99.69% of that low land belonged to the marine-connected component. The resulting connected share was 96.70% (61.30 km2), the highest in the sample.

Newport represented a water-priority, lowland-limited setting. Its 8.60 m storm tide ranked third, but only 0.164% of represented land lay below 2 m. Although 90.53% of that small lowland footprint was connected, the composite share was 0.148% (0.102 km2), ranking 67th. Immingham showed a different route to a low composite value: 20.14% of represented land was below 2 m, but only 2.01% of that land connected to the marine seed. Its connected share was 0.406% (0.249 km2). Orange areas in Fig. 3c are therefore classified low terrain outside the marine component, not missing blue cells. The explicit -0.5 m and +0.5 m curves further show that some transitions occur rapidly around the standardized 2 m threshold.

### Terrain definition changed individual priorities

The primary land graph used four-neighbour connectivity to avoid diagonal corner leakage. Switching to eight neighbours preserved the overall terrain ranking (rho = 0.96) but changed six top-20% membership assignments and increased connected share by as much as 44.1 percentage points at one station (Fig. 4c). Window and threshold choices also mattered: connected-share correlations with RP10 ranged from -0.42 at a 1 m threshold to -0.30 at 3 m, while 5 km and 20 km windows gave -0.41 and -0.39, respectively (Fig. 4d). Uniform offsets of -1 to +1 m retained a negative composite association but changed four top-set assignments in each scenario. Station jackknife changes in Spearman rho did not exceed 0.04, indicating that no single location generated the pooled result.

The finite class-0 land represented within the nominal 10 km windows ranged from approximately 14% to 79%. This geometry did not explain the water-terrain association: RP10 storm tide was uncorrelated with represented-land fraction (rho = 0.003), and adjusting ranks for that fraction changed the connected-share correlation only from -0.33 to -0.34. Expressing connected area as a share of the full nominal window likewise gave rho = -0.34. Recording window support nevertheless remains essential because the connected share and connected area answer different questions.

Seven national or local DTM cases provided an additional, deliberately non-inferential sensitivity check (Supplementary Fig. S4). With four-neighbour connectivity, DeltaDTM and local products remained similar at Delfzijl (96.70% versus 89.78%; intersection-over-union 0.926) but differed strongly at several other sites, including Sheerness (42.70% versus 9.63%) and Den Helder (71.73% versus 4.36%). The surfaces were not transformed to a common vertical datum, and provider resampling also differed. These contrasts therefore diagnose combined product, datum and resampling sensitivity; they do not validate either product against a common flood surface.

### Water-level product context remained secondary

In the 13-station source-verified tidal subset, spring tidal range was strongly associated with COAST-RP 10-year storm-tide magnitude (rho = 0.96) but not with connected land share (rho = -0.21; Supplementary Fig. S1). GSSR metadata and residual-surge calculations were used only to clarify product definitions. The local metadata field `corrn` is a reconstruction-correlation summary; no separate extreme-event skill field was present. Atmospheric predictor comparisons are therefore labelled predictor-consistency diagnostics in the Supplementary Information and are not used to support terrain ranking or causal claims.

## Discussion

The analysis identifies a difference between two regional screening questions. COAST-RP ranks the magnitude of a coastal water-level forcing, whereas the terrain calculation ranks the prevalence and raster continuity of low land under a standardized geodetic threshold. The weak rank concordance and limited top-set recovery show that one list cannot stand in for the other. This conclusion does not depend on presenting the observed negative correlation as a regional law: sector-block intervals crossed zero, and the top-set overlap was not unusually small under a spatially constrained null. The more defensible inference is that the screens are non-interchangeable within this sampled network.

The metric decomposition is central to that interpretation. A small connected share may indicate little low terrain, as at Newport, or substantial low terrain with little connection to the selected marine component, as at Immingham. These mechanisms lead to different follow-up questions. Lowland prevalence concerns the elevation distribution and the chosen vertical threshold. Conditional connectivity concerns channels, barriers, graph topology and marine-seed definition. Reporting both prevents a composite percentage from being mistaken for a direct measure of hydraulic connection.

The terrain calculation is not a flood map. It imposes no hydrograph, momentum, friction, drainage, river inflow, wave action, defence crest or structure operation. Dynamic pan-European modelling shows that these processes and coastal protection can materially alter flood extent [4]. The present calculation asks a narrower topological question: which represented land cells below a standardized terrain-elevation threshold share a raster component with an explicitly defined marine seed? This inexpensive screen can identify where terrain warrants closer examination, but it cannot replace local hydraulic modelling or observed inundation.

Vertical reference remains the principal barrier to event-level interpretation. DeltaDTM v1.1.1 uses EGM2008 heights, the English local product uses Ordnance Datum Newlyn and the Dutch product uses Normaal Amsterdams Peil. Coastal land and sea-level surfaces are often not aligned in a common vertical reference [8,16]. We therefore did not add COAST-RP storm tides to the terrain threshold or describe connected cells as a storm-tide response. The regional 2 m value is a standardized EGM2008 terrain elevation, not a 2 m local mean-sea-level perturbation. Likewise, the local-DTM comparison remains in the Supplementary Information because native-datum and provider-resampling effects cannot be separated from elevation-product effects.

Spatial sampling places a second limit on generalization. The network is concentrated around the United Kingdom, English Channel and southern North Sea, with only two stations in the Denmark-Norway sector. Strong Moran's I values for lowland metrics confirm that the 68 observations are not spatial replicates. Within-sector permutation, sector adjustment and leave-one-station checks support an association in the observed network, whereas sector-block resampling shows that its magnitude is sensitive to which coastal regions are represented. Future studies should use an independently defined and more evenly spaced coastal inventory, ideally with a coastline-based sampling design.

Several methodological choices affected individual priorities without reversing the broader finding. The composite association persisted from RP2 to RP100 and across window, threshold, vertical-offset, seed and match-distance alternatives. Nevertheless, 4- and 8-neighbour graphs changed six top-set assignments, and some local terrain products produced markedly different classifications. These sensitivities are consequential if a screening list is used to allocate local modelling effort. The station-level source data should therefore accompany any priority map rather than be reduced to a single regional ranking.

The strongest next test is an external benchmark. A common vertical reference would first be needed to compare terrain and coastal mean sea level consistently. Storm-tide magnitude, terrain components and their combination could then be evaluated against dynamic hazard or observed flood outcomes. Such evidence would be required to claim predictive complementarity or improved hazard ranking. The present study establishes non-interchangeability between two transparent screens; it does not designate either as truth.

## Methods

### Study design and sample

The primary analysis paired COAST-RP storm-tide return levels with independently calculated DeltaDTM terrain metrics. Candidate locations were drawn from the GSSR station metadata within 9 degrees W to 9 degrees E and 47 to 61 degrees N. This is therefore a sampled Northwest European station network rather than a spatially uniform coastline sample. The inventory contained 74 stations with DeltaDTM support and a resolvable official-mask marine seed. A pre-specified nearest COAST-RP distance of no more than 6 km defined the 68-station primary sample. All retained distances were no greater than 2.81 km; six Loire estuary stations at 6.90-39.42 km were excluded. The threshold is an extraction-quality screen, not a guarantee that a point represents the same along-coast process environment.

A separate GSSR-qualified subset required at least 25 metadata years and a source-metadata reconstruction correlation (`corrn`) of at least 0.55, leaving 44 stations. The local metadata contain no distinct extreme-event skill field, so `corrn` is not interpreted as one. Counts under correlations of 0.45, 0.55 and 0.65 and record lengths of 20, 25 and 30 years are retained as an audit. These filters affect supporting GSSR analyses only and do not define the primary COAST-RP-terrain sample.

Each primary station was assigned to one of six geographic sectors using a deterministic longitude-latitude rule: Atlantic-Celtic, western English Channel, British North Sea, eastern Channel and southern North Sea, Dutch-German Bight, and Denmark-Norway. The same identifiers were used in the map, block resampling and leave-one-sector calculations.

### COAST-RP storm-tide extraction

COAST-RP provides storm-tide return levels through probabilistic combination of tropical- and extratropical-cyclone surge levels with tidal levels [9,10]. The nearest coastal product point was identified by great-circle distance. Return levels of 2, 5, 10, 25, 50 and 100 years were extracted from the original netCDF variables. The 10-year value was specified as the primary comparison, while all six periods were used to test whether rank concordance depended on return-period choice. Spatial extraction sensitivity was assessed with 1 km and 2 km subsets and an unrestricted 74-station set. These analyses quantify nearest-point matching sensitivity; they do not represent COAST-RP model uncertainty or prove along-coast equivalence.

### DeltaDTM product version and mask audit

The downloaded elevation tiles identify themselves as DeltaDTM v1.1.1 and DeltaDTM.jl v1.1.1 and reference DOI 10.4121/21997565. The accompanying v1.1 README specifies the compound WGS84/EGM2008 reference and clipping at 30 m EGM2008. This differs from the 10 m plus mean-sea-level extent described for v1.0 in the 2024 paper [6]. The analysis therefore uses the downloaded v1.1.1 product definition rather than transferring the v1.0 cutoff to the newer tiles.

Official mask values were interpreted as land (0), ocean (1), lake (2), river (3) and clipped product support (255). Raster operations used 254 as an internal outside-support fill so that boundless reads and reprojection could never create false class-255 cells. A complete scan of the 72 extracted source mask tiles found no class-255 cells; the primary windows contained 3,320 outside-support cells and no official 255 cells. Only finite class-0 elevation cells entered land denominators. Lakes, clipped cells, outside-support cells and arbitrary no-data boundaries were excluded.

### Static connected-terrain metrics

Terrain was read in station-centred 10 km by 10 km geographic windows. Cell areas were calculated from the latitude-dependent raster geometry and all area totals were weighted by those values. The primary threshold was 2 m in the EGM2008 height reference supplied by DeltaDTM.

Ocean class 1 formed the initial marine seed. A river class-3 component was included only if it connected to ocean. When the 10 km crop did not contain class-1 ocean, the mask context was expanded to 25, 50, 100 and 200 km; the ocean-connected water component was then projected back to the station window. Stations remained missing rather than being assigned zero if no marine component could be established. The primary land graph used four-neighbour connectivity so that cells touching only at a corner did not create a pathway. Eight-neighbour connectivity was retained as a sensitivity test.

Four quantities were calculated for threshold eta:

**f_low(eta) = A(z <= eta) / A(reference land)**

**p_conn(eta) = A(connected and z <= eta) / A(z <= eta)**

**f_conn(eta) = A(connected and z <= eta) / A(reference land) = f_low(eta) x p_conn(eta)**

**A_conn(eta) = A(connected and z <= eta)**

Here, reference land comprises finite class-0 DeltaDTM cells within the fixed window. Accordingly, f_low and f_conn are shares of represented product land, not shares of every terrestrial cell in the nominal square. Window area, represented-land area, below-threshold area and connected area were retained separately. We also calculated connected area as a share of the nominal window and partial rank associations controlling for represented-land fraction. The principal manuscript maps show marine seed, connected below-threshold land, unconnected below-threshold land, other represented land and excluded water classes separately.

### Sensitivity analysis

The complete 74-station terrain grid contained 40 recorded configurations per station. One-at-a-time alternatives changed the window to 5 or 20 km, the threshold to 1 or 3 m, the graph to eight neighbours, the seed to class-1 ocean present within the local crop, the uniform elevation offset to -1, -0.5, +0.5 or +1 m, and COAST-RP matching to 1 km, 2 km or no distance limit. Uniform offsets are product-scale perturbations; they are not confidence intervals or spatially correlated error realizations. For each alternative, the workflow recalculated association, terrain-rank correlation with the primary setting, top-20% Jaccard overlap and membership changes. The return-period analysis crossed each of the six COAST-RP return levels with lowland prevalence, conditional connectivity, connected land share and connected area.

### Rank and spatial statistics

Spearman rho and Kendall tau were calculated between raw COAST-RP magnitude and each raw terrain metric. Spatially constrained permutation tests held water-level values fixed and reassigned terrain values only among stations in the same coastal sector. Ten thousand permutations produced two-sided p values and null intervals. A sector-adjusted rank association was also obtained by residualizing both rank vectors against coastal-sector indicators before correlation.

For a sample of n stations and top-set size k = ceiling(0.2n), the observed overlap was calculated at thresholds from 10% to 40%. Its inferential null used the same 10,000 within-sector permutations, preserving the number and distribution of high terrain values across sectors. The exact hypergeometric distribution was retained only as a nonspatial descriptive comparator.

Geographic generalizability was evaluated with 2,000 sector-block bootstrap replicates. Sectors, rather than stations, were sampled with replacement and all stations in a sampled sector were retained. A complementary leave-one-sector calculation omitted each of the same six sectors in turn. These intervals answer a different question from the within-sector permutation: they show sensitivity to the coastal sectors represented by the sample rather than conditional association within the observed composition.

Spatial autocorrelation was quantified with Moran's I using row-standardized binary great-circle weights at 150 and 250 km; stations without a neighbour inside the threshold were linked to their nearest neighbour. Significance used 4,999 randomizations. Sector-specific associations were reported for sectors with at least four stations. A leave-one-station jackknife recorded the influence of every location. Partial Spearman correlations controlled for the fraction of the nominal window represented by finite land.

### Rule-based map cases

Figure 3 cases were selected by machine-readable rules before visual inspection of their maps. The stable terrain-priority case was the top-20% connected-share station among the seven local-DTM cases with intersection-over-union of at least 0.75 and the smallest absolute local-minus-DeltaDTM share difference. The water-priority lowland-limited case was selected from storm-tide top-20% stations with conditional connectivity of at least 90% by maximizing terrain-minus-water rank displacement, with water rank breaking ties. The connectivity-filtered case was the station with the lowest conditional connectivity among those at or above the sample median below-2 m land share. The updated four-neighbour workflow selected Delfzijl, Newport and Immingham, respectively.

### National and local terrain cross-check

Environment Agency LiDAR Composite DTM was requested for Sheerness, Newlyn, Lowestoft and Immingham in EPSG:27700. The service's 2 m coverage was requested with a scale factor producing a nominal 10 m output; the interpolation kernel was controlled by the provider service and was not specified by the local code. Dutch Actueel Hoogtebestand Nederland DTM was requested for Den Helder, Delfzijl and Hoek van Holland in EPSG:28992 from the 0.5 m coverage, again at nominal 10 m support. The products use Ordnance Datum Newlyn and Normaal Amsterdams Peil, respectively [13,14].

The DeltaDTM official mask and marine seed were reprojected to each local grid with nearest-neighbour resampling, and both elevation products were classified with four-neighbour land connectivity. Connected-mask intersection-over-union was calculated on the local WCS grid after nearest-neighbour reprojection of the DeltaDTM connected mask. Grid shape, transform, coverage identifier, provider URL, file hash and resampling rule were recorded for every case. No vertical transformation was applied among EGM2008, Ordnance Datum Newlyn and Normaal Amsterdams Peil. The comparison is therefore termed a local-DTM product, datum and resampling cross-check, never validation, and is reported in the Supplementary Information.

### Supporting surge and tidal diagnostics

GSSR daily surge residuals were aggregated to annual maxima. For n annual maxima sorted in ascending order, the m-th value was assigned the non-exceedance plotting position F_m = m/(n+1). A target return period T used F = 1 - 1/T, with linear interpolation in F and no extrapolation beyond the empirical support. Bootstrap intervals describe sampling variability; lower and upper GSSR reconstruction bounds were evaluated separately. The descriptive cross-product difference was calculated as D10 = H10(COAST-RP storm tide) - H10(GSSR surge residual). Because the two quantities differ in physical variable, period, extreme-value method and spatial support, D10 was used only as product-definition context and not as model error, tidal contribution or product validation.

Daily GSSR surge was compared with ERA5-derived sea-level pressure, wind and precipitation for 1980-2010 [15]. Because these predictors also contribute to the reconstruction model, the analysis is described only as a predictor-consistency diagnostic. It does not constitute independent atmospheric validation, extreme-event skill evaluation, terrain evidence or causal attribution.

### Reproducibility and quality control

The frozen primary workflow writes all 2,960 station-configuration rows before producing summaries. Automated contracts require connected area not to exceed below-threshold area, four-neighbour connected area not to exceed eight-neighbour area under otherwise identical settings, and f_conn to equal f_low multiplied by p_conn to numerical precision. The workflow uses fixed seeds for permutation and block resampling. Input versions, mask counts, station coordinates, windows, grid support, source hashes and figure-source tables are retained in the audit package.

## Data availability

COAST-RP, GSSR and DeltaDTM are available from the repositories cited in this article [9-11]. The local terrain products are available from the Environment Agency and PDOK/Rijkswaterstaat services [13,14]. The processed 68-station table, 2,960-row robustness grid, figure-source tables, input hashes and compact reproducibility package are publicly available at https://github.com/Coucou2016/20260522-coastal-flood-scientific-data. Upstream raw products are identified by source URL and SHA-256 digest but are not redistributed from this repository; their original provider terms apply. An archival DOI will be added if one is issued for the accepted release.

## Code availability

The Python workflow for product matching, mask-aware terrain classification, statistical analysis, figure generation and standalone document export, together with fixed environment files and the one-command rebuild gate, is publicly available at https://github.com/Coucou2016/20260522-coastal-flood-scientific-data. Release archives provide a compact reviewer package; the Git repository remains the authoritative, inspectable source.

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
**Caption:** **a**, Locations of the 68 primary stations on a real basemap, coloured by the six coastal sectors used for spatial resampling. Open outlines denote membership of the storm-tide top 20%, connected-land-share top 20%, or both. **b**, Sample flow from 74 regional candidate locations to the 68-station primary analysis and 44-station GSSR-qualified supporting subset. The regional station inventory originates from GSSR metadata, but the principal COAST-RP-terrain comparison does not require a GSSR return-level estimate.

### Figure 2 | Storm-tide magnitude weakly recovers standardized terrain priorities

**File:** `figures/main/Fig2_regional_screening_agreement.png`  
**Caption:** **a**, COAST-RP 10-year storm tide versus the four-neighbour connected share of finite class-0 DeltaDTM land below 2 m EGM2008. Points have a fixed size and colour denotes coastal sector; the vertical axis is logarithmic. **b**, Raw station-level Spearman estimates and 95% ranges from resampling the six coastal sectors. Two-sided p values use 10,000 permutations within coastal sector. **c**, Observed top-set overlap and the median and 95% envelope from within-sector permutations. The observed curve remains inside the spatial null envelope. **d**, Spearman estimates for COAST-RP return periods from 2 to 100 years. Lowland prevalence and the composite connected share remain weakly negatively associated with storm-tide magnitude, whereas conditional connectivity does not.

### Figure 3 | Three mechanisms behind a high or low connected-land share

**File:** `figures/main/Fig3_connected_terrain_contrasts.png`  
**Caption:** **a-c**, Static 10 km DeltaDTM classifications at Delfzijl, Newport and Immingham, selected by the recorded rules in Methods. Coordinates are kilometres east and north of the gauge, and each map includes a 2 km scale bar. Blue denotes represented land below 2 m EGM2008 connected to the marine seed by a four-neighbour graph; orange denotes below-threshold land outside that component. Insets magnify original connected cells at low-share sites without enlarging their area in the main map. **d-f**, Decomposition into below-threshold land share, conditional connectivity and their product, the connected share of represented land. **g-i**, Threshold responses from 0 to 3 m. Solid lines are baseline calculations; dashed and dotted lines are explicit uniform -0.5 m and +0.5 m elevation-offset calculations. The horizontal values are standardized terrain elevations, not event-specific water levels, and the maps are not simulated flood extents.

### Figure 4 | Terrain-metric decomposition and analysis sensitivity

**File:** `figures/main/Fig4_metric_decomposition_robustness.png`  
**Caption:** **a**, Joint distribution of lowland prevalence and conditional connectivity, the two components of connected land share. **b**, Connected share versus the percentage of the nominal 10 km window represented by finite class-0 land. **c**, Four-neighbour primary values versus the eight-neighbour sensitivity. Orange symbols identify stations whose top-20% membership changes; the dashed line denotes equality. **d**, Spearman estimates under one-at-a-time changes in window, terrain threshold, graph topology, marine seed, uniform elevation offset and COAST-RP match distance. Values are recomputed from the full station grid for each setting.

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
8. Seeger, K. & Minderhoud, P. S. J. Sea level much higher than assumed in most coastal hazard assessments. *Nature* **652**, 667-674 (2026). https://doi.org/10.1038/s41586-026-10196-1
9. Dullaart, J. C. M. et al. Accounting for tropical cyclones more than doubles the global population exposed to low-probability coastal flooding. *Communications Earth & Environment* **2**, 135 (2021). https://doi.org/10.1038/s43247-021-00204-9
10. Dullaart, J. C. M. et al. COAST-RP: A global COastal dAtaset of Storm Tide Return Periods. 4TU.ResearchData (2022). https://doi.org/10.4121/13392314
11. Tadesse, M. G. & Wahl, T. A database of global storm surge reconstructions. *Scientific Data* **8**, 125 (2021). https://doi.org/10.1038/s41597-021-00906-x
12. Haigh, I. D. et al. Spatial and temporal analysis of extreme sea level and storm surge events around the coastline of the UK. *Scientific Data* **3**, 160107 (2016). https://doi.org/10.1038/sdata.2016.107
13. Environment Agency. LiDAR Composite Digital Terrain Model. https://environment.data.gov.uk/dataset/ce8fe7e7-bed0-4889-8825-19b042e128d2
14. Rijkswaterstaat. Actueel Hoogtebestand Nederland data room. https://www.ahn.nl/dataroom
15. Hersbach, H. et al. The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society* **146**, 1999-2049 (2020). https://doi.org/10.1002/qj.3803
16. Seeger, K. & Minderhoud, P. S. J. Addendum: Sea level much higher than assumed in most coastal hazard assessments. *Nature* (2026). https://doi.org/10.1038/s41586-026-11017-1
