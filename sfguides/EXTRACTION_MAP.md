# SFGuide extraction map (Phase 1)

Internal map for lifting content into **`sfguides/`** and **`snowflake/lab/`**. **Canonical learner path:** [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md), [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md), [tools/bronze_preload/README.md](../tools/bronze_preload/README.md).

[snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) holds the bronze **`event`** JSON contract and aggregate → Dynamic Iceberg Table patterns.

## Metadata (publish checklist)

| Field | Value |
|--------|--------|
| **Guide `id` (proposed)** | `lakehouse-iceberg-production-pipelines` |
| **Folder + file** | `sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md` |
| **Public title** | Lakehouse Transformations: Build Production Pipelines for your Iceberg Tables |
| **Author** | Kamesh Sampath, Gilberto Hernandez — _format for Quickstarts frontmatter (single field vs list) per [create-sfguide](https://github.com/Snowflake-Labs/sfguides) / your DA skill at Phase 2 PR_ |
| **Status** | Phase 1 map complete (bronze-first reader order + Tools/Overview agreed) |

## Docs inventory (`docs/`)

| File | Extract / action |
|------|------------------|
| [index.md](../docs/index.md) | Overview tone; Snowflake + Iceberg only if mined |
| [summary.md](../docs/summary.md) | “What you’ll learn” bullets → Overview |
| [setup.md](../docs/setup.md) | Mostly **omit**; replace with Snowflake + `snow` + AWS prereqs |
| [local_cloud.md](../docs/local_cloud.md) | **Omit** from quickstart (not part of AWS + Snowflake lab path) |
| [catalog_setup.md](../docs/catalog_setup.md) | Prefer **lab/bronze-landing-zone.md** for AWS catalog / warehouse narrative |
| [iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Optional **column / partition** reference for older aggregate-table layouts; raw bronze = **`balloon_game_events`** + JSON **`event`** per **REFERENCE.md** |
| [implementing_data_pipeline.md](../docs/implementing_data_pipeline.md) | Pipeline **order** and verification ideas → DT + verify H2s |
| [verifying_data_pipeline.md](../docs/verifying_data_pipeline.md) | Checklist style queries → post-DT validation |
| [dashboards.md](../docs/dashboards.md) | SiS page grouping |
| [leaderboard.md](../docs/leaderboard.md) | Leaderboard metrics copy |
| [color_analysis.md](../docs/color_analysis.md) | Color metrics copy |
| [performance_trends.md](../docs/performance_trends.md) | Trend metrics copy |
| [run_app.md](../docs/run_app.md) | Replace local Streamlit with **SiS** deploy steps |
| [troubleshooting.md](../docs/troubleshooting.md) | Rewrite for Snowflake/Glue/`snow` (appendix) |
| [assets/snowflake-logo-blue.svg](../docs/assets/snowflake-logo-blue.svg) | Optional asset for sfguide if allowed |

## Canonical SQL / schema (lab repo)

| Source | Use |
|--------|-----|
| [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) | Bronze JSON keys; DT **`PARSE_JSON`** patterns; aggregate roles |
| [snowflake/lab/*.sql](../snowflake/lab/) | Executable Snowflake steps as they land |

## Source → SFGuide section (rollup)

| Source | What to extract | Target in `sfguides/<id>/<id>.md` |
|--------|-----------------|-----------------------------------|
| [README.md](../README.md) | Accounts + repo orientation; AWS + Snowflake only | `## Overview` (tone) + `## Tools and prerequisites` (bullets) |
| [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md) | High-level story, “what you’ll learn” | `## Overview` |
| [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md) | Full bronze sequence, env vars, `task bronze:*`, Lake Formation after load | `## Bronze landing zone` (summary + link); keep long copy in lab |
| [tools/bronze_preload/README.md](../tools/bronze_preload/README.md) | CLI / `uv run` scripts / two AWS surfaces | `## Tools and prerequisites` + Bronze subsection |
| [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Tables `balloon_pops.*` | Bronze chapter “what you have” + Phase 3 SQL comments |
| [docs/catalog_setup.md](../docs/catalog_setup.md) | S3 / catalog concepts only if still useful | Overview or Bronze “why S3 Tables” one paragraph + link lab |
| [docs/implementing_data_pipeline.md](../docs/implementing_data_pipeline.md), [docs/verifying_data_pipeline.md](../docs/verifying_data_pipeline.md) | MV / pipeline order | Phase 3 DT + verify |
| [docs/dashboards.md](../docs/dashboards.md), leaderboard / color / performance chapters | Viz intent | Phase 3 SiS |
| [docs/run_app.md](../docs/run_app.md) | UX flow | SiS open / grant |
| [docs/troubleshooting.md](../docs/troubleshooting.md) | Patterns | Appendix |
| [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) | Aggregate → DT mapping | `snowflake/lab/*.sql` + sfguide Snowflake chapters |
| [packages/generator/](../packages/generator/) | Event payload | Bronze preload |
| [packages/dashboard/](../packages/dashboard/) | SQL against aggregates | SiS queries |
| [plans/snowflake_stack_refactor_97a1b8ee.plan.md](../plans/snowflake_stack_refactor_97a1b8ee.plan.md) | Phasing, Glue IRC | Internal |

## Concept mapping (stream → lakehouse)

| Source pattern | This lab |
|----------------|----------|
| JSON events on a bus + SQL aggregates | Bronze Iceberg JSON column on S3 + REST catalog; Snowflake **CLD**; **Dynamic Iceberg Tables** for silver |
| Managed Iceberg sinks | Snowflake-managed Iceberg (DTs) + **external volume** where documented |
| Local HTML docs | **Streamlit in Snowflake** + `sfguides/<id>/<id>.md` |

## Proposed guide outline (reader order)

**Intent:** Open with **Overview** and **Tools and prerequisites**, then the **Bronze landing zone** as the **first hands-on chapter** (still “setup” for Snowflake, but not buried). Learners see **what data exists**, **where it lives** (Glue + S3 warehouse + optional S3 Tables), and **what Snowflake will attach to** before any `CREATE CATALOG INTEGRATION`. Deep copy stays in [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md); the sfguide summarizes, links, and shows the Glue table inventory below.

### Frontmatter

`id`, `title`/`summary`, `authors`, `tags`, `license` per [Snowflake Quickstarts](https://github.com/Snowflake-Labs/sfguides) / create-sfguide checklist.

### `## Overview`

- End-to-end outcome: bronze Iceberg → linked catalog → Dynamic Iceberg Tables → Streamlit in Snowflake (optional DuckDB read).
- Short “you will” bullets; optional one-block architecture (Glue / S3 → Snowflake CLD → DTs → SiS).
- Sources: [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md), [README.md](../README.md) (Snowflake + AWS path only).

### `## Tools and prerequisites`

- **Accounts:** AWS + Snowflake; assumed roles / permissions (pointer to [lab/aws/README.md](../lab/aws/README.md) for IAM render if needed).
- **Local toolchain:** `uv` / `uv sync`; **`.envrc`** and `.venv/bin` on PATH; **`snow`** from `snowflake-cli`; **`task`**, **`task check-tools`** (`check-lab-prereqs`).
- **Repo entrypoints:** `[project.scripts]` in [pyproject.toml](../pyproject.toml) (`bronze-cli`, `load-bronze-sample`, …) and **`task bronze:*`** — link [tools/bronze_preload/README.md](../tools/bronze_preload/README.md).
- **Environment:** `.env.example` highlights (`AWS_PROFILE`, `BRONZE_BUCKET_NAME`, `LAB_USERNAME`, …); no secrets in-repo.
- Sources: [README.md](../README.md), [lab/bronze-landing-zone-MANUAL-TEST.md](../lab/bronze-landing-zone-MANUAL-TEST.md) and [lab/snowflake-cld-MANUAL-TEST.md](../lab/snowflake-cld-MANUAL-TEST.md) for smoke order; [docs/setup.md](../docs/setup.md) only if mined for generic tool install (omit cluster-only content).

### `## Bronze landing zone` (first hands-on chapter)

- **Why first:** grounds the lab so catalog linking and DTs have real Glue objects and sample rows; answers “what do I already have?”
- **What you run:** ordered gloss (`render-iam` optional → `glue-setup` → `s3tables-setup` → `load` / `task bronze:all`); **full procedure** → [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md).
- **What you have after:** **`balloon_game_events`** with JSON **`event`** column (see **Glue catalog inventory** below); optional callout for S3 Tables vs Glue warehouse (see bronze README “two AWS surfaces”).
- **Schema truth:** [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md); optional [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) for older aggregate-table layouts.

### Snowflake pipeline (main H2s after bronze)

_Use ≤4 words per H2 title where Quickstarts style requires it; wording can merge steps if length is an issue._

1. **Link Iceberg catalog** — `CREATE CATALOG INTEGRATION`, secrets, `DESCRIBE CATALOG INTEGRATION` (trust policy pointers).
2. **Create linked database** — `CREATE DATABASE … LINKED_CATALOG`.
3. **Build silver pipeline** — Dynamic Iceberg Tables (leaderboard-style aggregates per **REFERENCE.md**).
4. **Add windowed tables** — DTs for 15-second (or chosen) windows on `event_ts` per **REFERENCE.md** and Snowflake time-function docs.
5. **Visualize in Streamlit** — SiS deploy and queries.
6. **Query Iceberg externally** _(optional appendix)_ — DuckDB + read path for DT tables.

### Other sections (non–step-1 bodies)

| Section | Content |
|---------|---------|
| **Troubleshooting** | In **`sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md`**: **`094120` / “Failed to retrieve credentials from the Catalog”** — Lake Formation **Data lake locations** (LF vs hybrid, no federation), IAM/S3 chain, **`CREATE OR REPLACE DATABASE … LINKED_CATALOG`**, re-grants (`USAGE` on integration, ownership). |
| **Conclusion** | Recap bronze → Snowflake path; what to delete or keep in a shared AWS account. |
| **Appendix** | Extra troubleshooting (Glue / `snow` / Snowflake); optional mined patterns from `docs/` if rewritten for this lab. |
| **Resources** | Lab deep-links, `snowflake/lab/*.sql`, DuckDB gist/docs as needed. |

## Glue catalog inventory (Bronze reference)

| Glue database (example) | Iceberg tables |
|-------------------------|----------------|
| `balloon_pops` | `balloon_game_events` (raw); aggregates modeled as Snowflake Dynamic Iceberg Tables |

Align raw JSON with [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md). Optional extra column notes: [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md).

## Incremental Quickstart delivery (validate while building)

Update **`sfguides/<id>/<id>.md`** **as phases complete**, together with the lab assets they describe—do not wait until the whole lab is finished. Each commit should leave the guide **internally consistent** with `lab/` and `snowflake/lab/` at that point.

| Milestone | Typical Quickstart growth |
|-----------|---------------------------|
| **Phase 2 (scaffold)** | Create `sfguides/<id>/<id>.md` with frontmatter, **`## Overview`**, **`## Tools and prerequisites`**, and **`## Bronze landing zone`** (summaries + links to [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md); commands match `task bronze:*` / `pyproject` scripts). |
| **Phase 3 (Snowflake body)** | Add pipeline **`##`** steps (catalog integration → linked DB → DTs → SiS) as SQL and procedures are verified in `snowflake/lab/`. |
| **Phase 4 (closeout)** | **Conclusion**, **Appendix**, **Resources**; strip draft notes; align with create-sfguide checklist before **sfquickstarts** PR. |

WIP in **this repo** may use a draft frontmatter flag or top-of-file note; **published** Quickstarts should avoid empty or misleading steps.

## Phase 1 exit checklist

- [x] Extraction map covers `docs/*.md` where still useful and lab canonical paths
- [x] [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) holds bronze JSON + DT aggregate notes
- [x] Reviewer sign-off on map (human gate)
- [x] `author` frontmatter formatted per Snowflake Quickstarts (names above)
- [x] After sign-off: Phase 2 scaffold `sfguides/<id>/<id>.md` (start **incremental** updates per table above)
