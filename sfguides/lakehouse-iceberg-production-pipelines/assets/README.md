# Quickstart assets (screenshots)

Snowflake Quickstarts typically keep images next to the guide Markdown under an **`assets/`** directory (same guide id folder). This repo authors captures under **`lab/images/`** first, then **copies** the same filenames here so relative links like `assets/bronze-glue-databases.png` resolve when the guide is built or previewed.

```bash
# From repo root (after captures exist in lab/images/)
cp lab/images/bronze-glue-*.png \
  lab/images/bronze-s3-bucket.png \
  lab/images/bronze-s3tables-list.png \
  sfguides/lakehouse-iceberg-production-pipelines/assets/
# Optional when captured:
# cp lab/images/bronze-s3-iceberg-prefix.png sfguides/lakehouse-iceberg-production-pipelines/assets/
```

Keep **`lab/images/`** as the working copy for **`lab/bronze-landing-zone.md`**; keep **`assets/`** in sync for **`lakehouse-iceberg-production-pipelines.md`** when you publish or open a PR to **sfquickstarts**.

| File | Description |
|------|-------------|
| `bronze-glue-databases.png` | Glue Data Catalog — databases list. |
| `bronze-glue-database-detail.png` | Glue database — Location URI. |
| `bronze-glue-tables-list.png` | Glue — **`balloon_game_events`** in the database table list. |
| `bronze-glue-table-iceberg-detail.png` | Glue — Iceberg properties for **`balloon_game_events`**. |
| `bronze-s3-bucket.png` | S3 — buckets list with warehouse bucket. |
| `bronze-s3tables-list.png` | Amazon S3 Tables — table buckets list (includes **`BRONZE_S3TABLES_BUCKET_NAME`**). |
| `bronze-s3-iceberg-prefix.png` | **Optional** — S3 `iceberg/` prefix with `metadata/` / `data/`. |
