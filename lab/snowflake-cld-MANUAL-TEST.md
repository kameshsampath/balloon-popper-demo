# Manual test plan — Snowflake CLD (Glue catalog integration + catalog-linked database)

Use this checklist to validate **Snowflake Glue Iceberg REST catalog integration**, **IAM trust** on **`SIGV4_IAM_ROLE`**, **catalog-linked database (CLD)**, and **read path** to bronze **`balloon_game_events`** before learners or release notes depend on it.

The companion narrative **[`snowflake-catalog-cld.md`](snowflake-catalog-cld.md)** leads with the **core Snowflake path** (integration → trust → CLD → queries); **Lake Formation**, **IAM role** options, and **[`cld-with-extvol-setup-guide.md`](cld-with-extvol-setup-guide.md)** sit under **Additional reading** there—use them when preconditions below apply.

**Prerequisite:** Bronze landing is done so **`.aws-config/glue-database.json`** exists and Glue has table **`balloon_game_events`** (see [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md) sections 2 and 4, or section 5b for read-only prep only).

Run from the **repo root** with **`uv sync`** already done.

---

## 0. Preconditions

| Check | How |
|--------|-----|
| Host CLIs | `task check-tools` — **snow**, **aws**, **task**, **uv**, etc., plus **`aws sts get-caller-identity`** for a valid AWS session ([README](../README.md)) |
| Env | `task snowflake:print-env-hints` — then set **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** or **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**. Optional: **`SNOWFLAKE_DEFAULT_CONNECTION_NAME`**, **`SNOWFLAKE_ROLE`**, **`SNOWFLAKE_WAREHOUSE`**, or overrides for **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`** / **`SNOWFLAKE_LINKED_DATABASE_NAME`** (see [`.env.example`](../.env.example)). |
| Bronze artifacts | **`.aws-config/glue-database.json`** present after **`task bronze:glue-setup`** (or equivalent). |
| Lake Formation (vended path) | If **`CREATE CATALOG INTEGRATION`** uses **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`**, complete [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load) and [bronze-landing-zone-MANUAL-TEST.md §4a](bronze-landing-zone-MANUAL-TEST.md#4a-lake-formation-after-bronze-load) so the **SIGV4** role has LF grants and the warehouse S3 location is registered under a **separate** LF data-access role (**SIGV4** ≠ **`register-resource --role-arn`**). |
| Snowflake CLI auth | `snow connection list` — default or named connection works; optional `snow connection test` ([Managing Snowflake connections](https://docs.snowflake.com/developer-guide/snowflake-cli/connecting/configure-connections)). |
| AWS (IAM edits) | Same **`AWS_PROFILE`** / **`AWS_REGION`** you use for bronze when updating the **SIGV4** role’s trust policy in IAM. |
| IAM role for Glue REST | An IAM role whose ARN you will set as **`SIGV4_IAM_ROLE`**, with a **permissions** policy that allows **Glue** catalog reads and **Lake Formation** credential-vending APIs per [Snowflake Glue REST + LF](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue) — **not** the same principal as the bronze PyIceberg writer unless you have explicitly merged both designs. |

**Record (not in git):** Snowflake account locator, integration name, SIGV4 role name.

---

### Env vars (Snowflake CLD path)

| Variable | Required for | Used by | Notes |
|----------|---------------|---------|-------|
| `SNOWFLAKE_CATALOG_INTEGRATION_NAME` | optional | `snowflake-catalog-trust`, docs | Defaults to **`glue_rest_catalog_int`** if unset; override only if your **`CREATE CATALOG INTEGRATION`** used another name |
| `SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN` | `snowflake:generate-lab-sql` (unless `--placeholder-role` or `.txt` file) | `snowflake-lab-sql` | Same role that receives **trust** from **`render-glue-catalog-trust`** |
| `.aws-config/snowflake-glue-catalog-iam-role-arn.txt` | optional alternative to env | `snowflake-lab-sql` | First non-`#` line: `arn:aws:iam::…:role/…` |
| `SNOWFLAKE_DEFAULT_CONNECTION_NAME` | optional | `snow sql` | Named connection in **`config.toml`** when you do not rely on file default alone |
| `SNOWFLAKE_ROLE` | optional (trial default in **`.env.example`**) | `snow sql` | Often **`ACCOUNTADMIN`** on trials |
| `SNOWFLAKE_WAREHOUSE` | optional (trial default in **`.env.example`**) | `snow sql` | Often **`COMPUTE_WH`** |
| `SNOWFLAKE_LINKED_DATABASE_NAME` | optional | `snowflake-lab-sql generate` | Default **`balloon_game_events`** (same spelling as bronze table) |
| `BRONZE_S3TABLES_BUCKET_NAME` / `.aws-config/bronze-s3tables-last-bucket-name.txt` | S3 Tables SQL shape only | `snowflake-lab-sql generate --glue-s3tables-catalog` | Not required for default Glue Data Catalog SQL |
| `S3TABLES_NAMESPACE` | optional | `snowflake-lab-sql generate` | Default **`balloon_pops`** when unset (S3 Tables shape) |
| `SNOWFLAKE_GLUE_REST_USE_DATA_CATALOG` | optional | `snowflake-lab-sql generate` | Set to **`1`** / **`true`** / **`yes`** / **`on`** to force Glue Data Catalog (same as default) |
| `SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG` | optional | `snowflake-lab-sql generate` | Set to **`1`** / **`true`** / **`yes`** / **`on`** for **`CATALOG_NAME`** = **`<account>:S3tablescatalog/<bucket>`** |
| `GLUE_AWS_IAM_USER_ARN` + `GLUE_AWS_EXTERNAL_ID` | optional | `render-glue-catalog-trust` | Set both to skip **`snow sql`** `DESC` (CI / air-gapped) |
| `AWS_PROFILE` | if **`glue-database.json`** lacks **`CatalogId`** | `snowflake-lab-sql generate` | STS for account id when generating SQL |

---

## 1. Read-only — bronze values for Snowflake

**Goal:** Confirm Glue REST URI, account id, and **`GLUE_DATABASE`** align with **`.aws-config/glue-database.json`**.

1. `export AWS_PROFILE=…` and `export AWS_REGION=…` (same as bronze test).
2. Run: `task bronze:snowflake-summary` (or `task bronze:snowflake-summary-json`).
3. **Expect:** Exit **0**; output includes **`GLUE_ICEBERG_REST_URI`**, **`AWS_ACCOUNT_ID`**, **`GLUE_DATABASE`**, **`balloon_game_events`**.

**Pass:** Values match **`Name`** / **`CatalogId`** in **`.aws-config/glue-database.json`**.

---

## 2. Optional — create SIGV4 IAM role (AWS)

**Goal:** IAM role with Snowflake-aligned Glue/S3 **read** policy + ARN file for **`generate-lab-sql`**.

1. `export AWS_PROFILE=…` **`AWS_REGION=…`** (same as bronze).
2. Run: `task snowflake:create-glue-catalog-read-role` (preview: **`task snowflake:create-glue-catalog-read-role-dry-run`**).
3. **Expect:** Default role is **`snowflake_glue_catalog_read`** when **`LAB_USERNAME`** is unset; with the same **`LAB_USERNAME`** as bronze, it is **`<glue_slug>_snowflake_glue_catalog_read`** (see stderr **`info: IAM role name=…`**). Override with **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME`** if needed. **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** contains the role ARN; the command prints the ARN on stdout.

**Pass:** `aws iam get-role --role-name <that-role-name> --profile "$AWS_PROFILE" --query Role.Arn --output text` matches the file.

**Skip this section** if you use your own IAM role and set **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** / the **`.txt`** file manually.

---

## 3. Optional — generate runnable SQL

**Goal:** **`snowflake/lab/generated/*.generated.sql`** filled from **`.aws-config`** + SIGV4 role ARN.

1. Run: `task snowflake:print-env-hints` (defaults reminder).
2. Ensure **`SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN`** or **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`** (section 2 or manual).
3. Run: `task snowflake:generate-lab-sql`
4. **Expect:** **`snowflake/lab/generated/01_catalog_integration.generated.sql`** and **`02_cld_verify.generated.sql`** exist (gitignored).
5. Optional preview without files: `task snowflake:generate-lab-sql-stdout`

**Pass:** Open **`01_…`** — **default**: **`CATALOG_NAME`** = **12-digit account id**, **`CATALOG_NAMESPACE`** = **`GLUE_DATABASE`**; **S3 Tables** shape (**`--glue-s3tables-catalog`** / **`SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1`**): **`CATALOG_NAME`** = **`<account>:S3tablescatalog/<table-bucket>`** and **`CATALOG_NAMESPACE`** = **`S3TABLES_NAMESPACE`**. **`CATALOG_URI`**, **`SIGV4_SIGNING_REGION`**, and **`SIGV4_IAM_ROLE`** match your AWS region and IAM role.

---

## 4. Create catalog integration (Snowflake)

**Goal:** Integration exists and is **ENABLED** (may show IAM errors until trust is fixed — that is expected mid-test).

1. If you used the repo default name in SQL, skip **`export SNOWFLAKE_CATALOG_INTEGRATION_NAME`**; otherwise set it to match your **`CREATE CATALOG INTEGRATION`** identifier.
2. Run generated or hand-edited SQL, for example:  
   `snow sql --filename snowflake/lab/generated/01_catalog_integration.generated.sql`  
   (or **`snowflake/lab/01_catalog_integration.sql`** after uncommenting placeholders — see [snowflake-catalog-cld.md](snowflake-catalog-cld.md)).
3. In Snowflake (worksheet or CLI): `DESC CATALOG INTEGRATION <name>;` — confirm object exists.

**Pass:** **`DESC CATALOG INTEGRATION`** returns rows; **`GLUE_AWS_IAM_USER_ARN`** and **`GLUE_AWS_EXTERNAL_ID`** are present (trust material).

**Common failures:** Wrong **`CATALOG_NAMESPACE`** vs Glue DB name; wrong account id in **`CATALOG_NAME`**; **`SIGV4_IAM_ROLE`** ARN typo.

---

## 5. Describe via repo task (trust fields)

**Goal:** **`task snowflake:describe-catalog-integration`** matches Snowflake UI / `DESC`.

1. Run: `task snowflake:describe-catalog-integration` (uses default **`glue_rest_catalog_int`** unless **`SNOWFLAKE_CATALOG_INTEGRATION_NAME`** is set)
2. Optional JSON: `task snowflake:describe-catalog-integration-json`

**Pass:** Output mentions **`GLUE_AWS_IAM_USER_ARN`** / **`GLUE_AWS_EXTERNAL_ID`** (masked in human view is OK).

---

## 6. Render IAM trust JSON

**Goal:** Checked-in template → **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`**.

1. Run: `task snowflake:render-glue-catalog-trust`
2. **Expect:** **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`** exists and is valid JSON.

**Pass:** `python -m json.tool .aws-config/snowflake-glue-catalog-trust-policy.rendered.json` exits **0**; trust **`Principal`** / **`sts:ExternalId`** match **`DESC`** (see [snowflake/lab/README.md](../snowflake/lab/README.md)).

**Air-gapped / CI:** set **`GLUE_AWS_IAM_USER_ARN`** and **`GLUE_AWS_EXTERNAL_ID`**, then run **`render-glue-catalog-trust`** without invoking **`snow`**. Dry-run only: `task snowflake:render-glue-catalog-trust-dry-run`.

---

## 7. Apply trust (CLI or AWS IAM console)

**Goal:** The **same** IAM role as **`SIGV4_IAM_ROLE`** trusts Snowflake’s Glue catalog user + external id (replaces lab **bootstrap** trust from **`create-glue-catalog-read-role`**).

1. Run: `task snowflake:apply-glue-catalog-trust-from-rendered` **or** IAM console → **Trust relationships** → paste **`.aws-config/snowflake-glue-catalog-trust-policy.rendered.json`** (follow change control).
2. Confirm a **permissions** policy on that role still allows **Glue** + **Lake Formation** reads as required for vended access, and that **Lake Formation** grants + registered S3 location are in place ([Configure a catalog integration for AWS Glue Iceberg REST](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue), [Lake Formation after bronze load](bronze-landing-zone.md#lake-formation-after-bronze-load)).

**Pass:** Trust policy saves; after a short wait, **`DESC CATALOG INTEGRATION`** no longer reports persistent assume-role failures (exact messages vary by edition).

---

## 8. Catalog-linked database + discovery + read

**Goal:** CLD **`balloon_game_events`** (or **`SNOWFLAKE_LINKED_DATABASE_NAME`**) lists Glue schema and **`balloon_game_events`** table; **`SELECT event`** returns rows.

1. Run: `snow sql --filename snowflake/lab/generated/02_cld_verify.generated.sql`  
   (or uncomment and run **`snowflake/lab/02_cld_verify.sql`**).
2. **Expect:** **`CREATE DATABASE … LINKED_CATALOG`** succeeds; **`SYSTEM$CATALOG_LINK_STATUS`** acceptable state; **`SHOW SCHEMAS`** lists remote Glue DB as a schema; **`SHOW ICEBERG TABLES IN SCHEMA …`** includes **`balloon_game_events`**.
3. **Expect:** **`SELECT event … LIMIT 10`** returns JSON strings in **`event`**.

**Pass:** Discovery and read queries succeed; **`event`** column visible.

**Common failures:** Trust not propagated; wrong quoted **`"<glue_database>"`** case for **`SHOW ICEBERG TABLES`**; integration still **DISABLED**. **`SYSTEM$CATALOG_LINK_STATUS`** stuck with **credential** / **094120** / “**Failed to retrieve credentials from the Catalog**”: re-run **`task snowflake:create-glue-catalog-read-role`** so **`SnowflakeGlueCatalogRead`** includes **Lake Formation** APIs Snowflake documents for vended access, then confirm **Lake Formation** grants the **SIGV4** role on the Glue database/tables **and** the warehouse bucket is **registered** with a data-access role that can read **`BRONZE_BUCKET_NAME`** ([Lake Formation after bronze load](bronze-landing-zone.md#lake-formation-after-bronze-load), [Snowflake Glue REST — Lake Formation](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue)).

---

## 9. Regression — repo health

| Check | Command |
|--------|---------|
| Ruff (Snowflake lab tools) | `uv run ruff check tools/snowflake_lab/` |
| Task list | `task --list \| rg snowflake` — includes **`create-glue-catalog-read-role`**, **`apply-glue-catalog-trust-from-rendered`**, **`print-env-hints`**, **`generate-lab-sql`**, **`describe-catalog-integration`**, **`render-glue-catalog-trust`**. For silver DTs, **`task --list \| rg 'dt:'`** includes **`extvol-*`** before **`generate-sql`**. |

---

## 10. Optional — teardown (Snowflake)

**Goal:** Remove test integration and linked database from the trial account when you are finished (names vary with your **`SNOWFLAKE_LINKED_DATABASE_NAME`**).

Use a worksheet or **`snow sql`** with identifiers matching your run, for example:

```sql
DROP DATABASE IF EXISTS balloon_game_events;
DROP CATALOG INTEGRATION IF EXISTS glue_rest_catalog_int;
```

Align with current [DROP DATABASE](https://docs.snowflake.com/en/sql-reference/sql/drop-database) and [DROP CATALOG INTEGRATION](https://docs.snowflake.com/en/sql-reference/sql/drop-catalog-integration) documentation before executing in shared accounts.

**Pass:** Objects no longer appear in **`SHOW CATALOG INTEGRATIONS`** / **`SHOW DATABASES`**.

---

## 11. Optional — teardown (AWS SIGV4 lab IAM role)

If you created the role in **section 2**, remove it after bronze Glue/S3 Tables teardown (or when those are already gone) with the same **`AWS_PROFILE`**, **`AWS_REGION`**, and **`LAB_USERNAME`** as setup:

`task bronze:cleanup --yes -- --delete-snowflake-catalog-iam-role`

The CLI deletes only when the role exists **and** has tags **`project=balloon-popper-demo`** and **`purpose=snowflake-glue-catalog-read`**. Preview: `task bronze:cleanup-dry-run -- --delete-snowflake-catalog-iam-role`.

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|--------|
| Tester | | | Snowflake account / connection used (internal): |

**Next (silver):** [snowflake-dt-MANUAL-TEST.md](snowflake-dt-MANUAL-TEST.md) — start with **Phase A (external volume)**, then **Phase B (DTs)**.

**Related:** [snowflake-catalog-cld.md](snowflake-catalog-cld.md) (full narrative) · [snowflake/lab/README.md](../snowflake/lab/README.md) · [bronze-landing-zone-MANUAL-TEST.md](bronze-landing-zone-MANUAL-TEST.md) · [`.env.example`](../.env.example)
