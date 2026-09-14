#!/usr/bin/env python3
from make_cee_refined_figures import connected_terrain_df, ensure_dirs, make_fig4, stations_df, style

if __name__ == "__main__":
    style()
    ensure_dirs()
    stations = stations_df()
    make_fig4(stations, connected_terrain_df(stations))
