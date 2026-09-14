#!/usr/bin/env python3
from make_cee_refined_figures import ensure_dirs, make_fig2, rp_df, style

if __name__ == "__main__":
    style()
    ensure_dirs()
    make_fig2(rp_df())
