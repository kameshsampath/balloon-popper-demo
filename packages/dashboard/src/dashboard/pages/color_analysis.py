# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

### Color analysis Visualizations
import os

import altair as alt
import pandas as pd
import streamlit as st

from common.log.logger import get_logger
from dashboard.data.colors import  color_map

logger = get_logger("colo_analysis", os.environ.get("APP_LOG_LEVEL", "INFO"))

st.title("Color Analysis")



def analyze_balloon_stats(df, ca_selected_player):
    _filtered_df = df[df['player'] == ca_selected_player]

    # Favorite colors (most popped)
    color_counts = _filtered_df.groupby(['player', 'balloon_color']).size().reset_index(name='count')
    favorite_colors = color_counts.sort_values('count', ascending=False).groupby('player').first()

    player_data = favorite_colors[favorite_colors.index == ca_selected_player]
    if not player_data.empty:
        _favorite_color = player_data['balloon_color'].iloc[0]
        favorite_count = player_data['count'].iloc[0]
        favorite_tuple = (_favorite_color, favorite_count)
        return favorite_tuple

    return None


def analyze_color_patterns(df, ca_selected_player, gauge_color):
    _filtered_df = df[df['player'] == ca_selected_player]

    # Unique colors used by each player
    _unique_colors = df[df['player'] == selected_player]['balloon_color'].nunique()
    total_colors = df['balloon_color'].nunique()  # Total possible colors

    # Create data for the gauge chart with both values
    gauge_data = pd.DataFrame({
        'value': [_unique_colors],
        'max_value': [total_colors],
        'display': [f"{_unique_colors}/{total_colors}"]  # Add combined display format
    })

    base = alt.Chart(gauge_data).encode(
        theta=alt.Theta(
            'value:Q',
            scale=alt.Scale(domain=[0, total_colors])
        )
    ).properties(
        width=300,
        height=300
    )

    arc = base.mark_arc(
        innerRadius=100,
        cornerRadius=5,
        stroke="#fff"
    ).encode(
        color=alt.value(gauge_color)
    )

    # Modified text to show value/max_value
    text = base.mark_text(
        align='center',
        baseline='middle',
        fontSize=32,
        font='Arial'
    ).encode(
        text='display:N'  # Use the combined display format
    )

    title = alt.Chart(pd.DataFrame([{'text': 'Unique Colors vs Total Colors'}])).mark_text(
        align='center',
        baseline='top',
        fontSize=16,
        dy=150
    ).encode(
        text='text:N'
    )

    unique_chart = (arc + text + title)

    st.altair_chart(unique_chart)

    # Color distribution heatmap
    color_dist = (_filtered_df.groupby(['player', 'balloon_color'])
                  .size()
                  .astype(int)  # Ensure count is integer
                  .reset_index(name='count'))

    heatmap = alt.Chart(color_dist).mark_rect().encode(
        x=alt.X('player:N',
                title='Player',
                axis=alt.Axis(labels=False)),
        y=alt.Y('balloon_color:N', title='Balloon Color'),
        color=alt.Color('count:Q',
                        scale=alt.Scale(scheme=st.session_state.color_scheme),
                        legend=alt.Legend(format='d', values=sorted(color_dist['count'].unique()), )),
        # Use 'd' format for integers
        tooltip=['player', 'balloon_color',
                 alt.Tooltip('count:Q', format=',d')]  # Format tooltip as integer with commas
    ).properties(
        title='Color Usage Patterns',
        width=600,
        height=400
    )

    st.altair_chart(heatmap)


