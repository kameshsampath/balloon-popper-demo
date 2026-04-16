# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Balloon lab dashboard — Streamlit in Snowflake (SiS).

Multipage app (``st.navigation``) aligned with ``packages/dashboard``. Silver DT
identifiers come from **snowflake.yml** ``env`` (see ``silver_config.py``).

Prerequisites: apply ``03_dt_pipelines.generated.sql`` (or equivalent) and allow DT refresh.

See **``snowflake/sis/README.md``** and **``lab/snowflake-streamlit-sis.md``** for deploy.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Balloon lab — SiS", layout="wide", page_icon="🎈")

import data  # noqa: E402 — must follow set_page_config (first Streamlit command)

if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "viridis"

data.ensure_loaded()

pg = st.navigation(
    [
        st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("app_pages/leaderboard.py", title="Leaderboard", icon=":material/leaderboard:"),
        st.Page("app_pages/color_analysis.py", title="Color Analysis", icon=":material/palette:"),
        st.Page(
            "app_pages/performance_trends.py",
            title="Performance Trends",
            icon=":material/trending_up:",
        ),
    ],
    position="top",
)
pg.run()
