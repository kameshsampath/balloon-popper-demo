# Snowflake: Dynamic Iceberg Tables (silver over CLD)

This chapter is the **next Snowflake hands-on** after [Snowflake CLD](snowflake-catalog-cld.md). You keep **bronze** in Glue (read through the catalog-linked database), then add **Snowflake-managed Dynamic Iceberg Tables** that refresh on a schedule and write **Apache Iceberg** files to storage you control via an **external volume**.

Use current Snowflake documentation as the source of truth: [Create dynamic Apache Iceberg tables](https://docs.snowflake.com/en/user-guide/dynamic-tables-create-iceberg) and [CREATE DYNAMIC ICEBERG TABLE](https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table).

## Prerequisites

- **CLD path complete:** finish **[snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** first — catalog integration, trust, linked DB, and reads on **`balloon_game_events`** (or your `SNOWFLAKE_LINKED_DATABASE_NAME`) before you generate or apply **§3** DT SQL. Quick narrative: [snowflake-catalog-cld.md](snowflake-catalog-cld.md).
- **Configure then volume:** align env vars with **[§1](#1-configure-env-vars)** first, then complete **[§2](#2-silver-external-volume-do-this-before-dt-sql)** (or an equivalent manual setup) so **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** is set **before** **`task dt:generate-sql`**. Generated SQL uses `EXTERNAL_VOLUME`, `CATALOG = 'SNOWFLAKE'`, and `BASE_LOCATION` per Snowflake’s examples. Patterns for Glue + `ALLOW_WRITES = FALSE` and dual external IDs are in [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md); align storage URLs with your org.
- **Privileges:** role can `CREATE DATABASE` / `CREATE SCHEMA` (or use an existing silver database), `CREATE DYNAMIC ICEBERG TABLE`, `USAGE` on the **warehouse** and **external volume**, and **read** the CLD Iceberg table used in the `AS SELECT`.
- **Tooling:** `snow sql` from a working connection ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)); **`.aws-config/glue-database.json`** after **`task bronze:glue-setup`** (same input as CLD SQL generation).

## 1. Configure env vars

Raw rows in bronze live in **`balloon_game_events.event`** as a JSON string. **`task dt:generate-sql`** emits **five** Dynamic Iceberg Tables matching the legacy RisingWave MVs (`mv_leaderboard`, `mv_balloon_color_stats`, `mv_realtime_scores`, `mv_balloon_colored_pops`, `mv_color_performance_trends` — see **`docs/implementing_data_pipeline.md`** and [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md)).

Set or export the variables you need **before** **[§2](#2-silver-external-volume-do-this-before-dt-sql)** (extvol tasks read **`LAB_USERNAME`**, **`SILVER_EXTVOLUME_BUCKET_SLUG`**, **`SILVER_EXTVOLUME_PREFIX`**) and **before** **`task dt:generate-sql`** (generator reads **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`**, silver DB/schema, warehouse, path prefix). After **`task dt:extvol-create`**, copy the Snowflake volume name into **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** if you did not already have one.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SILVER_EXTVOLUME_BUCKET_SLUG` | *(none)* | Short fragment for **`sfutils-extvolumes --bucket`** (not the full S3 name; sfutils adds a prefix). If unset and **`LAB_USERNAME`** is set, resolver uses **`balloon-silver`** + **`--prefix`** = **`sanitize_lab_slug_bucket(LAB_USERNAME)`**. |
| `SILVER_EXTVOLUME_PREFIX` | *(none)* | When the bucket slug is the **`LAB_USERNAME`** default, optional **`--prefix`** override instead of the derived 24-char slug. |
| `SNOWFLAKE_SILVER_DATABASE` | `balloon_silver` | Native database for DT objects (not the CLD name). |
| `SNOWFLAKE_SILVER_SCHEMA` | `silver` | Schema for all silver DTs. |
| `SNOWFLAKE_WAREHOUSE` | `COMPUTE_WH` | Warehouse for refresh compute. |
| `SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME` | *(none)* | **Required for a real run** — external volume name (from **`task dt:extvol-create`** output once §2 is done, unless you reuse an existing volume). |
| `SNOWFLAKE_DT_PATH_PREFIX` | `balloon_lab` | Prefix for each table’s `BASE_LOCATION` under the volume (`<prefix>/dt_<name>`). |

Print hints (CLD + DT env reminders):

```bash
task snowflake:print-env-hints
```

## 2. Silver external volume (do this before DT SQL)

**Yes —** Dynamic Iceberg Tables in this lab declare **`EXTERNAL_VOLUME`** and **`BASE_LOCATION`**, so Snowflake writes silver Iceberg files to **your** cloud storage behind that volume. You still run **`CREATE EXTERNAL VOLUME`** / **`GRANT USAGE ON EXTERNAL VOLUME`** in Snowflake (per [CREATE EXTERNAL VOLUME](https://docs.snowflake.com/en/sql-reference/sql/create-external-volume)); on AWS you need an **S3 bucket (or prefix)** and an **IAM role** whose trust and permissions match what **`DESC EXTERNAL VOLUME`** / Snowflake docs require.

The repo already ships **[Snowflake-Labs/sfutils-extvolumes](https://github.com/Snowflake-Labs/sfutils-extvolumes)** as a dependency (**`uv sync`** → **`.venv/bin`**). That toolkit is meant for exactly this loop: drive **`snow sql`** against Snowflake, then render or apply **IAM** aligned with external volume / storage integration outputs — the same *style* as **`task snowflake:render-glue-catalog-trust`** (catalog trust) but for **volume** storage credentials.

**Practical guidance**

- Prefer **sfutils-extvolumes** when you want automation for **S3 + IAM + Snowflake external volume** setup for the **silver** Iceberg landing zone, instead of hand-building trust JSON and bucket policy in the console.
- Keep the **bronze** warehouse bucket (Glue / vended reads) **logically separate** from the **silver DT** prefix when you can: different buckets or at least distinct prefixes under an external volume reduce accidental overwrites and simplifies teardown.
- If you already followed **[cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md)** for catalog + volume on one role, reuse that volume for DTs **only** if the storage layout and `ALLOW_WRITES` / permissions still match what Dynamic Iceberg Tables need; otherwise create a volume dedicated to silver outputs.
- After any volume exists, set **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** to the Snowflake object name (see **§1** if you are updating **`.env`**) and run **`task dt:generate-sql`** (**§3**).

```bash
# After uv sync — same CLI as below; Task wrappers set bucket / volume from env:
task dt:extvol-help
task dt:extvol-create-help

# Workshop (same LAB_USERNAME as bronze): bucket base defaults to balloon-silver + lab slug prefix:
task dt:extvol-create-dry-run
# Solo: set a silver-only base; sfutils uses OS username prefix unless you pass --prefix after --:
SILVER_EXTVOLUME_BUCKET_SLUG=myname-balloon-silver task dt:extvol-create-dry-run
SILVER_EXTVOLUME_BUCKET_SLUG=myname-balloon-silver task dt:extvol-create -- --output json

# After you know the Snowflake volume name:
SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME=MY_VOLUME task dt:extvol-verify
```

## 3. Generate SQL (DT namespace)

Do **not** start here until **[snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** passes — DT SQL reads bronze through the catalog-linked database, and **`task dt:generate-sql`** uses **`.aws-config/glue-database.json`** (same artifact as CLD generation). Regenerating **`01`** / **`02`** when your Glue or integration inputs change is covered in [snowflake-catalog-cld.md](snowflake-catalog-cld.md) and [snowflake/lab/README.md](../snowflake/lab/README.md) (**`task snowflake:generate-lab-sql`**); this chapter focuses on **`03`** only.

**Silver pipelines** (writes `snowflake/lab/generated/03_dt_pipelines.generated.sql` — all five DTs):

```bash
task dt:generate-sql
```

If `SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME` is unset, the generator emits **`REPLACE_ME_ICEBERG_EXTERNAL_VOLUME`** and prints a **stderr** warning. Override once:

```bash
uv run snowflake-lab-sql generate --dt-pipelines-only --external-volume my_iceberg_ext_vol
```

**Optional — one-shot** (regenerate **`01`**, **`02`**, and **`03`** together after broader env changes): `task snowflake:generate-lab-sql-all` or `uv run snowflake-lab-sql generate` — see [snowflake/lab/README.md](../snowflake/lab/README.md).

## 4. Apply in Snowflake

```bash
snow sql --connection <your_connection> --filename snowflake/lab/generated/03_dt_pipelines.generated.sql
```

**Pass:** all five `CREATE OR REPLACE DYNAMIC ICEBERG TABLE` statements succeed; `SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA` lists the objects; after refresh, `SELECT` returns rows.

**Common misses:** missing `USAGE` on warehouse or external volume; wrong `EXTERNAL_VOLUME` name; CLD identifiers mis-quoted for Glue; `BASE_LOCATION` collisions — adjust `SNOWFLAKE_DT_PATH_PREFIX` or table names.

## 5. Verify with sample queries (manual test)

After DTs refresh, run read-only checks:

```bash
snow sql --connection <your_connection> --filename snowflake/lab/04_dt_verify_sample_queries.sql
```

Checklist and expected results: [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md).

## 6. Scaffold without generator

Commented pointer: [snowflake/lab/03_dt_pipelines.sql](../snowflake/lab/03_dt_pipelines.sql). Verification samples (checked in): [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql).

## Related

- [snowflake-streamlit-sis.md](snowflake-streamlit-sis.md) — **next:** Streamlit in Snowflake over **`dt_*`**
- [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) — prerequisite QA before DT SQL
- [snowflake-catalog-cld.md](snowflake-catalog-cld.md) — catalog integration and CLD
- [snowflake/lab/README.md](../snowflake/lab/README.md) — `task snowflake:*` and `task dt:*`
- [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) — JSON keys and MV ↔ DT map
- [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md) — short QA checklist
