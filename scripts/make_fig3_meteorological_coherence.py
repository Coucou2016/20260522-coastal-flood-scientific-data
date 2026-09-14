#!/usr/bin/env python3
from make_cee_refined_figures import corr_df, ensure_dirs, make_fig3, style

if __name__ == "__main__":
    style()
    ensure_dirs()
    make_fig3(corr_df())
