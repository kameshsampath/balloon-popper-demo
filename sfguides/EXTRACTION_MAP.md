# SFGuide extraction map (Phase 1)

Use this document while `docs/`, `polaris-forge-setup/`, and related trees still exist. After review, commit; then lift snippets into `snowflake/lab/`, `lab/bronze-landing-zone.md`, and the future `sfguides/<id>/<id>.md`.

See also [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) for MV → Dynamic Iceberg Table parity notes.

## Metadata (publish checklist)

| Field | Value |
|--------|--------|
| **Guide `id` (proposed)** | `lakehouse-iceberg-production-pipelines` |
| **Folder + file** | `sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md` |
| **Public title** | Lakehouse Transformations: Build Production Pipelines for your Iceberg Tables |
| **Author** | Kamesh Sampath — _confirm exact string required by [create-sfguide](https://github.com/Snowflake-Labs/sfguides) / your DA skill before Phase 2 PR_ |
| **Status** | Phase 1 map complete |

## Docs inventory (`docs/`)

| File | Extract / action |
|------|------------------|
| [index.md](../docs/index.md) | Overview tone; strip RisingWave/k3d promises |
| [summary.md](../docs/summary.md) | “What you’ll learn” bullets → Overview |
| [setup.md](../docs/setup.md) | Mostly **omit**; replace with Snowflake + `snow` + AWS prereqs |
| [local_cloud.md](../docs/local_cloud.md) | **Omit** or Related Resources “legacy stack” |
| [catalog_setup.md](../docs/catalog_setup.md) | Polaris narrative → link **lab/bronze-landing-zone.md** |
| [iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Canonical **column / partition** specs for all five tables |
| [implementing_data_pipeline.md](../docs/implementing_data_pipeline.md) | Pipeline **order** and verification ideas → DT + verify H2s |
| [verifying_data_pipeline.md](../docs/verifying_data_pipeline.md) | Checklist style queries → post-DT validation |
| [dashboards.md](../docs/dashboards.md) | SiS page grouping |
| [leaderboard.md](../docs/leaderboard.md) | Leaderboard metrics copy |
| [color_analysis.md](../docs/color_analysis.md) | Color metrics copy |
| [performance_trends.md](../docs/performance_trends.md) | Trend metrics copy |
| [run_app.md](../docs/run_app.md) | Replace local Streamlit with **SiS** deploy steps |
| [troubleshooting.md](../docs/troubleshooting.md) | Rewrite for Snowflake/Glue/`snow` (appendix) |
| [assets/snowflake-logo-blue.svg](../docs/assets/snowflake-logo-blue.svg) | Optional asset for sfguide if allowed |

## Template inventory (`polaris-forge-setup/templates/`)

| File | Extract |
|------|---------|
| [source.sql.j2](../polaris-forge-setup/templates/source.sql.j2) | MV SQL + `balloon_game_events` schema → DT definitions |
| [sink.sql.j2](../polaris-forge-setup/templates/sink.sql.j2) | Iceberg **table names** + DB name Jinja → CLD object names |
| [polaris.env.j2](../polaris-forge-setup/templates/polaris.env.j2), [bootstrap-credentials.env.j2](../polaris-forge-setup/templates/bootstrap-credentials.env.j2) | **Do not** paste secrets; use as checklist of env **names** only for bronze doc |
| [risingwave.yaml.j2](../polaris-forge-setup/templates/risingwave.yaml.j2), [postgresql.yml.j2](../polaris-forge-setup/templates/postgresql.yml.j2), [persistence.xml.j2](../polaris-forge-setup/templates/persistence.xml.j2) | **Omit** from sfguide (k8s/RW ops) |
| [notebooks/verify_setup.ipynb.j2](../polaris-forge-setup/templates/notebooks/verify_setup.ipynb.j2) | Optional: Snowflake Notebook “verify CLD” inspiration |

## Source → SFGuide section (rollup)

| Source | What to extract | Target in `sfguides/<id>/<id>.md` |
|--------|-----------------|-----------------------------------|
| [README.md](../README.md) | Prerequisites list (replace k3d/Kafka with Snowflake + AWS + `snow` + `uv` + Task) | `### Prerequisites` |
| [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md) | High-level story | `## Overview` |
| [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Tables `balloon_pops.*` | Setup verify + Phase 3 SQL comments |
| [docs/catalog_setup.md](../docs/catalog_setup.md) | Polaris/S3 concepts only | Link **lab/bronze-landing-zone.md** |
| [docs/implementing_data_pipeline.md](../docs/implementing_data_pipeline.md), [docs/verifying_data_pipeline.md](../docs/verifying_data_pipeline.md) | MV / pipeline order | Phase 3 DT + verify |
| [docs/dashboards.md](../docs/dashboards.md), leaderboard / color / performance chapters | Viz intent | Phase 3 SiS |
| [docs/run_app.md](../docs/run_app.md) | UX flow | SiS open / grant |
| [docs/troubleshooting.md](../docs/troubleshooting.md) | Patterns | Appendix |
| [polaris-forge-setup/templates/source.sql.j2](../polaris-forge-setup/templates/source.sql.j2) | All `mv_*` definitions | `snowflake/lab/*.sql` |
| [polaris-forge-setup/templates/sink.sql.j2](../polaris-forge-setup/templates/sink.sql.j2) | Five sink table names | CLD / bronze naming |
| [packages/generator/](../packages/generator/) | Event payload | Bronze preload |
| [packages/dashboard/](../packages/dashboard/) | SQL against aggregates | SiS queries |
| [plans/snowflake_stack_refactor_97a1b8ee.plan.md](../plans/snowflake_stack_refactor_97a1b8ee.plan.md) | Phasing, Glue IRC | Internal |

## Narrative change (RisingWave → Snowflake)

| Legacy concept | New lab role |
|----------------|--------------|
| Kafka source + RisingWave MVs | Bronze Iceberg on S3 + REST catalog; Snowflake **CLD** reads bronze; **Dynamic Iceberg Tables** replace MV semantics |
| RisingWave Iceberg sinks | Snowflake-managed Iceberg (DTs) + **external volume** |
| Local Streamlit / MkDocs | **Streamlit in Snowflake** + single `sfguides/<id>/<id>.md` |

## Proposed main H2 order (Phase 3 body)

_Use ≤4 words per H2 per create-sfguide; adjust wording to match skill._

1. **Link Iceberg catalog** — `CREATE CATALOG INTEGRATION`, secrets, `DESCRIBE CATALOG INTEGRATION` (trust policy pointers).
2. **Create linked database** — `CREATE DATABASE … LINKED_CATALOG`.
3. **Build silver pipeline** — Dynamic Iceberg Tables mirroring `mv_leaderboard` / `mv_balloon_color_stats` (names TBD).
4. **Add windowed tables** — DTs for tumble-window semantics (`mv_realtime_scores`, `mv_balloon_colored_pops`, `mv_color_performance_trends`).
5. **Visualize in Streamlit** — SiS deploy and queries.
6. **Query Iceberg externally** _(optional appendix)_ — DuckDB + HIRC read DT tables.

## First H2 after Setup

**Not** bronze loading. Setup ends with “bronze ready” + link to [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md). First **numbered / main** lab H2 = **Link Iceberg catalog** (or combined link + CLD if you merge for brevity).

## Glue catalog inventory (Prerequisites)

| Glue database (example) | Iceberg tables |
|-------------------------|----------------|
| `balloon_pops` | `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends` |

Align with [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) and [sink.sql.j2](../polaris-forge-setup/templates/sink.sql.j2).

## Phase 1 exit checklist

- [x] Extraction map covers all `docs/*.md` and key templates
- [x] [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) holds MV ↔ DT porting notes
- [ ] Reviewer sign-off on map (human gate)
- [ ] `author` string validated against Snowflake Quickstarts rules
- [ ] After sign-off: Phase 2 scaffold `sfguides/<id>/<id>.md`
