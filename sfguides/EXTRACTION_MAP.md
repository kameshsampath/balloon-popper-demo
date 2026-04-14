# SFGuide extraction map (Phase 1)

Use this document while `docs/`, `polaris-forge-setup/`, and related trees still exist. After review, commit; then lift snippets into `snowflake/lab/`, `lab/bronze-landing-zone.md`, and the future `sfguides/<id>/<id>.md`.

## Metadata (fill before publish)

| Field | Value |
|--------|--------|
| **Proposed guide `id`** | `lakehouse-iceberg-production-pipelines` (finalize in Phase 2) |
| **Public title** | Lakehouse Transformations: Build Production Pipelines for your Iceberg Tables |
| **Author** | _TBD — your Snowflake Quickstarts author string_ |
| **Status** | Draft map |

## Narrative change (RisingWave → Snowflake)

| Legacy concept | New lab role |
|----------------|--------------|
| Kafka source + RisingWave MVs | Bronze Iceberg on S3 + REST catalog; Snowflake **CLD** reads bronze; **Dynamic Iceberg Tables** replace MV semantics |
| RisingWave Iceberg sinks | Snowflake-managed Iceberg (DTs) + **external volume** |
| Local Streamlit / MkDocs | **Streamlit in Snowflake** + single `sfguides/<id>/<id>.md` |

## Source → SFGuide section

| Source | What to extract | Target in `sfguides/<id>/<id>.md` |
|--------|-----------------|-----------------------------------|
| [README.md](../README.md) | Prerequisites list (replace k3d/Kafka with Snowflake + AWS + `snow` + `uv` + Task) | `### Prerequisites` |
| [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md) | High-level story; drop RisingWave-specific URLs | `## Overview` → What You'll Learn / Build |
| [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Table identifiers, columns, partitioning for `balloon_pops.*` | Setup “verify bronze” + Phase 3 DT SQL comments / `schema.md` lift |
| [docs/setup.md](../docs/setup.md), [docs/local_cloud.md](../docs/local_cloud.md) | _Deprecate for Snowflake lab_; any generic env tips only | Omit or one-line “legacy local stack” in Related Resources if needed |
| [docs/catalog_setup.md](../docs/catalog_setup.md) | Polaris/S3 ideas only (not Ansible playbooks) | Cross-link to [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md) |
| [docs/implementing_data_pipeline.md](../docs/implementing_data_pipeline.md), [docs/verifying_data_pipeline.md](../docs/verifying_data_pipeline.md) | MV logic → DT graph order (leaderboard, color stats, windows, trends) | Phase 3 main H2s (CLD → DTs) |
| [docs/dashboards.md](../docs/dashboards.md), [docs/leaderboard.md](../docs/leaderboard.md), [docs/color_analysis.md](../docs/color_analysis.md), [docs/performance_trends.md](../docs/performance_trends.md) | Metrics definitions, chart intent | Phase 3 SiS + notebook copy |
| [docs/run_app.md](../docs/run_app.md) | Replace “run local Streamlit” with SiS deploy | Setup / Phase 3 |
| [docs/troubleshooting.md](../docs/troubleshooting.md) | Rewrite for Snowflake + AWS Glue/S3 Tables + `snow` CLI | Appendix or Related Resources |
| [polaris-forge-setup/templates/source.sql.j2](../polaris-forge-setup/templates/source.sql.j2) | MV definitions: `mv_leaderboard`, `mv_balloon_color_stats`, `mv_realtime_scores`, `mv_balloon_colored_pops`, `mv_color_performance_trends`; raw event fields | `snowflake/lab/*.sql` DT `AS SELECT` semantics |
| [polaris-forge-setup/templates/sink.sql.j2](../polaris-forge-setup/templates/sink.sql.j2) | Iceberg table names (if present) | Align with `balloon_pops` Iceberg identifiers |
| [packages/generator/src/stream/balloon_popper.py](../packages/generator/src/stream/balloon_popper.py) | Event shape (`player`, `balloon_color`, `score`, …) | Bronze preload + generator reuse |
| [packages/dashboard/src/dashboard/data/loaders.py](../packages/dashboard/src/dashboard/data/loaders.py) | Query shapes for leaderboard / colors / trends | SiS SQL against DTs or CLD |
| [plans/snowflake_stack_refactor_97a1b8ee.plan.md](../plans/snowflake_stack_refactor_97a1b8ee.plan.md) | Phasing, Glue IRC + `LINKED_CATALOG`, `bronze:*` tasks | Internal only (not in sfguide body) |

## First main H2 after Setup (Phase 3)

Per plan: **not** bronze loading. Open with **catalog integration → `CREATE DATABASE … LINKED_CATALOG`**, then Dynamic Iceberg Tables, then SiS, then optional DuckDB + HIRC appendix.

## Glue catalog inventory (for Prerequisites table)

When bronze is landed via **AWS Glue** / **S3 Tables**, document these **Glue database** and **table** names (Iceberg) for learners — align preload and `CATALOG_NAME`:

| Glue database (example) | Iceberg tables |
|-------------------------|----------------|
| `balloon_pops` | `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends` |

_Use the same logical names as [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md). Replace database name if your account uses a different Glue catalog namespace._

## Checklist before Phase 2 scaffold

- [ ] Reviewer approved this map
- [ ] Copy-paste snippets lifted into `snowflake/lab/` or notes where needed
- [ ] `id` and `author` finalized for frontmatter
