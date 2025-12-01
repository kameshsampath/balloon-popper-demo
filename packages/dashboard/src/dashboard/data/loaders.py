# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import os
from datetime import timedelta

import pandas as pd
import streamlit as st

from common.log.logger import get_logger
from dashboard.polaris import get_catalog

logger = get_logger("data_loaders", os.environ.get("APP_LOG_LEVEL", "INFO"))

catalog = get_catalog()

@st.cache_data(ttl=timedelta(seconds=3))
def load_leaderboard_data():
    """Load Leaderboard data."""
    try:
        # database
        namespace = "balloon_pops"
        # TODO: fix to use leaderboard
        table_leaderboard = "leaderboard"
        # Load leaderboard data
        table = catalog.load_table(f"{namespace}.{table_leaderboard}")
        __leaderboard = table.scan().to_pandas()
        return __leaderboard.sort_values(["total_score", "bonus_hits"], ascending=False)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None


@st.cache_data(ttl=timedelta(seconds=3))
def load_realtime_scores_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_realtime_scores_name = "realtime_scores"
        # Load Realtime scores
        tbl_realtime_scores = catalog.load_table(
            f"{namespace}.{tbl_realtime_scores_name}"
        )
        ## TODO: want to set the max window time to further filter data?
        _realtime_scores_df = tbl_realtime_scores.scan().to_pandas()

        # Convert time windows to datetime and extract hour
        _realtime_scores_df["window_start"] = pd.to_datetime(
            _realtime_scores_df["window_start"]
        )
        _realtime_scores_df["window_end"] = pd.to_datetime(
            _realtime_scores_df["window_end"]
        )

        return _realtime_scores_df
    except Exception as e3:
        st.error(f"Error loading data: {str(e3)}")
        return None


@st.cache_data(ttl=timedelta(seconds=3))
def load_color_analysis_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_balloon_colored_pops_name = "balloon_colored_pops"
        # Load balloon colored pops data
        table_balloon_colored_pops = catalog.load_table(
            f"{namespace}.{tbl_balloon_colored_pops_name}"
        )
        balloon_colored_pops = table_balloon_colored_pops.scan().to_pandas()
        # Convert numeric columns to Python native types
        balloon_colored_pops = balloon_colored_pops.astype(
            {"balloon_pops": int, "points_by_color": int, "bonus_hits": int}
        )

        tbl_balloon_colored_stats_name = "balloon_color_stats"
        # Load balloon colored pops data
        table_balloon_color_stats = catalog.load_table(
            f"{namespace}.{tbl_balloon_colored_stats_name}"
        )
        balloon_color_stats = table_balloon_color_stats.scan().to_pandas()

        return balloon_colored_pops, balloon_color_stats
    except Exception as e2:
        st.error(f"Error loading data: {str(e2)}")
        return None

@st.cache_data(ttl=timedelta(seconds=3))
def load_color_performance_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_color_performance = "color_performance_trends"
        # Load Realtime scores
        tbl_color_performance = catalog.load_table(
            f"{namespace}.{tbl_color_performance}"
        )
        _color_performance_df = tbl_color_performance.scan().to_pandas()
        _color_performance_df = _color_performance_df.astype(
            {
                "avg_score_per_pop": int,
                "total_pops": int,
            }
        )
        return _color_performance_df
    except Exception as e3:
        st.error(f"Error loading data: {str(e3)}")
        return None