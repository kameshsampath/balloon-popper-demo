import os
from datetime import timedelta

import altair as alt
import streamlit as st

from common.log.logger import get_logger
from polaris import catalog

logger = get_logger("polaris",os.environ.get("APP_LOG_LEVEL", "INFO"))

# Set page configuration - MUST BE FIRST ST COMMAND
st.set_page_config(
    page_title="Player Analytics", page_icon=":bar_chart:", layout="wide"
)

# Initialize session state to store data and settings
if "color_trend_data" not in st.session_state:
    st.session_state.color_trend_data = None
if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "viridis"


@st.cache_data(ttl=timedelta(seconds=3))
def load_data():
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


def show_home():
    st.title("Welcome to Player Analytics")

    st.markdown("""
    ## Player Analytics Dashboard

    Welcome to the Player Analytics Dashboard! Use the sidebar to navigate through different sections:

    - **Leaderboard**: View player rankings and scores
    - **Color Analysis**: Analyze balloon color distributions and trends
    - **Performance Trends**: Track player performance and bonus achievements
    """)




def show_color_analysis():
    st.title("Color Analysis")

    if st.session_state.balloon_colored_pops is not None:
        colored_pops, color_stats = st.session_state.balloon_colored_pops
        with st.expander("Color Analysis Raw"):
            col1, col2 = st.columns(2)
            col1.dataframe(colored_pops)
            col2.dataframe(color_stats)

        # Create color distribution from color_stats
        color_dist = (
            color_stats.groupby(["player", "balloon_color"])["balloon_pops"]
            .sum()
            .reset_index()
        )
        color_dist = color_dist.rename(columns={"balloon_pops": "hits"})

        # Color Distribution Section
        st.header("Balloon Color Distribution")

        # Calculate high-level metrics
        total_pops = color_dist["hits"].sum()
        most_common_color = color_dist.groupby("balloon_color")["hits"].sum().idxmax()
        least_common_color = color_dist.groupby("balloon_color")["hits"].sum().idxmin()
        unique_colors = len(color_dist["balloon_color"].unique())

        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Balloon Pops", f"{total_pops:,}")
        with col2:
            st.metric("Most Popular Color", most_common_color)
        with col3:
            st.metric("Least Popular Color", least_common_color)
        with col4:
            st.metric("Unique Colors", unique_colors)

        # Simple heatmap with adjusted height
        heatmap = (
            alt.Chart(color_dist)
            .mark_rect()
            .encode(
                x="balloon_color:N",
                y="player:N",
                color=alt.Color(
                    "hits:Q", scale=alt.Scale(scheme=st.session_state.color_scheme)
                ),
                tooltip=["player", "balloon_color", "hits"],
            )
            .properties(title="Balloon Color Distribution by Player", height=500)
        )

        # Display the chart
        st.altair_chart(heatmap, use_container_width=True)

        st.header("Color Analysis by Player and Metric")
        # Player selector
        players = colored_pops["player"].unique()
        selected_player = st.selectbox("Select Player", players)

        # Metric selector
        metrics = {
            "Balloon Pops": "balloon_pops",
            "Points by Color": "points_by_color",
            "Bonus Hits": "bonus_hits",
        }
        selected_metric = st.selectbox("Select Metric", list(metrics.keys()))

        # Filter data
        filtered_df = colored_pops[colored_pops["player"] == selected_player]

        # Create stacked bar chart
        chart = (
            alt.Chart(filtered_df)
            .mark_bar()
            .encode(
                x=alt.X("window_start:T", title="Time"),
                y=alt.Y(f"{metrics[selected_metric]}:Q", title=selected_metric),
                color=alt.Color("balloon_color:N", title="Balloon Color"),
                tooltip=[
                    "balloon_color",
                    metrics[selected_metric],
                    "window_start",
                    "window_end",
                ],
            )
            .properties(
                title=f"{selected_metric} by Color Over Time - {selected_player}"
            )
        )

        st.altair_chart(chart, use_container_width=True)

        st.header("Color Stats by Player")

        # Player selector
        players = color_stats["player"].unique()
        selected_player = st.selectbox("Select Player", players)

        # Filter data
        filtered_df = color_stats[color_stats["player"] == selected_player]

        # Bar chart
        chart = (
            alt.Chart(filtered_df)
            .mark_bar()
            .encode(
                x=alt.X("balloon_color:N", title="Balloon Color"),
                y=alt.Y("points_by_color:Q", title="Points"),
                color="balloon_color:N",
                tooltip=[
                    "balloon_color",
                    "balloon_pops",
                    "points_by_color",
                    "bonus_hits",
                ],
            )
            .properties(
                width=600,
                height=400,
                title=f"Performance by Balloon Color - {selected_player}",
            )
        )

        st.altair_chart(chart, use_container_width=True)


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
st.session_state.balloon_colored_pops = load_data()

st.session_state.color_performance_data = load_color_performance_data()

# Configure the pages with Material icons
pg = st.navigation(
    [
        st.Page(show_home, title="Home", icon=":material/home:", default=True),
        st.Page("pages/show_leaderboard.py", title="Leaderboard", icon=":material/leaderboard:"),
        st.Page(show_color_analysis, title="Color Analysis", icon=":material/palette:"),
        st.Page(
            show_color_performance_trends,
            title="Performance Trends",
            icon=":material/trending_up:",
        ),
    ]
)

# Run the selected page
pg.run()
