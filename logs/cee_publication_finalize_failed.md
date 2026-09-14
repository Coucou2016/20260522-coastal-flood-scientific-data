
## verify raw downloads

Command: `E:\Miniconda3\python.exe scripts/verify_downloads.py --strict`


```text
OK  COAST-RP.zip: 4 entries
OK  COAST-RP.nc: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\coast_rp\extracted\COAST-RP.nc (2,817,029 B)
OK  GSSR sheerness-p015-uk: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\sheerness_p015_uk.7z (409,263 B)
OK  GSSR newlyn-p001-uk: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\newlyn_p001_uk.7z (416,688 B)
OK  GSSR aberdeen-p038-uk: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\aberdeen_p038_uk.7z (418,279 B)
OK  GSSR hoekvanholla-hvh-nl: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\hoekvanholla_hvh_nl.7z (413,709 B)
OK  GSSR brest-france: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\brest_.7z (415,898 B)
OK  GSSR newyork-the-battery: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\newyork_thebattery__usa.7z (417,561 B)
OK  GSSR hong-kong-b: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\hong_kong_b_329b_china.7z (415,437 B)
OK  GSSR charleston-sc: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\gssr\era5\charleston,sc_261a_usa.7z (416,143 B)
OK  DeltaDTM tile index: E:\Projects\20260522-coastal-flood-scientific-data\data\raw\deltadtm\index\deltadtm_tiles.gpkg (2,891,776 B)
OK  sheerness-p015-uk_2014-01-01_2014-01-07_era5.json: 168 hourly steps
OK  sheerness-p015-uk_1980-01-01_2010-12-31_era5.json: 271752 hourly steps
OK  newlyn-p001-uk_1980-01-01_2010-12-31_era5.json: 271752 hourly steps
INFO Open-Meteo files: 9
OK  manifest.json (1,021 B)
---
All required checks passed.
```

Exit code: `0`


## quality audit

Command: `E:\Miniconda3\python.exe scripts/combo1_quality_audit.py`


```text
=== GSSR ===

sheerness-p015-uk: archive exists=True size=409263
  sha256(head): eec0b411958455a7
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.217 max=1.555 mean=0.271 p99=0.846
  annual_max: min=0.837 max=1.555 n_years=41

newlyn-p001-uk: archive exists=True size=416688
  sha256(head): c25a5cfa9820eeb4
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.212 max=0.770 mean=0.087 p99=0.390
  annual_max: min=0.384 max=0.770 n_years=41

aberdeen-p038-uk: archive exists=True size=418279
  sha256(head): 11b1c56ddda8628e
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.332 max=0.940 mean=0.111 p99=0.518
  annual_max: min=0.471 max=0.940 n_years=41

hoekvanholla-hvh-nl: archive exists=True size=413709
  sha256(head): 550f3d22b4554f7e
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.467 max=1.980 mean=0.249 p99=0.947
  annual_max: min=0.881 max=1.980 n_years=41

brest-france: archive exists=True size=415898
  sha256(head): 311bf99ea89a0c9b
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.262 max=0.866 mean=0.099 p99=0.437
  annual_max: min=0.384 max=0.866 n_years=41

newyork-the-battery: archive exists=True size=417561
  sha256(head): 1be861aa5df8dc90
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.713 max=1.560 mean=0.123 p99=0.580
  annual_max: min=0.564 max=1.560 n_years=41

hong-kong-b: archive exists=True size=415437
  sha256(head): 22c6ae44ce781742
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-1.185 max=1.721 mean=0.091 p99=0.362
  annual_max: min=0.361 max=1.721 n_years=41

charleston-sc: archive exists=True size=416143
  sha256(head): c40475f4476d7359
  rows=14973 range=1979-01-03 00:00:00 .. 2019-12-31 00:00:00
  surge_m: min=-0.734 max=1.411 mean=0.101 p99=0.388
  annual_max: min=0.392 max=1.411 n_years=41

=== COAST-RP ===
nc exists=True size=2817029
dims: {'stations': 23226}
vars sample: ['station_id', 'storm_tide_rp_0001', 'storm_tide_rp_0002', 'storm_tide_rp_0005', 'storm_tide_rp_0010', 'storm_tide_rp_0025', 'storm_tide_rp_0050', 'storm_tide_rp_0100']...
  storm_tide_rp_0010: min=0.031 max=9.343 mean=1.550
  storm_tide_rp_0100: min=0.045 max=9.598 mean=1.719
  lon range: -179.99 .. 179.96
  lat range: -84.71 .. 83.65

=== Open-Meteo ===

=== DeltaDTM Sheerness bbox ===
tif count under tiles: 67
  DeltaDTM_v1_1_N51E000.tif size=10258832
  DeltaDTM_v1_1_N50W006.tif size=856518
  DeltaDTM_v1_1_N57W003.tif size=988413
  DeltaDTM_v1_1_N52E004.tif size=15990786
  DeltaDTM_v1_1_N51E004.tif size=32373179
file: DeltaDTM_v1_1_N51E000.tif
  crs=EPSG:4326 res=(0.00041666666666666664, 0.0002777777777777778) shape=(3600, 2400) nodata=-9999.0
  bounds=BoundingBox(left=-0.00020833333333333332, bottom=51.00013888888889, right=0.9997916666666665, top=52.00013888888889)
  window shape=(360, 240) valid_frac=0.452
  elev valid: min=-6.682 max=30.000 mean=3.877 median=2.013
  bathtub +2m flooded_frac (all finite cells)=0.497
  cells below 2m elev: 49.7% of valid
  cells below 0m (EGM2008): 0.7%

=== Station match ===
            station_id  match_dist_km  coast_rp_rp10_m  coast_rp_lon
0    sheerness-p015-uk       0.492787            5.256      0.740000
1       newlyn-p001-uk       0.898627            3.346     -5.530000
2     aberdeen-p038-uk       1.263568            2.822     -2.058000
3  hoekvanholla-hvh-nl       0.431630            3.373      4.124000
4         brest-france       0.832603            4.313     -4.504000
5  newyork-the-battery       0.885056            1.311    -74.018997
6          hong-kong-b       4.761150            1.823    114.154999
7        charleston-sc       1.829531            1.346    -79.936996

=== RP comparison ===
            station_id  gssr_rp10_m  coast_rp_rp10_m  rp10_bias_m  match_dist_km
0    sheerness-p015-uk     1.330623            5.256    -3.925377       0.492787
1       newlyn-p001-uk     0.609171            3.346    -2.736829       0.898627
2     aberdeen-p038-uk     0.836282            2.822    -1.985718       1.263568
3  hoekvanholla-hvh-nl     1.502267            3.373    -1.870733       0.431630
4         brest-france     0.679649            4.313    -3.633351       0.832603
5  newyork-the-battery     1.189720            1.311    -0.121280       0.885056
6          hong-kong-b     1.006259            1.823    -0.816741       4.761150
7        charleston-sc     0.840616            1.346    -0.505383       1.829531
```


