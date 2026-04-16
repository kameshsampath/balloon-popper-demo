# Snowflake lab SQL (scaffold)

Step-by-step narrative (create integration → IAM trust → CLD → SHOW → SELECT): **[lab/snowflake-catalog-cld.md](../lab/snowflake-catalog-cld.md)**. **Manual QA:** **[lab/snowflake-cld-MANUAL-TEST.md](../lab/snowflake-cld-MANUAL-TEST.md)**.

**Dynamic Iceberg Tables (silver):** **[lab/snowflake-dynamic-iceberg-tables.md](../lab/snowflake-dynamic-iceberg-tables.md)**. **Manual QA:** **[lab/snowflake-dt-MANUAL-TEST.md](../lab/snowflake-dt-MANUAL-TEST.md)**.

Ordered scripts: **`01_catalog_integration.sql`**, **`02_cld_verify.sql`**, **`03_dt_pipelines.sql`** (scaffolds / comments). **Read-only DT checks:** **`04_dt_verify_sample_queries.sql`** (run after `03_dt_pipelines` + refresh). Use **`snow sql`** (Snowflake CLI **≥3.16**, from **`uv sync`**) against a configured connection. **DT tasks:** **`task dt:generate-sql`** / **`task dt:generate-sql-stdout`**. **Silver external volume (sfutils-extvolumes):** **`task dt:extvol-*`** (see **`lab/snowflake-dynamic-iceberg-tables.md`** — **`SILVER_EXTVOLUME_BUCKET_SLUG`** or **`LAB_USERNAME`**, then **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`**).

**Minimal env:** run **`task snowflake:print-env-hints`**. You do **not** need **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** by default — run **`task snowflake:create-glue-catalog-read-role`** first and **`generate-lab-sql`** reads **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**. Override the signer role only with that env var, **`--sigv4-role-arn`**, or a custom **`.txt`** line if you use another IAM role. **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`** and **`SNOWFLAKE_LINKED_DATABASE_NAME`** have repo defaults. Optional trial / multi-connection vars: [`.env.example`](../.env.example) ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)).

### Generate concrete SQL from bronze `.aws-config`

