# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import os

import streamlit as st
from common.log.logger import get_logger

from dashboard.data.loaders import (
    load_color_analysis_data,
    load_color_performance_data,
    load_leaderboard_data,
    load_realtime_scores_data,
)

# # Set page configuration - MUST BE FIRST ST COMMAND
# st.set_page_config(
#     page_title="Player Analytics", page_icon=":bar_chart:", layout="wide"
# )

logger = get_logger("polaris", os.environ.get("APP_LOG_LEVEL", "INFO"))


# Initialize session state to store data and settings
if "color_trend_data" not in st.session_state:
    st.session_state.color_trend_data = None
if "leaderboard_data" not in st.session_state:
    st.session_state.leaderboard_data = None
if "realtime_scores_data" not in st.session_state:
    st.session_state.realtime_scores_data = None
if "balloon_colored_pops" not in st.session_state:
    st.session_state.balloon_colored_pops = None
if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "viridis"


def show_home():
    st.title("Game Analytics Dashboards")

    st.markdown("""
Now that we've set up our data pipeline and loaded our game data, we can create interactive dashboards to visualize and analyze player performance. This chapter covers the analytics dashboards we've built to monitor different aspects of the Balloon Popper game.

## Purpose and Rationale

Analytics dashboards serve as the visual interface to our game data, allowing game designers, developers, and business stakeholders to:

1. **Monitor player performance** in real-time or based on historical data
2. **Identify patterns and trends** in gameplay that might not be apparent in raw data
3. **Make data-driven decisions** about game balance, difficulty, and feature development
4. **Track the success** of game modifications and updates

For our Balloon Popper game, we've created three specialized dashboards, each focusing on a specific aspect of gameplay analysis:

- **Leaderboard Dashboard**: For tracking competitive player performance
- **Color Analysis Dashboard**: For understanding player interaction with game elements
- **Performance Analysis Dashboard**: For analyzing scoring efficiency and patterns
    """)


# Load data once at startup

st.session_state.leaderboard_data = load_leaderboard_data()
st.session_state.balloon_colored_pops = load_color_analysis_data()
st.session_state.realtime_scores_data = load_realtime_scores_data()
st.session_state.color_performance_data = load_color_performance_data()

# Configure the pages with Material icons
pg = st.navigation(
    [
        st.Page(
            show_home,
            title="Home",
            icon=":material/home:",
            default=True,
        ),
        st.Page(
            "pages/leaderboard.py", title="Leaderboard", icon=":material/leaderboard:"
        ),
        st.Page(
            "pages/color_analysis.py", title="Color Analysis", icon=":material/palette:"
        ),
        st.Page(
            "pages/performance_trends.py",
            title="Performance Trends",
            icon=":material/trending_up:",
        ),
    ]
)

# Run the selected page
pg.run()
