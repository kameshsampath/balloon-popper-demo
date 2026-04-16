# Streamlit in Snowflake (SiS) — balloon lab

Source for a **warehouse-runtime** [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview) app that reads **silver Dynamic Iceberg Tables** (`dt_*`) produced by `task dt:generate-sql`.

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Entrypoint: `get_active_session()`, queries `balloon_silver.silver.dt_*`. |
| `environment.yml` | Anaconda channel dependencies for warehouse runtime ([dependency management](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/dependency-management)). |
| `deploy_streamlit_example.sql` | Commented `CREATE STAGE` / `CREATE STREAMLIT` / `ALTER … LIVE` / `GRANT` template. |

## Deploy (outline)

1. Complete **CLD + DT** lab steps so `dt_player_leaderboard` (and siblings) exist and have refreshed at least once.
2. In Snowflake, pick a schema (e.g. `balloon_silver.sis`) and create an **internal named stage** for app files.
3. **Upload** `streamlit_app.py` and `environment.yml` to that stage (`snow stage copy …` with [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/stage-commands/overview), or Snowsight).
4. Run **`CREATE STREAMLIT`** with `FROM @…`, `MAIN_FILE = 'streamlit_app.py'`, and **`QUERY_WAREHOUSE`** — see [`deploy_streamlit_example.sql`](deploy_streamlit_example.sql) and [CREATE STREAMLIT](https://docs.snowflake.com/en/sql-reference/sql/create-streamlit).
5. **Activate** the live version (`ALTER STREAMLIT … ADD LIVE VERSION FROM LAST` or open in Snowsight per docs).
6. **Grant** `USAGE` on the Streamlit object (and ensure the role can `SELECT` the underlying `dt_*` tables).

Narrative and privileges checklist: **[lab/snowflake-streamlit-sis.md](../../lab/snowflake-streamlit-sis.md)**.

## Optional later

Exploratory **Snowflake Notebooks** with Streamlit chart cells are **not** required for this path; they can be added later for authoring / ad hoc queries ([visualize in Notebooks](https://docs.snowflake.com/en/user-guide/ui-snowsight/notebooks-visualize-data)).

## Local Streamlit (not the lab outcome)

The **`packages/dashboard/`** app targets local PyIceberg / legacy layouts. For this Snowflake-first lab, treat **`task dashboard-local`** as optional developer tooling only — see root `README.md`.
