# Snowflake: Glue catalog integration and catalog-linked database (CLD)

This chapter is the **first Snowflake hands-on** after [bronze landing zone](bronze-landing-zone.md). The **core path** below walks **`CREATE CATALOG INTEGRATION`** through **IAM trust**, **catalog-linked database (CLD)**, **discovery**, and **read queries**. Longer AWS context—**Lake Formation** for vended Glue reads, **IAM role** creation options, **S3 Tables** `CATALOG_NAME` shape, and **external volume** delegation—is under **[Additional reading](#additional-reading)** so you can open it when needed.

All SQL in this chapter must match current Snowflake documentation—use [CREATE CATALOG INTEGRATION (Apache Iceberg REST)](https://docs.snowflake.com/en/sql-reference/sql/create-catalog-integration-rest), [Configure a catalog integration for AWS Glue Iceberg REST](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue), and [Use a catalog-linked database for Apache Iceberg tables](https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog-linked-database) as the source of truth.

## Prerequisites (short)

- **Bronze** is loaded: Glue database **`GLUE_DATABASE`** and table **`balloon_game_events`** (JSON column **`event`**). See [snowflake/lab/REFERENCE.md](../snowflake/lab/REFERENCE.md).
- **`.aws-config/glue-database.json`** exists after bronze **`glue-setup`** (used by **`task snowflake:generate-lab-sql`**).
- **`snow`** (Snowflake CLI) is configured for a role that can create integrations and databases ([Snowflake CLI installation](https://docs.snowflake.com/developer-guide/snowflake-cli/installation/installation)). Run **`task snowflake:print-env-hints`** for defaults and optional connection overrides ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)).
- **IAM** — an ARN for **`SIGV4_IAM_ROLE`** and trust/permissions aligned with Snowflake docs. The repo can create **`snowflake_glue_catalog_read`**; see [Additional reading — SIGV4 IAM role](#sigv4-iam-role-arn).
- **Lake Formation** — required when generated SQL uses **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`**. If you skip that until link checks fail, read [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load) in **`lab/bronze-landing-zone.md`**.
- **External volume path** (optional alternate to vended credentials for S3 access) — see [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md).

Scaffold SQL files (commented examples you uncomment and edit): [snowflake/lab/01_catalog_integration.sql](../snowflake/lab/01_catalog_integration.sql), [snowflake/lab/02_cld_verify.sql](../snowflake/lab/02_cld_verify.sql).

Alternatively, after bronze has written **`.aws-config/glue-database.json`**, **`task snowflake:generate-lab-sql`** emits **`01_catalog_integration.generated.sql`** and **`02_cld_verify.generated.sql`** from that file, region env, and the **Snowflake catalog IAM role ARN** (see [Additional reading](#sigv4-iam-role-arn)). Silver Dynamic Iceberg SQL: **`task dt:generate-sql`** → **`03_dt_pipelines.generated.sql`**. This repo uses **`<repo>/.aws-config/`** (not **`~/.aws-config`**); if you keep a personal copy elsewhere, symlink or paste the same one-line files here.

## 1. Create the catalog integration (Glue Iceberg REST)

Run **`CREATE CATALOG INTEGRATION`** (or **`CREATE OR REPLACE`**) with:

- **`CATALOG_SOURCE = ICEBERG_REST`**, **`TABLE_FORMAT = ICEBERG`**
- **`REST_CONFIG`**: **`CATALOG_URI`** = `https://glue.<region>.amazonaws.com/iceberg`, **`CATALOG_API_TYPE = AWS_GLUE`**, **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`** (explicit so reads work without a Snowflake external volume; see [CREATE CATALOG INTEGRATION (REST)](https://docs.snowflake.com/en/sql-reference/sql/create-catalog-integration-rest)), plus **`CATALOG_NAME`** / **`CATALOG_NAMESPACE`** aligned with how your Iceberg metadata is registered:
  - **AWS Glue Data Catalog** (repo **default** for **`task snowflake:generate-lab-sql`**): Snowflake [Step 2](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue#step-2-create-a-catalog-integration-in-snowflake) — **`CATALOG_NAME`** = **12-digit AWS account id** and **`CATALOG_NAMESPACE`** = **`GLUE_DATABASE`** (from **`.aws-config/glue-database.json`**). Same shape with **`snowflake-lab-sql generate --glue-data-catalog`** or **`SNOWFLAKE_GLUE_REST_USE_DATA_CATALOG=1`** (redundant with default).
  - **Glue Iceberg REST + Amazon S3 Tables** (opt-in): **`CATALOG_NAME`** = `'<12-digit AWS account id>:S3tablescatalog/<s3_table_bucket_name>'` and **`CATALOG_NAMESPACE`** = your **S3 Tables namespace** (**`S3TABLES_NAMESPACE`** / **`balloon_pops`** after **`s3tables-setup`**). This matches AWS Glue’s **nested catalog** id style for REST prefixes (see [Connecting to the Data Catalog using AWS Glue Iceberg REST endpoint](https://docs.aws.amazon.com/glue/latest/dg/connect-glu-iceberg-rest.html)). **`CATALOG_URI`** remains **`https://glue.<region>.amazonaws.com/iceberg`** (Snowflake **Glue** REST integration), not the separate [S3 Tables Iceberg REST endpoint](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-open-source.html) (`https://s3tables.<region>.amazonaws.com/iceberg`, SigV4 signing name **`s3tables`**). Emit with **`snowflake-lab-sql generate --glue-s3tables-catalog`** or **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`**, with the table-bucket from **`BRONZE_S3TABLES_BUCKET_NAME`**, **`SNOWFLAKE_S3TABLES_BUCKET_NAME`**, or **`.aws-config/bronze-s3tables-last-bucket-name.txt`**. Re-run **`task snowflake:create-glue-catalog-read-role`** so IAM includes **`S3TablesGlueCatalogRead`** on that hierarchy. Optional full override: **`SNOWFLAKE_GLUE_REST_CATALOG_NAME`** / **`snowflake-lab-sql generate --rest-catalog-name '…'`**.
- **`REST_AUTHENTICATION`**: **`TYPE = SIGV4`**, **`SIGV4_IAM_ROLE`** = ARN of the IAM role Snowflake will assume, **`SIGV4_SIGNING_REGION`** = region

Use **`snow sql`** or Snowflake worksheets:

```bash
# Option A — hand-edited scaffold:
snow sql --connection <your_connection> --filename snowflake/lab/01_catalog_integration.sql

# Option B — generated from .aws-config/glue-database.json (after task snowflake:generate-lab-sql):
snow sql --connection <your_connection> --filename snowflake/lab/generated/01_catalog_integration.generated.sql
```

The repo standard integration name is **`glue_rest_catalog_int`** (same default for **`task snowflake:generate-lab-sql`**, **`describe-catalog-integration`**, and **`render-glue-catalog-trust`**). You only need **`export SNOWFLAKE_CATALOG_INTEGRATION_NAME=…`** if you created the object under a **different** name.

```bash
task snowflake:print-env-hints   # defaults; SIGV4 env optional if create-read-role wrote .txt
# Optional if you did not use the default name:
# export SNOWFLAKE_CATALOG_INTEGRATION_NAME=my_other_name
```

## 2. Describe the catalog integration (trust details)

Snowflake returns the values you must place in the **trust policy** of **`SIGV4_IAM_ROLE`**:

| Property (describe output) | Use on IAM role |
|----------------------------|-----------------|
| **`GLUE_AWS_IAM_USER_ARN`** | **`Principal.AWS`** in **`sts:AssumeRole`** |
| **`GLUE_AWS_EXTERNAL_ID`** | **`Condition.StringEquals`** on **`sts:ExternalId`** |

Run in Snowflake:

```sql
DESC CATALOG INTEGRATION glue_rest_catalog_int;
```

Or use the repo helper (masks the external ID in the default text output):

```bash
task snowflake:describe-catalog-integration
```

JSON dump (full property map):

```bash
task snowflake:describe-catalog-integration-json
```

## 3. Update the correct IAM role (trust + permissions)

1. **Trust policy** — attach to the **same** IAM role whose ARN you set in **`SIGV4_IAM_ROLE`** (not the PyIceberg bronze writer role from **`lab/aws/bronze-glue-writer-policy.json`**).

   Render the trust document from this repo:

   ```bash
   task snowflake:render-glue-catalog-trust
   ```

   Output: **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`**. Apply it with **`task snowflake:apply-glue-catalog-trust-from-rendered`** (CLI) *or* in the IAM console → **Trust relationships** → **Edit trust policy** → paste or merge that JSON (follow your org’s change control).

2. **Permissions policy** — if you used **`task snowflake:create-glue-catalog-read-role`**, the role already has inline **SnowflakeGlueCatalogRead** from **`lab/aws/snowflake-glue-catalog-read-policy.json`** (Snowflake **Step 1**: **Glue** read on **`GLUE_DATABASE`**, **Lake Formation** APIs for vended credentials when you follow the LF path). Otherwise attach an approved template and reconcile ARNs with **`task bronze:snowflake-summary`**. For **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`** (this lab’s generated SQL), Glue must be able to **vend** temporary credentials for the table’s S3 location; that path typically needs **Lake Formation** data permissions on the Glue database/table **and** a registered S3 location with an LF **data-access** role (see [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load)) in addition to IAM—see [Configure a catalog integration for AWS Glue Iceberg REST](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue) (Lake Formation section) and AWS [underlying data access control](https://docs.aws.amazon.com/lake-formation/latest/dg/access-control-underlying-data.html).

3. **Propagate** — wait briefly after IAM save, then re-check **`DESC CATALOG INTEGRATION`** if Snowflake reported access errors earlier.

**Dry-run trust JSON only (no file write):**

```bash
task snowflake:render-glue-catalog-trust-dry-run
```

**External volume + catalog on one role:** if you use **`EXTERNAL_VOLUME_CREDENTIALS`** (omitting **`ACCESS_DELEGATION_MODE`** or setting delegation per docs) and attach an **external volume**, the IAM trust policy may need **two** Snowflake external IDs—see [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md).

## 4. Create the catalog-linked database (CLD)

With the integration **ENABLED** and IAM trust correct, create the **catalog-linked database** that mirrors Glue namespaces/schemas and Iceberg tables.

This lab uses **`balloon_game_events`** as the **catalog-linked database** name—the same spelling as the bronze **Iceberg table**—so a read path looks like **`balloon_game_events."<remote_schema>"."balloon_game_events"`**, where **`<remote_schema>`** is the **lowercase** remote namespace: your **`GLUE_DATABASE`** for the **default** generator (Snowflake Glue Data Catalog / Step 2), or your **`S3TABLES_NAMESPACE`** (for example **`balloon_pops`**) when you use **`--glue-s3tables-catalog`** / **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`** (Snowflake folds **unquoted** identifiers to uppercase in the UI). Override the linked DB name with **`SNOWFLAKE_LINKED_DATABASE_NAME`** before **`task snowflake:generate-lab-sql`** if you prefer another name.

```sql
CREATE OR REPLACE DATABASE balloon_game_events
  COMMENT = 'CLD: Glue bronze Iceberg (lab name matches raw table)'
  LINKED_CATALOG = (
    CATALOG = 'glue_rest_catalog_int'
  );
```

When using an **external volume** on the CLD, add **`EXTERNAL_VOLUME = '…'`** to **`CREATE DATABASE`** per Snowflake docs; end-to-end SQL and trust notes: [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md).

See [CREATE DATABASE (catalog-linked)](https://docs.snowflake.com/en/sql-reference/sql/create-database-catalog-linked.md).

Optional configuration checks:

```sql
SELECT SYSTEM$GET_CATALOG_LINKED_DATABASE_CONFIG('balloon_game_events');
SELECT SYSTEM$CATALOG_LINK_STATUS('balloon_game_events');
```

If **`SYSTEM$CATALOG_LINK_STATUS`** shows **`Failed to retrieve credentials from the Catalog`** (for example Snowflake error **094120**), that is **not** fixed by SQL alone: confirm the **SIGV4** role still has **Glue** + **Lake Formation** APIs Snowflake documents for vended access, the role’s **trust** uses **`GLUE_AWS_IAM_USER_ARN`** + **`sts:ExternalId`**, and **Lake Formation** grants that role access to the Glue database/tables **and** the warehouse **S3** location is registered with LF using a **different** data-access role that can read **`BRONZE_BUCKET_NAME`** (see [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load)). If **`SIGV4_IAM_ROLE`** and **`register-resource --role-arn`** point at the **same** IAM role, fix that split first—vending often fails in that configuration.

## 5. Show schemas and tables (discovery)

Remote Glue **database** names appear as **schemas** inside the linked database. For Glue, Snowflake’s CLD docs require **lowercase identifiers in double quotes** when the remote catalog is case-sensitive in that way.

```sql
USE DATABASE balloon_game_events;
SHOW SCHEMAS IN DATABASE balloon_game_events;
```

List Iceberg tables registered under a schema (replace **`"<remote_schema>"`** with the schema name you see—**`GLUE_DATABASE`** in lowercase for the **default** (Glue Data Catalog), or **`S3TABLES_NAMESPACE`** in lowercase when using **S3 Tables** catalog shape):

```sql
SHOW ICEBERG TABLES IN SCHEMA balloon_game_events."<remote_schema>";
```

If **`SHOW ICEBERG TABLES`** is not available in your edition, use [SHOW TABLES](https://docs.snowflake.com/en/sql-reference/sql/show-tables) / **Information Schema** per current docs.

## 6. Query the bronze table

Read raw rows (string JSON in **`event`**):

```sql
SELECT event
FROM balloon_game_events."<remote_schema>"."balloon_game_events"
LIMIT 10;
```

Project fields with **`PARSE_JSON`** (see [REFERENCE.md](../snowflake/lab/REFERENCE.md)):

```sql
SELECT
  PARSE_JSON(event):player::STRING            AS player,
  PARSE_JSON(event):balloon_color::STRING     AS balloon_color,
  PARSE_JSON(event):score::INTEGER            AS score,
  PARSE_JSON(event):event_ts::TIMESTAMP_TZ    AS event_ts
FROM balloon_game_events."<remote_schema>"."balloon_game_events"
LIMIT 10;
```

!!! tip "Automation: run repo tasks in this order"

    1. **`task bronze:snowflake-summary`** — refresh AWS/Glue copy-paste values (if anything changed since bronze setup). Ensure **`task bronze:glue-setup`** wrote **`.aws-config/glue-database.json`** (default **`generate-lab-sql`** uses **Glue Data Catalog** / Snowflake Step 2). For **S3 Tables** composite **`CATALOG_NAME`**, run **`task bronze:s3tables-setup`** so **`.aws-config/bronze-s3tables-last-bucket-name.txt`** (or **`BRONZE_S3TABLES_BUCKET_NAME`**) exists, then **`snowflake-lab-sql generate --glue-s3tables-catalog`** (or **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`**).
    2. **SIGV4 IAM role** — **`task snowflake:create-glue-catalog-read-role`** (creates **`snowflake_glue_catalog_read`**, permissions + bootstrap trust, writes **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**) *or* supply **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** / that file yourself. Optional: **`task snowflake:print-env-hints`**.
    3. **Lake Formation (vended-credentials path)** — after **`task bronze:load`**, follow [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load): **dedicated** LF **data-access** role (S3 read; **`register-resource --role-arn`**), Glue **`CreateTableDefaultPermissions`**, LF **`grant-permissions`** **to** the **SIGV4** role from step 2. **Never** use the same IAM role as both **`SIGV4_IAM_ROLE`** and the LF data-access role (vending failures).
    4. **`task snowflake:generate-lab-sql`** then **`snow sql --filename snowflake/lab/generated/01_catalog_integration.generated.sql`** (or hand-edit **`snowflake/lab/01_catalog_integration.sql`**). Override **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`** only if you did not use **`glue_rest_catalog_int`**.
    5. **`task snowflake:describe-catalog-integration`** — confirm **`GLUE_AWS_IAM_USER_ARN`** / **`GLUE_AWS_EXTERNAL_ID`** appear (trust fields).
    6. **`task snowflake:render-glue-catalog-trust`** — write **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`**.
    7. **`task snowflake:apply-glue-catalog-trust-from-rendered`** — replace bootstrap trust with Snowflake user + external ID *or* paste the same JSON in the IAM console for that role.
    8. **CLD + verify** — **`snowflake/lab/generated/02_cld_verify.generated.sql`** or **`snowflake/lab/02_cld_verify.sql`**.
    9. Optional: **`task snowflake:render-glue-catalog-trust-dry-run`** before step 6 to preview trust JSON without writing files.
    10. **Silver / Dynamic Iceberg Tables** — configure env (**[snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md)** §1), create or select a **silver** **external volume** (**§2**, **`task dt:extvol-*`** or manual), set **`SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME`**, then **`task dt:generate-sql`** and **`snow sql --filename snowflake/lab/generated/03_dt_pipelines.generated.sql`** — see the same chapter and **[snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md)** (env → Phase A → Phase B).

For more on the trust helper, see [snowflake/lab/README.md](../snowflake/lab/README.md).

## Additional reading

### Lake Formation (vended reads)

If you use **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`**, complete the AWS steps in [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load) in **`lab/bronze-landing-zone.md`**: a **dedicated** LF **data-access** role (trusted by **`lakeformation.amazonaws.com`**, S3 read on **`BRONZE_BUCKET_NAME`**) for **`register-resource`** with **`HybridAccessEnabled=false`** and **`WithFederation=false`** ([AWS `RegisterResource`](https://docs.aws.amazon.com/lake-formation/latest/APIReference/API_RegisterResource.html))—**not** hybrid access and **not** a federated Data Catalog resource—plus **`glue update-database`** to clear **`CreateTableDefaultPermissions`**, plus LF **`grant-permissions`** **to** the **Snowflake `SIGV4_IAM_ROLE`** (the catalog signer—not the data-access role). **Do not use one IAM role for both** the **`SIGV4_IAM_ROLE`** and the LF **`register-resource --role-arn`** data-access role; combining them commonly causes **credential vending errors**. Rationale and step-by-step “why”: same section. Snowflake documents the integration alongside [Glue Iceberg REST catalog integration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue).

### SIGV4 IAM role ARN

**`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** is the ARN of an **IAM role in your AWS account** that Snowflake will **assume** to call the **Glue Iceberg REST** endpoint. It is **not** returned by **`glue-database.json`** or **`task bronze:snowflake-summary`**. Do **not** reuse the bronze **PyIceberg writer** role for **`SIGV4_IAM_ROLE`** unless your organization has explicitly merged trust and permissions for both flows (the lab keeps them separate). Do **not** reuse the **Lake Formation data-access** role you pass to **`register-resource --role-arn`** as **`SIGV4_IAM_ROLE`** either—those roles must stay separate to avoid **vending credential** failures.

#### Option A — repo task creates the read role (recommended for the lab)

After **`task bronze:glue-setup`** (**`GLUE_DATABASE`** from **`glue-database.json`**, same **`AWS_PROFILE`** / **`AWS_REGION`** as other bronze tasks; keep **`BRONZE_BUCKET_NAME`** set for **`snowflake-summary`** and LF registration steps even when the **SIGV4** inline policy follows **Glue + Lake Formation** only):

1. **`task snowflake:create-glue-catalog-read-role`** (dry-run: **`task snowflake:create-glue-catalog-read-role-dry-run`**) — creates IAM role **`snowflake_glue_catalog_read`** (override with **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME`**) with:
   - **Permissions** from **`lab/aws/snowflake-glue-catalog-read-policy.json`**: align with Snowflake [Step 1](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue#step-1-configure-access-permissions-for-the-aws-glue-data-catalog) and the **Lake Formation** subsection—**Glue** read APIs scoped to **`GLUE_DATABASE`** (and **`catalog` / `catalog/*`** ARNs as needed), plus **Lake Formation** **`GetDataAccess`** and related temporary credential APIs for vended access. **S3 Tables federated catalog** (`s3tablescatalog/...` in **`CATALOG_NAME`**) is a separate IAM shape; the default generated SQL uses the **Glue Data Catalog** account id + **`GLUE_DATABASE`**. When Lake Formation governs the warehouse bucket, prefer **LF grants + LF data-access role** for **`s3:GetObject`** instead of duplicating broad S3 read on **`SIGV4_IAM_ROLE`**, after your security review.
   - **Bootstrap trust** (lab convenience): **`Principal`** = **`arn:aws:iam::<your-account-id>:root`** so principals in the same account (including Snowflake’s integration IAM user, once it exists) can assume the role while you iterate. **Tighten trust** in the next subsection after **`task snowflake:render-glue-catalog-trust`** using **`task snowflake:apply-glue-catalog-trust-from-rendered`** (Snowflake **`GLUE_AWS_IAM_USER_ARN`** + **`sts:ExternalId`**). Do **not** leave bootstrap trust in production shared accounts.
2. The task writes **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** and prints the role ARN — **`task snowflake:generate-lab-sql`** picks it up automatically.
3. **`task bronze:lakeformation-setup`** (after **`task bronze:load`**) — registers **`BRONZE_BUCKET_NAME`** with Lake Formation and grants LF access **to** this **`SIGV4`** role using a **separate** LF data-access role (see **`lab/bronze-landing-zone.md`**). **Never** use the same IAM role for **`SIGV4_IAM_ROLE`** and **`register-resource --role-arn`**.

Implementation: **`uv run snowflake-catalog-iam`** (`create-read-role`, **`apply-trust-from-rendered`**). Policy template: **`lab/aws/snowflake-glue-catalog-read-policy.json`**. Lake Formation: **`uv run bronze-cli lakeformation-setup`**.

#### Option B — create the role yourself (console or IaC)

**Look up the ARN after you create (or pick) the role:**

1. **AWS console:** **IAM** → **Roles** → open the role → copy **ARN** from the summary page.
2. **AWS CLI** (same profile as bronze):  
   `aws iam get-role --role-name <YourRoleName> --query Role.Arn --output text`

**Persist it for `generate-lab-sql`:**

- Put the ARN on the **first line** of **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** (see **`.aws-config/snowflake-glue-catalog-iam-role-arn.example`**), or **`export SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN=...`** ([`.env.example`](../.env.example)).

Precedence for generated SQL: **`--sigv4-role-arn`** / **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** (override signer role) → **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** (default after **`create-glue-catalog-read-role`**) → error (or **`--placeholder-role`** for a stub).

### External volume delegation

Step-by-step **external volume**, **dual external IDs** on IAM trust, **`ALLOW_WRITES = FALSE`**, **`GRANT USAGE ON EXTERNAL VOLUME`**, **`CREATE DATABASE … EXTERNAL_VOLUME`**, queries, cleanup, and a troubleshooting table: **[`lab/cld-with-extvol-setup-guide.md`](cld-with-extvol-setup-guide.md)**.

## Related

- [bronze-landing-zone.md](bronze-landing-zone.md) — AWS prerequisite
- [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md) — bronze landing QA (includes optional **`task bronze:snowflake-summary`**)
- [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) — **Snowflake CLD** QA (catalog integration → IAM trust → linked DB → **`SELECT`**)
- [snowflake-dynamic-iceberg-tables.md](snowflake-dynamic-iceberg-tables.md) — **Dynamic Iceberg Tables** over CLD (leaderboard DT)
- [cld-with-extvol-setup-guide.md](cld-with-extvol-setup-guide.md) — external volume path and troubleshooting
