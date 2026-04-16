# Streamlit in Snowflake (SiS) — balloon lab

Source for a **warehouse-runtime** [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview) app that reads **silver Dynamic Iceberg Tables** (`dt_*`) produced by `task dt:generate-sql`.

| File | Purpose |
|------|---------|
| `snowflake.yml` | Snowflake CLI project for **`snow streamlit deploy`**. Top-level **`env:`** holds **`SNOWFLAKE_SILVER_DATABASE`** / **`SNOWFLAKE_SILVER_SCHEMA`** (read at runtime from the staged copy — see **`silver_config.py`**). |
| `streamlit_app.py` | Entrypoint: **`st.navigation`**, loads **`data.ensure_loaded()`**, then multipage **`app_pages/`**. |
| `silver_config.py` | Resolves silver database + schema from staged **`snowflake.yml`** `env` (**`SNOWFLAKE_SILVER_DATABASE`** / **`SNOWFLAKE_SILVER_SCHEMA`** — same names as OS env and `task dt:*`). |
| `data.py` | Snowpark **`get_active_session()`** loaders into **`st.session_state`** for the pages. |
| `colors.py` | Altair color scale (same palette as **`packages/dashboard`**). |
| `app_pages/*.py` | **Home**, **Leaderboard**, **Color Analysis**, **Performance Trends** (ported from the local dashboard). |
| `environment.yml` | Conda deps: Streamlit, Snowpark, Altair, pandas ([dependency management](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management)). |
| `deploy_streamlit_example.sql` | Optional manual path: commented `CREATE STAGE` / `CREATE STREAMLIT` / `ALTER … LIVE` / `GRANT` template. |

## Deploy (recommended): Snowflake CLI

Requires [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation) **3.14+** (uses current `CREATE STREAMLIT … FROM @stage` flow; use **`--legacy`** only if your account still requires the old syntax).

1. Complete **CLD + DT** lab steps so `dt_player_leaderboard` (and siblings) exist and have refreshed at least once.
2. Point your **`snow`** connection at the database and schema where the Streamlit object should live (for example **`balloon_silver`**, schema **`apps`**). Create the schema once if needed: `CREATE SCHEMA IF NOT EXISTS balloon_silver.apps;`
3. From the **repo root**, deploy (uploads artifacts to the stage named in `snowflake.yml`, creates or replaces the Streamlit object):

   ```bash
   snow streamlit deploy balloon_game_dashboard --project snowflake/sis --replace
   ```

   Convenience wrapper (forwards extra flags after `--`):

   ```bash
   task snowflake:sis-deploy -- --open --warehouse COMPUTE_WH
   ```

   See **`snow streamlit deploy --help`** for **`--connection`**, **`--database`**, **`--schema`**, **`--warehouse`**, **`--prune`**, etc.

4. If viewers with **`USAGE`** still cannot open the app, run **`ALTER STREAMLIT … ADD LIVE VERSION FROM LAST`** once (see [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit) usage notes and [`deploy_streamlit_example.sql`](deploy_streamlit_example.sql)).

5. **Grant** `USAGE` on the Streamlit object (and ensure the role can `SELECT` the underlying `dt_*` tables).

## Deploy (optional): manual stage + SQL

1. In Snowflake, pick a schema (e.g. `balloon_silver.apps`) and create an **internal named stage** for app files.
2. **Upload** the full app tree (match **`snowflake.yml`** **`artifacts`**: `streamlit_app.py`, `environment.yml`, `snowflake.yml`, `silver_config.py`, `colors.py`, `data.py`, **`app_pages/`** — or use **`snow streamlit deploy`**).
3. Run **`CREATE STREAMLIT`** with `FROM @…`, `MAIN_FILE = 'streamlit_app.py'`, and **`QUERY_WAREHOUSE`** — see [`deploy_streamlit_example.sql`](deploy_streamlit_example.sql) and [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit).
4. **Activate** the live version (`ALTER STREAMLIT … ADD LIVE VERSION FROM LAST` or Snowsight).
5. **Grant** `USAGE` on the Streamlit object (and ensure the role can `SELECT` the underlying `dt_*` tables).

Narrative and privileges checklist: **[lab/snowflake-streamlit-sis.md](../../lab/snowflake-streamlit-sis.md)**.

## Optional later

Exploratory **Snowflake Notebooks** with Streamlit chart cells are **not** required for this path; they can be added later for authoring / ad hoc queries ([visualize in Notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-visualize-data)).

## Local Streamlit (not the lab outcome)

The **`packages/dashboard/`** app targets local PyIceberg / legacy layouts. For this Snowflake-first lab, treat **`task dashboard-local`** as optional developer tooling only — see root `README.md`.
