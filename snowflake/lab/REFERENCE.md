# Reference: legacy RisingWave → Snowflake DT porting

Use this when authoring `snowflake/lab/*.sql` and the sfguide Phase 3 body. **Do not** run RisingWave in the new lab; this file captures **semantic parity** only.

## Iceberg identifiers (bronze)

**This lab (Glue + `load-bronze-sample`):** one raw table, aligned with [source.sql.j2](../../polaris-forge-setup/templates/source.sql.j2):

| Glue database (example) | Raw table |
|-------------------------|-----------|
| Typically `balloon_pops` in docs | `balloon_game_events` |

**Legacy RisingWave sinks** (semantic targets for Snowflake DT SQL, not created by the bronze loader): [sink.sql.j2](../../polaris-forge-setup/templates/sink.sql.j2) — `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends`.

Historical per-table schema notes: [docs/iceberg_schema_design.md](../../docs/iceberg_schema_design.md).

## Raw stream (Kafka) → bronze fact

RisingWave [source.sql.j2](../../polaris-forge-setup/templates/source.sql.j2) declares typed columns for `balloon_game_events`. The **bronze loader** instead stores **one JSON object per row** in Iceberg string column **`event`** (Kafka **FORMAT PLAIN ENCODE JSON** style), with keys `player`, `balloon_color`, `score`, `page_id`, `favorite_color_bonus`, `event_ts` (ISO-8601 string). That matches how many streams deliver payloads before a warehouse extracts fields.

## Dynamic Iceberg Tables: JSON extraction (Snowflake)

In Snowflake, treat each row’s payload as semi-structured JSON, then write DT `AS SELECT` bodies that mirror the MVs. Use documented JSON functions and casting—for example [`PARSE_JSON`](https://docs.snowflake.com/en/sql-reference/functions/parse_json) and [`VARIANT` / dot/bracket paths](https://docs.snowflake.com/en/sql-reference/data-types-semistructured)—so DT SQL stays aligned with [source.sql.j2](../../polaris-forge-setup/templates/source.sql.j2) while the Iceberg bronze table stays a narrow **blob + catalog** shape.

Illustrative fragments (replace catalog/database/table identifiers with your CLD names; validate types against your integration):

```sql
-- v: one VARIANT per source row (column name matches tools/bronze_preload/bronze_tables.py)
WITH src AS (
  SELECT PARSE_JSON(event) AS v
  FROM linked_db.public.balloon_game_events
)
SELECT
  v:player::STRING            AS player,
  v:score::INTEGER            AS score,
  v:favorite_color_bonus::BOOLEAN AS favorite_color_bonus,
  v:event_ts::TIMESTAMP_TZ    AS event_ts
FROM src;
```

Windowed MVs (`TUMBLE` / 15s) map to Snowflake time-windowing in DT definitions (for example `TIME_SLICE` / `DATE_TRUNC` patterns appropriate to your refresh cadence—confirm against current [Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about) and SQL windowing docs rather than copying RisingWave `TUMBLE` verbatim).

## Materialized view → proposed Dynamic Iceberg Table

| Legacy MV (`source.sql.j2`) | Role | Notes for Snowflake DT `AS SELECT` |
|-----------------------------|------|-----------------------------------|
| `mv_leaderboard` | Per-player totals | From `PARSE_JSON(event)`: `GROUP BY v:player`; `SUM(v:score::INTEGER)`, `COUNT_IF(v:favorite_color_bonus::BOOLEAN)`, `MAX(v:event_ts::TIMESTAMP_TZ)` |
| `mv_balloon_color_stats` | Per player × color | `GROUP BY v:player`, `v:balloon_color::STRING` |
| `mv_realtime_scores` | 15s tumble window | Same JSON casts, then a 15-second grid on `event_ts` per Snowflake time-bucketing docs |
| `mv_balloon_colored_pops` | Pops per window × color | Same window semantics + color dimensions |
| `mv_color_performance_trends` | Color effectiveness in window | `GROUP BY v:balloon_color::STRING`, window bounds |

Full SQL: always diff against the template on disk before deleting `polaris-forge-setup/`.
