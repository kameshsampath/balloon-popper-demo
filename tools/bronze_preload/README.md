# Bronze preload (AWS + PyIceberg)

Land **sample** balloon analytics rows into **AWS Glue Data Catalog** Iceberg tables on **S3**, using the same logical names as the legacy RisingWave sinks (`balloon_pops.*`).

**Manual test checklist:** [lab/bronze-landing-zone-MANUAL-TEST.md](../../lab/bronze-landing-zone-MANUAL-TEST.md).

## Prerequisites

- **Phase 0:** copy [`.env.example`](../../.env.example) to `.env` and set variables (see comments in the example file). Do not commit `.env`.
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
| `LAB_USERNAME` | no | Workshop participant id; when set, defaults **`GLUE_DATABASE`** / **`BRONZE_S3TABLES_BUCKET_NAME`** if unset (see [`.env.example`](../../.env.example)) |
| `BRONZE_WAREHOUSE` | yes for `load` | `s3://your-bucket/prefix/` — Iceberg warehouse root on **general-purpose S3** |
| `GLUE_DATABASE` | no | Default `balloon_pops`, or `<glue_slug>_balloon_pops` when **`LAB_USERNAME`** is set and this var is unset |
| `BRONZE_S3TABLES_BUCKET_NAME` | yes for `s3tables-setup` | Globally unique **table bucket** name (`[0-9a-z-]{3,63}`), or derived from **`LAB_USERNAME`** when unset |
| `S3TABLES_NAMESPACE` | no | Default `balloon_pops` |
| `BRONZE_S3_ARN` | for `render-iam` | e.g. `arn:aws:s3:::your-warehouse-bucket` |

## Tasks (from repo root)

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export BRONZE_S3TABLES_BUCKET_NAME=my-lab-table-bucket-001

export BRONZE_WAREHOUSE=s3://my-bronze-bucket/iceberg/
export BRONZE_S3_ARN=arn:aws:s3:::my-bronze-bucket

task bronze:render-iam    # optional: writes .aws-config/bronze-glue-writer-policy.rendered.json
task bronze:glue-setup
task bronze:s3tables-setup
task bronze:load
# or
task bronze:all

# later (teardown metadata resources only)
task bronze:cleanup-dry-run
task bronze:cleanup
```

## Two AWS surfaces (by design)

1. **Glue Data Catalog + S3 warehouse** — `glue-setup` + **`load-bronze-sample`** create and append **Iceberg** tables your laptop can manage with **PyIceberg** (good for workshop data).
2. **Amazon S3 Tables** (table bucket + namespace + empty ICEBERG tables) — `s3tables-setup` provisions the **S3 Tables** layout for **Snowflake Glue Iceberg REST** / analytics alignment; rows are not duplicated there automatically until you wire a writer to that catalog.

## CLI (Click; Windows / macOS / Linux)

Entry points are registered in the root **`pyproject.toml`** under **`[project.scripts]`** (run from repo root after **`uv sync`**):

| `uv run …` | Role |
|--------|------|
| `uv run check-lab-prereqs` | Verify lab CLIs on `PATH` (same as `task check-tools`) |
| `uv run bronze-cli glue-setup` | Create Glue database + dump `.aws-config/glue-database.json` (add `--dry-run` for a plan) |
| `uv run bronze-cli s3tables-setup` | `aws s3tables` create bucket / namespace / five tables (`--dry-run` lists plan, read-only) |
| `uv run bronze-cli render-iam` | Substitute `${VAR}` in policy template → `.aws-config/` (`--dry-run` prints JSON only) |
| `uv run bronze-cli cleanup` | Delete Glue tables/database + S3 Tables namespace/table bucket (`--dry-run` first; requires confirmation or `--yes`) |
| `uv run load-bronze-sample` | PyIceberg append sample rows |

**Task** shortcuts: `task bronze:glue-setup`, `task bronze:s3tables-setup`, `task bronze:render-iam`, `task bronze:load`, `task bronze:cleanup`. Dry-run variants (included Taskfiles do not forward `--` args reliably): `task bronze:glue-setup-dry-run`, `task bronze:s3tables-setup-dry-run`, `task bronze:render-iam-dry-run`, `task bronze:cleanup-dry-run`.

Each subcommand accepts **Click options** with matching **`envvar=`** names (for example `--bronze-warehouse` / `BRONZE_WAREHOUSE`, `--s3tables-bucket` / `BRONZE_S3TABLES_BUCKET_NAME`), so you can override `.env` for one-off runs:  
`uv run bronze-cli glue-setup --aws-profile prod --bronze-warehouse s3://my/prefix/`

`cleanup` removes Glue/S3 Tables metadata only. It does **not** delete objects in your general-purpose S3 warehouse path (`BRONZE_WAREHOUSE`).

## Relationship to `packages/generator`

Event shapes mirror [packages/common/](../../packages/common) `GameEvent` / `GAME_CONFIG` for future alignment with full synthetic loads.
