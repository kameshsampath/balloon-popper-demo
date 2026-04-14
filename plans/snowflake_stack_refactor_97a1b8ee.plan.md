---
name: Snowflake Stack Refactor
overview: "Snowflake lab: bronze Iceberg on S3 (prereq) → catalog integration → CLD → Dynamic Iceberg Tables → Streamlit in Snowflake. Phased work: extraction map, bronze landing doc + preload, SQL lab, sfguide in four commits, repo carve-out. Tooling: sfutils-pat, sfutils-extvolumes, snow CLI >3.16, modular Taskfile."
todos:
  - id: sfguide-phase-1-map
    content: "Author + id; extraction map from docs/templates; commit under sfguides/"
    status: pending
  - id: phase-bronze-landing-zone
    content: "lab/bronze-landing-zone.md + tools/bronze-preload + Taskfile; include explicit Glue DB + table names bronze creates; Glue IRC per gist if needed; test; commit"
    status: pending
  - id: companion-repo-delete
    content: "After map + lifts, delete polaris-forge-setup, k8s, mkdocs, old docs, cluster bin, GH Pages workflow; tighten .gitignore"
    status: pending
  - id: snowflake-sql-lab
    content: "snowflake/lab/*.sql: integration → CREATE DATABASE … LINKED_CATALOG → DTs; align with sfguide Phase 3"
    status: pending
  - id: sfguide-phase-2-overview-setup
    content: "sfguides/<id>/<id>.md: frontmatter, Overview, Setup; Prerequisites bronze subsection lists Glue database + every table created; link lab/bronze-landing-zone.md; first main H2 in Phase 3; commit"
    status: pending
  - id: snowflake-notebooks
    content: "Primary hands-on in Snowflake Notebooks; keep in sync with snowflake/lab"
    status: pending
  - id: sis-visualization
    content: "Streamlit in Snowflake for game metrics; ship under snowflake/streamlit or lab SQL"
    status: pending
  - id: sfguide-phase-3-body
    content: "SFGuide Phase 3: CLD, DTs, SiS; short DuckDB+HIRC appendix (read DT Iceberg only); commit"
    status: pending
  - id: sfguide-phase-4-conclusion
    content: "Conclusion And Resources + create-sfguide checklist; commit"
    status: pending
  - id: deps-ci
    content: "pyproject: sfutils-pat, sfutils-extvolumes, snowflake-cli>3.16, preload deps; uv lock; drop docs workflow if unused"
    status: pending
  - id: taskfile-lab-modular
    content: "Taskfile: bronze, polaris, PAT, ext volumes, snow sql/streamlit; document in README"
    status: pending
isProject: false
---

**Source of truth**: [`plans/snowflake_stack_refactor_97a1b8ee.plan.md`](plans/snowflake_stack_refactor_97a1b8ee.plan.md).

# Snowflake lab refactor (simplified)

## Goal

Refactor this repo into a **Snowflake Quickstart–style lab**: **Lakehouse Transformations: Build Production Pipelines for your Iceberg Tables**. Balloon data remains the **sample domain**. **Learner narrative**: finish **bronze on S3** in Prerequisites/Setup, then the **first main Snowflake module is CLD** (catalog integration → `CREATE DATABASE … LINKED_CATALOG`), then **Dynamic Iceberg Tables**, then **Streamlit in Snowflake**.

## Execution rule

One todo (or one sfguide sub-phase) at a time: implement, validate, **commit**, then next.

## Order

1. **SFGuide Phase 1** — extraction map from existing [`docs/`](docs/) and templates; commit before large deletes.
2. **`phase-bronze-landing-zone`** — [`lab/bronze-landing-zone.md`](lab/bronze-landing-zone.md), `tools/bronze-preload/`, Taskfile tasks; **commit** before **`companion-repo-delete`**.
3. **`companion-repo-delete`** — remove obsolete trees (see below).
4. **`snowflake-sql-lab`** + **sfguide Phases 2–4** — SQL, notebooks, SiS, guide body and conclusion.

## Bronze (prerequisite only)

