# A reproducible multi-source fusion framework for coastal flood hazard screening using global storm-surge reconstructions, storm-tide return levels, open meteorological drivers, and coastal terrain

**Manuscript type:** Research article / data-integration workflow article  
**Target style:** Scientific Data / Communications Earth & Environment inspired, adapted to a conventional Introduction-Methodology-Results-Discussion-Conclusions structure  
**Draft status:** Complete working draft for internal review. Items marked **[to be completed]** require author, affiliation, exact journal formatting, or additional validation data.

## Abstract

Coastal flooding is driven by interacting oceanographic, meteorological, and topographic controls, yet reproducible global-to-local analysis remains difficult because commonly used datasets differ in spatial support, physical definition, vertical reference, temporal sampling, and computational accessibility. We developed and tested a fully open, reproducible data-fusion workflow that combines four public data streams: the Global Storm Surge Reconstruction (GSSR) daily surge database, COAST-RP storm-tide return-period levels, Open-Meteo ERA5-derived meteorological variables, and DeltaDTM coastal terrain. The framework was implemented for eight tide-gauge sites spanning northwest Europe, the eastern United States, and Hong Kong, with detailed DeltaDTM-based static sea-level-rise inundation screening for five European sites. The workflow downloads, verifies, extracts, spatially matches, merges, and visualizes all datasets using documented Python scripts, producing machine-readable tables, quality-audit reports, and standalone HTML outputs.

The analysis shows that all four data layers can be integrated reproducibly at modest computational cost, but also demonstrates that cross-product comparisons must be interpreted with care. At the eight stations, GSSR empirical 10-year return levels are systematically lower than COAST-RP 10-year storm-tide levels, with a mean difference of -1.95 m. This mismatch is largest at European stations, where GSSR represents reconstructed skew-surge or storm-surge residuals at tide gauges, whereas COAST-RP represents total storm-tide return levels at nearby coastal points. The comparison is therefore most useful as a cross-product consistency and sensitivity check, not as direct validation of absolute elevations. Meteorological-driver analysis over 1980-2010 indicates physically plausible negative Spearman correlations between daily reconstructed surge and mean sea-level pressure at the European sites, reaching -0.83 at Newlyn and -0.80 at Brest. DeltaDTM screening identifies pronounced site-to-site contrasts in lowland exposure: under a static +2.0 m relative sea-level perturbation, the flooded fraction of coastal-lowland cells is approximately 42.8% at Sheerness and 34.7% at Hoek van Holland, compared with less than 10% at Aberdeen, Brest, and Newlyn.

The resulting framework contributes a transparent protocol for combining open coastal-hazard products without rerunning global hydrodynamic models. Its main scientific value lies in disciplined product harmonization, explicit treatment of non-equivalent flood metrics, and rapid generation of reproducible evidence for site prioritization. Its limitations are equally important: the present implementation does not resolve dynamic flood propagation, wave setup, flood defenses, local datum transformations, or compound fluvial-pluvial boundary conditions. We conclude that open multi-source fusion can support first-order coastal flood screening and research planning when product definitions and uncertainties are made explicit.

**Keywords:** coastal flooding; storm surge; storm tide; DeltaDTM; Open-Meteo; ERA5; return period; sea-level rise; reproducible workflow; data fusion.

## 1. Introduction

Coastal flood risk is increasing because extreme water levels occur on top of rising mean sea level, changing storm climatology, land subsidence, and expanding exposure in low-elevation coastal zones. The hazard component alone is multi-dimensional: astronomical tide, meteorological surge, wave setup, seasonal and interannual sea-level variability, rainfall, river discharge, and nearshore morphology can combine to produce damaging inundation. For research, adaptation planning, and emergency screening, this creates a practical challenge. The most physically complete approaches require hydrodynamic modelling, accurate bathymetry and topography, high-resolution forcing, and carefully defined boundary conditions. These requirements are often too demanding for early-stage, multi-site comparative studies. Conversely, single-product screening studies may be easy to run but can hide important differences among products, especially when surge residuals, storm tides, return levels, and terrain elevations are compared as though they were the same physical quantity.

Recent open datasets have substantially improved this situation. The GSSR database provides reconstructed daily maximum storm-surge values at hundreds of tide-gauge locations using data-driven models trained from observed sea-level records and atmospheric reanalysis predictors. Tadesse and Wahl describe GSSR as a public global database of storm-surge reconstructions designed to extend the temporal basis for trend analysis and extreme-value assessment, including ERA5-driven reconstructions for 1979-2019. COAST-RP provides a complementary global coastal dataset of storm-tide return periods, explicitly combining tropical and extratropical cyclone contributions and expressing return levels for recurrence intervals from 1 to 1000 years. DeltaDTM provides a recent public-domain coastal digital terrain model at approximately 30 m resolution, correcting global surface elevation data toward bare-earth terrain using spaceborne lidar and other information. Open-Meteo offers a convenient API route to ERA5-derived historical meteorological variables, including mean sea-level pressure, wind, and precipitation. Together these resources make it feasible to construct a lightweight coastal-flood research workflow using only open data.

However, the existence of open datasets does not by itself solve the harmonization problem. GSSR values are surge-residual-like daily maxima at tide-gauge locations, whereas COAST-RP values are storm-tide return levels at global coastal points. DeltaDTM elevations are terrain heights referenced to a geoid, while flood levels may be referenced to local tidal datums, mean sea level, or product-specific vertical conventions. Open-Meteo meteorological variables are not water levels; they are explanatory or diagnostic drivers. A scientifically defensible workflow must therefore encode not only data access and processing, but also product definitions, matching assumptions, units, and uncertainty flags. Without that discipline, visually plausible figures can convey the wrong conclusion.

