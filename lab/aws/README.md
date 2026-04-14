# IAM policy templates (bronze)

- **`bronze-glue-writer-policy.json`** — Inline policy for a principal that runs **`tools/bronze_preload/bronze_cli.py`** (Glue / S3 Tables setup) and **`load_sample.py`** (Glue + S3 warehouse + optional S3 Tables control plane).

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
