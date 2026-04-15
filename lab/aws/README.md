# IAM policy templates (bronze + Snowflake CLD)

- **`bronze-glue-writer-policy.json`** — Inline policy for a principal that runs **`tools/bronze_preload/bronze_cli.py`** (Glue / S3 Tables setup) and **`load_sample.py`** (Glue + S3 warehouse + optional S3 Tables control plane).

- **`snowflake-glue-catalog-read-policy.json`** — Inline permissions for the **Snowflake Glue Iceberg REST** **`SIGV4_IAM_ROLE`**, rendered by **`uv run snowflake-catalog-iam create-read-role`**: **Glue** reads on **`${GLUE_DATABASE}`** (including **`catalog`** / **`catalog/*`**) plus **Lake Formation** **`GetDataAccess`**, **`GetTemporaryGlueTableCredentials`**, **`GetTemporaryGluePartitionCredentials`** per [Snowflake Step 1](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue#step-1-configure-access-permissions-for-the-aws-glue-data-catalog). **S3 object reads** for vended access use a **separate** LF data-access role and **`task bronze:lakeformation-setup`** (not **`s3:GetObject`** on **`SIGV4`** in this lab path). **Trust** (Snowflake Step 4): **`lab/aws/snowflake-glue-catalog-trust-policy.json`** → **`task snowflake:render-glue-catalog-trust`** → **`task snowflake:apply-glue-catalog-trust-from-rendered`**.

- **`lake-formation-bronze-warehouse-data-access-policy.json`** / **`lake-formation-bronze-warehouse-data-access-trust.json`** — Templates for the **Lake Formation** data-access IAM role (**trust** = **`lakeformation.amazonaws.com`**, **permissions** = S3 read on **`${BRONZE_BUCKET_NAME}`**). This role is **only** for **`register-resource --role-arn`**; do **not** reuse it as **`SIGV4_IAM_ROLE`**. Automation: **`task bronze:lakeformation-setup`**. Manual steps and rationale: [Lake Formation (after bronze load)](../bronze-landing-zone.md#lake-formation-after-bronze-load).

## Render to `.aws-config/` (no secrets committed)

From the repo root, with a real AWS account:

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export GLUE_DATABASE=balloon_pops   # optional with LAB_USERNAME (derived)
export BRONZE_BUCKET_NAME=your-warehouse-bucket   # IAM ARN is derived: arn:aws:s3:::...

task bronze:render-iam
# Preview only: task bronze:render-iam -- --dry-run
```

Or call the CLI directly: `uv run bronze-cli render-iam` (add `--dry-run` to print JSON without writing).

Attach `.aws-config/bronze-glue-writer-policy.rendered.json` to an IAM **user** or **role** you use for local `aws` + PyIceberg, or merge statements into an existing policy.

Tighten **`s3tables:*`** statements to specific ARNs once table buckets are known.
