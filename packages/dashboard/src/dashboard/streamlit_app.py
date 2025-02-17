import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from common.log.logger import get_logger
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError

logger = get_logger("balloon_game_dashboard")
logger.setLevel(os.environ.get("APP_LOG_LEVEL", "INFO"))
logger.info("JAI GURU!")

principal_creds = Path(os.getcwd()).joinpath("work", "principal.txt")
with open(principal_creds, "r") as file:
    realm, client_id, client_secret = file.readline().split(",")

logger.info(f"realm: {realm},client_id: {client_id},client_secret: {client_secret}")
# IMPORTANT!!! /api/catalog or get the prefix from your OpenCatalog instance
CATALOG_URI = "http://localhost:18181/api/catalog"
catalog_name = "balloon-game"
database_name = "balloon_pops"

catalog = RestCatalog(
    name=catalog_name,
    **{
        "uri": CATALOG_URI,
        "credential": f"{client_id}:{client_secret}",
        "header.content-type": "application/vnd.api+json",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
        "header.Polaris-Realm": realm,
        "warehouse": catalog_name,
        "scope": "PRINCIPAL_ROLE:ALL",
    },
)

try:
    catalog.create_namespace(database_name)
except NamespaceAlreadyExistsError:
    logger.info(f"Namespace '{database_name}' already exists.Skipping creation.")
except Exception as nse:
    logger.error(f"Error creating database {database_name},{nse} ")

# Set page configuration - MUST BE FIRST ST COMMAND
st.set_page_config(
    page_title="Player Analytics", page_icon=":bar_chart:", layout="wide"
)

# Initialize session state to store data and settings
if "color_trend_data" not in st.session_state:
    st.session_state.color_trend_data = None
if "color_scheme" not in st.session_state:
    st.session_state.color_scheme = "viridis"

# Settings in sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    # Color scheme selection
    color_schemes = [
        "viridis",
        "magma",
        "plasma",
        "inferno",  # Sequential
        "blues",
        "greens",
        "oranges",
        "reds",  # Single color
        "blueorange",
        "brownbluegreen",
        "purplegreen",
        "pinkyellowgreen",  # Diverging
    ]
    st.session_state.color_scheme = st.selectbox(
        "Color Theme",
        options=color_schemes,
        index=color_schemes.index(st.session_state.color_scheme),
    )


@st.cache_data
def load_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_balloon_colored_pops_name = "balloon_colored_pops"
        # Load balloon colored pops data
        table_balloon_colored_pops = catalog.load_table(f"{namespace}.{tbl_balloon_colored_pops_name}")
        balloon_colored_pops = table_balloon_colored_pops.scan().to_pandas()
        # Convert numeric columns to Python native types
        balloon_colored_pops = balloon_colored_pops.astype({
            'balloon_pops': int,
            'points_by_color': int,
            'bonus_hits': int
        })

        tbl_balloon_colored_stats_name = "balloon_color_stats"
        # Load balloon colored pops data
        table_balloon_color_stats = catalog.load_table(f"{namespace}.{tbl_balloon_colored_stats_name}")
        balloon_color_stats = table_balloon_color_stats.scan().to_pandas()

        return balloon_colored_pops,balloon_color_stats
    except Exception as e2:
        st.error(f"Error loading data: {str(e2)}")
        return None


@st.cache_data
def load_leaderboard_data():
    """Load Leaderboard data."""
    try:
        # database
        namespace = "balloon_pops"
        table_leaderboard = "leaderboard"
        # Load leaderboard data
        table = catalog.load_table(f"{namespace}.{table_leaderboard}")
        leaderboard = table.scan().to_pandas()
        return (leaderboard.
                    sort_values(["total_score","bonus_hits"], ascending=False)
                )
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

@st.cache_data
def load_realtime_scores_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_realtime_scores_name = "realtime_scores"
        # Load Realtime scores
        tbl_realtime_scores = catalog.load_table(f"{namespace}.{tbl_realtime_scores_name}")
        ## TODO: want to set the max window time to further filter data?
        _realtime_scores_df = tbl_realtime_scores.scan().to_pandas()
        return _realtime_scores_df
    except Exception as e3:
        st.error(f"Error loading data: {str(e3)}")
        return None

@st.cache_data
def load_color_performance_data():
    """Load and preprocess the color trend data."""
    try:
        # database
        namespace = "balloon_pops"
        tbl_color_performance = "color_performance_trends"
        # Load Realtime scores
        tbl_color_performance = catalog.load_table(f"{namespace}.{tbl_color_performance}")
        _color_performance_df = tbl_color_performance.scan().to_pandas()
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