This study develops such a workflow for an initial "Combo 1" dataset combination: GSSR + COAST-RP + Open-Meteo ERA5 + DeltaDTM. The objective is not to build a new hydrodynamic model, but to demonstrate a reproducible multi-source fusion framework that can answer three screening-level research questions:

1. How do reconstructed station-scale surge extremes compare with nearby coastal storm-tide return levels when the products are kept physically distinct?
2. Are daily reconstructed surges statistically associated with open meteorological drivers in ways that are physically plausible across sites?
3. How sensitive are nearby coastal lowlands to relative sea-level perturbations when evaluated with a real open coastal terrain model?

The study is designed as a reproducible data-integration article rather than a definitive local flood-risk assessment. That distinction is central. We intentionally avoid presenting static inundation as an operational forecast, and we do not interpret GSSR-COAST-RP differences as direct model error. Instead, the work focuses on a transparent integration protocol, quality auditing, and the generation of interpretable figures and tables that can support subsequent, more specialized modelling.

The study makes four practical contributions. First, it provides a compact, script-driven implementation that downloads and verifies all required data layers for the selected stations. Second, it formalizes a cross-product matching and reporting procedure that exposes distance, product type, return level, and bias metrics. Third, it integrates Open-Meteo ERA5-derived pressure, wind, and precipitation variables to evaluate event-scale meteorological associations without requiring users to operate a full reanalysis archive. Fourth, it replaces the initial synthetic terrain demonstration with real DeltaDTM tiles for five European stations and generates multi-site static inundation figures. These components collectively form a research-ready foundation for a larger coastal-flood paper or supplementary dataset descriptor.

## 2. Data and study sites

### 2.1 Study-site selection

The workflow was implemented for eight tide-gauge sites selected to span contrasting tidal regimes, storm climates, and data-product behavior while keeping the computational burden small. The sites are Sheerness, Newlyn, Aberdeen, Hoek van Holland, Brest, New York-The Battery, Hong Kong, and Charleston. The European sites were prioritized for real DeltaDTM terrain screening because the Europe DeltaDTM package was available locally and could be selectively extracted into station-scale tiles. The United States and Hong Kong sites remain included in the surge-return-level and meteorological-driver analyses, but their terrain expansion would require downloading the North America and Asia DeltaDTM packages, respectively.

The selected sites serve a methodological purpose rather than a claim of regional completeness. Sheerness and Hoek van Holland represent low-lying estuarine or deltaic settings where static sea-level perturbations are expected to interact strongly with terrain. Newlyn, Brest, and Aberdeen provide higher-relief or more spatially constrained coastal settings. New York-The Battery and Charleston provide eastern United States examples where GSSR and COAST-RP 10-year levels are much closer than in the European examples, helping diagnose whether the European mismatch reflects a unit or coding error. Hong Kong provides a tropical/subtropical Asian site with different cyclone and meteorological controls.

### 2.2 GSSR storm-surge reconstructions

The GSSR layer supplies reconstructed daily maximum storm-surge values at tide-gauge locations. The implemented workflow uses the ERA5 branch for the selected eight stations. Each station file was downloaded as a compressed archive, extracted, parsed, and standardized to a common daily table. The source variable name in the downloaded CSV files is retained in the audit trail and renamed internally to `surge_m` for analysis. For the current implementation, the reconstructed daily series span 1979-01-03 to 2019-12-31, yielding approximately 14,973 daily rows per station before temporal overlap with meteorological drivers is applied.

GSSR is treated as a station-scale storm-surge or skew-surge reconstruction, not as total water level. This matters for every subsequent comparison. In tidally energetic European locations, total storm tide can exceed residual surge by several metres because astronomical tide contributes a large portion of the total water level. Consequently, GSSR return levels are expected to be lower than COAST-RP storm-tide return levels where tide is included in the latter product.

### 2.3 COAST-RP storm-tide return levels

COAST-RP provides global coastal storm-tide return levels for multiple recurrence intervals. In the workflow, `COAST-RP.nc` is extracted from the downloaded COAST-RP archive and matched to each tide-gauge station using the nearest coastal point. The current processed table contains return levels for 10-, 50-, and 100-year periods at the nearest COAST-RP point, together with station-to-point distance and a match flag. All eight stations in the present implementation have nearest-neighbour distances below 6 km, and no station is flagged as a long-distance match.

COAST-RP values are interpreted as total storm-tide return levels. The product is not a direct time series and is not expected to have the same physical definition as GSSR residual surge. Its value in this workflow is to provide a widely available coastal return-level benchmark and to test the implications of using return-level surfaces in conjunction with station reconstructions.

### 2.4 Open-Meteo ERA5 meteorological drivers

Open-Meteo was used to retrieve historical ERA5-derived meteorological variables for each station. The current implementation focuses on daily summaries for 1980-2010, including daily minimum mean sea-level pressure, daily maximum wind speed, and daily precipitation totals. These variables are merged with GSSR daily surge values by date. The overlap period yields 11,323 daily records per station. Open-Meteo does not provide storm-surge or water-level data in this workflow; it is used only as a convenient source of atmospheric drivers.

The meteorological analysis is intentionally simple: Spearman rank correlations are computed between daily reconstructed surge and pressure, wind, and precipitation variables. The objective is not causal attribution, but a physically interpretable screening diagnostic. Strong negative surge-pressure correlations at European sites are expected under inverse-barometer and storm-circulation effects, whereas weaker or regionally different correlations can indicate distinct local mechanisms, data limitations, or the need for more detailed modelling.

### 2.5 DeltaDTM coastal terrain

DeltaDTM is used for real terrain-based static inundation screening. The current terrain workflow uses the DeltaDTM tile index to identify station-relevant one-degree tiles, selectively extracts the required GeoTIFFs from the Europe package, and reads station-centred windows for the five European sites. The resulting tiles are:

