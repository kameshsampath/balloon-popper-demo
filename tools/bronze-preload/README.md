# Bronze preload (AWS + PyIceberg)

Land **sample** balloon analytics rows into **AWS Glue Data Catalog** Iceberg tables on **S3**, using the same logical names as the legacy RisingWave sinks (`balloon_pops.*`).

## Prerequisites

- **AWS account** and **AWS CLI v2** (for `s3tables` commands, use **2.34+**).
- **`AWS_PROFILE`** set to a profile with permissions for Glue, S3, and (if you run `bronze:s3tables-setup`) S3 Tables control plane. See [lab/aws/README.md](../../lab/aws/README.md) to render a starter policy into `.aws-config/`.
- **`uv`** and repo dependencies: `uv sync`.
- **Optional — Snowflake-backed bucket + external volume:** this repo depends on [Snowflake-Labs/sfutils-extvolumes](https://github.com/Snowflake-Labs/sfutils-extvolumes). Use **`task bronze:extvolume-create`** (or `bronze:extvolume-dry-run`) when you want **`sfutils-extvolumes create`** to provision the **S3 bucket**, IAM role/policy, and **Snowflake external volume** in one step (requires **`snow`** CLI configured). Then point **`BRONZE_WAREHOUSE`** at `s3://<created-bucket>/iceberg/` using the tool’s naming rules (`{prefix}-{bucket}` by default).

## Environment

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_PROFILE` | yes | Credential profile for real AWS |
| `AWS_REGION` | recommended | Overrides profile default region |
| `BRONZE_WAREHOUSE` | yes for `load` | `s3://your-bucket/prefix/` — Iceberg warehouse root on **general-purpose S3** |
| `GLUE_DATABASE` | no | Default `balloon_pops` |
| `BRONZE_S3TABLES_BUCKET_NAME` | yes for `s3tables-setup` | Globally unique **table bucket** name (`[0-9a-z-]{3,63}`) |
| `S3TABLES_NAMESPACE` | no | Default `balloon_pops` |
| `BRONZE_S3_ARN` | for `render-iam` | e.g. `arn:aws:s3:::your-warehouse-bucket` |
| `BRONZE_EXTVOLUME_BUCKET` | for `extvolume-*` | Base name passed to `sfutils-extvolumes create --bucket` (default `balloon-bronze-warehouse`) |

## Tasks (from repo root)

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export BRONZE_S3TABLES_BUCKET_NAME=my-lab-table-bucket-001

# Optional first — create S3 + Snowflake external volume (see sfutils-extvolumes README for names):
# export BRONZE_EXTVOLUME_BUCKET=balloon-bronze-warehouse
# task bronze:extvolume-dry-run
# task bronze:extvolume-create
# export BRONZE_WAREHOUSE=s3://<username>-balloon-bronze-warehouse/iceberg/
# export BRONZE_S3_ARN=arn:aws:s3:::<username>-balloon-bronze-warehouse

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

## Scripts

| Script | Role |
|--------|------|
| `scripts/glue-setup.sh` | `aws glue create-database` + dump `.aws-config/glue-database.json` |
| `scripts/s3tables-setup.sh` | `aws s3tables` create bucket / namespace / five tables |
| `scripts/render-iam.sh` | `envsubst` policy template → `.aws-config/` |
| `load_sample.py` | PyIceberg append sample rows |

## Relationship to `packages/generator`

Event shapes mirror [packages/common/](../../packages/common) `GameEvent` / `GAME_CONFIG` for future alignment with full synthetic loads.
