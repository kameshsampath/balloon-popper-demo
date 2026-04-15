# Local AWS lab config (generated)

This directory holds **machine-local** artifacts for the bronze landing path: rendered IAM policy JSON, trust-policy snippets, optional `aws` CLI output you save for debugging, etc.

**After bronze setup, treat Glue-related names here as source of truth** (not duplicate values in **`.env`** unless you intentionally override). Typical files:

| Written by | Files (examples) | Use |
|------------|------------------|-----|
| **`bronze:glue-setup`** | **`glue-database.json`**, **`bronze-warehouse-uri.txt`** | Glue database name, warehouse bucket, account id for Snowflake **`CATALOG_NAME`** |
| **`bronze:s3tables-setup`** | **`s3tables-table-bucket-arn.txt`**, **`bronze-s3tables-last-bucket-name.txt`**, optional **`s3tables-*.json`** | S3 Tables table-bucket (ARN is canonical; last-bucket line is the same logical bucket, including any **`-<epoch_millis>`** when **`BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX`** was set during that run) |
| **`task snowflake:create-glue-catalog-read-role`** | **`snowflake-glue-catalog-iam-role-arn.txt`** | SIGV4 role ARN for generated SQL |
| **`task bronze:lakeformation-setup`** | **`lake-formation-bronze-data-access-role-arn.txt`** | LF S3 data-access role ARN (**not** the SIGV4 role; used by `register-resource`) |

**S3 Tables bucket resolution** ( **`snowflake-lab-sql generate`**, **`bronze-cli snowflake-summary`** ): CLI **`--s3tables-bucket`** (generate only) → **`SNOWFLAKE_S3TABLES_BUCKET_NAME`** → parse name from **`s3tables-table-bucket-arn.txt`** → first line of **`bronze-s3tables-last-bucket-name.txt`** → **`BRONZE_S3TABLES_BUCKET_NAME`**. Keeps generated catalog SQL aligned with the optional S3 Tables control-plane bucket.

**`bronze:cleanup`** ( **`bronze-cli cleanup`** ) reads this directory under the **repository root** (not **`~/.aws-config`**): it overlays **`GLUE_DATABASE`** / **`BRONZE_BUCKET_NAME`** from **`glue-database.json`** and **`BRONZE_S3TABLES_BUCKET_NAME`** from the resolver above when those files exist, unless you pass **`--no-aws-config`**. After **successful** cleanup (non–dry-run), **bronze-authored** files listed above are **deleted** from **`.aws-config/`** so a stale clone does not keep torn-down names; **Snowflake** artifacts (**`snowflake-glue-catalog-*`**) are **not** removed.

**`snowflake-lab-sql generate`** and **`snowflake-catalog-iam create-read-role`** **fail fast** if **`glue-database.json`** is missing. **`generate`** in S3 Tables catalog mode also needs the table-bucket resolved from files or env — run the matching **`task bronze:*`** steps first.

- Use **`AWS_PROFILE`** (and **`AWS_REGION`**) with the real AWS account; scripts should write here at **runtime**, not commit filled files.
- Everything except this `README` and any `*.example` files is **gitignored**—do not paste secrets into the repo.

Templates live under **`lab/aws/`** (bronze writer policy, **Snowflake Glue catalog trust** stub, etc.). Rendered trust for catalog integration: **`snowflake-glue-catalog-trust-policy.rendered.json`** (from **`task snowflake:render-glue-catalog-trust`**).

**Snowflake Glue REST `SIGV4_IAM_ROLE`:** Default path: **`task snowflake:create-glue-catalog-read-role`** creates the role and writes **`snowflake-glue-catalog-iam-role-arn.txt`** (first line = ARN); **`generate-lab-sql`** uses that file when **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** is unset. Override the signer role only if you use your own IAM role: export **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** or edit the **`.txt`** (see [snowflake-glue-catalog-iam-role-arn.example](snowflake-glue-catalog-iam-role-arn.example), [lab/snowflake-catalog-cld.md](../lab/snowflake-catalog-cld.md)). Not the same principal as the bronze PyIceberg writer unless you merged both by design.

**Defaults reminder:** **`task snowflake:print-env-hints`** lists repo standard **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`**, linked-database default, and optional trial **`SNOWFLAKE_*`** overrides.

**Create SIGV4 read role (AWS):** **`task snowflake:create-glue-catalog-read-role`** writes **`snowflake-glue-catalog-iam-role-arn.txt`** after creating IAM role **`snowflake_glue_catalog_read`** (see [lab/snowflake-catalog-cld.md](../lab/snowflake-catalog-cld.md)). After **`task snowflake:render-glue-catalog-trust`**, run **`task snowflake:apply-glue-catalog-trust-from-rendered`** to replace bootstrap trust with Snowflake’s principal + external ID.