- Sheerness: `DeltaDTM_v1_1_N51E000.tif`
- Newlyn: `DeltaDTM_v1_1_N50W006.tif`
- Aberdeen: `DeltaDTM_v1_1_N57W003.tif`
- Hoek van Holland: `DeltaDTM_v1_1_N51E004.tif` and `DeltaDTM_v1_1_N52E004.tif`
- Brest: `DeltaDTM_v1_1_N48W005.tif`

The terrain analysis uses real DeltaDTM data, not the earlier synthetic coastal-slope placeholder. The quality audit verifies CRS, nodata, resolution, valid-cell fractions, and elevation statistics for each station window. The current method remains a static bathtub sensitivity calculation and should not be interpreted as dynamic flood propagation.

## 3. Methodology

### 3.1 Reproducible workflow architecture

The workflow is implemented as a sequence of Python scripts with explicit input and output folders. Raw downloads are stored under `data/raw/`, processed tables under `data/processed/`, figures under `figures/`, standalone reports under `reports/`, and human-readable documentation under `docs/`. The principal execution entry point is `scripts/run_combo1_pipeline.py`, which orchestrates station matching, GSSR processing, Open-Meteo driver merging, inundation analysis, figure generation, and HTML report generation. Additional scripts perform data download, verification, DeltaDTM tile extraction, quality auditing, and academic-report building.

The pipeline was designed around three reproducibility principles. First, raw data are not overwritten silently; extracted and processed products retain enough metadata to trace their source. Second, intermediate tables are stored in machine-readable formats such as Parquet, JSON, and GeoJSON. Third, key outputs are summarized in both lightweight JSON and standalone HTML reports so that results can be reviewed without rerunning the entire workflow. This dual machine-human output structure is important for iterative scientific development: the data tables support reanalysis, while the HTML reports support inspection and communication.

### 3.2 Spatial matching between tide gauges and COAST-RP coastal points

Each GSSR tide-gauge location is matched to the nearest COAST-RP coastal point. Early review identified that simple degree-to-kilometre approximations could misrepresent matching distances, especially across latitudes. The final workflow computes distances using a Haversine formula and records the result in kilometres. A match flag is assigned so that future sites beyond a conservative distance threshold can be treated with caution.

The current eight-station set has no long-distance matches. Match distances range from approximately 0.43 km at Hoek van Holland to 4.76 km at Hong Kong. These short distances support the use of the nearest coastal point for screening, but they do not eliminate representation differences. Tide gauges may sit inside estuaries, harbours, or engineered coastlines, whereas COAST-RP points represent modelled coastal locations. We therefore report distances but do not use them to claim absolute equivalence.

### 3.3 Empirical return-level estimation from GSSR

For each station, the daily GSSR reconstruction is converted into an annual-maximum series. Empirical return levels are then estimated using a plotting-position approach. The current implementation reports empirical 10-, 50-, and 100-year levels from the available annual maxima. Because the GSSR ERA5 branch spans roughly 41 years, high-return-period estimates beyond the record length are treated conservatively. In the processed table, the 50- and 100-year empirical levels may equal the maximum annual value for some stations; this reflects limited sample length and non-parametric estimation, not a fitted extrapolation.

This choice is deliberate. Parametric extreme-value modelling could be added later, but the present article prioritizes transparent cross-product screening. A simple empirical estimate avoids introducing additional modelling assumptions while still providing a useful station-scale extreme metric. The limitation is clearly documented: GSSR empirical return levels are not a replacement for a fully fitted local extreme-value analysis.

### 3.4 Cross-product return-level comparison

The return-level comparison calculates differences between GSSR empirical surge return levels and COAST-RP storm-tide return levels at matched sites. The principal metric is:

`bias_RP10 = GSSR_RP10_surge - COAST_RP_RP10_storm_tide`

Equivalent metrics are reported for 50- and 100-year return periods. Negative values indicate that the GSSR residual-surge return level is lower than the COAST-RP storm-tide return level. This is expected where COAST-RP includes astronomical tide and GSSR does not. The comparison is therefore framed as a diagnostic of product definitions and relative magnitudes, not as direct model validation.

The workflow also computes a Pearson correlation between the eight GSSR and COAST-RP 10-year values. The resulting coefficient is low (0.109) and should not be overinterpreted because the two products do not represent the same variable. The manuscript treats this result as evidence that naive cross-product validation is inappropriate unless product definitions are harmonized.

### 3.5 Meteorological-driver analysis

Daily Open-Meteo variables are aggregated and merged with GSSR daily reconstructed surge. For each station, Spearman rank correlations are computed between surge and three drivers: daily minimum mean sea-level pressure, daily maximum wind speed, and daily precipitation total. Spearman correlation is used because the relationships can be non-linear and affected by extremes.

The main expected pattern is a negative relationship between surge and pressure in extratropical storm-dominated regions. Wind correlations are expected to vary with coast orientation, storm track, fetch, and local hydrodynamics. Precipitation correlations are interpreted cautiously because rainfall can indicate storm conditions but does not directly create marine surge; it is more relevant to compound-flood screening when river discharge and drainage are included.

### 3.6 DeltaDTM static inundation screening

For each European station with available DeltaDTM tiles, a station-centred bounding box is extracted. Nodata cells are masked. Terrain statistics are calculated for all valid cells, including minimum, maximum, mean, median, valid-cell fraction, fraction below 0 m, and fraction below 2 m. Static inundation is then evaluated for relative sea-level perturbations of +0.5 m, +1.0 m, and +2.0 m using:

`depth = max(0, SLR - DEM)`

The workflow reports two flooded fractions: one over all valid cells and one over a coastal-lowland mask. The published figures emphasize the lowland metric because the station windows may include cliffs, uplands, and non-coastal terrain that are not the focus of coastal flood sensitivity. The method does not include hydraulic connectivity, flood defenses, wave setup, friction, drainage, or dynamic propagation. Therefore, it is best interpreted as a terrain-based sensitivity screen.

