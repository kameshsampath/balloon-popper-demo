# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from pandas import Timestamp


def create_score_chart(data, f_selected_players, f_time_unit: str = "minutes"):
    filtered_df = data[data["player"].isin(f_selected_players)]

    if filtered_df.empty:
        raise ValueError("No data available for the selected players and time range")

    filtered_df = filtered_df.copy()
    filtered_df["window_start"] = pd.to_datetime(filtered_df["window_start"])

    aggregated_df = (
        filtered_df.groupby(["window_start", "player"])["total_score"].max().reset_index()
    )

    if f_time_unit == "hours":
        time_format = "%H:%M"
    else:
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

    lines = base.mark_line()
    points = base.mark_circle(size=100).encode(
        tooltip=[
            alt.Tooltip("player:N", title="Player"),
            alt.Tooltip("total_score:Q", title="Total Score", format=".0f"),
            alt.Tooltip("window_start:T", title="Time", format=time_format),
        ]
    )

    return (
        (lines + points)
        .properties(width=700, height=400, title="Player Total Score Trends Over Time")
        .interactive()
    )


def filter_data_by_time(
    df: pd.DataFrame, f_start_time: Timestamp, f_end_time: Timestamp
):
    start_pd = pd.to_datetime(f_start_time)
    end_pd = pd.to_datetime(f_end_time)
    mask = (df["window_start"] >= start_pd) & (df["window_start"] <= end_pd)
    return df[mask]


st.title("Leaderboard")
st.caption("Real-time analytics of player performance — top-5 scoreboard with bonus hits and interactive score trends over selectable time ranges.")

if st.session_state.leaderboard_data is not None:
    leaderboard = st.session_state.leaderboard_data
    latest_records = leaderboard.sort_values("event_ts", ascending=False).drop_duplicates("player")
    combined_stats = (
        latest_records.groupby("player")
        .agg({"total_score": "sum", "bonus_hits": "sum"})
        .reset_index()
        .sort_values("total_score", ascending=False)
    )

    st.header("Scoreboard")
    max_score = int(combined_stats["total_score"].max()) if not combined_stats.empty else 1
    st.dataframe(
        combined_stats.head(5),
        column_config={
            "player": "Player",
            "total_score": st.column_config.ProgressColumn(
                "Total Score",
                help="Player's total score with visual progress bar",
                format="%d",
                min_value=0,
                max_value=max_score,
            ),
            "bonus_hits": st.column_config.NumberColumn(
                "Bonus Hits",
                help="Player's bonus pops",
                format="%d",
            ),
        },
        hide_index=True,
    )

    if st.session_state.realtime_scores_data is not None:
        st.header("Leaderboard Score Analysis")
        realtime_scores_df = st.session_state.realtime_scores_data

        leaders = combined_stats["player"].unique()[:5]

        with st.sidebar:
            st.header("⚙️ Settings")
            selected_players = st.multiselect(
                "Select Players",
                options=list(leaders),
                default=list(leaders),
            )

            min_time = realtime_scores_df["window_start"].min()
            max_time = realtime_scores_df["window_start"].max()

            time_unit = st.radio(
                "Time Display Unit", options=["minutes", "hours"], horizontal=True
            )

            col1, col2 = st.columns(2)

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
                end_time = st.time_input("End Time", value=pd.to_datetime(max_time).time())
                end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(max_time).date(),
                    min_value=pd.to_datetime(min_time).date(),
                    max_value=pd.to_datetime(max_time).date(),
                )

        start_datetime = pd.to_datetime(f"{start_date} {start_time}")
        end_datetime = pd.to_datetime(f"{end_date} {end_time}")

        filtered_realtime_scores_df = filter_data_by_time(
            realtime_scores_df, start_datetime, end_datetime
        )

        if selected_players:
            chart = create_score_chart(filtered_realtime_scores_df, selected_players, time_unit)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.warning("Please select at least one player from the sidebar.")