```text
E:\Projects\20260522-coastal-flood-scientific-data\scripts\combo1_quality_audit.py:53: FutureWarning: The return type of `Dataset.dims` will be changed to return a set of dimension names in future, in order to be more consistent with `DataArray.dims`. To access a mapping from dimension names to lengths, please use `Dataset.sizes`.
  print(f"dims: {dict(ds.dims)}")
```

Exit code: `0`


## rebuild refined figures

Command: `E:\Miniconda3\python.exe scripts/make_cee_refined_figures.py`


```text
Refined Fig.2-Fig.5 written to E:\Projects\20260522-coastal-flood-scientific-data\figures\main
Connected terrain source data written to E:\Projects\20260522-coastal-flood-scientific-data\data\figure_source
```

Exit code: `0`


## rebuild review HTML

Command: `E:\Miniconda3\python.exe scripts/build_cee_review_html.py`


```text
wrote E:\Projects\20260522-coastal-flood-scientific-data\manuscript\process_terrain_coastal_flood_CEE_manuscript_review.html
```

Exit code: `0`


## compile key scripts

Command: `E:\Miniconda3\python.exe -m py_compile scripts/make_cee_refined_figures.py scripts/build_cee_review_html.py scripts/audit_publication_readiness.py scripts/validate_publication_package.py scripts/finalize_cee_publication_package.py`

Exit code: `0`


## publication readiness audit

Command: `E:\Miniconda3\python.exe scripts/audit_publication_readiness.py`


```text
PUBLICATION READINESS AUDIT: FAIL
- HTML embeds 7 images; expected 5.
- Review HTML still contains submission placeholder: 待补充
- Review HTML should include the no-fabricated-data statement from the manuscript.
- HTML embedded image is stale or mismatched for Fig4_deltadtm_terrain_sensitivity.png.
- HTML embedded image is stale or mismatched for Fig5_process_terrain_typology.png.
- Fig5 should contain five European terrain-screening sites, found 30.
- check_fig5 failed: 'pressure'
- Table 4 source missing columns: ['Non-connected bathtub +2.0 m (%)', 'Ocean-connected +0.5 m (%)', 'Ocean-connected +1.0 m (%)', 'Ocean-connected +2.0 m (%)']
- Manuscript does not state the boundary-only connectivity seed rule.
- Manuscript is missing required caution/wording: physically distinct diagnostics
- Manuscript is missing required caution/wording: upper-range capped terrain values at 30 m
- Manuscript still contains submission placeholder: 待补充
- Manuscript should explicitly state that no data were fabricated.
```

Exit code: `1`


# Failure

publication readiness audit failed with exit code 1