def show_leaderboard():
    st.title("Leaderboard")

    if st.session_state.leaderboard_data is not None:
        leaderboard = st.session_state.leaderboard_data

        # Calculate total score per player
        total_scores = leaderboard.groupby("player")["total_score"].sum().reset_index()
        total_scores = total_scores.sort_values("total_score", ascending=False)

        # Calculate total bonus hits per player
        bonus_hits = leaderboard.groupby("player")["bonus_hits"].sum().reset_index()
        bonus_hits = bonus_hits.sort_values("bonus_hits", ascending=False)

        # Create two columns for the leaderboards
        col1, col2 = st.columns(2)

        # Display main leaderboard in first column
        with col1:
            st.header("Overall Score")
            st.dataframe(
                total_scores,
                column_config={
                    "player": "Player",
                    "total_score": st.column_config.ProgressColumn(
                        "Total Score",
                        help="Player's total score with visual progress bar",
                        format="%d",
                        min_value=0,
                        max_value=int(total_scores["total_score"].max()),
                    ),
                },
                hide_index=True,
            )

        # Display bonus hits leaderboard in second column
        with col2:
            st.header("Bonus Performance")
            st.dataframe(
                bonus_hits,
                column_config={
                    "player": "Player",
                    "bonus_hits": st.column_config.ProgressColumn(
                        "Bonus Hits",
                        help="Number of bonus hits achieved",
                        format="%d",
                        min_value=0,
                        max_value=int(bonus_hits["bonus_hits"].max()),
                    ),
                },
                hide_index=True,
            )

        if st.session_state.realtime_scores_data is not None:
            realtime_scores = st.session_state.realtime_scores_data
            st.header("Score Trends")


            # Add player selection dropdown using the leaderboard players
            players = leaderboard['player'].unique()
            selected_players = st.multiselect('Select Players', players, default=players)

            # Filter data based on selection
            filtered_df = realtime_scores[realtime_scores['player'].isin(selected_players)]

            # Updated chart with filtered data
            chart = alt.Chart(filtered_df).mark_line(point=True).encode(
                x=alt.X('window_start:T', title='Time'),
                y=alt.Y('total_score:Q', title='Total Score'),
                color=alt.Color('player:N', title='Player'),
                tooltip=['player', 'total_score', 'window_start', 'window_end']
            ).properties(
                title='Real-time Player Scores (15s Windows)'
            )

            st.altair_chart(chart, use_container_width=True)


def show_color_analysis():
    st.title("Color Analysis")

    if st.session_state.color_trend_data is not None:
        color_trend,color_stats = st.session_state.color_trend_data
        # st.dataframe( color_trend)
        # Create color distribution from color_trend data
        color_dist = (
            color_trend.groupby(["player", "balloon_color"])["balloon_pops"]
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
        players = color_trend['player'].unique()
        selected_player = st.selectbox('Select Player', players)

        # Metric selector
        metrics = {
            'Balloon Pops': 'balloon_pops',
            'Points by Color': 'points_by_color',
            'Bonus Hits': 'bonus_hits'
        }
        selected_metric = st.selectbox('Select Metric', list(metrics.keys()))

        # Filter data
        filtered_df = color_trend[color_trend['player'] == selected_player]

        # Create stacked bar chart
        chart = alt.Chart(filtered_df).mark_bar().encode(
            x=alt.X('window_start:T', title='Time'),
            y=alt.Y(f'{metrics[selected_metric]}:Q', title=selected_metric),
            color=alt.Color('balloon_color:N', title='Balloon Color'),
            tooltip=['balloon_color', metrics[selected_metric], 'window_start', 'window_end']
        ).properties(
            title=f'{selected_metric} by Color Over Time - {selected_player}'
        )

        st.altair_chart(chart, use_container_width=True)

        st.header("Color Stats by Player")

        # Player selector
        players = color_stats['player'].unique()
        selected_player = st.selectbox('Select Player', players)

        # Filter data
        filtered_df = color_stats[color_stats['player'] == selected_player]

        # Bar chart
        chart = alt.Chart(filtered_df).mark_bar().encode(
            x=alt.X('balloon_color:N', title='Balloon Color'),
            y=alt.Y('points_by_color:Q', title='Points'),
            color='balloon_color:N',
            tooltip=['balloon_color', 'balloon_pops', 'points_by_color', 'bonus_hits']
        ).properties(
            width=600,
            height=400,
            title=f'Performance by Balloon Color - {selected_player}'
        )

        st.altair_chart(chart, use_container_width=True)


def show_performance_trends():
    st.title("Balloon Activity Patterns")

    if st.session_state.color_performance_data is not None:
        performance_trends = st.session_state.color_performance_data
        st.dataframe(performance_trends)

        # Time series with dual metrics
        base = alt.Chart(performance_trends).encode(
            x=alt.X('window_start:T', title='Time')
        )

        # Line for average score
        lines = base.mark_line().encode(
            y=alt.Y('avg_score_per_pop:Q', title='Avg Score per Pop'),
            color=alt.Color('balloon_color:N', title='Color')
        )

        # Circles for pop volume
        circles = base.mark_circle().encode(
            y=alt.Y('total_pops:Q', title='Total Pops'),
            size='total_pops:Q',
            color=alt.Color('balloon_color:N'),
            opacity=alt.value(0.6)
        )

        # Combine charts
        chart = alt.layer(lines, circles).resolve_scale(
            y='independent'
        ).properties(
            title='Color Performance Trends Over Time'
        )

        st.altair_chart(chart, use_container_width=True)



# Load data once at startup
st.session_state.leaderboard_data = load_leaderboard_data()
st.session_state.color_trend_data = load_data()
st.session_state.realtime_scores_data = load_realtime_scores_data()
st.session_state.color_performance_data = load_color_performance_data()

# Configure the pages with Material icons
pg = st.navigation(
    [
        st.Page(show_home, title="Home", icon=":material/home:", default=True),
        st.Page(show_leaderboard, title="Leaderboard", icon=":material/leaderboard:"),
        st.Page(show_color_analysis, title="Color Analysis", icon=":material/palette:"),
        st.Page(
            show_performance_trends,
            title="Performance Trends",
            icon=":material/trending_up:",
        ),
    ]
)

# Run the selected page
pg.run()
