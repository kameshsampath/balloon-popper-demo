import os
from datetime import timedelta

import streamlit as st

from common.log.logger import get_logger
from dashboard.data.loaders import load_leaderboard_data, load_realtime_scores_data, load_color_analysis_data,load_color_performance_data

# # Set page configuration - MUST BE FIRST ST COMMAND
# st.set_page_config(
#     page_title="Player Analytics", page_icon=":bar_chart:", layout="wide"
# )

logger = get_logger("polaris",os.environ.get("APP_LOG_LEVEL", "INFO"))


# Initialize session state to store data and settings
if "color_trend_data" not in st.session_state:
    st.session_state.color_trend_data = None
if 'leaderboard_data' not in st.session_state:
    st.session_state.leaderboard_data = None
if 'realtime_scores_data' not in st.session_state:
    st.session_state.realtime_scores_data = None
if 'balloon_colored_pops' not in st.session_state:
    st.session_state.balloon_colored_pops = None
if 'color_scheme' not in st.session_state:
    st.session_state.color_scheme = 'viridis'


def show_home():
    st.title("Welcome to Player Analytics")

    st.markdown("""
    ## Player Analytics Dashboard

    Welcome to the Player Analytics Dashboard! Use the sidebar to navigate through different sections:

    - **Leaderboard**: View player rankings and scores
    - **Color Analysis**: Analyze balloon color distributions and trends
    - **Performance Trends**: Track player performance and bonus achievements
    """)


# Load data once at startup

st.session_state.leaderboard_data = load_leaderboard_data()
st.session_state.balloon_colored_pops = load_color_analysis_data()
st.session_state.realtime_scores_data = load_realtime_scores_data()
st.session_state.color_performance_data = load_color_performance_data()

# Configure the pages with Material icons
pg = st.navigation(
    [
        st.Page(show_home, title="Home", icon=":material/home:", default=True, ),
        st.Page("pages/leaderboard.py", title="Leaderboard", icon=":material/leaderboard:"),
        st.Page("pages/color_analysis.py", title="Color Analysis", icon=":material/palette:"),
        st.Page("pages/performance_trends.py", title="Performance Trends", icon=":material/trending_up:", ),
    ]
)

# Run the selected page
pg.run()
