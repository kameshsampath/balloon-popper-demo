# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Glue / S3 Tables names for the bronze landing zone (single raw-events path for CLD + DT)."""

# Matches RisingWave ``balloon_game_events`` in ``polaris-forge-setup/templates/source.sql.j2``.
# Each row stores one Kafka-style JSON object (Iceberg string column); Snowflake DT uses
# ``PARSE_JSON`` / VARIANT-style paths. Aggregates move to Dynamic Iceberg Tables, not this loader.
BRONZE_RAW_EVENTS_TABLE = "balloon_game_events"
# Glue / Iceberg column holding ``FORMAT PLAIN ENCODE JSON``-shaped payload (one object per row).
BRONZE_EVENT_JSON_COLUMN = "event"

BRONZE_GLUE_TABLES: tuple[str, ...] = (BRONZE_RAW_EVENTS_TABLE,)
