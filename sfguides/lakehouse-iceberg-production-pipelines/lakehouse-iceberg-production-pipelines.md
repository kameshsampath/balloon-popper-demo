author: Kamesh Sampath, Gilberto Hernandez
id: lakehouse-iceberg-production-pipelines
categories: snowflake-site:taxonomy/solution-center/certification/quickstart,snowflake-site:taxonomy/product/data-engineering,snowflake-site:taxonomy/product/analytics
language: en
summary: Stop pipeline sprawl and the cost of data duplication. In this advanced lab, you will learn to perform secure, in-place transformations across your entire data estate. You will connect externally managed Iceberg tables with Catalog Linked Databases to always work on fresh data without ETL, build efficient and declarative pipelines with Dynamic Tables for Iceberg preserving multi-engine access to your data, and implement business continuity to ensure your production data is always available.
environments: web
status: Published
feedback link: https://github.com/Snowflake-Labs/sfguides/issues

# Lakehouse Transformations: Build Production Pipelines for your Iceberg Tables

## Overview

This quickstart shows how to build a bronze-to-silver Iceberg pipeline with AWS and Snowflake, without introducing a separate ETL copy into a second storage system. You first prepare a bronze Iceberg landing zone in AWS (Glue catalog, S3 warehouse, and optional S3 Tables control plane), then connect Snowflake to the same catalog and continue with Catalog Linked Databases and Dynamic Iceberg Tables.

The guide is intentionally bronze-first so learners can see exactly what data exists before running Snowflake catalog integration SQL.

### What You'll Learn

- How to prepare a workshop-safe bronze layer on AWS using Glue, S3, and task-driven automation.
- How Snowflake uses catalog integration and linked catalogs to query externally managed Iceberg metadata.
- How to evolve bronze data into production-friendly Dynamic Iceberg Tables and analytics surfaces.

### What You'll Build

You will build a working lakehouse workflow where bronze Iceberg tables are created and loaded in AWS, then consumed and transformed in Snowflake. The end state is a repeatable pattern for cross-engine Iceberg access with Snowflake-managed transformation layers.

### Prerequisites

- Access to a [Snowflake account](https://signup.snowflake.com/?utm_source=snowflake-devrel&utm_medium=developer-guides&utm_cta=developer-guides)
- Access to an AWS account with permissions for Glue, S3, and S3 Tables (if you run that optional control-plane setup)
- Local environment with `uv`, `task`, and AWS CLI available on `PATH`

## Tools and prerequisites

### Accounts and permissions

- AWS account and profile (`AWS_PROFILE`) that can create/update Glue database metadata and access your bronze S3 warehouse bucket.
- Snowflake account with permissions to create catalog integration and linked database objects in your target role/database.

### Local toolchain

From the repository root:

```bash
uv sync
task check-tools
```

`task check-tools` validates required CLIs for this lab flow (`aws`, `snow`, `task`, `envsubst`, `jq`, `cortex`, `uv`) and recommended helpers (`direnv`, `curl`, `openssl`).

### Environment inputs

Use `.env.example` as your source of truth, then set values in `.env` (never commit `.env`):

- `AWS_PROFILE`
- `AWS_REGION`
- `LAB_USERNAME` (recommended for workshop-shared AWS accounts)
- `BRONZE_WAREHOUSE`
- `BRONZE_S3_ARN`
- Optional overrides such as `GLUE_DATABASE` and `BRONZE_S3TABLES_BUCKET_NAME`

### Task and script entrypoints

Bronze automation uses `task bronze:*` and Python entrypoints declared in `pyproject.toml`:

- `uv run bronze-cli ...`
- `uv run load-bronze-sample`

For command details and expected outputs, see `tools/bronze_preload/README.md`.

## Bronze landing zone

This section is the first hands-on chapter because all downstream Snowflake steps assume these tables already exist.

### Run bronze setup

Use these tasks in order (or `task bronze:all` once prerequisites are in place):

```bash
task bronze:render-iam          # optional policy render helper
task bronze:glue-setup
task bronze:s3tables-setup
task bronze:load
```

Dry-run variants are available to preview behavior:

```bash
task bronze:render-iam-dry-run
task bronze:glue-setup-dry-run
task bronze:s3tables-setup-dry-run
```

### Cleanup bronze resources

At the end of workshop runs, you can remove bronze metadata resources with:

```bash
task bronze:cleanup-dry-run
task bronze:cleanup
```

This teardown removes Glue/S3 Tables metadata created by bronze automation. It does not delete data files in your general-purpose S3 warehouse path.

### Verify what you have

After bronze setup, you should have these Iceberg tables in your Glue database:

- `leaderboard`
- `balloon_color_stats`
- `realtime_scores`
- `balloon_colored_pops`
- `color_performance_trends`

Use this detailed runbook for full step-by-step setup, validation, and troubleshooting:

- `lab/bronze-landing-zone.md`
- `lab/bronze-landing-zone-MANUAL-TEST.md`

In the next phase, this guide will add Snowflake catalog integration and linked database sections that consume the bronze objects created here.
