# Reference: legacy RisingWave → Snowflake DT porting

Use this when authoring `snowflake/lab/*.sql` and the sfguide Phase 3 body. **Do not** run RisingWave in the new lab; this file captures **semantic parity** only.

## Iceberg identifiers (bronze)

From [polaris-forge-setup/templates/sink.sql.j2](../../polaris-forge-setup/templates/sink.sql.j2) (`database.name` / `table.name`):

| Iceberg database (Jinja `balloon_game_db`) | Table |
|--------------------------------------------|--------|
| Typically `balloon_pops` in docs | `leaderboard` |
| | `balloon_color_stats` |
| | `realtime_scores` |
| | `balloon_colored_pops` |
| | `color_performance_trends` |

Schema details: [docs/iceberg_schema_design.md](../../docs/iceberg_schema_design.md).

## Raw stream (Kafka) → bronze fact

Source shape in [source.sql.j2](../../polaris-forge-setup/templates/source.sql.j2): `balloon_game_events` columns `player`, `balloon_color`, `score`, `page_id`, `favorite_color_bonus`, `event_ts`.

## Materialized view → proposed Dynamic Iceberg Table

| Legacy MV (`source.sql.j2`) | Role | Notes for Snowflake DT `AS SELECT` |
|-----------------------------|------|-----------------------------------|
| `mv_leaderboard` | Per-player totals | `GROUP BY player`; `total_score`, `bonus_hits`, `event_ts` |
| `mv_balloon_color_stats` | Per player × color | `GROUP BY player, balloon_color` |
| `mv_realtime_scores` | 15s tumble window | Map `TUMBLE(..., INTERVAL '15 SECONDS')` to windowing in DT SQL or staged aggregates |
| `mv_balloon_colored_pops` | Pops per window × color | Same window semantics |
| `mv_color_performance_trends` | Color effectiveness in window | `GROUP BY balloon_color`, window bounds |

Full SQL: always diff against the template on disk before deleting `polaris-forge-setup/`.
