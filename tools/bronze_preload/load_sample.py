#!/usr/bin/env python3
# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Create (if needed) a single Glue Iceberg raw-events table and append JSON rows.

Bronze is **one table** — ``balloon_game_events``. Each row is one **JSON object** (Kafka
``FORMAT PLAIN ENCODE JSON`` style) in string column ``event``, so streaming-shaped data
lands as a blob; **Snowflake Dynamic Iceberg Tables** use JSON extraction (for example
``PARSE_JSON``) for downstream DTs. Aggregates are not written here.

Requires real AWS credentials (e.g. AWS_PROFILE) and:
  BRONZE_BUCKET_NAME  general-purpose S3 warehouse bucket (see ``task bronze:glue-setup``).
Optional:
  GLUE_DATABASE, LAB_USERNAME, AWS_REGION (see module docstring in previous revisions).
  BRONZE_SAMPLE_ROW_COUNT  number of simulated events when using ``--row-count`` mode
  BRONZE_LOAD_DURATION_MINUTES  simulated generator duration in duration mode
  DELAY / BRONZE_GENERATOR_DELAY  seconds between pops (Kafka parity)
  NUM_PLAYERS, BONUS_PROBABILITY
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pyarrow as pa
from common.game_generator import BalloonGameGenerator
from common.stream.models import GameEvent
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NamespaceAlreadyExistsError
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType

from .bronze_aws import (
    assert_bronze_warehouse_bucket_exists,
    apply_bronze_from_aws_config,
    derive_bronze_resource_names,
    resolve_bronze_warehouse,
)
from .bronze_tables import BRONZE_EVENT_JSON_COLUMN, BRONZE_RAW_EVENTS_TABLE


def _ts(hour: int = 12) -> datetime:
    return datetime(2026, 1, 15, hour, 0, 0, tzinfo=timezone.utc)


def _sanitize_glue_slug(lab: str) -> str:
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