### 3.7 Quality assurance and self-review

A dedicated quality-audit document and scripts were used to address concerns that poor-looking figures might reflect synthetic or erroneous data. The audit confirms that GSSR archives, COAST-RP NetCDF, Open-Meteo JSON, and DeltaDTM GeoTIFFs were all present on disk and actually read by the analysis. It also documents the main causes of initially unsatisfactory outputs: product-definition mismatch, insufficient figure annotation, and static bathtub limitations.

Several corrections were applied during iterative review. Matching distances were converted to Haversine kilometres. DeltaDTM plots were revised to mask nodata, use geographic extents, display terrain context, and annotate station positions. The Sheerness inundation figure was regenerated using real DeltaDTM. Additional real DeltaDTM figures were generated for Newlyn, Aberdeen, Hoek van Holland, and Brest. The HTML reports were converted to self-contained files with embedded figures and tables. These revisions substantially improved interpretability without changing the fundamental limitations of the approach.

## 4. Results

### 4.1 Data inventory and processing completeness

The implemented Combo 1 workflow successfully produced all major data layers required for the analysis. Processed outputs include nearest COAST-RP matches, merged GSSR daily data, daily meteorological drivers, driver-surge correlations, RP comparison tables, inundation GeoJSON files, inundation sensitivity summaries, and complete standalone HTML reports. The central summary file records eight stations in the return-level analysis, five European stations in the real-terrain inundation analysis, and 11 figure files available for reporting.

The raw and processed data volumes remain modest compared with full hydrodynamic modelling workflows. The COAST-RP NetCDF is small enough for rapid local processing. GSSR station files are downloaded individually. Open-Meteo JSON files are larger because they contain hourly or daily driver records, but they remain manageable for the selected stations. DeltaDTM is the largest component because continental packages are several gigabytes; however, once the Europe package was downloaded and verified, only six station-relevant COG tiles were needed for the five European terrain screens.

### 4.2 COAST-RP matching and return-level comparison

All eight tide-gauge sites were matched to nearby COAST-RP coastal points with distances below 6 km. The 10-year return-level comparison reveals two distinct behaviours. At European stations, GSSR 10-year empirical surge levels are much lower than COAST-RP 10-year storm-tide levels. Sheerness has a GSSR RP10 of 1.33 m and a COAST-RP RP10 of 5.26 m, giving a bias of -3.93 m. Brest has a GSSR RP10 of 0.68 m and a COAST-RP RP10 of 4.31 m, giving a bias of -3.63 m. Newlyn, Aberdeen, and Hoek van Holland also show negative differences between -1.87 and -2.74 m.

In contrast, the United States sites have much smaller 10-year differences. New York-The Battery has a GSSR RP10 of 1.19 m and a COAST-RP RP10 of 1.31 m, giving a bias of -0.12 m. Charleston has a GSSR RP10 of 0.84 m and a COAST-RP RP10 of 1.35 m, giving a bias of -0.51 m. Hong Kong is intermediate, with a bias of -0.82 m. The mean RP10 bias across all eight stations is -1.95 m.

This pattern is scientifically instructive. If the workflow had a simple unit conversion error, a systematic coding error, or an incorrect return-period column, all stations would likely be affected in a similar direction and magnitude. Instead, the largest differences occur in tidally energetic European settings where storm tide includes a large astronomical-tide component. The smaller United States differences support the conclusion that the pipeline is reading plausible values, while the European mismatch reflects product-definition differences.

### 4.3 GSSR daily surge behaviour at Sheerness

The Sheerness hydrograph illustrates the nature of the GSSR signal. Daily reconstructed surge values are residual-like, with maxima near 1.55 m and a 99th percentile of approximately 0.85 m. The empirical RP10 is 1.33 m. These values are physically plausible for skew-surge or residual-surge reconstructions but should not be confused with total water levels in a macrotidal estuary.

The revised hydrograph figure includes both GSSR thresholds and a COAST-RP storm-tide RP10 reference line, explicitly noting that the latter is not the same physical variable as the daily GSSR series. This figure is useful pedagogically because it shows why a naive interpretation could be misleading: a COAST-RP storm-tide level around 5.26 m will appear far above the GSSR residual-surge series, but that difference is expected when tide is included in one product and removed from the other.

### 4.4 Meteorological-driver correlations

The Open-Meteo driver analysis identifies physically plausible associations between reconstructed surge and atmospheric variables. At Newlyn, the Spearman correlation between surge and pressure is -0.831, the strongest pressure relationship in the station set. Brest also shows a strong negative pressure correlation (-0.796), followed by Aberdeen (-0.724) and Hoek van Holland (-0.539). These negative correlations are consistent with extratropical storm conditions, inverse-barometer effects, and wind-driven setup.

Wind correlations are positive at all stations, though magnitudes vary. Hoek van Holland has the strongest surge-wind correlation (0.610), followed by Sheerness (0.512), Brest (0.442), and Aberdeen (0.422). These patterns are plausible but should not be interpreted as purely local wind causality because the GSSR reconstruction itself is derived from broader meteorological predictors and the Open-Meteo extraction is station-centred. Precipitation correlations are moderate at Brest (0.585), Newlyn (0.530), and Hoek van Holland (0.486), but weak or near zero at several other sites. These results suggest that precipitation may serve as a storm-context indicator in some locations, but a true compound-flood analysis would require catchment discharge, drainage, and rainfall-runoff modelling.

Charleston shows very weak correlations with all three driver variables in the current workflow. This does not necessarily imply data error. It may reflect the mismatch between a simple station-centred daily driver extraction and the processes that dominate surge at that location, including tropical cyclone track geometry, shelf dynamics, and timing relative to tide. Hong Kong shows positive surge-pressure correlation in the current daily rank analysis, again indicating that the simple driver screen is not sufficient for all regions. These cases are useful reminders that the meteorological step is exploratory, not a substitute for process modelling.

