# Reference: Snowflake Dynamic Iceberg Tables from bronze JSON

Use this when authoring `snowflake/lab/*.sql` and the quickstart Snowflake chapters. It defines the **bronze stream contract** and how **Dynamic Iceberg Tables** can project and aggregate it with Snowflake-documented JSON APIs.

## Iceberg identifiers (bronze)

**Glue + `load-bronze-sample`:** one raw-events table.

| Glue database (example) | Raw table |
|-------------------------|-----------|
| Typically `balloon_pops` in docs | `balloon_game_events` |

Optional historical column layouts (not used by the current bronze loader): [docs/iceberg_schema_design.md](../../docs/iceberg_schema_design.md).

## Bronze `event` JSON (stream contract)

Each Iceberg row has string column **`event`** containing one JSON object (Kafka-style **PLAIN JSON**), with keys:

| Key | Type in JSON | Notes |
|-----|----------------|-------|
| `player` | string | |
| `balloon_color` | string | |
| `score` | number | integer score |
| `page_id` | number | loader uses `0` until a producer sets it |
| `favorite_color_bonus` | boolean | |
| `event_ts` | string | ISO-8601 timestamp |

## Dynamic Iceberg Tables: JSON extraction (Snowflake)

In Snowflake, parse the payload with documented functions—for example [`PARSE_JSON`](https://docs.snowflake.com/en/sql-reference/functions/parse_json) and [`VARIANT` / paths](https://docs.snowflake.com/en/sql-reference/data-types-semistructured)—then build DT `AS SELECT` definitions. Confirm syntax and Iceberg DT rules against current [Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about) documentation.

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

**15-second windows:** express tumbling / fixed windows with Snowflake time functions appropriate to your DT target lag (for example `TIME_SLICE` on `event_ts`); confirm windowing against current SQL docs rather than copying non-Snowflake dialects.

## Aggregate targets → Dynamic Iceberg Table roles

Silver-style tables the lab builds from the raw stream (names are illustrative—match your `CREATE DYNAMIC TABLE` identifiers):

| Lab aggregate / DT role | Purpose | Notes for DT `AS SELECT` |
|-------------------------|---------|---------------------------|
| Per-player leaderboard | Totals and bonus counts | From `PARSE_JSON(event)`: `GROUP BY v:player`; `SUM(v:score::INTEGER)`, `COUNT_IF(v:favorite_color_bonus::BOOLEAN)`, `MAX(v:event_ts::TIMESTAMP_TZ)` |
| Per player × color | Pops and points by color | `GROUP BY v:player`, `v:balloon_color::STRING` |
| Realtime scores (15s window) | Windowed totals | JSON casts, then 15-second time buckets on `event_ts` |
| Balloon colored pops (window) | Pops per window × color | Same window semantics + color dimensions |
| Color performance (window) | Effectiveness by color | `GROUP BY v:balloon_color::STRING`, window bounds |

Keep DT definitions version-controlled next to this file; align column names with **Streamlit in Snowflake** and dashboard queries as you add them.

**IAM trust for Glue Iceberg REST catalog integration:** after `CREATE CATALOG INTEGRATION`, use **`task snowflake:render-glue-catalog-trust`** (see [README.md](README.md)) to materialize the Snowflake **`GLUE_AWS_IAM_USER_ARN`** / **`GLUE_AWS_EXTERNAL_ID`** pair into a trust policy JSON—parallel to how **sfutils-extvolumes** drives **`snow sql`** plus templated IAM for external volumes.
