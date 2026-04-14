# Bronze landing zone (prerequisite)

This document is the **detailed** prerequisite for the Snowflake lab: **Iceberg bronze on S3** and a **REST catalog** Snowflake can use before **`CREATE DATABASE … LINKED_CATALOG`**.

**Phase 0 — environment:** copy [`.env.example`](../.env.example) to `.env`, fill in **AWS** and **bronze** variables (never commit `.env`). Run **`task check-tools`** from the repo root to confirm required CLIs (**aws**, **snow**, **task**, **envsubst**, **jq**, **cortex**, **uv**) and recommended tools (**direnv**, **curl**, **openssl**) are on your `PATH` (see [README](../README.md)). Install **[direnv](https://direnv.net/)** and allow the repo (e.g. `direnv allow`) so `.envrc` loads `.env` automatically. Extend `.env.example` as new phases add Snowflake CLI, PAT, or DuckDB IRC variables.

**Shared AWS account / workshop:** set **`LAB_USERNAME`** (one id per participant) so Glue database and S3 Tables bucket name default to unique values when **`GLUE_DATABASE`** / **`BRONZE_S3TABLES_BUCKET_NAME`** are not set. See comments in [`.env.example`](../.env.example). **`S3TABLES_NAMESPACE`** stays `balloon_pops` inside each participant’s table bucket unless you change it deliberately.

**Manual QA:** follow [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md).

The Quickstart **Setup** section should summarize steps here and link to this file. **Do not** make “load bronze” the first main Snowflake chapter—learners start Snowflake hands-on at **CLD**.

## What gets created in AWS Glue

When you use the **Glue / S3 Tables** path, the workshop should create (or register) an Iceberg **Glue database** and the following **tables** (names align with [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md)):

| Glue database (example) | Tables |
|-------------------------|--------|
| `balloon_pops` | `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends` |

Replace `balloon_pops` with your **Glue catalog / S3 Tables namespace** if it differs. Match **`CATALOG_NAME`** in Snowflake `CREATE CATALOG INTEGRATION` so **`LINKED_CATALOG`** sees the same objects.

**Polaris-only path:** publish an analogous list (REST **namespace** + **table** identifiers) in Prerequisites instead of Glue.

## Automation (`task bronze:…`)

Modular tasks live in [`.taskfiles/bronze.yml`](../.taskfiles/bronze.yml) (included from the root `Taskfile.yml`). Implementation is **Python + Click** ([`tools/bronze-preload/bronze_cli.py`](../tools/bronze-preload/bronze_cli.py)) so the same commands work on **Windows, Linux, and macOS** (still requires **AWS CLI** on `PATH` for `s3tables` and for `sts` in `render-iam`). Use a **real** AWS account: set **`AWS_PROFILE`** (and usually **`AWS_REGION`**). See [tools/bronze-preload/README.md](../tools/bronze-preload/README.md) for full env vars.

| Task | Purpose |
|------|---------|
| `task bronze:render-iam` | Render `lab/aws/bronze-glue-writer-policy.json` → `.aws-config/*.rendered.json` (needs `BRONZE_S3_ARN`) |
| `task bronze:render-iam-dry-run` | Print substituted policy JSON only (no file write) |
| `task bronze:glue-setup` | Create Glue database for **`GLUE_DATABASE`** with `LocationUri` = **`BRONZE_WAREHOUSE`** |
| `task bronze:glue-setup-dry-run` | Preview Glue setup (read-only **GetDatabase**; no create / no local JSON) |
| `task bronze:s3tables-setup` | **`aws s3tables`** — table bucket **`BRONZE_S3TABLES_BUCKET_NAME`**, namespace **`balloon_pops`**, five **`ICEBERG`** tables (CLI **2.34+**) |
| `task bronze:s3tables-setup-dry-run` | Preview S3 Tables setup (read-only list; no creates) |
| `task bronze:load` | **`load_sample.py`** — PyIceberg appends sample rows into Glue Iceberg tables on **`BRONZE_WAREHOUSE`** |
| `task bronze:all` | `glue-setup` → `s3tables-setup` → `load` |

### Glue + S3 warehouse vs S3 Tables (two surfaces)

- **Glue Data Catalog + S3** — `glue-setup` and **`bronze:load`** populate **Iceberg** metadata + files for the five logical tables (workshop-friendly).
- **Amazon S3 Tables** — `s3tables-setup` creates the **table bucket / namespace / ICEBERG table** objects for Snowflake **Glue Iceberg REST** alignment; they are **not** auto-filled by `load_sample.py` (add a Glue-REST writer later if you want one copy only).

Keep **secrets** out of Task YAML; use **`.aws-config/`** for generated policy JSON (see [.aws-config/README.md](../.aws-config/README.md)).

### Local config directory (`.aws-config/`)

Use a repo-local **`.aws-config/`** directory (not `~/.aws`) for **generated** IAM JSON, trust-policy fragments, or other outputs from the bronze CLI—filled at **run time** from **environment variables** and **`AWS_PROFILE`**. The tree is **gitignored** except [`.aws-config/README.md`](../.aws-config/README.md) and optional `*.example` files. **Committed** policy **templates** with placeholders should live under **`lab/aws/`** (added when bronze tasks are implemented).

## Recommended order

1. Pick **region** (AWS, S3, Snowflake aligned).
2. **S3 warehouse bucket** — create a general-purpose S3 bucket (console, IaC, or your org’s process), then set **`BRONZE_WAREHOUSE`** (`s3://<bucket>/<prefix>/`, often `…/iceberg/`) and **`BRONZE_S3_ARN`** to match that bucket.
3. **IAM** for writers (PyIceberg / Glue role) and bucket policy for Snowflake **storage integration** / **external volume** where your Snowflake lab needs them; use **`task bronze:render-iam`** for the lab’s Glue-writer policy template when applicable.
4. **Glue** path: run `task bronze:glue-setup` then `task bronze:s3tables-setup` (or your CFN equivalent).
5. **REST catalog**: either **Polaris** (reachable from Snowflake, not only `localhost`) or **Glue Iceberg REST** (`https://glue.<region>.amazonaws.com/iceberg`, `CATALOG_API_TYPE = AWS_GLUE`, SIGv4 — see [gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) and Snowflake docs).
6. **Load**: `task bronze:load` (or `task bronze:all` from a clean slate).
7. **Verify**: Glue / S3 Tables lists tables above; optional Snowflake `DESCRIBE CATALOG INTEGRATION` smoke.

## Snowflake handoff

Record (outside git): catalog integration **URI**, **OAuth / SIGv4 role ARNs**, **external IDs**, **storage integration** names. Bronze **data paths** must stay consistent with **Dynamic Iceberg Table** **external volume** prefixes documented in the main lab.

## References

- [Iceberg schema (this repo)](../docs/iceberg_schema_design.md)
- [Snowflake: Iceberg REST catalog integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest)
- [Glue + Snowflake IAM / SQL gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426)
- [Lakehouse walkthrough (video)](https://youtu.be/DObaF-Fk1_A)
