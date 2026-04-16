# Generated Snowflake lab SQL

Files matching `*.generated.sql` in this directory are produced by:

```bash
task snowflake:print-env-hints    # defaults + SIGV4 reminder
task snowflake:generate-lab-sql
```

They are gitignored. **Default** inputs: **`.aws-config/glue-database.json`** (12-digit **CatalogId** and **Glue database name** for **`CATALOG_NAME`** / **`CATALOG_NAMESPACE`** per [Snowflake Glue REST Step 2](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue#step-2-create-a-catalog-integration-in-snowflake)), **`AWS_REGION`**, and **`SIGV4_IAM_ROLE`** (default first line of **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**).

**S3 Tables** composite **`CATALOG_NAME`**: set **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`** or pass **`--glue-s3tables-catalog`**, plus **`BRONZE_S3TABLES_BUCKET_NAME`** or **`.aws-config/bronze-s3tables-last-bucket-name.txt`** and **`S3TABLES_NAMESPACE`**.

See **[../README.md](../README.md)**, **[lab/snowflake-catalog-cld.md](../../../lab/snowflake-catalog-cld.md)**, and **[lab/snowflake-dynamic-iceberg-tables.md](../../../lab/snowflake-dynamic-iceberg-tables.md)**. **Catalog + CLD:** `task snowflake:generate-lab-sql` → `01` / `02`. **Silver DTs:** `task dt:generate-sql` → **`03_dt_pipelines.generated.sql`** (five tables).

Preview without writing files:

```bash
task snowflake:generate-lab-sql-stdout
```
