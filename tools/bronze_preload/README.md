# Bronze preload (AWS + PyIceberg)

Land **sample** raw balloon game events into a single **AWS Glue Data Catalog** Iceberg table on **S3** — **`balloon_game_events`**. Each row is one **JSON object** in string column **`event`** (Kafka **PLAIN JSON** shape; field list in [snowflake/lab/REFERENCE.md](../../snowflake/lab/REFERENCE.md)). **Snowflake Dynamic Iceberg Tables** use **`PARSE_JSON`** / semi-structured paths over **`event`** for aggregates. This loader does not write silver tables.

If you already created **`balloon_game_events`** with the older multi-column schema, **drop** that Glue table (or run **`bronze:cleanup`** then **`glue-setup`** + **`load`**) before loading this JSON layout—**`ensure_table`** does not evolve schemas in place.

**Manual test checklist:** [lab/bronze-landing-zone-MANUAL-TEST.md](../../lab/bronze-landing-zone-MANUAL-TEST.md).

## Prerequisites

- **Phase 0:** copy [`.env.example`](../../.env.example) to `.env` and set variables (see comments in the example file). Do not commit `.env`. **`bronze-cli`** loads **`<repo>/.env`** at startup (`override=False`), so **`task bronze:*`** sees **`BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX`** and other keys even when direnv is not active.
- **AWS account** and **AWS CLI v2** (for `s3tables` commands, use **2.34+**).
- **`AWS_PROFILE`** set to a profile with permissions for Glue, S3, and (if you run `bronze:s3tables-setup`) S3 Tables control plane. See [lab/aws/README.md](../../lab/aws/README.md) to render a starter policy into `.aws-config/`.
- **`uv`** and repo dependencies: `uv sync`.

## Snowflake CLI and external volumes

After **`uv sync`**, **`snow`** (Snowflake CLI **≥3.16**) and **`sfutils-extvolumes`** live in **`.venv/bin`** — [`.envrc`](../../.envrc) prepends that directory so you usually do **not** need a separate global Snowflake CLI install for this repo.