### 4.5 DeltaDTM terrain statistics

Real DeltaDTM terrain windows reveal strong contrasts among the five European sites. Sheerness and Hoek van Holland are the lowest-lying among the analysed windows. Sheerness has a median valid-cell elevation of 2.47 m, a mean elevation of 4.46 m, and 41.0% of valid cells below 2 m. Hoek van Holland has a median elevation of 3.85 m and 34.7% of valid cells below 2 m. Aberdeen, Brest, and Newlyn have much higher median elevations: 22.46 m, 30.0 m, and 30.0 m, respectively. Their fractions below 2 m are correspondingly small, ranging from 0.57% at Newlyn to 2.33% at Aberdeen when measured over all valid cells.

These statistics align with visual expectations. Sheerness lies near low-lying estuarine terrain in the Thames and Medway region. Hoek van Holland is part of the Dutch coastal-delta context, where low-lying terrain and engineered flood protection dominate flood-risk interpretation. Newlyn and Brest are coastal but embedded in more rugged or higher terrain windows. Aberdeen includes harbour lowlands but also higher surrounding topography.

### 4.6 Static sea-level-rise inundation sensitivity

The static DeltaDTM inundation results amplify the terrain contrasts. Under +0.5 m relative sea-level perturbation, the flooded fraction of coastal-lowland cells is 2.13% at Sheerness and 5.15% at Hoek van Holland. Under +1.0 m, the corresponding values rise to 10.18% and 15.67%. Under +2.0 m, Sheerness reaches 42.78% and Hoek van Holland reaches 34.72%. These high sensitivities are consistent with their low terrain distributions.

The remaining three sites show lower flooded fractions under +2.0 m: 8.26% at Newlyn, 7.63% at Brest, and 7.24% at Aberdeen when measured over the coastal-lowland mask. Their all-valid-cell flooded fractions are even lower because the station windows include extensive higher ground. The distinction between all-valid and coastal-lowland denominators is important. A large upland fraction can mask the vulnerability of the actual nearshore lowland zone if only all-valid-cell percentages are reported.

The inundation maps should be read as sensitivity visualizations, not flood forecasts. They show where terrain is lower than the imposed water-level perturbation, after nodata masking, but they do not test whether water can hydraulically reach each cell. They also ignore levees, sea walls, drainage structures, wave setup, river flow, and local vertical-datum transformations. In highly protected areas such as the Netherlands, this omission is especially important. Nevertheless, the maps are valuable for first-order comparison because they use consistent open terrain data and identical perturbation levels across sites.

### 4.7 Integrated interpretation across products

The combined results support a clear interpretation. GSSR provides useful temporal information about reconstructed residual-surge variability at tide gauges. COAST-RP provides spatially extensive storm-tide return levels that include tide and rare-cyclone contributions. Open-Meteo provides accessible atmospheric context. DeltaDTM provides terrain exposure context. None of these layers alone gives a complete flood-risk answer, but together they support a structured screening workflow.

The most important scientific result is not the numerical bias itself, but the demonstration that cross-product differences can be diagnostic when product definitions are explicit. The European RP differences initially appeared to be poor results. After quality review, they became evidence of a common pitfall in coastal-flood data fusion: residual surge and storm tide are often placed on the same axis without sufficient explanation. By turning that mismatch into an explicit methodological finding, the workflow becomes more robust and more useful for other researchers.

## 5. Figures and tables

### Figure set

**Figure 1. Combo 1 workflow and data-fusion concept.**  
Recommended source: create from `report.html` or add a schematic figure before journal submission. The figure should show GSSR, COAST-RP, Open-Meteo ERA5, and DeltaDTM flowing into station matching, temporal merging, return-level comparison, driver correlation, terrain sensitivity, and quality audit. **[to be completed as final vector figure]**

**Figure 2. RP10 comparison across eight stations.**  
Source file: `figures/combo1_rp10_comparison.png`. The figure compares GSSR empirical surge RP10 and COAST-RP storm-tide RP10. The caption must emphasize that the two variables are not equivalent.

**Figure 3. Regionalized RP10 comparison.**  
Source file: `figures/combo1_rp10_dual_region.png`. This figure separates the European sites from the non-European examples and clarifies why the European biases are larger.

**Figure 4. GSSR-COAST-RP validation diagnostic.**  
Source file: `figures/combo1_gssr_coastrp_validation.png`. This diagnostic should be described as cross-product consistency screening, not direct validation.

**Figure 5. Sheerness reconstructed surge hydrograph.**  
Source file: `figures/combo1_hydrograph_sheerness.png`. This figure demonstrates the residual-surge nature of GSSR and the difference from storm-tide thresholds.

**Figure 6. Multi-station GSSR return-level behaviour.**  
Source file: `figures/combo1_rp_multi_station.png`. This figure summarizes empirical return-level estimates from station reconstructions.

**Figure 7. Meteorological-driver correlation heatmap.**  
Source file: `figures/combo1_driver_correlation_heatmap.png`. This figure shows Spearman correlations between reconstructed surge and pressure, wind, and precipitation.

**Figure 8. Sheerness DeltaDTM static SLR inundation sensitivity.**  
Source file: `figures/inundation_sensitivity_sheerness-p015-uk.png`. This figure uses real DeltaDTM and shows strong lowland sensitivity under +2 m.

**Figure 9. Hoek van Holland DeltaDTM static SLR inundation sensitivity.**  
Source file: `figures/inundation_sensitivity_hoekvanholla-hvh-nl.png`. This figure shows low-lying Dutch coastal terrain and multi-tile DeltaDTM mosaicking.

