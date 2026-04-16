# Manual test plan — Dynamic Iceberg Tables (silver)

Use after [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) passes. Full narrative: [snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md).

**Order:** configure env (**[snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md) §1**) → **Phase A (silver external volume)** → **Phase B (DT SQL and apply)** so `03_dt_pipelines.generated.sql` has a real `EXTERNAL_VOLUME` and storage is ready.

**Defaults in this doc:** silver database **`balloon_silver`**, schema **`silver`** (override if you set `SNOWFLAKE_SILVER_DATABASE` / `SNOWFLAKE_SILVER_SCHEMA`). **Sample queries:** checked-in script [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql) — run with `snow sql --filename snowflake/lab/04_dt_verify_sample_queries.sql` after DTs have had time to refresh ([Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-about) monitoring in Snowflake docs).

## Preconditions (both phases)

- [ ] CLD reads work per [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) (bronze `balloon_game_events` visible through the linked database).
- [ ] `.aws-config/glue-database.json` present (same artifact **`task dt:generate-sql`** uses for Glue identifier quoting).
- [ ] Valid **AWS** session and **`snow`** connection for [sfutils-extvolumes](https://github.com/Snowflake-Labs/sfutils-extvolumes) when using **`task dt:extvol-*`** ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)).

## Env configuration (do this first)

Align **`.env`** (or exports) with [snowflake-dynamic-iceberg-tables.md §1](snowflake-dynamic-iceberg-tables.md#1-configure-env-vars) **before** Phase A so extvol and `generate-sql` see the same values:

- [ ] **`LAB_USERNAME`** (workshop) and/or **`SILVER_EXTVOLUME_BUCKET_SLUG`** / **`SILVER_EXTVOLUME_PREFIX`** (solo or overrides) — drives **`task dt:extvol-*`** resolution.
- [ ] **`SNOWFLAKE_SILVER_DATABASE`**, **`SNOWFLAKE_SILVER_SCHEMA`**, **`SNOWFLAKE_WAREHOUSE`**, **`SNOWFLAKE_DT_PATH_PREFIX`** — match what you want in generated `03` SQL (defaults in the narrative).
- [ ] **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** — set **after** Phase A if you create a new volume; required before a real **`task dt:generate-sql`** run.

```bash
task snowflake:print-env-hints
```

## Phase A — Silver external volume (before DT)

Use a **silver-only** bucket slug for **`sfutils-extvolumes --bucket`** — not **`BRONZE_BUCKET_NAME`**. Set **`SILVER_EXTVOLUME_BUCKET_SLUG`** in `.env` or inline for solo runs. See **`task dt:extvol-create-help`** and **`task dt:extvol-help`**.

### A1. Preview create (dry run)

Workshop (**`LAB_USERNAME`** already set for bronze): `task dt:extvol-create-dry-run` (resolver uses base **`balloon-silver`** + **`--prefix`** matching **`<bucket_slug>`** in **`BRONZE_BUCKET_NAME`**).

Solo or custom slug: `SILVER_EXTVOLUME_BUCKET_SLUG=<your-silver-slug> task dt:extvol-create-dry-run`

**Pass:** Command exits 0; output lists intended bucket / IAM / Snowflake volume names with no AWS or Snowflake mutations.

### A2. Create volume (or skip if you already have one)

`task dt:extvol-create -- --output json` (workshop) or `SILVER_EXTVOLUME_BUCKET_SLUG=<your-silver-slug> task dt:extvol-create -- --output json`

(Adjust flags after `--` as needed, e.g. `--no-writes` per org policy.)

**Pass:** S3 bucket, IAM role/policy, and Snowflake **external volume** exist; CLI finishes verification unless you passed **`--skip-verify`**.

### A3. Record env and verify

- Set **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** to the Snowflake volume object name (from CLI text or JSON).
- `SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME=<name> task dt:extvol-verify`

**Pass:** Verify exits 0. Your Snowflake role has **`USAGE`** on that external volume and on the warehouse you will use in generated DT SQL (default **`COMPUTE_WH`** or **`SNOWFLAKE_WAREHOUSE`**).

**Alternative:** If you created the volume outside this repo, still complete **A3** (name + **`USAGE`** + **`task dt:extvol-verify`** when the volume was created with sfutils-extvolumes).

## Phase B — Dynamic Iceberg Tables

### B1. Generate DT SQL

`task dt:generate-sql`

**Pass:** `snowflake/lab/generated/03_dt_pipelines.generated.sql` exists; **`EXTERNAL_VOLUME`** matches **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** (not `REPLACE_ME_ICEBERG_EXTERNAL_VOLUME` unless you intend to edit the file); the bronze table FQN inside the file matches your CLD (`<linked_db>."<glue_db_lower>"."balloon_game_events"`).

### B2. Apply DT SQL

`snow sql --filename snowflake/lab/generated/03_dt_pipelines.generated.sql`

**Pass:** five `CREATE OR REPLACE DYNAMIC ICEBERG TABLE` statements complete without authorization or volume errors.

### B3. Discovery

```sql
USE DATABASE balloon_silver;
USE SCHEMA silver;
SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA;
```

**Pass:** five rows: `dt_player_leaderboard`, `dt_balloon_color_stats`, `dt_realtime_scores`, `dt_balloon_colored_pops`, `dt_color_performance_trends`. If state is not yet active, wait for `TARGET_LAG` refresh per Snowflake docs, then re-check.

### B4. Sample reads (per table)

Run the bundled script (recommended), or paste blocks below.

**B4a — Leaderboard**

```sql
SELECT player, total_score, bonus_pops, last_event_ts
FROM balloon_silver.silver.dt_player_leaderboard
ORDER BY total_score DESC NULLS LAST
LIMIT 15;
```

**Pass:** One row per `player` from bronze; `total_score` / `bonus_pops` non-null where bronze had data; `last_event_ts` is the max event time for that player.

**B4b — Per player × color**

```sql
SELECT player, balloon_color, balloon_pops, points_by_color, bonus_hits, last_event_ts
FROM balloon_silver.silver.dt_balloon_color_stats
ORDER BY player, points_by_color DESC NULLS LAST
LIMIT 20;
```

**Pass:** `(player, balloon_color)` unique; counts and sums align with intuition from raw pops.

**B4c — 15s window scores**

```sql
SELECT player, total_score, window_start, window_end
FROM balloon_silver.silver.dt_realtime_scores
ORDER BY window_start DESC, player
LIMIT 20;
```

**Pass:** `window_end` equals `DATEADD(second, 15, window_start)` for each row; multiple players can share the same `window_start`.

**B4d — Windowed pops by color**

```sql
SELECT player, balloon_color, balloon_pops, window_start, window_end
FROM balloon_silver.silver.dt_balloon_colored_pops
ORDER BY window_start DESC, player, balloon_color
LIMIT 20;
```

**Pass:** Same 15s window semantics as **B4c**; dimensions include color.

**B4e — Color performance by window**

```sql
SELECT balloon_color, avg_score_per_pop, total_pops, window_start, window_end
FROM balloon_silver.silver.dt_color_performance_trends
ORDER BY window_start DESC, balloon_color
LIMIT 20;
```

**Pass:** `avg_score_per_pop` is a finite average; `total_pops` ≥ 1 for populated windows.

### B5. Window span sanity (all windowed DTs)

```sql
SELECT
  'dt_realtime_scores' AS tbl,
  COUNT_IF(window_end <> DATEADD(second, 15, window_start)) AS bad_spans
FROM balloon_silver.silver.dt_realtime_scores
UNION ALL
SELECT 'dt_balloon_colored_pops', COUNT_IF(window_end <> DATEADD(second, 15, window_start))
FROM balloon_silver.silver.dt_balloon_colored_pops
UNION ALL
SELECT 'dt_color_performance_trends', COUNT_IF(window_end <> DATEADD(second, 15, window_start))
FROM balloon_silver.silver.dt_color_performance_trends;
```

**Pass:** `bad_spans = 0` for all three (empty tables yield 0 rows — then skip or load more bronze first).

### B6. Optional — bronze parity (leaderboard row count)

Edit the FQN to match your catalog-linked database and **lowercase** Glue schema (same as `02_cld_verify` / `SHOW SCHEMAS`).

```sql
SELECT
  (SELECT COUNT(*) FROM balloon_silver.silver.dt_player_leaderboard) AS dt_players,
  (
    SELECT COUNT(DISTINCT PARSE_JSON(event):player::STRING)
    FROM balloon_game_events."<glue_db_lower>"."balloon_game_events"
  ) AS bronze_distinct_players;
```

**Pass (steady state):** `dt_players = bronze_distinct_players` when every distinct player has at least one event in bronze. If DT is still refreshing, retry after a short wait.

### B7. One-shot script

From repo root:

```bash
snow sql --connection <your_connection> --filename snowflake/lab/04_dt_verify_sample_queries.sql
```

Edit **`04_dt_verify_sample_queries.sql`** `USE DATABASE` / `USE SCHEMA` if you overrode defaults. Uncomment and fix the optional bronze block at the bottom for parity.

## Next — Streamlit in Snowflake

After DTs refresh and verify queries pass, see **[snowflake-streamlit-sis.md](snowflake-streamlit-sis.md)** to deploy with **`snow streamlit deploy`** (or stage + **`CREATE STREAMLIT`**) so the SiS app reads **`balloon_silver.silver.dt_*`**, then go **live** if your account requires it.

## Failure notes

- **External volume / IAM:** **`task dt:extvol-update-trust`** if trust drifted; see [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md) and Snowflake [CREATE EXTERNAL VOLUME](https://docs.snowflake.com/en/sql-reference/sql/create-external-volume).
- **Warehouse:** grant `USAGE` on the warehouse named in the generated `03` script (default `COMPUTE_WH` or `SNOWFLAKE_WAREHOUSE`).
- **Empty windowed DTs:** ensure bronze load has events spanning more than one 15-second bucket, or widen the time range in bronze load; otherwise window aggregates may be empty even when leaderboard has rows.
