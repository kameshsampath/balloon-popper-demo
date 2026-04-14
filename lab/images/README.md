# Lab images (screenshots)

PNG (or WebP) files referenced from [bronze-landing-zone.md](../bronze-landing-zone.md). Add them when you finalize workshop or quickstart visuals; until then the Markdown image links will appear broken in some viewers.

## Bronze load — AWS Console (capture during manual test)

Use the **same** account, region, `GLUE_DATABASE`, and `BRONZE_BUCKET_NAME` as your successful `task bronze:load` run. Crop or blur account IDs if you publish publicly.

| File | What to capture |
|------|------------------|
| `bronze-glue-databases.png` | **Glue → Data catalog → Databases**: list including your bronze database (e.g. `balloon_pops` or `<user>_balloon_pops`). |
| `bronze-glue-database-detail.png` | **Glue → same database →** details pane showing **Location** / **Location URI** = `s3://<BRONZE_BUCKET_NAME>/iceberg/`. |
| `bronze-glue-tables-list.png` | **Glue → Tables** (scoped to that database): **`balloon_game_events`** visible. |
| `bronze-glue-table-iceberg-detail.png` | **Glue → `balloon_game_events`**: properties showing **Apache Iceberg** (or **Table format: Iceberg**) and relevant location/metadata fields. |
| `bronze-s3-bucket.png` | **S3 → Buckets**: row for **`BRONZE_BUCKET_NAME`** (optional if redundant with next shot). |
| `bronze-s3-iceberg-prefix.png` | **Optional.** **S3 → bucket → `iceberg/`**: `metadata/` and `data/` (or similar) after load. Skip if the tree is noisy or redundant with Glue; CLI `aws s3 ls` still validates. |
| `bronze-s3tables-list.png` | **Amazon S3 Tables → Table buckets** (or equivalent): list including **`BRONZE_S3TABLES_BUCKET_NAME`** after **`s3tables-setup`**. Same account/region as **`AWS_PROFILE`**. |

### Quickstart (`sfquickstarts`)

The published guide expects the **same filenames** under **`sfguides/lakehouse-iceberg-production-pipelines/assets/`** (see [assets/README.md](../../sfguides/lakehouse-iceberg-production-pipelines/assets/README.md)). Copy from this folder when you sync the quickstart.

Console navigation names can vary slightly by AWS Region and UI revision; align with **Glue Data catalog** and **S3** as in [AWS Glue documentation](https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html).