**Figure 10. Aberdeen, Newlyn, and Brest DeltaDTM static SLR sensitivity.**  
Source files: `figures/inundation_sensitivity_aberdeen-p038-uk.png`, `figures/inundation_sensitivity_newlyn-p001-uk.png`, and `figures/inundation_sensitivity_brest-france.png`. These can be combined into a multi-panel figure in final layout.

**Figure 11. Multi-site inundation sensitivity summary.**  
Recommended source: generated from `data/processed/inundation_sensitivity_all.json`. **[to be completed if the newly added plotting script is run successfully]**

### Table 1. Data products and roles in the workflow

| Product | Main variable used | Spatial support | Time or return-period support | Role in this study | Key limitation |
| --- | --- | --- | --- | --- | --- |
| GSSR ERA5 | Daily reconstructed surge (`surge_m`) | Tide-gauge station | 1979-2019 daily | Station-scale surge time series and empirical return levels | Residual/skew surge, not total water level |
| COAST-RP | Storm-tide return levels | Global coastal points | RP 1-1000 years | Coastal return-level benchmark | Storm tide includes tide; not directly equivalent to GSSR |
| Open-Meteo ERA5 | Pressure, wind, precipitation | Station-centred API extraction | 1980-2010 daily summaries | Meteorological driver screening | No water-level variables |
| DeltaDTM | Coastal terrain elevation | Approx. 30 m coastal raster | Static terrain | Relative SLR inundation sensitivity | No hydrodynamics or defenses |

### Table 2. GSSR and COAST-RP 10-year return-level comparison

| Station | GSSR RP10 (m) | COAST-RP RP10 (m) | Bias GSSR-COAST (m) | Match distance (km) |
| --- | ---: | ---: | ---: | ---: |
| Sheerness | 1.33 | 5.26 | -3.93 | 0.49 |
| Newlyn | 0.61 | 3.35 | -2.74 | 0.90 |
| Aberdeen | 0.84 | 2.82 | -1.99 | 1.26 |
| Hoek van Holland | 1.50 | 3.37 | -1.87 | 0.43 |
| Brest | 0.68 | 4.31 | -3.63 | 0.83 |
| New York-The Battery | 1.19 | 1.31 | -0.12 | 0.89 |
| Hong Kong | 1.01 | 1.82 | -0.82 | 4.76 |
| Charleston | 0.84 | 1.35 | -0.51 | 1.83 |

### Table 3. Meteorological-driver correlations with GSSR daily surge

| Station | Days | Surge vs pressure | Surge vs wind | Surge vs precipitation |
| --- | ---: | ---: | ---: | ---: |
| Aberdeen | 11,323 | -0.724 | 0.422 | 0.252 |
| Brest | 11,323 | -0.796 | 0.442 | 0.585 |
| Charleston | 11,323 | 0.041 | 0.054 | 0.068 |
| Hoek van Holland | 11,323 | -0.539 | 0.610 | 0.486 |
| Hong Kong | 11,323 | 0.159 | 0.331 | -0.079 |
| Newlyn | 11,323 | -0.831 | 0.364 | 0.530 |
| New York-The Battery | 11,323 | -0.261 | 0.175 | 0.355 |
| Sheerness | 11,323 | -0.228 | 0.512 | 0.159 |

### Table 4. DeltaDTM static SLR sensitivity at European sites

| Station | DEM source | Median elevation (m) | Flooded lowland +0.5 m | Flooded lowland +1.0 m | Flooded lowland +2.0 m |
| --- | --- | ---: | ---: | ---: | ---: |
| Sheerness | DeltaDTM N51E000 | 2.47 | 2.13% | 10.18% | 42.78% |
| Hoek van Holland | DeltaDTM mosaic(2) | 3.85 | 5.15% | 15.67% | 34.72% |
| Newlyn | DeltaDTM N50W006 | 30.00 | 2.52% | 4.19% | 8.26% |
| Brest | DeltaDTM N48W005 | 30.00 | 3.67% | 5.22% | 7.63% |
| Aberdeen | DeltaDTM N57W003 | 22.46 | 2.39% | 3.77% | 7.24% |

## 6. Discussion

### 6.1 Scientific interpretation of the GSSR-COAST-RP mismatch

The central interpretive issue in this study is the mismatch between GSSR surge return levels and COAST-RP storm-tide return levels. At first glance, the European differences of 2-4 m appear to be a serious problem. After product-definition review, they are better understood as a demonstration of why coastal flood datasets cannot be merged mechanically.

Storm surge, skew surge, storm tide, and extreme sea level are related but distinct quantities. A surge residual is the non-tidal component of sea level after removing predicted tide or a related baseline. Skew surge is often defined as the difference between the observed high water and predicted high tide within a tidal cycle. Storm tide is the total water level produced by tide plus surge. In macrotidal environments, the tide component can dominate total elevation. Therefore, a station-scale residual-surge reconstruction should not be expected to match a storm-tide return level at the same numerical magnitude.

This distinction is not merely semantic. It changes scientific conclusions. If the European bias were interpreted as model error, one might incorrectly reject either GSSR or COAST-RP. If interpreted correctly, it reveals that the workflow is comparing complementary layers: GSSR helps characterize temporal surge variability, while COAST-RP helps characterize total coastal return levels. The integration is useful precisely because it exposes this difference.

### 6.2 Value of open meteorological-driver screening

The Open-Meteo component adds explanatory context at minimal cost. The pressure correlations at Newlyn, Brest, Aberdeen, and Hoek van Holland are strong and physically plausible. These results support the use of station-centred meteorological drivers as a rapid diagnostic for extratropical surge regimes. The weaker or unexpected correlations at Charleston and Hong Kong show the limits of the approach. Tropical-cyclone surge depends strongly on track, size, translation speed, angle of approach, shelf geometry, and tide timing. A simple daily station-centred pressure or wind series cannot capture all of these controls.