After **`task bronze:glue-setup`** (writes **`.aws-config/glue-database.json`**), **`task snowflake:generate-lab-sql`** emits scripts under **`snowflake/lab/generated/`** (gitignored) with **Glue Data Catalog** / Snowflake Step 2 defaults (**`CATALOG_NAME`** = account id, **`CATALOG_NAMESPACE`** = **`GLUE_DATABASE`**). For **S3 Tables** composite **`CATALOG_NAME`**, run **`task bronze:s3tables-setup`** first, then **`snowflake-lab-sql generate --glue-s3tables-catalog`** (or **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`**). **`--glue-data-catalog`** still forces the same default shape explicitly.

| Step | Command |
|------|---------|
| 1 | Default: **`task snowflake:create-glue-catalog-read-role`** writes **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** — no **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** needed. Override only for a different signer role (env, **`--sigv4-role-arn`**, or **`.txt`**). Same role receives **`apply-glue-catalog-trust-from-rendered`**. See [lab/snowflake-catalog-cld.md](../lab/snowflake-catalog-cld.md). |
| 2 | **`task snowflake:generate-lab-sql`** — writes **`01_catalog_integration.generated.sql`** and **`02_cld_verify.generated.sql`** only (`REST_CONFIG` includes **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`** for vended Glue reads). |
| 3 | **`snow sql --filename snowflake/lab/generated/01_catalog_integration.generated.sql`** (after IAM trust is applied). |
| 4 | **`snow sql --filename snowflake/lab/generated/02_cld_verify.generated.sql`** — CLD + sample reads. |
| 5 | **Silver external volume (before DT SQL):** set DT env per narrative **§1**, then with **`LAB_USERNAME`**, run **`task dt:extvol-create-dry-run`** then **`task dt:extvol-create`** (defaults: **`--bucket balloon-silver`**, **`--prefix`** = same workshop slug as bronze). Solo: set **`SILVER_EXTVOLUME_BUCKET_SLUG`**. Then set **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** from CLI output; optional **`task dt:extvol-verify`**. See **[lab/snowflake-dynamic-iceberg-tables.md](../lab/snowflake-dynamic-iceberg-tables.md)** §1–§2 and **`tools/snowflake_lab/extvol_resolve.py`**. |
| 6 | **`task dt:generate-sql`** — writes **`03_dt_pipelines.generated.sql`** (five Dynamic Iceberg Tables; **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`** should already be set from step 5). Optional one-shot: **`task snowflake:generate-lab-sql-all`**. |
| 7 | **`snow sql --filename snowflake/lab/generated/03_dt_pipelines.generated.sql`** — see **[lab/snowflake-dynamic-iceberg-tables.md](../lab/snowflake-dynamic-iceberg-tables.md)**. |
| 8 | **Streamlit in Snowflake (SiS):** **`snow streamlit deploy`** with **`snowflake/sis/snowflake.yml`** (or manual stage + **`CREATE STREAMLIT`**). Quick path: **`task snowflake:sis-deploy`**. Narrative: **[lab/snowflake-streamlit-sis.md](../lab/snowflake-streamlit-sis.md)**; files: **[snowflake/sis/README.md](../sis/README.md)**. |

**Stub role ARN (teaching / scratch):** `uv run snowflake-lab-sql generate --placeholder-role` (writes **`arn:aws:iam::<account>:role/REPLACE_ME_GLUE_CATALOG_READ`** using **CatalogId** or STS).

**Stdout only:** **`task snowflake:generate-lab-sql-stdout`** (catalog + CLD), **`task dt:generate-sql-stdout`** (silver DTs).

Entry point: **`uv run snowflake-lab-sql`** (`generate`, **`print-env-hints`**). Implementation: **`tools/snowflake_lab/sql_generate.py`**, **`tools/snowflake_lab/defaults.py`**.

## Automate IAM trust for Glue Iceberg REST catalog integration

After you run **`CREATE CATALOG INTEGRATION`** for **AWS Glue Iceberg REST** (`CATALOG_SOURCE = ICEBERG_REST`, `CATALOG_API_TYPE = AWS_GLUE`), Snowflake exposes trust fields on the integration object. Attach them to the **trust policy** of the **same IAM role** you set in `REST_AUTHENTICATION` (`SIGV4_IAM_ROLE`), per [Configure a catalog integration for AWS Glue Iceberg REST](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue) (Step 3–4).

This repo automates that the same way **sfutils-extvolumes** automates external-volume flows: **`snow sql`** to read Snowflake, then a **checked-in JSON template** → **`.aws-config/`** output.

| Step | Command |
|------|---------|
| 1 | Default integration name is **`glue_rest_catalog_int`** (override **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`** only if yours differs). Ensure **`snow sql`** can connect (optional **`SNOWFLAKE_DEFAULT_CONNECTION_NAME`**, **`SNOWFLAKE_ROLE`**, **`SNOWFLAKE_WAREHOUSE`**). |
| 2 | `task snowflake:describe-catalog-integration` — confirms `DESC CATALOG INTEGRATION` returns `GLUE_AWS_IAM_USER_ARN` / `GLUE_AWS_EXTERNAL_ID` (external ID is masked in the human view). |
| 3 | `task snowflake:render-glue-catalog-trust` — writes **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`** from **`lab/aws/snowflake-glue-catalog-trust-policy.json`**. |
| 4 | In IAM, paste that JSON as the role’s **trust policy** (or merge statements with your org’s standards). |

**Dry-run (stdout only):** `task snowflake:render-glue-catalog-trust-dry-run` or `uv run snowflake-catalog-trust render-glue-catalog-trust --dry-run`.

**CI / air-gapped:** set **`GLUE_AWS_IAM_USER_ARN`** and **`GLUE_AWS_EXTERNAL_ID`** and run **`render-glue-catalog-trust`** so **`snow`** is not invoked (integration name is irrelevant when both **`GLUE_*`** are set).

Entry point: **`uv run snowflake-catalog-trust`** (`describe-catalog-integration`, `render-glue-catalog-trust`). Implementation: **`tools/snowflake_lab/catalog_trust.py`**.

## Create the SIGV4 IAM role (AWS) — optional automation

| Step | Command |
|------|---------|
| 1 | **`task snowflake:create-glue-catalog-read-role`** — IAM role **`snowflake_glue_catalog_read`** (override **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME`**), Glue/S3 read policy, **bootstrap** same-account trust, writes **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**. |
| 2 | After **`render-glue-catalog-trust`**, **`task snowflake:apply-glue-catalog-trust-from-rendered`** — sets assume-role policy to Snowflake **`GLUE_AWS_IAM_USER_ARN`** + **external ID**. |
| Dry-run | **`task snowflake:create-glue-catalog-read-role-dry-run`** — print JSON only. |

Entry point: **`uv run snowflake-catalog-iam`** (`create-read-role`, `apply-trust-from-rendered`). Implementation: **`tools/snowflake_lab/catalog_iam.py`**, policy template **`lab/aws/snowflake-glue-catalog-read-policy.json`**.

## Glue IRC + IAM (gist and Snowflake docs)

For full **`CREATE CATALOG INTEGRATION`** SQL, Lake Formation, and companion **permissions** JSON beyond the trust stub above, continue to align with current Snowflake and AWS docs and patterns such as [Snowflake + Glue S3 Tables gist](https://gist.github.com/kameshsampath/e9c8c27097dd23378d70f63c9e978426) (cross-check every field before production). **`lab/aws/bronze-glue-writer-policy.json`** remains the **PyIceberg / bronze writer** policy, not the Snowflake integration role policy.

| Artifact | Role |
|----------|------|
| `lab/aws/snowflake-glue-catalog-trust-policy.json` | **Trust** only — Snowflake Glue catalog IAM user + external ID |
| Gist `iam_policy.json` | **Permissions** on the integration IAM role (Glue + S3 + optional Lake Formation) |
| `lab/aws/bronze-glue-writer-policy.json` | Bronze **loader** / writer to S3 + Glue (separate principal) |

See [REFERENCE.md](REFERENCE.md) for bronze **`event`** JSON and Dynamic Iceberg Table notes.