- **`snow --version`** / SQL: use the venv’s `snow` (or **`uv run snow …`** from any cwd).
- **External volumes** ([Snowflake-Labs/sfutils-extvolumes](https://github.com/Snowflake-Labs/sfutils-extvolumes)): **`sfutils-extvolumes --help`** for the bundled CLI; naming helpers (`to_aws_name`, etc.) live in that package.

This repo’s bronze path still uses **local** name rules in `bronze_aws.py` (Glue slug length 20, S3 Tables bucket slug length 24, then `-balloon-s3tables`). That is **not identical** to every helper in `sfutils-extvolumes` (e.g. `to_aws_name` has **no** that 24-character cap)—do not assume parity until you align and test.

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_PROFILE` | yes | Credential profile for real AWS |
| `AWS_REGION` | recommended | Overrides profile default region |
| `LAB_USERNAME` | no | Workshop participant id; when set, you can leave **`BRONZE_BUCKET_NAME`** / **`BRONZE_S3TABLES_BUCKET_NAME`** empty for derived defaults (see [`.env.example`](../../.env.example)) |
| `BRONZE_BUCKET_NAME` | yes for `glue-setup` / `load` | General-purpose S3 warehouse bucket; **`glue-setup` creates it if missing** (idempotent). With **`LAB_USERNAME`**, omit for **`<slug>-balloon-bronze`** or set a short suffix → **`<slug>-<suffix>`**; without **`LAB_USERNAME`**, set the full global name. Warehouse URI `s3://<bucket>/iceberg/` is printed after `glue-setup` and saved in `.aws-config/bronze-warehouse-uri.txt`. |
| `GLUE_DATABASE` | no | Default `balloon_pops`, or `<glue_slug>_balloon_pops` when **`LAB_USERNAME`** is set and this var is unset |
| `BRONZE_S3TABLES_BUCKET_NAME` | yes for `s3tables-setup` | Globally unique **table bucket** name (`[0-9a-z-]{3,63}`). With **`LAB_USERNAME`**, leave empty for **`<slug>-balloon-s3tables`** or set a suffix (same rules as **`BRONZE_BUCKET_NAME`**) |
| `BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX` | no | If `1` / `true` / `yes` / `y` / `on`, appends **`-<epoch_millis>`** to the resolved table-bucket name **once** when **`s3tables-setup`** runs (not on every `derive` / summary / IAM call—avoids IAM vs Snowflake drift). **`s3tables-setup`** writes **`.aws-config/s3tables-table-bucket-arn.txt`** and **`bronze-s3tables-last-bucket-name.txt`**. Snowflake tools read the bucket from those files when env overrides are unset. **`bronze:cleanup`** removes bronze **`.aws-config/`** files after successful teardown |
| `S3TABLES_NAMESPACE` | no | Default `balloon_pops` |
| `BRONZE_LOAD_DURATION_MINUTES` | no | Generator batch length when **not** using row/synthetic mode (default **5**; max **240**) |
| `BRONZE_GENERATOR_DELAY` | no | Seconds between pops in generator mode (falls back to **`DELAY`**; default **1.0**, min **0.05**) |
| `NUM_PLAYERS` | no | Player pool size for generator batch (default **12**) |
| `BRONZE_SAMPLE_ROW_COUNT` | no | If set, forces **synthetic** mode: that many **raw** `GameEvent` rows appended to **`balloon_game_events`** (max **100000**); overridden by **`--duration-minutes`** on the CLI |

## Tasks (from repo root)

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
# Workshop: set LAB_USERNAME in .env and leave bucket vars empty, or solo:
export BRONZE_BUCKET_NAME=my-bronze-bucket
export BRONZE_S3TABLES_BUCKET_NAME=my-lab-table-bucket-001

task bronze:render-iam    # optional: writes .aws-config/bronze-glue-writer-policy.rendered.json
task bronze:glue-setup
task bronze:s3tables-setup
task bronze:load
# After task snowflake:create-glue-catalog-read-role (vended-credentials path):
# task bronze:lakeformation-setup-dry-run
# task bronze:lakeformation-setup
task bronze:load-more   # optional: append additional rows for extended exercises
# or
task bronze:all

# later (teardown metadata resources only)
task bronze:cleanup-dry-run
task bronze:cleanup
```

## Two AWS surfaces (by design)

1. **Glue Data Catalog + S3 warehouse** — `glue-setup` + **`load-bronze-sample`** append Iceberg rows to **`balloon_game_events`** (column **`event`** = JSON text per pop). **Default:** simulate **`packages/generator`** pops for **5 minutes** at **`DELAY` / `BRONZE_GENERATOR_DELAY`** seconds per pop (same rate as Kafka). **Optional:** **`--row-count`** / **`BRONZE_SAMPLE_ROW_COUNT`** for a fast synthetic fill (`page_id` inside JSON is **0** until a real Kafka pipeline sets it).
2. **Amazon S3 Tables** (table bucket + namespace + empty ICEBERG table **`balloon_game_events`**) — `s3tables-setup` provisions the **S3 Tables** layout for **Snowflake Glue Iceberg REST** / analytics alignment; rows are not duplicated there automatically until you wire a writer to that catalog.

## CLI (Click; Windows / macOS / Linux)

Entry points are registered in the root **`pyproject.toml`** under **`[project.scripts]`** (run from repo root after **`uv sync`**):

| `uv run …` | Role |
|--------|------|
| `uv run check-lab-prereqs` | Verify lab CLIs on `PATH` and **`aws sts get-caller-identity`** (same as `task check-tools`) |
| `uv run bronze-cli glue-setup` | Create Glue database + dump `.aws-config/glue-database.json` and `.aws-config/bronze-warehouse-uri.txt` (add `--dry-run` for a plan) |
| `uv run bronze-cli s3tables-setup` | `aws s3tables` create bucket / namespace / **`balloon_game_events`** ICEBERG table (`--dry-run` lists plan, read-only) |
| `uv run bronze-cli render-iam` | Substitute `${VAR}` in policy template → `.aws-config/`; sets **`BRONZE_S3_ARN`** from **`BRONZE_BUCKET_NAME`** internally (`--dry-run` prints JSON only) |
| `uv run bronze-cli snowflake-summary` | Read-only: print exports / ARNs / Glue REST URI + table names for Snowflake catalog / CLD prep (`--json` for one object) |
| `uv run bronze-cli lakeformation-setup` | Lake Formation prep for Snowflake vended reads: **`register_resource`** with **`HybridAccessEnabled=False`**, **`WithFederation=False`**, then Glue DB defaults + LF grants (`--dry-run` to preview). Needs **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** and **`glue-database.json`**. Optional env: **`LAKE_FORMATION_BRONZE_DATA_ACCESS_ROLE_NAME`**, **`LAKE_FORMATION_ADMIN_ESCAPE_PRINCIPAL_ARN`**. |
| `uv run bronze-cli cleanup` | Delete Glue tables/database + S3 Tables namespace/table bucket (`--dry-run` first; requires confirmation or `--yes`) |
| `uv run load-bronze-sample` | Append rows: default **generator** batch (`--duration-minutes M`, or env); **`--row-count N`** synthetic mode; **`--dataset more`** second batch |

**Task** shortcuts: `task bronze:glue-setup`, `task bronze:s3tables-setup`, `task bronze:render-iam`, `task bronze:snowflake-summary`, `task bronze:snowflake-summary-json`, `task bronze:load`, `task bronze:lakeformation-setup`, `task bronze:lakeformation-setup-dry-run`, `task bronze:cleanup`. Dry-run variants (included Taskfiles do not forward `--` args reliably): `task bronze:glue-setup-dry-run`, `task bronze:s3tables-setup-dry-run`, `task bronze:render-iam-dry-run`, `task bronze:cleanup-dry-run`.

For **`snowflake-summary`**, Task only forwards extra CLI flags after a bare `--` (see [Forward CLI arguments](https://taskfile.dev/usage/#forwarding-cli-arguments-to-commands)): `task bronze:snowflake-summary -- --json`. Prefer **`task bronze:snowflake-summary-json`** when you only need JSON.
Use `task bronze:load-more` to append a second batch after `bronze:load`. Examples: `uv run load-bronze-sample --duration-minutes 15` (more pops), `uv run load-bronze-sample --row-count 500` (synthetic stress), `uv run load-bronze-sample --row-count 20` (smoke). With **Task**, pass flags after `--`: `task bronze:load -- --duration-minutes 20`.

Each subcommand accepts **Click options** with matching **`envvar=`** names (for example `--bronze-bucket-name` / `BRONZE_BUCKET_NAME` on **`glue-setup`** and **`render-iam`**, `--s3tables-bucket` / `BRONZE_S3TABLES_BUCKET_NAME`), so you can override `.env` for one-off runs:  
`uv run bronze-cli glue-setup --aws-profile prod --bronze-bucket-name my-bucket`

`cleanup` removes Glue/S3 Tables metadata only. It does **not** delete objects under `s3://<BRONZE_BUCKET_NAME>/iceberg/` in your warehouse bucket.

## Snowflake catalog trust (Phase 2)

For **Glue Iceberg REST** catalog integration, IAM **trust** on your `SIGV4_IAM_ROLE` is generated separately: **`task snowflake:render-glue-catalog-trust`** (see [snowflake/lab/README.md](../../snowflake/lab/README.md)). That follows the same **`snow sql` + template → `.aws-config/`** pattern as **sfutils-extvolumes** for external volumes, but targets **`DESC CATALOG INTEGRATION`** output instead. By default **`bronze-cli cleanup`** re-reads **repo** **`.aws-config/`** ( **`glue-database.json`**, S3 Tables ARN / last-bucket name — not **`~/.aws-config`**) so targets match the last **`glue-setup`** / **`s3tables-setup`**; pass **`--no-aws-config`** to use only env / **`LAB_USERNAME`** derivation. After successful deletes it removes bronze-authored **`.aws-config/`** files so the next run does not point at torn-down resources.

## Relationship to `packages/generator`

[`common.game_generator.BalloonGameGenerator`](../../packages/common/src/common/game_generator.py) is shared with **`packages/generator`** (Kafka producer). **`load-bronze-sample`** replays the same pop logic in-process and appends each pop as one row in **`balloon_game_events`**. Use **`task generator-local`** when you need a live stream into Kafka.
For denser data, increase **`BRONZE_LOAD_DURATION_MINUTES`** or lower **`BRONZE_GENERATOR_DELAY`**; for a fixed row count, use **`--row-count`** / **`BRONZE_SAMPLE_ROW_COUNT`**.
