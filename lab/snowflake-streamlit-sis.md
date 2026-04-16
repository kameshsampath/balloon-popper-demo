# Snowflake: Streamlit in Snowflake (SiS) over silver DTs

This chapter is the **visualization step** after [Dynamic Iceberg Tables](snowflake-dynamic-iceberg-tables.md) and [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md). You ship a **Streamlit in Snowflake** object that queries **`balloon_silver.silver.dt_*`** (or your overrides) using **`get_active_session()`** — no local Streamlit server required for the lab outcome.

Use [docs.snowflake.com](https://docs.snowflake.com) as the source of truth: [Getting started with Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview), [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit), [Manage dependencies](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management).

## Prerequisites

- **DTs live and readable:** `03_dt_pipelines` applied; `SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA` lists the five `dt_*` objects; your role can `SELECT` them (see [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql)).
- **Silver DT location:** edit **`snowflake/sis/snowflake.yml`** top-level **`env:`** keys **`SILVER_DB`** and **`SILVER_SCHEMA`** so they match **`SNOWFLAKE_SILVER_DATABASE`** / **`SNOWFLAKE_SILVER_SCHEMA`** used with **`task dt:generate-sql`**, then redeploy. The staged **`snowflake.yml`** is parsed at runtime (**`silver_config.py`**). Optional OS overrides **`SILVER_DB`** / **`SILVER_SCHEMA`** apply if your environment sets them in the warehouse runtime.
- **Privileges:** role used to **create** the Streamlit object: **`CREATE STREAMLIT`** on the target schema, **`READ`** on the internal stage used for `FROM @…`, **`USAGE`** on **`QUERY_WAREHOUSE`**. Roles that **run** the app need **`USAGE`** on the Streamlit object and **`SELECT`** on the underlying tables (see access matrix in [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit)).
- **Snowflake CLI:** [Install](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation) **3.14+** for **`snow streamlit deploy`** ([command reference](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/streamlit-commands/deploy), [create with CLI](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/create-streamlit-snowflake-cli)).

## 1. Deploy with Snowflake CLI (recommended)

1. Ensure your **`snow`** connection’s **database** and **schema** are where you want the Streamlit object (for example **`balloon_silver`** / **`sis`**), or pass **`--database`** / **`--schema`** on the command. Create the schema once if needed, for example: `CREATE SCHEMA IF NOT EXISTS balloon_silver.sis;`
2. From **repo root**, using **`snowflake/sis/snowflake.yml`**:

   ```bash
   snow streamlit deploy balloon_game_dashboard --project snowflake/sis --replace
   ```

   Optional: open in a browser after deploy: add **`--open`**. Override warehouse: **`--warehouse YOUR_WH`** (must match a warehouse your role can use).

   Repo shortcut (forwards flags after **`--`**):

   ```bash
   task snowflake:sis-deploy -- --open
   ```

3. If needed for your account, promote the version users see: **`ALTER STREAMLIT … ADD LIVE VERSION FROM LAST`** (see [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit) and **[snowflake/sis/deploy_streamlit_example.sql](../snowflake/sis/deploy_streamlit_example.sql)**).

## 2. Open and share

Open the app in **Snowsight** (or your org’s supported entry point), then **`GRANT USAGE`** on the Streamlit object to analyst roles as needed.

## 3. Optional — manual stage + SQL

Instead of the CLI, you can **`snow stage copy`** (or Snowsight) and run **`CREATE STREAMLIT`** from a stage using the commented template **[snowflake/sis/deploy_streamlit_example.sql](../snowflake/sis/deploy_streamlit_example.sql)**. See **[snowflake/sis/README.md](../snowflake/sis/README.md)** for the full checklist.

## Optional later — Snowflake Notebooks

**Not required** for this lab path: you can add a **Snowflake Notebook** later to prototype SQL and use supported **Streamlit chart elements** in cells ([Visualize data in Snowflake Notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-visualize-data), [Streamlit in notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-use-with-snowflake)). Keep the **SiS app** as the durable dashboard you hand to learners.

## Related

- [snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md) — silver DT generation and apply
- [snowflake/sis/README.md](../snowflake/sis/README.md) — file layout, **`snowflake.yml`**, deploy outline
- [snowflake/lab/README.md](../snowflake/lab/README.md) — SQL lab index
