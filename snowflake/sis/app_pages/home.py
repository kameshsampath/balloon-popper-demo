# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0

import streamlit as st

st.title("Game Analytics Dashboards")

st.markdown("""
Now that we've set up our data pipeline and loaded our game data, we can create interactive dashboards
to visualize and analyze player performance. This **Streamlit in Snowflake** app reads **silver Dynamic
Iceberg Tables** (`dt_*`) in the database/schema configured in **snowflake.yml** (`SNOWFLAKE_SILVER_DATABASE`, `SNOWFLAKE_SILVER_SCHEMA`).

## Purpose

- **Monitor player performance** from DT-backed aggregates
- **Identify patterns** in gameplay
- **Track scoring** over 15-second windows

Use the sidebar navigation for **Leaderboard**, **Color Analysis**, and **Performance Trends**.
""")
