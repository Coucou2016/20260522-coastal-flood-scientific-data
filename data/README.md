# Data directory layout (Combo 1)

All paths below are relative to the repository root. **Do not commit large binaries** — keep `data/raw/` in `.gitignore`.

```text
data/
├── README.md                 # this file
├── manifest.json             # optional: checksums after verify_downloads.py
├── raw/
│   ├── gssr/
│   │   ├── era5/             # per-station .7z or extracted CSV
│   │   └── metadata/         # eraint.geojson station index (optional)
│   ├── coast_rp/
│   │   ├── COAST-RP.zip
│   │   └── extracted/        # COAST-RP.nc, COAST-RP_ETC.nc, COAST-RP_TC.nc, README.txt
│   ├── deltadtm/
│   │   ├── index/            # deltadtm_tiles.gpkg, deltadtm_v1_1.vrt, README.md
│   │   ├── zips/             # continent zips if downloaded wholesale
│   │   └── tiles/            # extracted 1°×1° COG .tif for MVP bbox
│   └── open_meteo/
│       ├── hourly/           # JSON per station × date range
│       └── daily/            # aggregated driver features (processed)
└── processed/
    ├── stations.parquet      # harmonized station table
    ├── gssr_daily.parquet
    ├── coast_rp_nearest.parquet
    ├── drivers_daily.parquet
    └── inundation_sensitivity/  # static bathtub outputs (Phase 3)
```

## MVP vs full download tiers

| Tier | What to fetch | Approx. disk |
|------|----------------|--------------|
| **MVP-min** | COAST-RP zip + 8 GSSR `.7z` + Open-Meteo event/climatology windows + `deltadtm_tiles.gpkg` only | **~30–80 MB** |
| **MVP+terrain** | MVP-min + DeltaDTM tiles inside `deltadtm_mvp_bbox` (~20–40 tiles) | **~150–400 MB** |
| **Regional** | `Europe.zip` from 4TU (v1.1) | **~2.4 GB** |
| **Full GSSR ERA5** | Figshare `eraFiveSurgeReconstruction.7z` (882 stations) | **~297 MB** (+ extract) |
| **Full DeltaDTM** | All continent zips (v1.1) | **~36 GB** unzipped |

## Version pins (lock in manuscript Table 1)

| Dataset | DOI / source | Pin date |
|---------|--------------|----------|
| GSSR ERA5 | [10.6084/m9.figshare.12970931](https://doi.org/10.6084/m9.figshare.12970931) | download date |
| COAST-RP v2 | [10.4121/13392314.v2](https://doi.org/10.4121/13392314.v2) | download date |
| DeltaDTM v1.1 | [10.4121/21997565.v4](https://doi.org/10.4121/21997565.v4) | download date |
| Open-Meteo ERA5 | API `models=era5` | query timestamp |
