# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Snowpark loaders for SiS pages (silver Dynamic Iceberg Tables)."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

import silver_config as sc


def _session():
    return get_active_session()


def _lower_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names (Snowpark returns uppercase by default)."""
    df.columns = df.columns.str.lower()
    return df


@st.cache_data(ttl=45)
def _load_leaderboard_raw(silver_db: str, silver_schema: str) -> pd.DataFrame:
    fq = f"{silver_db}.{silver_schema}.dt_player_leaderboard"
    q = f"""
        SELECT player, total_score, bonus_pops, last_event_ts
        FROM {fq}
        ORDER BY total_score DESC NULLS LAST
    """
    return _lower_cols(_session().sql(q).to_pandas())


@st.cache_data(ttl=45)
def _load_realtime_raw(silver_db: str, silver_schema: str) -> pd.DataFrame:
    fq = f"{silver_db}.{silver_schema}.dt_realtime_scores"
    q = f"""
        SELECT player, total_score, window_start, window_end
        FROM {fq}
    """
    df = _lower_cols(_session().sql(q).to_pandas())
    if not df.empty:
        df["window_start"] = pd.to_datetime(df["window_start"])
        df["window_end"] = pd.to_datetime(df["window_end"])
    return df


@st.cache_data(ttl=45)
def _load_color_stats_raw(silver_db: str, silver_schema: str) -> pd.DataFrame:
    fq = f"{silver_db}.{silver_schema}.dt_balloon_color_stats"
    q = f"""
        SELECT player, balloon_color, balloon_pops, points_by_color, bonus_hits, last_event_ts
        FROM {fq}
    """
    df = _lower_cols(_session().sql(q).to_pandas())
    if not df.empty:
        df = df.astype({"balloon_pops": "int64", "points_by_color": "int64", "bonus_hits": "int64"})
    return df


@st.cache_data(ttl=45)
def _load_color_performance_raw(silver_db: str, silver_schema: str) -> pd.DataFrame:
    fq = f"{silver_db}.{silver_schema}.dt_color_performance_trends"
    q = f"""
        SELECT balloon_color, avg_score_per_pop, total_pops, window_start, window_end
        FROM {fq}
    """
    df = _lower_cols(_session().sql(q).to_pandas())
    if not df.empty:
        df["window_start"] = pd.to_datetime(df["window_start"])
        df["avg_score_per_pop"] = pd.to_numeric(df["avg_score_per_pop"], errors="coerce")
        df["total_pops"] = pd.to_numeric(df["total_pops"], errors="coerce").astype("int64")
    return df


def _leaderboard_for_ui(df: pd.DataFrame) -> pd.DataFrame:
    """Match local dashboard column names (leaderboard page)."""
    if df.empty:
        return df
    out = df.rename(columns={"bonus_pops": "bonus_hits", "last_event_ts": "event_ts"})
    return out


def ensure_loaded() -> None:
    """Populate ``st.session_state`` keys used by ``pages/*.py``."""
    sig = sc.silver_ids()
    if st.session_state.get("_sis_data_sig") == sig and st.session_state.get("leaderboard_data") is not None:
        return
    try:
        db, sch = sig
        lb = _load_leaderboard_raw(db, sch)
        st.session_state.leaderboard_data = _leaderboard_for_ui(lb)
        st.session_state.balloon_colored_pops = (_load_color_stats_raw(db, sch), None)
        st.session_state.realtime_scores_data = _load_realtime_raw(db, sch)
        st.session_state.color_performance_data = _load_color_performance_raw(db, sch)
        st.session_state._sis_data_sig = sig
    except Exception as err:  # noqa: BLE001 — show any Snowflake error in-app
        st.session_state.leaderboard_data = None
        st.session_state.balloon_colored_pops = None
        st.session_state.realtime_scores_data = None
        st.session_state.color_performance_data = None
        st.session_state._sis_load_error = str(err)
        st.error(f"Could not load silver DTs: {err}")