The most appropriate interpretation is therefore tiered. For extratropical European sites, the driver screen provides a useful confirmation that the GSSR reconstruction is meteorologically coherent. For cyclone-influenced or complex coastal sites, it identifies the need for richer event-based predictors. Future work could add IBTrACS storm tracks, spatial pressure gradients, wind-direction components, offshore wave variables, and river discharge.

### 6.3 Terrain sensitivity and the role of DeltaDTM

The transition from synthetic DEM to real DeltaDTM substantially improved the credibility of the inundation figures. DeltaDTM provides a globally consistent, public-domain coastal DTM designed for flood-impact modelling. In this workflow, it makes the difference between a process demonstration and a meaningful terrain screen.

The five European sites show that static SLR sensitivity is controlled strongly by local hypsometry. Sheerness and Hoek van Holland respond sharply to +2 m perturbations because large fractions of their valid lowland cells lie below 2 m. Newlyn, Brest, and Aberdeen show much lower sensitivity within the selected windows because most valid cells are higher. These differences are visible in both the maps and the summary statistics.

However, the static method is intentionally limited. It does not include hydraulic connectivity; therefore, isolated low cells below the threshold could be counted as flooded even if disconnected from the sea. It ignores flood defenses; therefore, protected lowlands in the Netherlands and elsewhere may be overestimated. It ignores wave setup and river flows; therefore, some exposed coastal or estuarine areas may be underestimated. The method is best suited for relative comparison and identifying sites where more detailed modelling is warranted.

### 6.4 Reproducibility, reporting, and auditability

A notable outcome of the project is the reporting infrastructure. The workflow produces processed tables, figures, logs, quality-audit documents, and standalone HTML reports. This matters because coastal flood data integration is prone to silent errors: wrong units, wrong variable definitions, unmasked nodata, coordinate mismatch, vertical-datum confusion, and accidental use of placeholder data. The project encountered several such risks during iteration and addressed them through explicit audit checks.

The audit trail is especially important for trust. The quality report documents that all four data layers are real files on disk and that the final Sheerness and multi-site inundation figures use real DeltaDTM COGs. The report also explains why the RP comparison looks poor if misread. This transparency makes the workflow more scientifically defensible than a polished figure set without provenance.

### 6.5 Innovation and contribution

The novelty of this study is not a new hydrodynamic equation or a new global dataset. Rather, it is a reproducible integration protocol that makes existing open datasets work together while preserving their definitions. The contribution is practical and methodological:

1. It shows how to create a lightweight coastal-flood screening pipeline from open data without rerunning global hydrodynamic models.
2. It demonstrates a concrete QA process for detecting product-definition mismatch and placeholder terrain use.
3. It produces multi-site figures that combine extreme-water-level context, meteorological drivers, and terrain sensitivity.
4. It frames cross-product disagreement as scientific information rather than simply an error.

This type of contribution is suitable for a data-integration or methods-oriented paper, particularly if expanded with additional stations, observed water-level validation, and more formal uncertainty treatment.

## 7. Limitations and future work

Several limitations should be addressed before journal submission or operational use. First, the current GSSR return-level estimates are empirical and limited by the ERA5-period record length. Parametric extreme-value analysis could be added, but it should include uncertainty intervals and sensitivity to threshold or block-maxima choices.

Second, vertical datums are not fully harmonized. DeltaDTM uses an EGM2008-related vertical reference, while water-level products may relate to MSL, tidal datums, or model-specific references. The present SLR analysis is therefore relative rather than absolute. Future work should implement site-specific datum transformations where possible.

Third, static bathtub inundation does not account for connectivity, protection, roughness, or hydrodynamic attenuation. A defensible impact assessment would require connectivity filtering, defense data, or dynamic modelling. The current maps should remain labelled as sensitivity screens.

Fourth, the station set is small. Eight stations are sufficient for method demonstration but not for regional generalization. A stronger paper would expand to dozens or hundreds of stations, stratified by tidal range, cyclone exposure, geomorphic setting, and data availability.

Fifth, compound flooding is only partially represented. Precipitation is included as a meteorological indicator, but river discharge, pluvial drainage, and catchment hydrology are not included. Future work could combine ERA5 rainfall, reanalysis runoff, GRDC or local gauge discharge, and coastal water levels to better assess compound events.

Sixth, terrain analysis currently covers only European sites because the Europe DeltaDTM package was downloaded. Extending the analysis to New York, Charleston, and Hong Kong would require additional DeltaDTM continental packages. This is technically straightforward but data-intensive.

## 8. Conclusions

This study developed and implemented a reproducible multi-source fusion framework for coastal flood hazard screening using GSSR, COAST-RP, Open-Meteo ERA5, and DeltaDTM. The workflow successfully produced station-scale surge reconstructions, nearest-neighbour storm-tide return levels, meteorological-driver correlations, real-terrain inundation sensitivity maps, quality-audit documentation, and standalone reports.

The results demonstrate both the promise and the risk of open coastal-flood data fusion. The promise is that a small number of public datasets can quickly generate meaningful evidence across multiple sites. The risk is that variables with different physical definitions can be mistakenly compared as though they were equivalent. In the present analysis, the large European differences between GSSR RP10 and COAST-RP RP10 are expected because GSSR represents residual surge while COAST-RP represents storm tide. This finding is not a failure of the workflow; it is one of its most important lessons.

Meteorological-driver correlations provide a useful first-order diagnostic, especially at European extratropical sites where surge and pressure are strongly negatively correlated. DeltaDTM static inundation screening highlights strong lowland sensitivity at Sheerness and Hoek van Holland and much lower sensitivity at Newlyn, Brest, and Aberdeen within the selected windows. These terrain results are based on real DeltaDTM tiles but remain static sensitivity estimates rather than dynamic forecasts.

