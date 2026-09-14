#!/usr/bin/env python3
"""Build source-tracked tidal-regime metadata for Fig. 2.

This script replaces the earlier purely indicative tidal metadata table with a
source-tracked table. Where a machine-readable or parseable public authority
source is available locally, values are marked source_verified. Where only a
context source or provisional value is available, values remain flagged as
indicative_context so the manuscript cannot silently overclaim them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
FIG_SOURCE = ROOT / "data" / "figure_source"

NTSLF_URL = "https://ntslf.org/tides/uk-network/predictions-hilo"
NTSLF_AJAX_URL = "https://ntslf.org/files/ntslf_php/hilo_pred.php"
NTSLF_DEFINITIONS_URL = "https://ntslf.org/tides/definitions"
NOAA_DATUM_URLS = {
    "newyork-the-battery": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8518750/datums.json?units=metric",
    "charleston-sc": "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8665530/datums.json?units=metric",
}
NOAA_STATION_IDS = {
    "newyork-the-battery": "8518750",
    "charleston-sc": "8665530",
}


FOCAL = {
    "sheerness-p015-uk": {"label": "Sheerness", "ntslf_name": "Sheerness"},
    "newlyn-p001-uk": {"label": "Newlyn", "ntslf_name": "Newlyn"},
    "aberdeen-p038-uk": {"label": "Aberdeen", "ntslf_name": "Aberdeen"},
    "hoekvanholla-hvh-nl": {
        "label": "Hoek van Holland",
        "fallback_range": 1.7,
        "fallback_regime": "mesotidal",
        "source_status": "indicative_context",
        "source": "Port of Rotterdam/Rijkswaterstaat candidate source identified; exact station spring range not yet extracted automatically",
        "source_url": "https://www.portofrotterdam.com/nl/actuele-informatie/weer-getijde-en-waterdiepte",
        "notes": "Retain as context until HydroMeteoBundel or Rijkswaterstaat station statistics are parsed.",
    },
    "brest-france": {
        "label": "Brest",
        "fallback_range": 6.1,
        "fallback_regime": "macrotidal",
        "source_status": "indicative_context",
        "source": "SHOM/REFMAR tidal-prediction definitions identified; exact station spring range not yet extracted automatically",
        "source_url": "https://refmar.shom.fr/sites/default/files/2025-01/GT-TSH_CatD_Fiche_Prediction_maree.pdf",
        "notes": "Retain as context until SHOM station PMVE/BMVE or harmonic metadata are parsed.",
    },
    "hong-kong-b": {
        "label": "Hong Kong",
        "fallback_range": 1.9,
        "fallback_regime": "mesotidal",
        "source_status": "official_general_context",
        "source": "Hong Kong Observatory notes give mean tidal range context for Hong Kong waters",
        "source_url": "https://www.hko.gov.hk/en/tide/enotes.htm",
        "notes": "HKO notes report mean tidal range of about 1 m in Victoria Harbour and 1.4 m at Tsim Bei Tsui; spring-range value remains contextual.",
    },
    "newyork-the-battery": {"label": "New York-The Battery", "noaa_id": "8518750"},
    "charleston-sc": {"label": "Charleston", "noaa_id": "8665530"},
}


EXTENDED_ALIASES = {
    "fishguard-p055-uk": "Fishguard",
    "holyhead-p054-uk": "Holyhead",
    "immingham-p026-uk": "Immingham",
    "lerwick-p041-uk": "Lerwick",
    "lowestoft-p024-uk": "Lowestoft",
    "milfordhaven-p056-uk": "Milford Haven",
    "millport-p049-uk": "Millport",
    "portpatrick-p063-uk": "Portpatrick",
    "stornoway-p042-uk": "Stornoway",
    "wick-p035-uk": "Wick",
}


def tidal_regime(range_m: float | None) -> str:
    if range_m is None or pd.isna(range_m):
        return "unknown"
    if range_m < 2.0:
        return "mesotidal"
    if range_m < 4.0:
        return "meso-macrotidal"
    return "macrotidal"


def parse_ntslf_hilo() -> dict[str, dict[str, float]]:
    path = FIG_SOURCE / "ntslf_hilo_pred_ajax.html"
    if not path.exists():
        return {}
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    out: dict[str, dict[str, float]] = {}
    for h2 in soup.find_all("h2"):
        station = h2.get_text(" ", strip=True).split(", years")[0].strip()
        hl = h2.find_next_sibling("div", class_="hl")
        if hl is None:
            continue
        vals: dict[str, float] = {}
        for div in hl.find_all("div", recursive=False):
            spans = [s.get_text(" ", strip=True).replace("−", "-") for s in div.find_all("span", recursive=False)]
            if len(spans) < 2:
                continue
            label = spans[0].lower()
            value_text = re.sub(r"[^0-9.+-]", "", spans[1])
            try:
                vals[label] = float(value_text)
            except ValueError:
                continue
        if "mean high water springs" in vals and "mean low water springs" in vals:
            mhws = vals["mean high water springs"]
            mlws = vals["mean low water springs"]
            out[station.lower()] = {
                "mhws_m": mhws,
                "mlws_m": mlws,
                "spring_tidal_range_m": round(mhws - mlws, 2),
            }
    return out


def noaa_mean_range(station_id: str) -> tuple[float | None, str | None, str | None]:
    path = FIG_SOURCE / f"noaa_{station_id}_datums.json"
    if not path.exists():
        return None, None, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    datums = {item["name"]: item["value"] for item in payload.get("datums", [])}
    if "MN" in datums:
        return float(datums["MN"]), payload.get("epoch"), payload.get("accepted")
    if "MHW" in datums and "MLW" in datums:
        return float(datums["MHW"] - datums["MLW"]), payload.get("epoch"), payload.get("accepted")
    return None, payload.get("epoch"), payload.get("accepted")


def focal_rows() -> pd.DataFrame:
    ntslf = parse_ntslf_hilo()
    rows = []
    for station_id, meta in FOCAL.items():
        if "ntslf_name" in meta:
            parsed = ntslf.get(str(meta["ntslf_name"]).lower())
            if parsed:
                rng = parsed["spring_tidal_range_m"]
                rows.append(
                    {
                        "station_id": station_id,
                        "label": meta["label"],
                        "tidal_range_metric": "mean spring range = MHWS - MLWS",
                        "spring_tidal_range_m": rng,
                        "tidal_regime": tidal_regime(rng),
                        "mhws_m": parsed["mhws_m"],
                        "mlws_m": parsed["mlws_m"],
                        "source_status": "source_verified",
                        "source": "National Tidal and Sea Level Facility highest/lowest predicted tides table",
                        "source_url": NTSLF_URL,
                        "definition_url": NTSLF_DEFINITIONS_URL,
                        "notes": "Values parsed from the NTSLF AJAX table; heights are given relative to chart datum.",
                    }
                )
                continue
        if "noaa_id" in meta:
            rng, epoch, accepted = noaa_mean_range(str(meta["noaa_id"]))
            rows.append(
                {
                    "station_id": station_id,
                    "label": meta["label"],
                    "tidal_range_metric": "NOAA MN mean range of tide",
                    "spring_tidal_range_m": rng,
                    "tidal_regime": tidal_regime(rng),
                    "mhws_m": None,
                    "mlws_m": None,
                    "source_status": "source_verified",
                    "source": f"NOAA CO-OPS tidal datums API station {meta['noaa_id']}",
                    "source_url": NOAA_DATUM_URLS[station_id],
                    "definition_url": "https://tidesandcurrents.noaa.gov/datum_options.html",
                    "notes": f"NOAA MN is mean range of tide, not MHWS-MLWS; epoch={epoch}; accepted={accepted}.",
                }
            )
            continue
        rng = float(meta["fallback_range"])
        rows.append(
            {
                "station_id": station_id,
                "label": meta["label"],
                "tidal_range_metric": "spring range context",
                "spring_tidal_range_m": rng,
                "tidal_regime": meta["fallback_regime"],
                "mhws_m": None,
                "mlws_m": None,
                "source_status": meta["source_status"],
                "source": meta["source"],
                "source_url": meta["source_url"],
                "definition_url": "",
                "notes": meta["notes"],
            }
        )
    return pd.DataFrame(rows)


def extended_rows() -> pd.DataFrame:
    ntslf = parse_ntslf_hilo()
    ext_path = FIG_SOURCE / "Fig5_nw_europe_extended_screening.csv"
    if not ext_path.exists():
        return pd.DataFrame()
    ext = pd.read_csv(ext_path)
    focal = focal_rows().set_index("station_id")
    focal_alias = {"brest": "brest-france"}
    rows = []
    for _, station in ext.iterrows():
        sid = station["station_id"]
        focal_sid = focal_alias.get(sid, sid)
        if focal_sid in focal.index:
            row = focal.loc[focal_sid].to_dict()
            row["station_id"] = sid
            row["station"] = station["station"]
            rows.append(row)
            continue
        name = EXTENDED_ALIASES.get(sid)
        parsed = ntslf.get(name.lower()) if name else None
        if parsed:
            rng = parsed["spring_tidal_range_m"]
            rows.append(
                {
                    "station_id": sid,
                    "station": station["station"],
                    "label": station["station"],
                    "tidal_range_metric": "mean spring range = MHWS - MLWS",
                    "spring_tidal_range_m": rng,
                    "tidal_regime": tidal_regime(rng),
                    "mhws_m": parsed["mhws_m"],
                    "mlws_m": parsed["mlws_m"],
                    "source_status": "source_verified",
                    "source": "National Tidal and Sea Level Facility highest/lowest predicted tides table",
                    "source_url": NTSLF_URL,
                    "definition_url": NTSLF_DEFINITIONS_URL,
                    "notes": "Values parsed from the NTSLF AJAX table; heights are given relative to chart datum.",
                }
            )
        else:
            rows.append(
                {
                    "station_id": sid,
                    "station": station["station"],
                    "label": station["station"],
                    "tidal_range_metric": "not available",
                    "spring_tidal_range_m": None,
                    "tidal_regime": "not_source_verified",
                    "mhws_m": None,
                    "mlws_m": None,
                    "source_status": "missing_or_not_yet_extracted",
                    "source": "",
                    "source_url": "",
                    "definition_url": "",
                    "notes": "Non-UK/non-US extended-site tidal metadata not automatically extracted in this run.",
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    FIG_SOURCE.mkdir(parents=True, exist_ok=True)
    focal = focal_rows()
    focal.to_csv(FIG_SOURCE / "Fig2_tidal_regime_metadata.csv", index=False)
    focal.to_csv(FIG_SOURCE / "Fig2_tidal_regime_metadata_source_verified.csv", index=False)
    extended = extended_rows()
    if not extended.empty:
        extended.to_csv(FIG_SOURCE / "TableS_tidal_regime_metadata_source_tracked.csv", index=False)
    print(focal[["station_id", "spring_tidal_range_m", "tidal_regime", "source_status"]].to_string(index=False))
    if not extended.empty:
        print(extended["source_status"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
