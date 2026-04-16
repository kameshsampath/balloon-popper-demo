# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from colors import color_map

st.title("Color Analysis")
st.caption("Insights into players' balloon color preferences — usage patterns, color distribution heatmap, and per-color metrics (pops, points, bonus hits).")


def analyze_balloon_stats(df, ca_selected_player):
    _filtered_df = df[df["player"] == ca_selected_player]

    color_counts = (
        _filtered_df.groupby(["player", "balloon_color"]).size().reset_index(name="count")
    )
    favorite_colors = color_counts.sort_values("count", ascending=False).groupby("player").first()

    if ca_selected_player not in favorite_colors.index:
        return None
    row = favorite_colors.loc[ca_selected_player]
    return row["balloon_color"], int(row["count"])


def analyze_color_patterns(df, ca_selected_player, gauge_color):
    _filtered_df = df[df["player"] == ca_selected_player]

    _unique_colors = df[df["player"] == ca_selected_player]["balloon_color"].nunique()
    total_colors = df["balloon_color"].nunique()

    gauge_data = pd.DataFrame(
        {
            "value": [_unique_colors],
            "max_value": [total_colors],
            "display": [f"{_unique_colors}/{total_colors}"],
        }
    )

    base = alt.Chart(gauge_data).encode(theta=alt.Theta("value:Q", scale=alt.Scale(domain=[0, total_colors]))).properties(
        width=300,
        height=300,
    )

    arc = base.mark_arc(innerRadius=100, cornerRadius=5, stroke="#fff").encode(color=alt.value(gauge_color))

    text = base.mark_text(align="center", baseline="middle", fontSize=32, font="Arial").encode(
        text="display:N"
    )

    title = (
        alt.Chart(pd.DataFrame([{"text": "Unique Colors vs Total Colors"}]))
        .mark_text(align="center", baseline="top", fontSize=16, dy=150)
        .encode(text="text:N")
    )

    unique_chart = arc + text + title
    st.altair_chart(unique_chart)

    color_dist = (
        _filtered_df.groupby(["player", "balloon_color"])
        .size()
        .astype(int)
        .reset_index(name="count")
    )

    heatmap = (
        alt.Chart(color_dist)
        .mark_rect()
        .encode(
            x=alt.X("player:N", title="Player", axis=alt.Axis(labels=False)),
            y=alt.Y("balloon_color:N", title="Balloon Color"),
            color=alt.Color(
                "count:Q",
                scale=alt.Scale(scheme=st.session_state.color_scheme),
                legend=alt.Legend(format="d", values=sorted(color_dist["count"].unique())),
            ),
            tooltip=["player", "balloon_color", alt.Tooltip("count:Q", format=",d")],
        )
        .properties(
            title="Color Usage Patterns",
            width=600,
            height=400,
        )
    )

    st.altair_chart(heatmap)


