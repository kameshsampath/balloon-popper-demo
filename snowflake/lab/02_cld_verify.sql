-- Step 4 — Catalog-linked database (CLD) using the catalog integration above
-- Syntax: https://docs.snowflake.com/en/sql-reference/sql/create-database-catalog-linked
-- Guide: https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog-linked-database

-- CREATE OR REPLACE DATABASE balloon_game_events
--   COMMENT = 'CLD: Glue bronze Iceberg (lab name matches raw table)'
--   LINKED_CATALOG = (
--     CATALOG = 'glue_rest_catalog_int'
--   );

-- Step 5 — Sync and object discovery (wait a short interval after CREATE DATABASE if needed)
-- SELECT SYSTEM$CATALOG_LINK_STATUS('balloon_game_events');

-- Step 6 — List remote namespaces as schemas and Iceberg tables
-- USE DATABASE balloon_game_events;
-- SHOW SCHEMAS IN DATABASE balloon_game_events;
-- SHOW ICEBERG TABLES IN SCHEMA balloon_game_events."<lowercase_glue_database_name>";

-- Glue identifiers are case-sensitive in CLD: use lowercase with double quotes for database/schema/table names
-- when your Glue names are lowercase (see Snowflake CLD identifier requirements).

-- Step 7 — Sample read (bronze raw JSON column `event`)
-- SELECT event
-- FROM balloon_game_events."<glue_database_name>"."balloon_game_events"
-- LIMIT 10;

-- Optional: project JSON in Snowflake
-- SELECT
--   PARSE_JSON(event):player::STRING       AS player,
--   PARSE_JSON(event):event_ts::TIMESTAMP_TZ AS event_ts
-- FROM balloon_game_events."<glue_database_name>"."balloon_game_events"
-- LIMIT 10;