Overall, the Combo 1 framework is suitable as a reproducible research scaffold for coastal flood screening, figure generation, and manuscript development. With expanded station coverage, formal extreme-value uncertainty, datum harmonization, and dynamic or connectivity-aware inundation modelling, it could be developed into a more comprehensive open coastal flood hazard assessment.

## Data availability

All input datasets used in this workflow are public. GSSR is available through the repositories described by Tadesse and Wahl (2021). COAST-RP is available through 4TU.ResearchData. Open-Meteo historical weather data are accessed through the Open-Meteo API. DeltaDTM is available through the public DeltaDTM data release and associated tile index. Processed files generated in this project are stored locally under `data/processed/`. Large raw files are intentionally ignored by version control.

## Code availability

The local workflow scripts are stored under `scripts/`. The main entry point is `scripts/run_combo1_pipeline.py`. Supporting scripts include downloaders, verifiers, station matching, GSSR-COAST merging, Open-Meteo driver fetching, DeltaDTM tile extraction, static inundation analysis, figure generation, quality audit, and report generation. The script `scripts/build_academic_report.py` builds the standalone Chinese academic HTML report, and `scripts/generate_html_reports.py` builds the modular standalone HTML reports.

## Acknowledgements

**[to be completed]** The author(s) thank the developers and maintainers of GSSR, COAST-RP, Open-Meteo, DeltaDTM, ERA5, and the open-source Python geospatial ecosystem.

## Author contributions

**[to be completed]** Conceptualization: [name]. Data curation: [name]. Methodology: [name]. Software: [name]. Visualization: [name]. Writing-original draft: [name]. Writing-review and editing: [name].

## Competing interests

The author(s) declare no competing interests. **[to be confirmed]**

## References

1. Tadesse, M. G. & Wahl, T. A database of global storm surge reconstructions. *Scientific Data* 8, 125 (2021). DOI: 10.1038/s41597-021-00906-x.
2. Dullaart, J. C. M. et al. Accounting for tropical cyclones more than doubles the global population exposed to low-probability coastal flooding. *Communications Earth & Environment* 2, 135 (2021). DOI: 10.1038/s43247-021-00204-9.
3. Dullaart, J. C. M. et al. COAST-RP: A global COastal dAtaset of Storm Tide Return Periods. 4TU.ResearchData (2021). DOI: 10.4121/13392314.
4. Pronk, M. et al. DeltaDTM: A global coastal digital terrain model. *Scientific Data* 11, 273 (2024). DOI: 10.1038/s41597-024-03091-9.
5. Hersbach, H. et al. The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society* 146, 1999-2049 (2020). DOI: 10.1002/qj.3803.
6. Muis, S., Verlaan, M., Winsemius, H. C., Aerts, J. C. J. H. & Ward, P. J. A global reanalysis of storm surges and extreme sea levels. *Scientific Data* 3, 160040 (2016). DOI: 10.1038/sdata.2016.40.
7. Mentaschi, L. et al. Global long-term observations of coastal erosion and accretion. *Scientific Reports* 8, 12876 (2018). DOI: 10.1038/s41598-018-30904-w.
8. Mentaschi, L. et al. Global-scale data set of extreme sea levels and waves for coastal flood hazard assessment. *Frontiers in Marine Science* 7, 263 (2020). DOI: 10.3389/fmars.2020.00263.
9. Vousdoukas, M. I. et al. Global probabilistic projections of extreme sea levels show intensification of coastal flood hazard. *Nature Communications* 9, 2360 (2018). DOI: 10.1038/s41467-018-04692-w.
10. Kirezci, E. et al. Projections of global-scale extreme sea levels and resulting episodic coastal flooding over the 21st century. *Scientific Reports* 10, 11629 (2020). DOI: 10.1038/s41598-020-67736-6.
11. Kulp, S. A. & Strauss, B. H. New elevation data triple estimates of global vulnerability to sea-level rise and coastal flooding. *Nature Communications* 10, 4844 (2019). DOI: 10.1038/s41467-019-12808-z.
12. Yamazaki, D. et al. A high-accuracy map of global terrain elevations. *Geophysical Research Letters* 44, 5844-5853 (2017). DOI: 10.1002/2017GL072874.
13. Bloemendaal, N. et al. Generation of a global synthetic tropical cyclone hazard dataset using STORM. *Scientific Data* 7, 40 (2020). DOI: 10.1038/s41597-020-0381-2.
14. Vousdoukas, M. I. et al. Developments in large-scale coastal flood hazard mapping. *Natural Hazards and Earth System Sciences* 16, 1841-1853 (2016). DOI: 10.5194/nhess-16-1841-2016.
15. Le Cozannet, G. et al. Quantifying uncertainties of sandy shoreline change projections as sea level rises. *Scientific Reports* 9, 42 (2019). DOI: 10.1038/s41598-018-37017-4.
16. Oppenheimer, M. et al. Sea level rise and implications for low-lying islands, coasts and communities. In *IPCC Special Report on the Ocean and Cryosphere in a Changing Climate* (2019). DOI: 10.1017/9781009157964.006.
17. Frederikse, T. et al. The causes of sea-level rise since 1900. *Nature* 584, 393-397 (2020). DOI: 10.1038/s41586-020-2591-3.
18. Nicholls, R. J. et al. A global analysis of subsidence, relative sea-level change and coastal flood exposure. *Nature Climate Change* 11, 338-342 (2021). DOI: 10.1038/s41558-021-00993-z.
19. Wahl, T. et al. Understanding extreme sea levels for broad-scale coastal impact and adaptation analysis. *Nature Communications* 8, 16075 (2017). DOI: 10.1038/ncomms16075.
20. Open-Meteo. Historical Weather API documentation. https://open-meteo.com/en/docs/historical-weather-api. Accessed 2026-05-26. DOI: **[no DOI; documentation source]**.

