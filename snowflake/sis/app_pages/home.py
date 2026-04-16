# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import streamlit as st

st.title("Game Analytics Dashboards")

st.markdown("""
Interactive analytics for the Balloon Popper game, powered by **Dynamic Iceberg Tables** in Snowflake.
Use the sidebar to navigate between the three dashboards.

| Dashboard | What it shows |
|---|---|
| **Leaderboard** | Top-5 scoreboard with bonus hits and score trends over time |
| **Color Analysis** | Per-player balloon color preferences, usage heatmap, and color metrics |
| **Performance Trends** | Scoring efficiency, distribution over time, and 15-second window summaries |
""")
