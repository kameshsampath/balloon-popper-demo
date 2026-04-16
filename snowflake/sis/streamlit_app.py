# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Balloon lab dashboard — Streamlit in Snowflake (SiS).

Runs **inside** Snowflake using `get_active_session()` to query **Dynamic Iceberg Table** outputs.
Defaults match `snowflake-lab-sql` generated DT SQL: database **`balloon_silver`**, schema **`silver`**.

Prerequisites: apply `03_dt_pipelines.generated.sql` (or equivalent) and allow DT refresh before expecting rows.

See **`snowflake/sis/README.md`** and **`lab/snowflake-streamlit-sis.md`** for **`snow streamlit deploy`** (via **`snowflake.yml`**) or manual `CREATE STREAMLIT`.
"""

from __future__ import annotations

import streamlit as st
from snowflake.snowpark.context import get_active_session

SILVER_DB = "balloon_silver"
SILVER_SCHEMA = "silver"


def _fqt(table: str) -> str:
    return f"{SILVER_DB}.{SILVER_SCHEMA}.{table}"


def main() -> None:
    st.set_page_config(page_title="Balloon lab — SiS", layout="wide")
    st.title("Balloon pops — silver aggregates")
    st.caption(
        "Dynamic Iceberg Tables (`dt_*`) in the native silver database. "
        "Override `SILVER_DB` / `SILVER_SCHEMA` in this file if you changed generator defaults."
    )

    session = get_active_session()

    tab_lb, tab_color, tab_win = st.tabs(
        ("Leaderboard", "Per-player × color", "15s windows"),
    )

    with tab_lb:
        q = f"""
            SELECT player, total_score, bonus_pops, last_event_ts
            FROM {_fqt("dt_player_leaderboard")}
            ORDER BY total_score DESC NULLS LAST
            LIMIT 25
        """
        df = session.sql(q).to_pandas()
        st.dataframe(df, use_container_width=True, hide_index=True)
        if not df.empty and "player" in df.columns and "total_score" in df.columns:
            head = df.head(15).set_index("player")["total_score"]
            st.bar_chart(head)

    with tab_color:
        q2 = f"""
            SELECT player, balloon_color, balloon_pops, points_by_color, bonus_hits, last_event_ts
            FROM {_fqt("dt_balloon_color_stats")}
            ORDER BY player, points_by_color DESC NULLS LAST
            LIMIT 30
        """
        st.dataframe(session.sql(q2).to_pandas(), use_container_width=True, hide_index=True)

    with tab_win:
        q3 = f"""
            SELECT player, total_score, window_start, window_end
            FROM {_fqt("dt_realtime_scores")}
            ORDER BY window_start DESC, player
            LIMIT 30
        """
        st.dataframe(session.sql(q3).to_pandas(), use_container_width=True, hide_index=True)


main()
