import streamlit as st
import altair as alt
import os
import pandas as pd
from common.log.logger import get_logger
from dashboard.data.colors import  color_map

st.header('Balloon Performance Analysis')

logger = get_logger("performance_trends", os.environ.get("APP_LOG_LEVEL", "INFO"))

def show_summary(df):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Average Score",
                  f"{df['avg_score_per_pop'].mean():.1f}")
    with col2:
        st.metric("Best Score",
                  f"{df['avg_score_per_pop'].max():.1f}")
    with col3:
        st.metric("Total Balloons",
                  f"{df['total_pops'].sum()}")


if st.session_state.color_performance_data is not None:
    performance_trends_df = st.session_state.color_performance_data

    performance_trends_df['window_start'] = pd.to_datetime(performance_trends_df['window_start'])
    performance_trends_df['avg_score_per_pop'] = pd.to_numeric(performance_trends_df['avg_score_per_pop'])

    show_summary(performance_trends_df)

    # Main box plot
    main_chart = alt.Chart(performance_trends_df).mark_boxplot(
        extent='min-max',
        median=dict(color='white'),
        size=40
    ).encode(
        x=alt.X('window_start:T',
                title='Time Window',
                axis=alt.Axis(format='%H:%M:%S', labelAngle=-45)),
        y=alt.Y('avg_score_per_pop:Q',
                title='Average Score per Pop',
                scale=alt.Scale(zero=False)),
        color=alt.Color('window_start:T',
                        legend=None,
                        scale=alt.Scale(scheme='viridis')),
        tooltip=[
            alt.Tooltip('window_start:T', title='Time Window', format='%H:%M:%S'),
            alt.Tooltip('avg_score_per_pop:Q', title='Score', format='.1f'),
            alt.Tooltip('total_pops:Q', title='Total Pops')
        ]
    ).properties(
        width=700,
        height=400,
        title={
            'text': 'Performance Distribution Over Time',
            'fontSize': 20,
            'anchor': 'middle'
        }
    ).interactive()

    # Display main chart
    st.altair_chart(main_chart, use_container_width=True)

    # Add color-based metrics
    st.subheader('Performance by Balloon Color')

    # Calculate color-based statistics
    color_stats = performance_trends_df.groupby('balloon_color').agg({
        'avg_score_per_pop': ['mean', 'min', 'max', 'count'],
        'total_pops': 'sum'
    }).round(1)

    color_stats.columns = ['Average Score', 'Min Score', 'Max Score', 'Count', 'Total Pops']
    color_stats = color_stats.sort_values('Average Score', ascending=False)

    # Display color statistics with configured columns
    st.dataframe(
        color_stats,
        column_config={
            "balloon_color": st.column_config.TextColumn(
                label="Balloon Color",
                help="Color of the balloon"
            ),
            "Average Score": st.column_config.NumberColumn(
                label="Average Score",
                help="Mean score for this color",
                format="%.1f",
                min_value=0
            ),
            "Min Score": st.column_config.NumberColumn(
                label="Min Score",
                help="Lowest score for this color",
                format="%.1f",
                min_value=0
            ),
            "Max Score": st.column_config.NumberColumn(
                label="Max Score",
                help="Highest score for this color",
                format="%.1f",
                min_value=0
            ),
            "Count": st.column_config.NumberColumn(
                label="Count",
                help="Number of occurrences",
                format="%d",
                min_value=0
            ),
            "Total Pops": st.column_config.NumberColumn(
                label="Total Pops",
                help="Total number of pops for this color",
                format="%d",
                min_value=0
            )
        },
        use_container_width=True,
        hide_index=False) # Show balloon color as index

    # Create color performance chart
    color_chart = alt.Chart(performance_trends_df).mark_bar().encode(
        x=alt.X('balloon_color:N',
                title='Balloon Color',
                sort='-y',
                axis=alt.Axis(labels=False)),  # Remove x-axis labels
        y=alt.Y('mean(avg_score_per_pop):Q',
                title='Average Score'),
        color=alt.Color('balloon_color:N',
                        legend=None,
                        scale=alt.Scale(domain=list(color_map.keys()),
                                        range=list(color_map.values()))),
        tooltip=[
            alt.Tooltip('balloon_color:N', title='Color'),
            alt.Tooltip('mean(avg_score_per_pop):Q', title='Avg Score', format='.1f'),
            alt.Tooltip('count():Q', title='Count')
        ]
    ).properties(
        width=700,
        height=300,
        title='Average Score by Balloon Color'
    ).interactive()

    # Display color chart
    st.altair_chart(color_chart, use_container_width=True)

    # Time window summary
    st.subheader('Time Window Summary')
    # Create the time summary with aggregations
    time_summary = performance_trends_df.groupby(pd.Grouper(key='window_start', freq='15S')).agg({
        'avg_score_per_pop': ['mean', 'min', 'max', 'count'],
        'total_pops': 'sum'
    }).round(1)

    # Rename columns
    time_summary.columns = ['Mean Score', 'Min Score', 'Max Score', '# Balloons', 'Total Pops']
    time_summary = time_summary.reset_index()
    time_summary = time_summary.rename(columns={'window_start': 'Timestamp'})

    # Display with column configuration
    st.dataframe(
        time_summary,
        column_config={
            "Timestamp": st.column_config.DatetimeColumn(
                "Timestamp",
                format="HH:mm:ss",
                help="15-second intervals"
            ),
            "Mean Score": st.column_config.NumberColumn(
                "Mean Score",
                format="%.1f",
                help="Average score in the interval"
            ),
            "Min Score": st.column_config.NumberColumn(
                "Min Score",
                format="%.1f"
            ),
            "Max Score": st.column_config.NumberColumn(
                "Max Score",
                format="%.1f"
            ),
            "# Balloons": st.column_config.NumberColumn(
                "# Balloons",
                format="%d",
                help="Number of balloons in the interval"
            ),
            "Total Pops": st.column_config.NumberColumn(
                "Total Pops",
                format="%d",
                help="Total balloon pops in the interval"
            )
        },
        use_container_width=True,
        hide_index=True
    )

