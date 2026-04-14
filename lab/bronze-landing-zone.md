# Bronze landing zone (prerequisite)

This document is the **detailed** prerequisite for the Snowflake lab: **Iceberg bronze on S3** and a **REST catalog** Snowflake can use before **`CREATE DATABASE … LINKED_CATALOG`**.

**Phase 0 — environment:** copy [`.env.example`](../.env.example) to `.env`, fill in **AWS** and **bronze** variables (never commit `.env`). Run **`task check-tools`** from the repo root to confirm required CLIs (**aws**, **snow**, **task**, **envsubst**, **jq**, **cortex**, **uv**) and recommended tools (**direnv**, **curl**, **openssl**) are on your `PATH` (see [README](../README.md)). Install **[direnv](https://direnv.net/)** and allow the repo (e.g. `direnv allow`) so `.envrc` loads `.env` automatically. Extend `.env.example` as new phases add Snowflake CLI, PAT, or DuckDB IRC variables.

**Shared AWS account / workshop:** set **`LAB_USERNAME`** (one id per participant) so **`GLUE_DATABASE`** defaults when unset, and **`BRONZE_BUCKET_NAME`** / **`BRONZE_S3TABLES_BUCKET_NAME`** get a per-participant prefix (see [`.env.example`](../.env.example)). **`S3TABLES_NAMESPACE`** stays `balloon_pops` inside each participant’s table bucket unless you change it deliberately.

### Environment variables reference

| Variable | Used by | Purpose |
|----------|---------|---------|
| `AWS_PROFILE` | all `task bronze:*` commands | Choose AWS credentials/profile for real account operations |
| `AWS_REGION` | all `task bronze:*` commands | Ensure Glue/S3/S3 Tables calls target the correct region |
| `LAB_USERNAME` | derivation in `bronze_cli.py` | Derives **`GLUE_DATABASE`** when unset; prefixes **`BRONZE_BUCKET_NAME`** and **`BRONZE_S3TABLES_BUCKET_NAME`** unless already **`<bucket_slug>-…`** |
| `BRONZE_BUCKET_NAME` | `bronze:glue-setup`, `bronze:load`, `bronze:render-iam` | General-purpose S3 bucket (must exist). With **`LAB_USERNAME`**, defaults to **`<bucket_slug>-balloon-bronze`** or **`<bucket_slug>-<your-suffix>`** if you set a short name; warehouse URI is `s3://<bucket>/iceberg/` (printed after `glue-setup`, `.aws-config/bronze-warehouse-uri.txt`). **`render-iam`** derives **`arn:aws:s3:::<bucket>`** for the policy (no separate ARN env var). |
| `GLUE_DATABASE` (optional) | `bronze:glue-setup`, `bronze:load` | Override derived/default Glue database name |
| `BRONZE_S3TABLES_BUCKET_NAME` | `bronze:s3tables-setup` | S3 Tables bucket; same **`<bucket_slug>-balloon-*`** pattern as **`BRONZE_BUCKET_NAME`** (empty + **`LAB_USERNAME`** → **`<bucket_slug>-balloon-s3tables`**) |
| `BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX` (optional) | `bronze_aws.derive_bronze_resource_names` | Truthy values append **`-<epoch_millis>`** for unique test bucket names; **`s3tables-setup`** writes **`.aws-config/bronze-s3tables-last-bucket-name.txt`**. **`bronze:cleanup`** reads that file (repo **`.aws-config/`**, not **`~/.aws-config`**) by default so teardown matches the last run; use **`uv run bronze-cli cleanup --no-aws-config`** if you must ignore on-disk hints. |
| `S3TABLES_NAMESPACE` (optional) | `bronze:s3tables-setup`, `bronze:cleanup` | Namespace to create/manage/delete inside S3 Tables bucket |

**Manual QA:** follow [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md).

The Quickstart **Setup** section should summarize steps here and link to this file. **Do not** make “load bronze” the first main Snowflake chapter—learners start Snowflake hands-on at **CLD**.

## What gets created in AWS Glue

When you use the **Glue / S3 Tables** path, the workshop should create (or register) an Iceberg **Glue database** and a single raw-events **table** **`balloon_game_events`**. Each row stores one **JSON object** in string column **`event`** (Kafka-style **PLAIN JSON** payload: `player`, `balloon_color`, `score`, `page_id`, `favorite_color_bonus`, `event_ts`). **Snowflake Dynamic Iceberg Tables** use JSON extraction (for example **`PARSE_JSON`**) to mirror [``polaris-forge-setup/templates/source.sql.j2``](../polaris-forge-setup/templates/source.sql.j2) MVs; see [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md).

| Glue database (example) | Raw Iceberg table | Columns (logical) |
|-------------------------|-------------------|---------------------|
| `balloon_pops` | `balloon_game_events` | `event` (VARCHAR/STRING JSON per row) |

Replace `balloon_pops` with your **Glue catalog / S3 Tables namespace** if it differs. Match **`CATALOG_NAME`** in Snowflake `CREATE CATALOG INTEGRATION` so **`LINKED_CATALOG`** sees the same objects. Historical five-table schema notes remain in [docs/iceberg_schema_design.md](../docs/iceberg_schema_design.md) for reference only.

**Polaris-only path:** publish an analogous list (REST **namespace** + **table** identifiers) in Prerequisites instead of Glue.

## Automation (`task bronze:…`)

Modular tasks live in [`.taskfiles/bronze.yml`](../.taskfiles/bronze.yml) (included from the root `Taskfile.yml`). Implementation is **Python + Click** ([`tools/bronze_preload/bronze_cli.py`](../tools/bronze_preload/bronze_cli.py)) so the same commands work on **Windows, Linux, and macOS** (still requires **AWS CLI** on `PATH` for `s3tables` and for `sts` in `render-iam`). Use a **real** AWS account: set **`AWS_PROFILE`** (and usually **`AWS_REGION`**). See [tools/bronze_preload/README.md](../tools/bronze_preload/README.md) for full env vars.

| Task | Purpose |
|------|---------|
| `task bronze:render-iam` | Render `lab/aws/bronze-glue-writer-policy.json` → `.aws-config/*.rendered.json` (policy **`BRONZE_S3_ARN`** is derived from **`BRONZE_BUCKET_NAME`**) |
| `task bronze:render-iam-dry-run` | Print substituted policy JSON only (no file write) |
| `task bronze:glue-setup` | Create Glue database for **`GLUE_DATABASE`** with `LocationUri` **`s3://<BRONZE_BUCKET_NAME>/iceberg/`** |
| `task bronze:glue-setup-dry-run` | Preview Glue setup (read-only **GetDatabase**; no create / no local JSON) |
| `task bronze:s3tables-setup` | **`aws s3tables`** — table bucket **`BRONZE_S3TABLES_BUCKET_NAME`**, namespace **`balloon_pops`**, one **`ICEBERG`** table **`balloon_game_events`** (CLI **2.34+**) |
| `task bronze:s3tables-setup-dry-run` | Preview S3 Tables setup (read-only list; no creates) |
| `task bronze:snowflake-summary` | Read-only: print exports, ARNs, Glue Iceberg REST URI, and table names for Snowflake catalog / CLD prep (optional `task bronze:snowflake-summary-json` for JSON) |
| `task bronze:load` | **`load_sample.py`** — default **generator** replay (**`BRONZE_LOAD_DURATION_MINUTES`** / **`DELAY`**) appends each **`GameEvent`** as one row in **`balloon_game_events`**; **`--row-count`** / **`BRONZE_SAMPLE_ROW_COUNT`** for synthetic mode |
| `task bronze:load-more` | Append a second prebuilt dataset into the same Glue Iceberg tables (optional) |
| `task bronze:cleanup-dry-run` | Preview bronze cleanup plan (no deletes) |
| `task bronze:cleanup` | Delete Glue tables/database + S3 Tables namespace/table-bucket metadata (asks confirmation unless `--yes`). Overlays **`GLUE_DATABASE`**, **`BRONZE_BUCKET_NAME`**, **`BRONZE_S3TABLES_BUCKET_NAME`** from repo **`.aws-config/glue-database.json`** and **`.aws-config/bronze-s3tables-last-bucket-name.txt`** when present (last local **`glue-setup`** / **`s3tables-setup`**). **Does not** delete or empty **`BRONZE_BUCKET_NAME`** in S3; clear **`iceberg/`** yourself if you want warehouse data removed |
| `task bronze:all` | Runs `glue-setup` → `s3tables-setup` → `load` in strict sequence |

### Glue + S3 warehouse vs S3 Tables (two surfaces)

- **Glue Data Catalog + S3** — `glue-setup` and **`bronze:load`** populate **Iceberg** metadata + files for **`balloon_game_events`** (workshop-friendly raw stream).
- **Amazon S3 Tables** — `s3tables-setup` creates the **table bucket / namespace / ICEBERG** shell for **`balloon_game_events`** for Snowflake **Glue Iceberg REST** alignment; it is **not** auto-filled by `load_sample.py` (add a Glue-REST writer later if you want one copy only).

### Athena (and other SQL clients)

**`task bronze:load`** registers **Iceberg** tables only in the **AWS Glue Data Catalog** under **`GLUE_DATABASE`**, with data under **`s3://<BRONZE_BUCKET_NAME>/iceberg/`** (PyIceberg `glue` catalog — see [`load_sample.py`](../tools/bronze_preload/load_sample.py)). The loaded table exposes column **`event`** (string holding one JSON object per row); use Athena JSON functions to project fields. In [Amazon Athena](https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html):

1. **Data source:** **`AwsDataCatalog`** (typical).
2. **Catalog:** use the **default** Glue catalog for the account. In the Athena UI this is often **None** / blank / “default” — do **not** pick **`s3tables/<table-bucket>`** from the dropdown; that path is the **S3 Tables** federated catalog (empty Iceberg shells for this lab until another writer commits metadata). If your console shows **`AwsDataCatalog`** / **`awsdatacatalog`** instead of None, that is the same idea: avoid any catalog whose name starts with **`s3tables/`**.
3. **Database:** the **Glue** database from bronze (see **`GLUE_DATABASE`** in `.env` or **`Name`** in `.aws-config/glue-database.json`). With **`LAB_USERNAME`** set and **`GLUE_DATABASE`** unset, it is usually **`<glue_slug>_balloon_pops`** (for example **`ksampath_balloon_pops`**), **not** the string **`balloon_pops`** alone (that name is often the **S3 Tables namespace**, a different object).

If you query through an **S3 Tables** catalog (SQL or UI paths like **`s3tablescatalog/<table-bucket>`** or **`s3tables/…`** in the catalog dropdown), the lab’s S3 Tables **`balloon_game_events`** registration is an **empty shell** until some engine writes Iceberg metadata into that table bucket. Athena then fails with errors such as **missing `metadata_location`**. For the seed dataset from this repo, use the **default Glue** catalog + **`GLUE_DATABASE`**, or **re-load** using a writer that targets S3 Tables.

Keep **secrets** out of Task YAML; use **`.aws-config/`** for generated policy JSON (see [.aws-config/README.md](../.aws-config/README.md)).

### Local config directory (`.aws-config/`)

Use a repo-local **`.aws-config/`** directory (not `~/.aws`) for **generated** IAM JSON, trust-policy fragments, or other outputs from the bronze CLI—filled at **run time** from **environment variables** and **`AWS_PROFILE`**. The tree is **gitignored** except [`.aws-config/README.md`](../.aws-config/README.md) and optional `*.example` files. **Committed** policy **templates** with placeholders should live under **`lab/aws/`** (added when bronze tasks are implemented).

## Recommended order

1. Pick **region** (AWS, S3, Snowflake aligned).
2. **S3 warehouse bucket** — create a general-purpose S3 bucket (console, IaC, or your org’s process). Set **`BRONZE_BUCKET_NAME`** (or use **`LAB_USERNAME`** defaults). **`render-iam`** derives **`arn:aws:s3:::<bucket>`** for the policy template.
3. **IAM** for writers (PyIceberg / Glue role) and bucket policy for Snowflake **storage integration** / **external volume** where your Snowflake lab needs them; use **`task bronze:render-iam`** for the lab’s Glue-writer policy template when applicable.
4. **Glue** path: run `task bronze:glue-setup` then `task bronze:s3tables-setup` (or your CFN equivalent).
5. **REST catalog**: either **Polaris** (reachable from Snowflake, not only `localhost`) or **Glue Iceberg REST** (`https://glue.<region>.amazonaws.com/iceberg`, `CATALOG_API_TYPE = AWS_GLUE`, SIGv4 — see [gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) and Snowflake docs).
6. **Load**: `task bronze:load` (or `task bronze:all` from a clean slate).
7. **Verify**: see [Verify bronze load in the AWS Console](#verify-bronze-load-in-the-aws-console) (Glue + S3 warehouse) and [Verify S3 Tables in the AWS Console](#verify-s3-tables-in-the-aws-console) (table buckets after **`s3tables-setup`**); CLI checks remain in [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md). Optional: Snowflake `DESCRIBE CATALOG INTEGRATION` smoke when that phase exists.
8. **Cleanup (optional end-of-lab)**: `task bronze:cleanup-dry-run` then `task bronze:cleanup` when you want to remove **Glue and S3 Tables metadata** only. Your **general-purpose warehouse bucket** (**`BRONZE_BUCKET_NAME`**, often **`<slug>-balloon-bronze`**) is **not** deleted or emptied; delete **`s3://…/iceberg/`** objects in the console or with **`aws s3 rm`** if you need a full data reset.

## Verify bronze load in the AWS Console

After **`task bronze:load`** (or **`task bronze:all`**), confirm rows landed where Glue and PyIceberg expect: **AWS Glue Data Catalog** (table metadata) and **Amazon S3** (Iceberg warehouse layout under `iceberg/`). Use the same **Region** and account as **`AWS_PROFILE`**.

AWS occasionally renames console areas; if labels differ, use the service search bar for **Glue** and **S3** and open **Data catalog** / **Databases** for Glue.

### AWS Glue Data Catalog

1. Open the [AWS Management Console](https://console.aws.amazon.com/) with permissions to read Glue.
2. Go to **Glue** → **Data catalog** → **Databases** (or **Catalog** → **Databases**, depending on console layout).
3. Open the database whose name matches **`GLUE_DATABASE`** (see [What gets created in AWS Glue](#what-gets-created-in-aws-glue); default **`balloon_pops`** or derived when **`LAB_USERNAME`** is set).
4. Open **Tables** for that database. You should see **`balloon_game_events`** (raw event stream for CLD + Dynamic Iceberg Tables in Snowflake).
5. Open **`balloon_game_events`**. Confirm the table type / format indicates **Apache Iceberg** and that storage references stay under **`s3://<BRONZE_BUCKET_NAME>/iceberg/`**.

![Glue Data Catalog — Databases list including your GLUE_DATABASE](images/bronze-glue-databases.png)

![Glue — Database details showing Location URI under s3://…/iceberg/](images/bronze-glue-database-detail.png)

![Glue — Tables list for the bronze database (balloon_game_events)](images/bronze-glue-tables-list.png)

![Glue — Iceberg properties for balloon_game_events](images/bronze-glue-table-iceberg-detail.png)

### Amazon S3 (warehouse bucket)

1. Open **S3** → **Buckets** → the bucket named **`BRONZE_BUCKET_NAME`**.
2. Open the **`iceberg/`** prefix (this matches Glue **LocationUri** `s3://<BRONZE_BUCKET_NAME>/iceberg/` from **`glue-setup`**).
3. After load, expect Iceberg-style **`metadata/`** and **`data/`** (or equivalent) keys under that prefix.

![S3 — Buckets list highlighting BRONZE_BUCKET_NAME](images/bronze-s3-bucket.png)

**Optional screenshot** (`images/bronze-s3-iceberg-prefix.png`): after you open the **`iceberg/`** prefix in the console, capture **`metadata/`** and **`data/`** (or equivalent) so learners see proof of Iceberg files on S3. Omit the file until you have a clear shot; the CLI check `aws s3 ls s3://$BRONZE_BUCKET_NAME/iceberg/` remains enough to validate.

## Verify S3 Tables in the AWS Console

After **`task bronze:s3tables-setup`**, confirm the **Amazon S3 Tables** control plane shows your **table bucket** (name = **`BRONZE_S3TABLES_BUCKET_NAME`**). Console labels vary; use the top search bar for **S3 Tables** if needed. [S3 Tables](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables.html) stores a separate Iceberg surface from the **Glue + general S3** warehouse: default **`bronze:load`** writes to **`BRONZE_BUCKET_NAME`** / **`iceberg/`** (previous section), while S3 Tables holds the **`balloon_game_events`** **ICEBERG** table definition for Snowflake **Glue Iceberg REST** alignment until another engine commits there.

1. Open **Amazon S3 Tables** → **Table buckets** (or equivalent list view for table buckets in your region).
2. Find the row whose name matches **`BRONZE_S3TABLES_BUCKET_NAME`** (same value as in `.env` or from **`task bronze:snowflake-summary`**).
3. Optional: open that table bucket and confirm namespaces / tables align with **`S3TABLES_NAMESPACE`** (default **`balloon_pops`**) and **`balloon_game_events`**.

![Amazon S3 Tables — table buckets list including BRONZE_S3TABLES_BUCKET_NAME](images/bronze-s3tables-list.png)

**Screenshot file list** (filenames and what each should show): [lab/images/README.md](images/README.md). For the Snowflake Quickstart build, copy the same PNGs into **`sfguides/lakehouse-iceberg-production-pipelines/assets/`** (see [assets/README.md](../sfguides/lakehouse-iceberg-production-pipelines/assets/README.md)).

## Snowflake handoff

Record (outside git): catalog integration **URI**, **OAuth / SIGv4 role ARNs**, **external IDs**, **storage integration** names. Bronze **data paths** must stay consistent with **Dynamic Iceberg Table** **external volume** prefixes documented in the main lab.

## References

- [Iceberg schema (this repo)](../docs/iceberg_schema_design.md)
- [Snowflake: Iceberg REST catalog integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest)
- [Glue + Snowflake IAM / SQL gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426)
- [Lakehouse walkthrough (video)](https://youtu.be/DObaF-Fk1_A)
