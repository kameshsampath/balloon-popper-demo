# Snowflake: Streamlit in Snowflake (SiS) over silver DTs

This chapter is the **visualization step** after [Dynamic Iceberg Tables](snowflake-dynamic-iceberg-tables.md) and [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md). You ship a **Streamlit in Snowflake** object that queries **`balloon_silver.silver.dt_*`** (or your overrides) using **`get_active_session()`** — no local Streamlit server required for the lab outcome.

Use [docs.snowflake.com](https://docs.snowflake.com) as the source of truth: [Getting started with Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview), [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit), [Manage dependencies](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management).

## Prerequisites

- **DTs live and readable:** `03_dt_pipelines` applied; `SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA` lists the five `dt_*` objects; your role can `SELECT` them (see [snowflake/lab/04_dt_verify_sample_queries.sql](../snowflake/lab/04_dt_verify_sample_queries.sql)).
- **Identifiers:** checked-in **`snowflake/sis/streamlit_app.py`** defaults to **`balloon_silver`**, **`silver`**. Edit that file before upload if you set **`SNOWFLAKE_SILVER_DATABASE`** / **`SNOWFLAKE_SILVER_SCHEMA`** to different names when generating SQL.
- **Privileges:** role used to **create** the Streamlit object: **`CREATE STREAMLIT`** on the target schema, **`READ`** on the internal stage used for `FROM @…`, **`USAGE`** on **`QUERY_WAREHOUSE`**. Roles that **run** the app need **`USAGE`** on the Streamlit object and **`SELECT`** on the underlying tables (see access matrix in [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit)).

## 1. Stage app files

From the **repo root**, follow **[snowflake/sis/README.md](../snowflake/sis/README.md)** to create a schema + internal stage and **`snow stage copy`** (or Snowsight upload) for:

- **`snowflake/sis/streamlit_app.py`**
- **`snowflake/sis/environment.yml`**

## 2. Create and go live

Use the commented template **[snowflake/sis/deploy_streamlit_example.sql](../snowflake/sis/deploy_streamlit_example.sql)** as a checklist: **`CREATE OR REPLACE STREAMLIT`**, then **`ALTER STREAMLIT … ADD LIVE VERSION FROM LAST`** (or the Snowsight flow documented for your account).

## 3. Open and share

Open the app in **Snowsight** (or your org’s supported entry point), then **`GRANT USAGE`** on the Streamlit object to analyst roles as needed.

## Optional later — Snowflake Notebooks

**Not required** for this lab path: you can add a **Snowflake Notebook** later to prototype SQL and use supported **Streamlit chart elements** in cells ([Visualize data in Snowflake Notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-visualize-data), [Streamlit in notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-use-with-snowflake)). Keep the **SiS app** as the durable dashboard you hand to learners.

## Related

- [snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md) — silver DT generation and apply
- [snowflake/sis/README.md](../snowflake/sis/README.md) — file layout and deploy outline
- [snowflake/lab/README.md](../snowflake/lab/README.md) — SQL lab index
