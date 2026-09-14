#!/usr/bin/env python3
from make_cee_refined_figures import connected_terrain_df, corr_df, ensure_dirs, make_fig5, rp_df, stations_df, style

if __name__ == "__main__":
    style()
    ensure_dirs()
    stations = stations_df()
    make_fig5(rp_df(), corr_df(), connected_terrain_df(stations), stations)
