# Local AWS lab config (generated)

This directory holds **machine-local** artifacts for the bronze landing path: rendered IAM policy JSON, trust-policy snippets, optional `aws` CLI output you save for debugging, etc. After a successful **`bronze:s3tables-setup`**, **`bronze-s3tables-last-bucket-name.txt`** holds the resolved table-bucket name (including any **`-<epoch_millis>`** suffix when **`BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX`** was set) for cleanup or copy/paste.

**`bronze:cleanup`** ( **`bronze-cli cleanup`** ) reads this directory under the **repository root** (not **`~/.aws-config`**): it overlays **`GLUE_DATABASE`** / **`BRONZE_BUCKET_NAME`** from **`glue-database.json`** and **`BRONZE_S3TABLES_BUCKET_NAME`** from **`bronze-s3tables-last-bucket-name.txt`** when those files exist, unless you pass **`--no-aws-config`**.

- Use **`AWS_PROFILE`** (and **`AWS_REGION`**) with the real AWS account; scripts should write here at **runtime**, not commit filled files.
- Everything except this `README` and any `*.example` files is **gitignored**—do not paste secrets into the repo.

Templates live under **`lab/aws/`** (or similar) once the bronze automation is added.
