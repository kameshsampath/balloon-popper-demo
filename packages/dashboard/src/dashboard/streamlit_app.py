import os
from datetime import timedelta

import altair as alt
import streamlit as st

from common.log.logger import get_logger
from polaris import catalog

from dashboard.data.loaders import  load_leaderboard_data,load_realtime_scores_data,load_color_analysis_data

logger = get_logger("polaris",os.environ.get("APP_LOG_LEVEL", "INFO"))

# Set page configuration - MUST BE FIRST ST COMMAND
st.set_page_config(
    page_title="Player Analytics", page_icon=":bar_chart:", layout="wide"
)

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


def show_home():
    st.title("Welcome to Player Analytics")

    st.markdown("""
    ## Player Analytics Dashboard

    Welcome to the Player Analytics Dashboard! Use the sidebar to navigate through different sections:

    - **Leaderboard**: View player rankings and scores
    - **Color Analysis**: Analyze balloon color distributions and trends
    - **Performance Trends**: Track player performance and bonus achievements
    """)



def show_color_performance_trends():
    st.title("Balloon Activity Patterns")

    if st.session_state.color_performance_data is not None:
        performance_trends = st.session_state.color_performance_data
        # st.dataframe(performance_trends)

        # Create scatter plot
        scatter = (
            alt.Chart(performance_trends)
            .mark_circle(size=60)
            .encode(
                x=alt.X("total_pops:Q", title="Total Pops"),
                y=alt.Y("avg_score_per_pop:Q", title="Average Score per Pop"),
                color=alt.Color("balloon_color:N", title="Balloon Color"),
                tooltip=[
                    alt.Tooltip("balloon_color:N", title="Color"),
                    alt.Tooltip("total_pops:Q", title="Total Pops"),
                    alt.Tooltip("avg_score_per_pop:Q", title="Avg Score"),
                    alt.Tooltip("window_start:T", title="Time Window Start"),
                ],
            )
            .properties(width=700, height=400, title="Color Performance Scatter Plot")
            .interactive()
        )

        # Create time series line chart
        line = (
            alt.Chart(performance_trends)
            .mark_line()
            .encode(
                x=alt.X("window_start:T", title="Time"),
                y=alt.Y("avg_score_per_pop:Q", title="Average Score"),
                color=alt.Color("balloon_color:N", title="Balloon Color"),
                tooltip=[
                    alt.Tooltip("balloon_color:N", title="Color"),
                    alt.Tooltip("avg_score_per_pop:Q", title="Avg Score"),
                    alt.Tooltip("window_start:T", title="Time"),
                ],
            )
            .properties(width=700, height=300, title="Score Trends Over Time")
            .interactive()
        )

        # Display charts in Streamlit
        st.altair_chart(scatter, use_container_width=True)
        st.altair_chart(line, use_container_width=True)


# Load data once at startup

st.session_state.leaderboard_data = load_leaderboard_data()
st.session_state.balloon_colored_pops = load_color_analysis_data()
st.session_state.realtime_scores_data = load_realtime_scores_data()
st.session_state.color_performance_data = load_color_performance_data()

# Configure the pages with Material icons
pg = st.navigation(
    [
        st.Page(show_home, title="Home", icon=":material/home:", default=True),
        st.Page("pages/show_leaderboard.py", title="Leaderboard", icon=":material/leaderboard:"),
        st.Page("pages/show_color_analysis.py", title="Color Analysis", icon=":material/palette:"),
        st.Page(
            show_color_performance_trends,
            title="Performance Trends",
            icon=":material/trending_up:",
        ),
    ]
)

# Run the selected page
pg.run()