def create_balloon_chart(ca_filtered_df, ca_selected_player, ca_selected_metric):
    """
    Creates a chart based on the selected metric and player
    """
    # Mapping of metric names to their display titles
    metric_titles = {
        "balloon_pops": "Balloon Pops",
        "points_by_color": "Points by Color",
        "bonus_hits": "Bonus Hits"
    }

    # Base chart
    base_chart = alt.Chart(ca_filtered_df).mark_bar().encode(
        x=alt.X('balloon_color:N',
                title=None,
                axis=alt.Axis(labels=False, ticks=False)),
        y=alt.Y(f'sum({ca_selected_metric}):Q',
                title='Total'),
        color=alt.Color('balloon_color:N',
                        scale=alt.Scale(domain=list(color_map.keys()),
                                        range=list(color_map.values())),
                        legend=None),
        tooltip=[
            alt.Tooltip('balloon_color:N', title='Color'),
            alt.Tooltip(f'sum({ca_selected_metric}):Q',
                        title=metric_titles[ca_selected_metric],
                        format=',.0f')
        ]
    ).properties(
        title=f"{metric_titles[ca_selected_metric]}",
        width=600,
        height=400
    ).interactive()

    # Add real-time total as text overlay
    total_value = ca_filtered_df[ca_selected_metric].sum()
    total_text = alt.Chart({'values': [{'total': total_value}]}).mark_text(
        align='right',
        baseline='top',
        fontSize=20,
        dx=-10,
        dy=10
    ).encode(
        text=alt.Text('total:Q', format=',.0f'),
        x=alt.value(580),  # Slightly adjusted for better positioning
        y=alt.value(30)
    )

    # Player's total score (specifically for points)
    if ca_selected_metric == 'points_by_color':
        player_total = ca_filtered_df['points_by_color'].sum()
        score_text = alt.Chart({'values': [{'score': player_total}]}).mark_text(
            align='left',
            baseline='top',
            fontSize=16,
            text='Total Score',
            dx=10,
            dy=10
        ).encode(
            x=alt.value(20),
            y=alt.value(30)
        )
        score_value = alt.Chart({'values': [{'score': player_total}]}).mark_text(
            align='left',
            baseline='top',
            fontSize=16,
            fontWeight='bold',
            dx=100,
            dy=10
        ).encode(
            text=alt.Text('score:Q', format=',.0f'),
            x=alt.value(20),
            y=alt.value(30)
        )
        return alt.layer(base_chart, total_text, score_text, score_value)

    return alt.layer(base_chart, total_text)


def to_df(series: pd.Series, cols: list[str]) -> pd.DataFrame:
    __least_used_df = pd.DataFrame(series).reset_index()
    __least_used_df.columns = cols
    return __least_used_df


if st.session_state.balloon_colored_pops is not None:
    colored_pops, color_stats = st.session_state.balloon_colored_pops

    with st.sidebar:
        st.header("⚙️ Settings")
        # Player selector
        players = sorted(colored_pops["player"].unique())
        selected_player = st.sidebar.selectbox(
            "Select Player",
            options=players,
        )
        # Metric selector
        metrics = {
            "Balloon Pops": "balloon_pops",
            "Points by Color": "points_by_color",
            "Bonus Hits": "bonus_hits",
        }
        selected_metric = st.sidebar.selectbox("Select Metric", list(metrics.keys()))

    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    favorite_color = analyze_balloon_stats(colored_pops, selected_player)[0]
    with col1:
        st.metric("Player Name", selected_player)
    with col2:
        st.metric("Total Balloon Pops", colored_pops[colored_pops['player'] == selected_player]['balloon_pops'].sum())
    with col3:
        st.metric("Total Colors Used", colored_pops['balloon_color'].nunique())
    with col4:
        st.metric("Favorite Color", favorite_color)

    analyze_balloon_stats(colored_pops, selected_player)

    analyze_color_patterns(colored_pops, selected_player, favorite_color)

    # Additional statistics
    st.header('Color Statistics')

    stat_col1, stat_col2 = st.columns(2)
    with stat_col1:
        # Least used colors
        least_used = colored_pops['balloon_color'].value_counts().nsmallest(3)
        st.write("### Least Popular Colors")
        least_used_df = to_df(least_used, ['balloon_color', 'count'])
        least_used_df['balloon_color'] = least_used_df['balloon_color'].str.title()
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
                    max_value=int(least_used_df['count'].max())
                )
            },
            hide_index=True
        )

    with stat_col2:
        # Most used colors
        most_used = colored_pops['balloon_color'].value_counts().nlargest(3)
        st.write("### Most Popular Colors")
        most_used_df = to_df(most_used, ['balloon_color', 'count'])
        most_used_df['balloon_color'] = least_used_df['balloon_color'].str.title()
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
                    max_value=int(most_used_df['count'].max())
                )
            },
            hide_index=True
        )

    st.header('By Specific Metric')
    # Filter data
    filtered_df = colored_pops[colored_pops["player"] == selected_player]

    if 'filtered_df' in locals() and 'selected_player' in locals():
        metric_column = metrics[selected_metric]
        chart = create_balloon_chart(filtered_df, selected_player, metric_column)
        st.altair_chart(chart, use_container_width=True)