def create_balloon_chart(ca_filtered_df, _ca_selected_player, ca_selected_metric):
    metric_titles = {
        "balloon_pops": "Balloon Pops",
        "points_by_color": "Points by Color",
        "bonus_hits": "Bonus Hits",
    }

    base_chart = (
        alt.Chart(ca_filtered_df)
        .mark_bar()
        .encode(
            x=alt.X("balloon_color:N", title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y(f"sum({ca_selected_metric}):Q", title="Total"),
            color=alt.Color(
                "balloon_color:N",
                scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("balloon_color:N", title="Color"),
                alt.Tooltip(f"sum({ca_selected_metric}):Q", title=metric_titles[ca_selected_metric], format=",.0f"),
            ],
        )
        .properties(
            title=f"{metric_titles[ca_selected_metric]}",
            width=600,
            height=400,
        )
        .interactive()
    )

    total_value = ca_filtered_df[ca_selected_metric].sum()
    total_text = (
        alt.Chart({"values": [{"total": total_value}]})
        .mark_text(align="right", baseline="top", fontSize=20, dx=-10, dy=10)
        .encode(
            text=alt.Text("total:Q", format=",.0f"),
            x=alt.value(580),
            y=alt.value(30),
        )
    )

    if ca_selected_metric == "points_by_color":
        player_total = ca_filtered_df["points_by_color"].sum()
        score_text = (
            alt.Chart({"values": [{"score": player_total}]})
            .mark_text(align="left", baseline="top", fontSize=16, text="Total Score", dx=10, dy=10)
            .encode(x=alt.value(20), y=alt.value(30))
        )
        score_value = (
            alt.Chart({"values": [{"score": player_total}]})
            .mark_text(align="left", baseline="top", fontSize=16, fontWeight="bold", dx=100, dy=10)
            .encode(
                text=alt.Text("score:Q", format=",.0f"),
                x=alt.value(20),
                y=alt.value(30),
            )
        )
        return alt.layer(base_chart, total_text, score_text, score_value)

    return alt.layer(base_chart, total_text)


def to_df(series: pd.Series, cols: list[str]) -> pd.DataFrame:
    __least_used_df = pd.DataFrame(series).reset_index()
    __least_used_df.columns = cols
    return __least_used_df


if st.session_state.balloon_colored_pops is not None:
    colored_pops, _color_stats = st.session_state.balloon_colored_pops

    with st.sidebar:
        st.header("⚙️ Settings")
        players = sorted(colored_pops["player"].unique())
        selected_player = st.selectbox(
            "Select Player",
            options=players,
        )
        metrics = {
            "Balloon Pops": "balloon_pops",
            "Points by Color": "points_by_color",
            "Bonus Hits": "bonus_hits",
        }
        selected_metric = st.selectbox("Select Metric", list(metrics.keys()))

    fav = analyze_balloon_stats(colored_pops, selected_player)
    if fav is None:
        st.info("No color rows for this player yet.")
        st.stop()

    favorite_color = fav[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Player Name", selected_player)
    with col2:
        st.metric(
            "Total Balloon Pops",
            int(colored_pops[colored_pops["player"] == selected_player]["balloon_pops"].sum()),
        )
    with col3:
        st.metric("Total Colors Used", int(colored_pops["balloon_color"].nunique()))
    with col4:
        st.metric("Favorite Color", favorite_color)

    analyze_color_patterns(colored_pops, selected_player, favorite_color)

    st.header("Color Statistics")

    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        least_used = colored_pops["balloon_color"].value_counts().nsmallest(3)
        st.write("### Least Popular Colors")
        least_used_df = to_df(least_used, ["balloon_color", "count"])
        least_used_df["balloon_color"] = least_used_df["balloon_color"].str.title()
        max_c = int(least_used_df["count"].max()) if not least_used_df.empty else 1
        st.dataframe(
            least_used_df,
            column_config={
                "balloon_color": st.column_config.TextColumn(
                    label="Balloon Color",
                    help="Balloon Color",
                ),
                "count": st.column_config.ProgressColumn(
                    "Count",
                    help=f"Count of the least popular color for the player {selected_player}",
                    format="%d",
                    min_value=0,
                    max_value=max_c,
                ),
            },
            hide_index=True,
        )

    with stat_col2:
        most_used = colored_pops["balloon_color"].value_counts().nlargest(3)
        st.write("### Most Popular Colors")
        most_used_df = to_df(most_used, ["balloon_color", "count"])
        most_used_df["balloon_color"] = most_used_df["balloon_color"].str.title()
        max_m = int(most_used_df["count"].max()) if not most_used_df.empty else 1
        st.dataframe(
            most_used_df,
            column_config={
                "balloon_color": st.column_config.TextColumn(
                    label="Balloon Color",
                    help="Balloon Color",
                ),
                "count": st.column_config.ProgressColumn(
                    "Count",
                    help=f"Count of the most popular color for the player {selected_player}",
                    format="%d",
                    min_value=0,
                    max_value=max_m,
                ),
            },
            hide_index=True,
        )

    st.header("By Specific Metric")
    filtered_df = colored_pops[colored_pops["player"] == selected_player]

    metric_column = metrics[selected_metric]
    chart = create_balloon_chart(filtered_df, selected_player, metric_column)
    st.altair_chart(chart, use_container_width=True)
