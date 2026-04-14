# Bronze preload (AWS + PyIceberg)

Land **sample** balloon analytics rows into **AWS Glue Data Catalog** Iceberg tables on **S3**, using the same logical names as the legacy RisingWave sinks (`balloon_pops.*`).

**Manual test checklist:** [lab/bronze-landing-zone-MANUAL-TEST.md](../../lab/bronze-landing-zone-MANUAL-TEST.md).

## Prerequisites

- **Phase 0:** copy [`.env.example`](../../.env.example) to `.env` and set variables (see comments in the example file). Do not commit `.env`.
- **AWS account** and **AWS CLI v2** (for `s3tables` commands, use **2.34+**).
- **`AWS_PROFILE`** set to a profile with permissions for Glue, S3, and (if you run `bronze:s3tables-setup`) S3 Tables control plane. See [lab/aws/README.md](../../lab/aws/README.md) to render a starter policy into `.aws-config/`.
- **`uv`** and repo dependencies: `uv sync`.

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
```

## Two AWS surfaces (by design)

1. **Glue Data Catalog + S3 warehouse** — `glue-setup` + **`load_sample.py`** create and append **Iceberg** tables your laptop can manage with **PyIceberg** (good for workshop data).
2. **Amazon S3 Tables** (table bucket + namespace + empty ICEBERG tables) — `s3tables-setup` provisions the **S3 Tables** layout for **Snowflake Glue Iceberg REST** / analytics alignment; rows are not duplicated there automatically until you wire a writer to that catalog.

## CLI (Click; Windows / macOS / Linux)

| Command | Role |
|--------|------|
| `uv run python tools/bronze-preload/bronze_cli.py glue-setup` | Create Glue database + dump `.aws-config/glue-database.json` (add `--dry-run` for a plan) |
| `uv run python tools/bronze-preload/bronze_cli.py s3tables-setup` | `aws s3tables` create bucket / namespace / five tables (`--dry-run` lists plan, read-only) |
| `uv run python tools/bronze-preload/bronze_cli.py render-iam` | Substitute `${VAR}` in policy template → `.aws-config/` (`--dry-run` prints JSON only) |
| `load_sample.py` | PyIceberg append sample rows (unchanged entrypoint) |

**Task** shortcuts: `task bronze:glue-setup`, `task bronze:s3tables-setup`, `task bronze:render-iam`. Dry-run variants (included Taskfiles do not forward `--` args reliably): `task bronze:glue-setup-dry-run`, `task bronze:s3tables-setup-dry-run`, `task bronze:render-iam-dry-run`.

## Relationship to `packages/generator`

Event shapes mirror [packages/common/](../../packages/common) `GameEvent` / `GAME_CONFIG` for future alignment with full synthetic loads.
