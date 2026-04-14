# Snowflake lab SQL (scaffold)

Ordered scripts for the hands-on lab will live here (e.g. `01_catalog.sql`, `02_cld.sql`, `03_dynamic_tables.sql`). **Phase 1** adds [REFERENCE.md](REFERENCE.md) only—no executable DDL until account placeholders and edition checks are done.

## Snowflake + Glue S3 Tables (gist reference)

The repo does **not** yet vendor the SQL/IAM from [Snowflake s3tables integration (gist)](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426); treat that gist as the starting point when you add `01_catalog.sql` / CLD DDL here. Reconcile with current Snowflake docs before shipping.

| Gist artifact | Intended use in this lab |
|---------------|---------------------------|
| `iceberg_tables.sql` | `CREATE CATALOG INTEGRATION` (Glue IRC), optional `CREATE ICEBERG TABLE` vs `CREATE DATABASE … LINKED_CATALOG`, `DESCRIBE CATALOG INTEGRATION` |
| `iam_policy.json` | **Snowflake integration** IAM role policy (Glue `s3tablescatalog` ARNs + Lake Formation `GetDataAccess`) — **not** the same as [lab/aws/bronze-glue-writer-policy.json](../../lab/aws/bronze-glue-writer-policy.json) (bronze **writer** / PyIceberg) |
| `trust_policy.json` | Trust Snowflake’s `API_AWS_IAM_USER_ARN` + external id from `DESCRIBE CATALOG INTEGRATION` |