- **Glue visibility in the guide**: In **Prerequisites** (or the Setup subsection that covers loading bronze), add a short **“What gets created in AWS Glue”** block: **Glue database name** (or catalog namespace) and an **explicit list of every Iceberg table** the bronze path registers in the **Glue Data Catalog** / **S3 Tables** surface (names only—no secrets). Match whatever `CATALOG_NAME` / `LINKED_CATALOG` will expose in Snowflake. Repeat the same list in [`lab/bronze-landing-zone.md`](lab/bronze-landing-zone.md) as the detailed source of truth; keep sfguide copy concise.
- **Doc**: [`lab/bronze-landing-zone.md`](lab/bronze-landing-zone.md) — S3, IAM, bucket policy, REST catalog **reachable from Snowflake**, preload, verify.
- **Default path**: **Polaris** + **PyIceberg** → same warehouse layout Snowflake will **catalog-link**.
- **Alternate path** (document when needed): **Glue Iceberg REST** — `CATALOG_SOURCE = ICEBERG_REST`, `CATALOG_API_TYPE = AWS_GLUE`, `CATALOG_URI = https://glue.<region>.amazonaws.com/iceberg`, SIGv4 + vended credentials or external volume per Snowflake docs; then **`CREATE DATABASE … LINKED_CATALOG = ( CATALOG = '<integration>' )`**. Patterns and IAM: [gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426).
- **Do not** use DuckDB+HIRC for bronze; use it **after DTs** to read Snowflake-managed Iceberg ([hirc-duckdb-demo](https://github.com/kameshsampath/hirc-duckdb-demo)).

## Snowflake lab artifacts

- **`snowflake/lab/*.sql`**: placeholders → **`CREATE CATALOG INTEGRATION`** (REST) → **`CREATE DATABASE … LINKED_CATALOG`** → **`CREATE DYNAMIC ICEBERG TABLE`** chain; mirror former pipeline semantics from lifted schema/templates (copy snippets before deleting old paths).
- **External volume** for DT outputs; **sfutils-pat** / **sfutils-extvolumes** in [`pyproject.toml`](pyproject.toml); **`snow` > 3.16** for `snow sql`, notebooks, streamlit.
- **SiS** as primary viz; reuse generator from [`packages/generator/`](packages/generator/) for preload rows.

## Sfguide

- Layout: `sfguides/<id>/<id>.md` matching Snowflake-Labs/sfguides conventions.
- Structure and checklist: follow your **create-sfguide** skill; skim **sfquickstarts** examples for tone.
- **Setup** summarizes bronze + links **`lab/bronze-landing-zone.md`**; **first main H2 after Setup = CLD** (not bronze loading).
- **Prerequisites / bronze load**: When bronze uses **Glue** (job, registration, or Glue IRC path), the module must **name every Glue table** (and database/namespace) learners will have after the step—so they can map Glue → `LINKED_CATALOG` → downstream SQL. If you also document a **Polaris-only** fork, add an analogous **REST catalog table list** there for parity.

## Repo carve-out (delete)

Before delete: lift **schema / column** notes from [`docs/iceberg_schema_design.md`](docs/iceberg_schema_design.md) and template SQL into `snowflake/lab/` or a short `schema.md`.

Remove: [`polaris-forge-setup/`](polaris-forge-setup/), [`k8s/`](k8s/), [`config/cluster-config.yaml`](config/cluster-config.yaml), [`bin/setup.sh`](bin/setup.sh) / [`bin/cleanup.sh`](bin/cleanup.sh), [`mkdocs.yaml`](mkdocs.yaml), [`docs/`](docs/), Polaris-only notebooks, [`.github/workflows/docs.yml`](.github/workflows/docs.yml) unless replaced. Keep: [`plans/`](plans/), [`packages/`](packages/), pyproject/uv, modular [`Taskfile.yml`](Taskfile.yml), `snowflake/lab/`, `sfguides/`, new `lab/` + `tools/bronze-preload/`.

## README

Prerequisites, clone, env vars, links to sfguide + [walkthrough](https://youtu.be/DObaF-Fk1_A) + [Glue/Snowflake gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) + bronze doc + HIRC demo.

## Naming and publish

Finalize **`id`** slug in Phase 1; align README/pyproject strings with the public title. When complete, **push to a new GitHub repo** if desired; optional one-line pointer to this repo’s history.

## Teaching one-liners

- **CLD**: Snowflake reads bronze **metadata** via REST; **files** stay on **S3**.
- **DTs**: Snowflake-managed Iceberg pipeline; **external volume** for files; other engines consume via **Iceberg REST** where applicable.
- **SiS**: default dashboard for the same game metrics story.

## Risks

Confirm **DDL** (catalog integration, `LINKED_CATALOG`, DTs) against current Snowflake docs for your account edition.

## Merged from

Earlier phased quickstart work lives in this file only (`phased_sf_quickstart_4fb30bd5` superseded).
