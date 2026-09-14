#!/usr/bin/env python3
from make_cee_refined_figures import build_tables, connected_terrain_df, corr_df, rp_df, stations_df

if __name__ == "__main__":
    build_tables(rp_df(), corr_df(), connected_terrain_df(stations_df()))
