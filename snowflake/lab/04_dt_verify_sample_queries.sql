-- Read-only checks for silver Dynamic Iceberg Tables (after 03_dt_pipelines + refresh).
-- Run: snow sql --connection <conn> --filename snowflake/lab/04_dt_verify_sample_queries.sql
-- Defaults match generator: database balloon_silver, schema silver. Change USE lines if you overrode env.

USE DATABASE balloon_silver;
USE SCHEMA silver;

-- ---------------------------------------------------------------------------
-- 1) Discovery — all five DTs visible in this schema
-- ---------------------------------------------------------------------------
SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA;

-- ---------------------------------------------------------------------------
-- 2) dt_player_leaderboard — per-player totals (mv_leaderboard parity)
-- ---------------------------------------------------------------------------
SELECT player, total_score, bonus_pops, last_event_ts
FROM dt_player_leaderboard
ORDER BY total_score DESC NULLS LAST
LIMIT 15;

SELECT COUNT(*) AS leaderboard_rows FROM dt_player_leaderboard;

-- ---------------------------------------------------------------------------
-- 3) dt_balloon_color_stats — player × color (mv_balloon_color_stats parity)
-- ---------------------------------------------------------------------------
SELECT player, balloon_color, balloon_pops, points_by_color, bonus_hits, last_event_ts
FROM dt_balloon_color_stats
ORDER BY player, points_by_color DESC NULLS LAST
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 4) dt_realtime_scores — 15s windows (mv_realtime_scores parity)
-- ---------------------------------------------------------------------------
SELECT player, total_score, window_start, window_end
FROM dt_realtime_scores
ORDER BY window_start DESC, player
LIMIT 20;

SELECT
  COUNT(*) AS windowed_rows,
  COUNT_IF(window_end = DATEADD(second, 15, window_start)) AS rows_with_15s_span
FROM dt_realtime_scores;

-- ---------------------------------------------------------------------------
-- 5) dt_balloon_colored_pops — window × player × color
-- ---------------------------------------------------------------------------
SELECT player, balloon_color, balloon_pops, window_start, window_end
FROM dt_balloon_colored_pops
ORDER BY window_start DESC, player, balloon_color
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 6) dt_color_performance_trends — window × color aggregates
-- ---------------------------------------------------------------------------
SELECT balloon_color, avg_score_per_pop, total_pops, window_start, window_end
FROM dt_color_performance_trends
ORDER BY window_start DESC, balloon_color
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 7) Optional — bronze vs silver row-count parity (edit FQN to your CLD path)
-- ---------------------------------------------------------------------------
-- Replace LINKED_DB and quoted lowercase Glue database name from SHOW SCHEMAS / 02_cld_verify.
-- Pass (after DT refresh): dt_players should equal bronze_distinct_players when every player has ≥1 event.
/*
WITH bronze AS (
  SELECT PARSE_JSON(event):player::STRING AS player
  FROM LINKED_DB."glue_db_lower"."balloon_game_events"
)
SELECT
  (SELECT COUNT(*) FROM dt_player_leaderboard) AS dt_players,
  (SELECT COUNT(DISTINCT player) FROM bronze) AS bronze_distinct_players;
*/
