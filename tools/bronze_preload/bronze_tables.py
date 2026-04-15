# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Glue / S3 Tables names for the bronze landing zone (single raw-events path for CLD + DT)."""

# Raw stream table: one JSON object per row in ``BRONZE_EVENT_JSON_COLUMN`` (Iceberg string).
# Snowflake DT uses ``PARSE_JSON`` / semi-structured paths. Aggregates live in Dynamic Iceberg Tables, not here.
BRONZE_RAW_EVENTS_TABLE = "balloon_game_events"
# Glue / Iceberg column holding ``FORMAT PLAIN ENCODE JSON``-shaped payload (one object per row).
BRONZE_EVENT_JSON_COLUMN = "event"

BRONZE_GLUE_TABLES: tuple[str, ...] = (BRONZE_RAW_EVENTS_TABLE,)