def schema_balloon_game_events() -> Schema:
    """One string column: JSON per row (same logical fields as ``source.sql.j2`` source)."""
    return Schema(
        NestedField(1, BRONZE_EVENT_JSON_COLUMN, StringType(), required=True),
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


def iceberg_rows_to_pa_table(schema: Schema, rows: list[dict]) -> pa.Table:
    return pa.Table.from_pylist(rows, schema=schema.as_arrow())


DEFAULT_ROW_COUNT = 2500
MAX_ROW_COUNT = 100_000
DEFAULT_DURATION_MINUTES = 5.0
MAX_DURATION_MINUTES = 240.0
MAX_GENERATOR_EVENTS = 100_000


def resolve_row_count(cli_value: int | None) -> int:
    if cli_value is not None:
        return max(1, min(cli_value, MAX_ROW_COUNT))
    raw = (os.environ.get("BRONZE_SAMPLE_ROW_COUNT") or "").strip()
    if raw:
        try:
            return max(1, min(int(raw), MAX_ROW_COUNT))
        except ValueError:
            print(
                f"warning: ignoring invalid BRONZE_SAMPLE_ROW_COUNT={raw!r}; using {DEFAULT_ROW_COUNT}",
                file=sys.stderr,
            )
    return DEFAULT_ROW_COUNT


def _delay_seconds() -> float:
    raw = (os.environ.get("BRONZE_GENERATOR_DELAY") or os.environ.get("DELAY") or "1.0").strip()
    try:
        return max(0.05, float(raw))
    except ValueError:
        return 1.0


def _num_players() -> int:
    try:
        return max(2, int(os.environ.get("NUM_PLAYERS", "12")))
    except ValueError:
        return 12


def _bonus_probability() -> float:
    try:
        return float(os.environ.get("BONUS_PROBABILITY", "0.15"))
    except ValueError:
        return 0.15


def resolve_duration_minutes(cli_value: float | None) -> float:
    if cli_value is not None:
        return max(0.05, min(float(cli_value), MAX_DURATION_MINUTES))
    raw = (os.environ.get("BRONZE_LOAD_DURATION_MINUTES") or "").strip()
    if raw:
        try:
            return max(0.05, min(float(raw), MAX_DURATION_MINUTES))
        except ValueError:
            print(
                f"warning: ignoring invalid BRONZE_LOAD_DURATION_MINUTES={raw!r}; "
                f"using {DEFAULT_DURATION_MINUTES}",
                file=sys.stderr,
            )
    return DEFAULT_DURATION_MINUTES


def event_count_for_duration(duration_minutes: float, delay_sec: float) -> int:
    n = int(duration_minutes * 60.0 / delay_sec)
    return max(1, min(n, MAX_GENERATOR_EVENTS))


@dataclass(frozen=True)
class EventBatchPlan:
    """Simulated Kafka-style pop batch (always converted to ``balloon_game_events`` rows)."""

    n_events: int
    delay_sec: float
    clock_start: datetime
    rng_seed: int
    mode: str  # "synthetic" | "generator"


def resolve_event_batch_plan(
    *,
    dataset: str,
    row_count_cli: int | None,
    duration_cli: float | None,
) -> EventBatchPlan:
    clock = _ts(12) + (timedelta(hours=2) if dataset == "more" else timedelta(0))
    seed = 44_251 if dataset == "more" else 44_250
    delay = _delay_seconds()

    if row_count_cli is not None:
        n = resolve_row_count(row_count_cli)
        return EventBatchPlan(
            n_events=n,
            delay_sec=delay,
            clock_start=clock,
            rng_seed=seed,
            mode="synthetic",
        )
    if duration_cli is not None:
        dm = resolve_duration_minutes(duration_cli)
        return EventBatchPlan(
            n_events=event_count_for_duration(dm, delay),
            delay_sec=delay,
            clock_start=clock,
            rng_seed=seed,
            mode="generator",
        )
    if (os.environ.get("BRONZE_SAMPLE_ROW_COUNT") or "").strip():
        n = resolve_row_count(None)
        return EventBatchPlan(
            n_events=n,
            delay_sec=delay,
            clock_start=clock,
            rng_seed=seed,
            mode="synthetic",
        )
    if (os.environ.get("BRONZE_LOAD_DURATION_MINUTES") or "").strip():
        dm = resolve_duration_minutes(None)
        return EventBatchPlan(
            n_events=event_count_for_duration(dm, delay),
            delay_sec=delay,
            clock_start=clock,
            rng_seed=seed,
            mode="generator",
        )
    dm = DEFAULT_DURATION_MINUTES
    return EventBatchPlan(
        n_events=event_count_for_duration(dm, delay),
        delay_sec=delay,
        clock_start=clock,
        rng_seed=seed,
        mode="generator",
    )


def _player_name(rng: random.Random) -> str:
    adjectives = ("Swift", "Bouncy", "Cosmic", "Lucky", "Mighty", "Gentle", "Wild")
    nouns = ("Balloon", "Cloud", "Star", "Wind", "Phoenix", "Dragon", "Spirit")
    return f"{rng.choice(adjectives)} {rng.choice(nouns)}"


def _build_generator_player_pool(rng: random.Random, n: int) -> list[str]:
    pool: list[str] = []
    seen: set[str] = set()
    while len(pool) < n:
        name = _player_name(rng)
        if name not in seen:
            seen.add(name)
            pool.append(name)
    return pool


def simulate_game_events(plan: EventBatchPlan) -> list[GameEvent]:
    rng = random.Random(plan.rng_seed)
    gen = BalloonGameGenerator(_bonus_probability(), rng=rng)
    players = _build_generator_player_pool(rng, _num_players())
    events: list[GameEvent] = []
    for i in range(plan.n_events):
        ts = plan.clock_start + timedelta(seconds=i * plan.delay_sec)
        player = players[i % len(players)]
        events.append(gen.generate_pop(player, event_ts=ts))
    return events


def game_event_to_json_line(ev: GameEvent) -> str:
    """Serialize to one JSON object per Kafka-style PLAIN JSON line (``page_id`` until the producer sets it)."""
    payload = {
        "player": ev.player,
        "balloon_color": ev.balloon_color,
        "score": ev.score,
        "page_id": 0,
        "favorite_color_bonus": ev.favorite_color_bonus,
        "event_ts": ev.event_ts,
    }
    return json.dumps(payload, separators=(",", ":"))


def game_events_to_rows(events: list[GameEvent]) -> list[dict]:
    """``GameEvent`` → single-column Iceberg rows (JSON string under ``BRONZE_EVENT_JSON_COLUMN``)."""
    col = BRONZE_EVENT_JSON_COLUMN
    return [{col: game_event_to_json_line(ev)} for ev in events]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load raw balloon_game_events into Glue Iceberg (single bronze table for CLD + DT)."
    )
    parser.add_argument(
        "--dataset",
        choices=("seed", "more"),
        default="seed",
        help="Dataset variant: shifts RNG seed and clock anchor for a second append wave.",
    )
    vol = parser.add_mutually_exclusive_group()
    vol.add_argument(
        "--row-count",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Simulate exactly N GameEvents (raw rows). Uses BRONZE_SAMPLE_ROW_COUNT when set "
            f"without this flag; default {DEFAULT_ROW_COUNT}. Mutually exclusive with "
            f"--duration-minutes. Max {MAX_ROW_COUNT}."
        ),
    )
    vol.add_argument(
        "--duration-minutes",
        type=float,
        default=None,
        metavar="M",
        help=(
            "Simulate pops for M minutes at DELAY/BRONZE_GENERATOR_DELAY seconds per pop "
            f"(Kafka producer rate). Default when neither flag nor BRONZE_SAMPLE_ROW_COUNT: "
            f"{DEFAULT_DURATION_MINUTES} min (or BRONZE_LOAD_DURATION_MINUTES)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = resolve_event_batch_plan(
        dataset=args.dataset,
        row_count_cli=args.row_count,
        duration_cli=args.duration_minutes,
    )

    derive_bronze_resource_names()
    apply_bronze_from_aws_config()
    warehouse = resolve_bronze_warehouse()
    assert_bronze_warehouse_bucket_exists(os.environ["BRONZE_BUCKET_NAME"])
    try:
        db = resolve_glue_database()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    catalog = open_catalog(warehouse)
    ensure_ns(catalog, db)

    events = simulate_game_events(plan)
    row_list = game_events_to_rows(events)
    schema = schema_balloon_game_events()

    if plan.mode == "synthetic":
        print(
            f"info: {plan.mode} mode — {plan.n_events} GameEvent(s) → {BRONZE_RAW_EVENTS_TABLE} "
            f"(dataset={args.dataset!r})",
            flush=True,
        )
        summary = f"events={plan.n_events}, mode=synthetic"
    else:
        print(
            f"info: {plan.mode} mode — {plan.n_events} GameEvent(s) (~{plan.n_events * plan.delay_sec / 60:.2f} min "
            f"timeline at {plan.delay_sec:g}s/pop) → {BRONZE_RAW_EVENTS_TABLE} (dataset={args.dataset!r})",
            flush=True,
        )
        summary = f"events={plan.n_events}, delay_sec={plan.delay_sec:g}, mode=generator"

    t0 = time.perf_counter()
    ensure_table(catalog, db, BRONZE_RAW_EVENTS_TABLE, schema)
    append_rows(
        catalog,
        db,
        BRONZE_RAW_EVENTS_TABLE,
        iceberg_rows_to_pa_table(schema, row_list),
    )
    elapsed = time.perf_counter() - t0
    n = len(row_list)
    print(f"info: {db}.{BRONZE_RAW_EVENTS_TABLE}: loaded {n} row(s) in {elapsed:.3f}s", flush=True)

    print(
        f"OK: dataset {args.dataset!r}, {summary} — Glue database {db!r}, warehouse {warehouse!r}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
