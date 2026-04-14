# IAM policy templates (bronze)

- **`bronze-glue-writer-policy.json`** — Inline policy for a principal that runs **`tools/bronze-preload/scripts/*.sh`** and **`load_sample.py`** (Glue + S3 warehouse + optional S3 Tables control plane).

## Render to `.aws-config/` (no secrets committed)

From the repo root, with a real AWS account:

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export GLUE_DATABASE=balloon_pops
export BRONZE_S3_ARN=arn:aws:s3:::your-warehouse-bucket   # no trailing slash

mkdir -p .aws-config
envsubst < lab/aws/bronze-glue-writer-policy.json > .aws-config/bronze-glue-writer-policy.rendered.json
```

Attach `.aws-config/bronze-glue-writer-policy.rendered.json` to an IAM **user** or **role** you use for local `aws` + PyIceberg, or merge statements into an existing policy.

Tighten **`s3tables:*`** statements to specific ARNs once table buckets are known.
