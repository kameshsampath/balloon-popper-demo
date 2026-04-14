# SFGuide extraction map (Phase 1)

Use this document while `docs/`, `polaris-forge-setup/`, and related trees still exist. After review, commit; then lift snippets into `snowflake/lab/`, `lab/bronze-landing-zone.md`, and the future `sfguides/<id>/<id>.md`.

See also [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) for MV → Dynamic Iceberg Table parity notes.

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
| [index.md](../docs/index.md) | Overview tone; strip RisingWave/k3d promises |
| [summary.md](../docs/summary.md) | “What you’ll learn” bullets → Overview |
| [setup.md](../docs/setup.md) | Mostly **omit**; replace with Snowflake + `snow` + AWS prereqs |
| [local_cloud.md](../docs/local_cloud.md) | **Omit** or Related Resources “legacy stack” |
| [catalog_setup.md](../docs/catalog_setup.md) | Polaris narrative → link **lab/bronze-landing-zone.md** |
| [iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Legacy **column / partition** specs for old sink tables; raw bronze = **`balloon_game_events`** in **`source.sql.j2`** |
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
| [README.md](../README.md) | Accounts + repo orientation; strip k3d/Kafka | `## Overview` (tone) + `## Tools and prerequisites` (bullets) |
| [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md) | High-level story, “what you’ll learn” | `## Overview` |
| [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md) | Full bronze sequence, env vars, `task bronze:*` | `## Bronze landing zone` (summary + link); keep long copy in lab |
| [tools/bronze_preload/README.md](../tools/bronze_preload/README.md) | CLI / `uv run` scripts / two AWS surfaces | `## Tools and prerequisites` + Bronze subsection |
| [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) | Tables `balloon_pops.*` | Bronze chapter “what you have” + Phase 3 SQL comments |
| [docs/catalog_setup.md](../docs/catalog_setup.md) | Polaris/S3 concepts only | Overview or Bronze “why S3 Tables” one paragraph + link lab |
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

## Proposed guide outline (reader order)

**Intent:** Open with **Overview** and **Tools and prerequisites**, then the **Bronze landing zone** as the **first hands-on chapter** (still “setup” for Snowflake, but not buried). Learners see **what data exists**, **where it lives** (Glue + S3 warehouse + optional S3 Tables), and **what Snowflake will attach to** before any `CREATE CATALOG INTEGRATION`. Deep copy stays in [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md); the sfguide summarizes, links, and shows the Glue table inventory below.

### Frontmatter

`id`, `title`/`summary`, `authors`, `tags`, `license` per [Snowflake Quickstarts](https://github.com/Snowflake-Labs/sfguides) / create-sfguide checklist.

### `## Overview`

- End-to-end outcome: bronze Iceberg → linked catalog → Dynamic Iceberg Tables → Streamlit in Snowflake (optional DuckDB read).
- Short “you will” bullets; optional one-block architecture (Glue / S3 → Snowflake CLD → DTs → SiS).
- Sources: [docs/index.md](../docs/index.md), [docs/summary.md](../docs/summary.md), [README.md](../README.md) (Snowflake path only; omit legacy k3d stack).

### `## Tools and prerequisites`

- **Accounts:** AWS + Snowflake; assumed roles / permissions (pointer to [lab/aws/README.md](../lab/aws/README.md) for IAM render if needed).
- **Local toolchain:** `uv` / `uv sync`; **`.envrc`** and `.venv/bin` on PATH; **`snow`** from `snowflake-cli`; **`task`**, **`task check-tools`** (`check-lab-prereqs`).
- **Repo entrypoints:** `[project.scripts]` in [pyproject.toml](../pyproject.toml) (`bronze-cli`, `load-bronze-sample`, …) and **`task bronze:*`** — link [tools/bronze_preload/README.md](../tools/bronze_preload/README.md).
- **Environment:** `.env.example` highlights (`AWS_PROFILE`, `BRONZE_BUCKET_NAME`, `LAB_USERNAME`, …); no secrets in-repo.
- Sources: [README.md](../README.md), [lab/bronze-landing-zone-MANUAL-TEST.md](../lab/bronze-landing-zone-MANUAL-TEST.md) for smoke order; [docs/setup.md](../docs/setup.md) only where still accurate (**omit** k8s/k3d).

### `## Bronze landing zone` (first hands-on chapter)

- **Why first:** grounds the lab so catalog linking and DTs have real Glue objects and sample rows; answers “what do I already have?”
- **What you run:** ordered gloss (`render-iam` optional → `glue-setup` → `s3tables-setup` → `load` / `task bronze:all`); **full procedure** → [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md).
- **What you have after:** five table names + one-line purpose each (see **Glue catalog inventory** below); optional callout for S3 Tables vs Glue warehouse (see bronze README “two AWS surfaces”).
- **Schema truth:** link [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) for columns/partitions.

### Snowflake pipeline (main H2s after bronze)

_Use ≤4 words per H2 title where Quickstarts style requires it; wording can merge steps if length is an issue._

1. **Link Iceberg catalog** — `CREATE CATALOG INTEGRATION`, secrets, `DESCRIBE CATALOG INTEGRATION` (trust policy pointers).
2. **Create linked database** — `CREATE DATABASE … LINKED_CATALOG`.
3. **Build silver pipeline** — Dynamic Iceberg Tables mirroring `mv_leaderboard` / `mv_balloon_color_stats` (names TBD).
4. **Add windowed tables** — DTs for tumble-window semantics (`mv_realtime_scores`, `mv_balloon_colored_pops`, `mv_color_performance_trends`).
5. **Visualize in Streamlit** — SiS deploy and queries.
6. **Query Iceberg externally** _(optional appendix)_ — DuckDB + read path for DT tables.

### Other sections (non–step-1 bodies)

| Section | Content |
|---------|---------|
| **Conclusion** | Recap bronze → Snowflake path; what to delete or keep in a shared AWS account. |
| **Appendix** | Troubleshooting ([docs/troubleshooting.md](../docs/troubleshooting.md) patterns rewritten for Glue/`snow`/Snowflake only), limits, links to legacy `docs/` if anything remains. |
| **Resources** | Lab deep-links, `snowflake/lab/*.sql`, DuckDB gist/docs as needed. |

## Glue catalog inventory (Bronze reference)

| Glue database (example) | Iceberg tables |
|-------------------------|----------------|
| `balloon_pops` | `balloon_game_events` (raw); aggregates modeled as Snowflake Dynamic Iceberg Tables |

Align raw columns with [source.sql.j2](../polaris-forge-setup/templates/source.sql.j2). Legacy sink names in [sink.sql.j2](../polaris-forge-setup/templates/sink.sql.j2) / [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) are reference only for DT SQL parity.

## Incremental Quickstart delivery (validate while building)

Update **`sfguides/<id>/<id>.md`** **as phases complete**, together with the lab assets they describe—do not wait until the whole lab is finished. Each commit should leave the guide **internally consistent** with `lab/` and `snowflake/lab/` at that point.

| Milestone | Typical Quickstart growth |
|-----------|---------------------------|
| **Phase 2 (scaffold)** | Create `sfguides/<id>/<id>.md` with frontmatter, **`## Overview`**, **`## Tools and prerequisites`**, and **`## Bronze landing zone`** (summaries + links to [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md); commands match `task bronze:*` / `pyproject` scripts). |
| **Phase 3 (Snowflake body)** | Add pipeline **`##`** steps (catalog integration → linked DB → DTs → SiS) as SQL and procedures are verified in `snowflake/lab/`. |
| **Phase 4 (closeout)** | **Conclusion**, **Appendix**, **Resources**; strip draft notes; align with create-sfguide checklist before **sfquickstarts** PR. |

WIP in **this repo** may use a draft frontmatter flag or top-of-file note; **published** Quickstarts should avoid empty or misleading steps.

## Phase 1 exit checklist

- [x] Extraction map covers all `docs/*.md` and key templates
- [x] [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md) holds MV ↔ DT porting notes
- [x] Reviewer sign-off on map (human gate)
- [x] `author` frontmatter formatted per Snowflake Quickstarts (names above)
- [x] After sign-off: Phase 2 scaffold `sfguides/<id>/<id>.md` (start **incremental** updates per table above)
