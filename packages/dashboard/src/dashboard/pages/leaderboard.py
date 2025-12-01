# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

### Leaderboard Visualizations
import os

import altair as alt
import pandas as pd
import streamlit as st
from common.log.logger import get_logger
from pandas import Timestamp

logger = get_logger("polaris", os.environ.get("APP_LOG_LEVEL", "INFO"))


def create_score_chart(data, f_selected_players, f_time_unit: str = "minutes"):
    filtered_df = data[data["player"].isin(f_selected_players)]

    logger.info(f"Input data shape:{data.shape}")
    logger.info(f"Selected players:{f_selected_players}")
    logger.info(f"Data types: {filtered_df.dtypes}")

    if filtered_df.empty:
        raise ValueError("No data available for the selected players and time range")

    # Ensure window_start is datetime
    filtered_df["window_start"] = pd.to_datetime(filtered_df["window_start"])

    # Aggregate scores by sum instead of mean
    aggregated_df = (
        filtered_df.groupby(["window_start", "player"])["total_score"]
        .max()
        .reset_index()
    )

    # Configure time format based on selected time unit
    if f_time_unit == "hours":
        time_format = "%H:%M"
    else:  # minutes
        time_format = "%H:%M:%S"

    base = alt.Chart(aggregated_df).encode(
        x=alt.X(
            "window_start:T",
            title="Time",
            axis=alt.Axis(format=time_format, labelAngle=-45, grid=True),
        ),
        y=alt.Y("total_score:Q", title="Total Score"),
        color=alt.Color("player:N", title="Player"),
    )

    # Create lines
    lines = base.mark_line()

    # Create points
    points = base.mark_circle(size=100).encode(
        tooltip=[
            alt.Tooltip("player:N", title="Player"),
            alt.Tooltip("total_score:Q", title="Total Score", format=".0f"),
            alt.Tooltip("window_start:T", title="Time", format=time_format),
        ]
    )

    # Combine lines and points
    __chart = (
        (lines + points)
        .properties(width=700, height=400, title="Player Total Score Trends Over Time")
        .interactive()
    )

    return __chart


def filter_data_by_time(
    df: pd.DataFrame, f_start_time: Timestamp, f_end_time: Timestamp
):
    # Convert input datetime objects to pandas datetime with timezone info
    start_pd = pd.to_datetime(f_start_time).tz_localize("UTC")
    end_pd = pd.to_datetime(f_end_time).tz_localize("UTC")

    # Create mask using pandas datetime objects
    mask = (df["window_start"] >= start_pd) & (df["window_start"] <= end_pd)
    return df[mask]


st.title("Leaderboard")

if st.session_state.leaderboard_data is not None:
    leaderboard = st.session_state.leaderboard_data
    latest_records = leaderboard.sort_values(
        "event_ts", ascending=False
    ).drop_duplicates("player")
    combined_stats = (
        latest_records.groupby("player")
        .agg({"total_score": "sum", "bonus_hits": "sum"})
        .reset_index()
        .sort_values("total_score", ascending=False)
    )

    st.header("Scoreboard")
    st.dataframe(
        combined_stats.head(5),
        column_config={
            "player": "Player",
            "total_score": st.column_config.ProgressColumn(
                "Total Score",
                help="Player's total score with visual progress bar",
                format="%d",
                min_value=0,
                max_value=int(combined_stats["total_score"].max()),
            ),
            "bonus_hits": st.column_config.NumberColumn(
                "Bonus Hits",
                help="Player's bonus hits",
                format="%d",
            ),
        },
        hide_index=True,
    )

    if st.session_state.realtime_scores_data is not None:
        st.header("Leaderboard Score Analysis")
        realtime_scores_df = st.session_state.realtime_scores_data

        # get only top 5 players
        leaders = combined_stats["player"].unique()[:5]

        # Settings in sidebar
        with st.sidebar:
            st.header("⚙️ Settings")
            # Player filter
            selected_players = st.sidebar.multiselect(
                "Select Players",
                options=leaders,
                default=leaders,
            )

            # Time unit selector
            min_time = realtime_scores_df["window_start"].min()
            max_time = realtime_scores_df["window_start"].max()

            time_unit = st.sidebar.radio(
                "Time Display Unit", options=["minutes", "hours"], horizontal=True
            )

            # Time range inputs
            col1, col2 = st.sidebar.columns(2)

            with col1:
                start_time = st.time_input(
                    "Start Time", value=pd.to_datetime(min_time).time()
                )
                start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(min_time).date(),
                    min_value=pd.to_datetime(min_time).date(),
                    max_value=pd.to_datetime(max_time).date(),
                )

            with col2:
                end_time = st.time_input(
                    "End Time", value=pd.to_datetime(max_time).time()
                )
                end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(max_time).date(),
                    min_value=pd.to_datetime(min_time).date(),
                    max_value=pd.to_datetime(max_time).date(),
                )

        # Combine date and time with proper datetime handling
        start_datetime = pd.to_datetime(f"{start_date} {start_time}")
        end_datetime = pd.to_datetime(f"{end_date} {end_time}")

        # Display chart
        filtered_realtime_scores_df = filter_data_by_time(
            realtime_scores_df, start_datetime, end_datetime
        )

        if selected_players:
            chart = create_score_chart(
                filtered_realtime_scores_df, selected_players, time_unit
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Please select at least one player from the sidebar.")
