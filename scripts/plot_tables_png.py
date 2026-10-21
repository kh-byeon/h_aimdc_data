#!/usr/bin/env python3
"""Alias for ``make_figure_tables.py``.

    PAPER_RUN=q1000 python scripts/plot_tables_png.py
    PAPER_RUN=q3500 python scripts/plot_tables_png.py
"""
from __future__ import annotations

from make_figure_tables import main

if __name__ == "__main__":
    main()
