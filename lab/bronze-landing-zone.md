# Bronze landing zone (prerequisite)

This document is the **detailed** prerequisite for the Snowflake lab: **Iceberg bronze on S3** and a **REST catalog** Snowflake can use before **`CREATE DATABASE … LINKED_CATALOG`**.

The Quickstart **Setup** section should summarize steps here and link to this file. **Do not** make “load bronze” the first main Snowflake chapter—learners start Snowflake hands-on at **CLD**.

## What gets created in AWS Glue

When you use the **Glue / S3 Tables** path, the workshop should create (or register) an Iceberg **Glue database** and the following **tables** (names align with [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md)):

| Glue database (example) | Tables |
|-------------------------|--------|
| `balloon_pops` | `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends` |

Replace `balloon_pops` with your **Glue catalog / S3 Tables namespace** if it differs. Match **`CATALOG_NAME`** in Snowflake `CREATE CATALOG INTEGRATION` so **`LINKED_CATALOG`** sees the same objects.

**Polaris-only path:** publish an analogous list (REST **namespace** + **table** identifiers) in Prerequisites instead of Glue.

## Automation (`task bronze:…`)

Modular tasks live in [`.taskfiles/bronze.yml`](../.taskfiles/bronze.yml) (included from the root `Taskfile.yml`):

| Task | Purpose |
|------|---------|
| `task bronze:glue-setup` | Glue database, job parameters, IAM **pointers** (implement `aws` CLI / scripts) |
| `task bronze:s3tables-setup` | S3 bucket / S3 Tables catalog steps (implement CLI or CloudFormation wrappers) |
| `task bronze:load` | Land bronze rows (PyIceberg / Glue job — wire to [tools/bronze-preload](../tools/bronze-preload/README.md)) |
| `task bronze:all` | Runs the three steps in order |

Tasks ship as **stubs** until wired; keep **secrets** in the environment / AWS profile, not in Task YAML.

## Recommended order

1. Pick **region** (AWS, S3, Snowflake aligned).
2. **S3** bucket + encryption + prefix layout for Iceberg warehouse.
3. **IAM** for writers (PyIceberg / Glue role) and bucket policy for Snowflake **storage integration** / **external volume** where needed.
4. **Glue** path: run `task bronze:glue-setup` then `task bronze:s3tables-setup` (or your CFN equivalent).
5. **REST catalog**: either **Polaris** (reachable from Snowflake, not only `localhost`) or **Glue Iceberg REST** (`https://glue.<region>.amazonaws.com/iceberg`, `CATALOG_API_TYPE = AWS_GLUE`, SIGv4 — see [gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) and Snowflake docs).
6. **Load**: `task bronze:load` (or `task bronze:all` from a clean slate).
7. **Verify**: Glue / S3 Tables lists tables above; optional Snowflake `DESCRIBE CATALOG INTEGRATION` smoke.

## Snowflake handoff

Record (outside git): catalog integration **URI**, **OAuth / SIGv4 role ARNs**, **external IDs**, **storage integration** names. Bronze **data paths** must stay consistent with **Dynamic Iceberg Table** **external volume** prefixes documented in the main lab.

## References

- [Iceberg schema (this repo)](../docs/iceberg_schema_design.md)
- [Snowflake: Iceberg REST catalog integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest)
- [Glue + Snowflake IAM / SQL gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426)
- [Lakehouse walkthrough (video)](https://youtu.be/DObaF-Fk1_A)
