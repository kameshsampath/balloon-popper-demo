-- Example scaffold: Streamlit in Snowflake (warehouse runtime) from an internal stage.
-- Replace identifiers (database, schema, stage, role, warehouse, streamlit name) for your account.
-- Canonical syntax: https://docs.snowflake.com/en/sql-reference/sql/create-streamlit
-- Getting started: https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview
--
-- Prefer Snowflake CLI when you can (upload + CREATE in one step):
--   snow streamlit deploy balloon_game_dashboard --project snowflake/sis --replace
--   https://docs.snowflake.com/en/developer-guide/snowflake-cli/command-reference/streamlit-commands/deploy
--   https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/create-streamlit-snowflake-cli

-- 1) Schema + stage to hold uploaded app files (streamlit_app.py, environment.yml)
-- CREATE SCHEMA IF NOT EXISTS balloon_silver.apps;
-- CREATE STAGE IF NOT EXISTS balloon_silver.apps.dashboard_src;

-- 2) Upload from your workstation (Snowflake CLI examples; paths relative to repo root):
--    snow connection set-default --connection <your_connection>
--    snow stage copy snowflake/sis/streamlit_app.py @balloon_silver.apps.dashboard_src/
--    snow stage copy snowflake/sis/environment.yml @balloon_silver.apps.dashboard_src/

-- 3) Create the Streamlit object (files are copied at CREATE time; re-upload + OR REPLACE to update)
-- CREATE OR REPLACE STREAMLIT balloon_silver.apps.balloon_game_dashboard
--   FROM @balloon_silver.apps.dashboard_src
--   MAIN_FILE = 'streamlit_app.py'
--   QUERY_WAREHOUSE = COMPUTE_WH
--   TITLE = 'Balloon pops — silver';

-- 4) Go live (required after CREATE): see "Usage notes" in CREATE STREAMLIT docs.
-- ALTER STREAMLIT balloon_silver.apps.balloon_game_dashboard ADD LIVE VERSION FROM LAST;

-- 5) Grants — readers need USAGE on the Streamlit object and underlying SELECT on silver tables / DTs.
-- GRANT USAGE ON STREAMLIT balloon_silver.apps.balloon_game_dashboard TO ROLE <analyst_role>;
