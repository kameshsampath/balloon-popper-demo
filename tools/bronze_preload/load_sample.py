#!/usr/bin/env python3
# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Create (if needed) Glue Iceberg tables and append small sample rows.

Requires real AWS credentials (e.g. AWS_PROFILE) and:
  BRONZE_WAREHOUSE  s3://bucket/prefix/   — Iceberg warehouse root
Optional:
  GLUE_DATABASE     default balloon_pops (or <slug>_balloon_pops when LAB_USERNAME is set and GLUE_DATABASE unset)
  LAB_USERNAME      workshop participant id — unique Glue DB / S3 table bucket defaults (see .env.example)
  AWS_REGION        if not set in profile
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pyarrow as pa
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import DecimalType, LongType, NestedField, StringType, TimestamptzType


def _ts(hour: int = 12) -> datetime:
    return datetime(2026, 1, 15, hour, 0, 0, tzinfo=timezone.utc)


def _sanitize_glue_slug(lab: str) -> str:
    """Match ``bronze_aws.sanitize_lab_slug_glue``: [a-z0-9_], max 20."""
    u = lab.lower()
    u = re.sub(r"[^a-z0-9_]+", "_", u)
    u = re.sub(r"_+", "_", u).strip("_")
    return u[:20] if u else ""


def resolve_glue_database() -> str:
    if os.environ.get("GLUE_DATABASE"):
        return os.environ["GLUE_DATABASE"]
    lab = os.environ.get("LAB_USERNAME", "").strip()
    if not lab:
        return "balloon_pops"
    gslug = _sanitize_glue_slug(lab)
    if not gslug:
        raise ValueError(
            "LAB_USERNAME must yield a non-empty Glue slug (letters, numbers, underscore, hyphen)"
        )
    return f"{gslug}_balloon_pops"


def schema_leaderboard() -> Schema:
    return Schema(
        NestedField(1, "player", StringType(), required=True),
        NestedField(2, "total_score", LongType(), required=True),
        NestedField(3, "bonus_hits", LongType(), required=True),
        NestedField(4, "event_ts", TimestamptzType(), required=True),
    )


def schema_balloon_color_stats() -> Schema:
    return Schema(
        NestedField(1, "player", StringType(), required=True),
        NestedField(2, "balloon_color", StringType(), required=True),
        NestedField(3, "points_by_color", LongType(), required=True),
        NestedField(4, "bonus_hits", LongType(), required=True),
        NestedField(5, "event_ts", TimestamptzType(), required=True),
    )


def schema_realtime_scores() -> Schema:
    return Schema(
        NestedField(1, "player", StringType(), required=True),
        NestedField(2, "total_score", LongType(), required=True),
        NestedField(3, "window_start", TimestamptzType(), required=True),
        NestedField(4, "window_end", TimestamptzType(), required=True),
    )


def schema_balloon_colored_pops() -> Schema:
    return Schema(
        NestedField(1, "player", StringType(), required=True),
        NestedField(2, "balloon_color", StringType(), required=True),
        NestedField(3, "balloon_pops", LongType(), required=True),
        NestedField(4, "points_by_color", LongType(), required=True),
        NestedField(5, "bonus_hits", LongType(), required=True),
        NestedField(6, "window_start", TimestamptzType(), required=True),
        NestedField(7, "window_end", TimestamptzType(), required=True),
    )


def schema_color_performance_trends() -> Schema:
    return Schema(
        NestedField(1, "balloon_color", StringType(), required=True),
        NestedField(2, "avg_score_per_pop", DecimalType(10, 28), required=True),
        NestedField(3, "total_pops", LongType(), required=True),
        NestedField(4, "window_start", TimestamptzType(), required=True),
        NestedField(5, "window_end", TimestamptzType(), required=True),
    )


def open_catalog(warehouse: str):
    if os.environ.get("AWS_REGION"):
        os.environ.setdefault("AWS_DEFAULT_REGION", os.environ["AWS_REGION"])
    return load_catalog(
        "bronze_glue",
        **{"type": "glue", "warehouse": warehouse},
    )


def ensure_ns(catalog, db: str) -> None:
    try:
        catalog.create_namespace(db)
    except NamespaceAlreadyExistsError:
        pass


def ensure_table(catalog, db: str, name: str, schema: Schema) -> None:
    ident = (db, name)
    if catalog.table_exists(ident):
        return
    catalog.create_table(
        ident,
        schema=schema,
        partition_spec=PartitionSpec(),
        properties={"write.format.default": "parquet"},
    )


def append_rows(catalog, db: str, name: str, table: pa.Table) -> None:
    tbl = catalog.load_table((db, name))
    tbl.append(table)


def main() -> int:
    warehouse = os.environ.get("BRONZE_WAREHOUSE")
    if not warehouse:
        print("error: set BRONZE_WAREHOUSE (s3://bucket/prefix/)", file=sys.stderr)
        return 1
    warehouse = warehouse.rstrip("/") + "/"
    try:
        db = resolve_glue_database()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    catalog = open_catalog(warehouse)
    ensure_ns(catalog, db)

    ws = _ts(12)
    we = ws + timedelta(seconds=15)

    ensure_table(catalog, db, "leaderboard", schema_leaderboard())
    append_rows(
        catalog,
        db,
        "leaderboard",
        pa.Table.from_pylist(
            [
                {
                    "player": "alice",
                    "total_score": 1200,
                    "bonus_hits": 3,
                    "event_ts": _ts(14),
                },
                {
                    "player": "bob",
                    "total_score": 980,
                    "bonus_hits": 1,
                    "event_ts": _ts(14),
                },
            ]
        ),
    )

    ensure_table(catalog, db, "balloon_color_stats", schema_balloon_color_stats())
    append_rows(
        catalog,
        db,
        "balloon_color_stats",
        pa.Table.from_pylist(
            [
                {
                    "player": "alice",
                    "balloon_color": "red",
                    "points_by_color": 400,
                    "bonus_hits": 1,
                    "event_ts": _ts(13),
                },
                {
                    "player": "alice",
                    "balloon_color": "blue",
                    "points_by_color": 150,
                    "bonus_hits": 0,
                    "event_ts": _ts(13),
                },
            ]
        ),
    )

    ensure_table(catalog, db, "realtime_scores", schema_realtime_scores())
    append_rows(
        catalog,
        db,
        "realtime_scores",
        pa.Table.from_pylist(
            [
                {
                    "player": "alice",
                    "total_score": 50,
                    "window_start": ws,
                    "window_end": we,
                },
            ]
        ),
    )

    ensure_table(catalog, db, "balloon_colored_pops", schema_balloon_colored_pops())
    append_rows(
        catalog,
        db,
        "balloon_colored_pops",
        pa.Table.from_pylist(
            [
                {
                    "player": "bob",
                    "balloon_color": "green",
                    "balloon_pops": 5,
                    "points_by_color": 300,
                    "bonus_hits": 0,
                    "window_start": ws,
                    "window_end": we,
                },
            ]
        ),
    )

    ensure_table(catalog, db, "color_performance_trends", schema_color_performance_trends())
    append_rows(
        catalog,
        db,
        "color_performance_trends",
        pa.Table.from_pylist(
            [
                {
                    "balloon_color": "red",
                    "avg_score_per_pop": Decimal("95.5"),
                    "total_pops": 10,
                    "window_start": ws,
                    "window_end": we,
                },
            ]
        ),
    )

    print(f"OK: appended sample rows to Glue database {db!r} under warehouse {warehouse!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
