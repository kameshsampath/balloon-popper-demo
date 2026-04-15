# Manual test plan — bronze landing

Use this checklist to validate **AWS + Glue + optional S3 Tables** before learners or CI depend on it. Run from the **repo root** with `uv sync` already done.

---

## 0. Preconditions

| Check | How |
|--------|-----|
| Host CLIs | `task check-tools` — **required:** **aws**, **snow**, **task**, **envsubst**, **jq**, **cortex**, **uv**; then **`aws sts get-caller-identity`** (valid AWS session). **Recommended:** **direnv**, **curl**, **openssl**; **optional:** **git** ([README](../README.md)) |
| Env template (Phase 0) | `cp .env.example .env` then edit `.env` — or rely on **direnv** + `.env` / `.envrc.local`. Set **`AWS_PROFILE`**, **`AWS_REGION`**, and for workshops **`LAB_USERNAME`** (leave both bucket vars empty for **`<bucket_slug>-balloon-bronze`** / **`<bucket_slug>-balloon-s3tables`**; see `.env.example`). |
| Python | `python --version` shows **3.12+** |
| uv | `uv --version` works |
| AWS CLI | `aws --version` — for S3 Tables steps, **v2.34+** (`aws s3tables help`) |
| Profile | `export AWS_PROFILE=<profile>` (real AWS account; this plan does not use emulated cloud endpoints) |
| Region | `export AWS_REGION=<region>` (or region set on the profile) |

### Env vars and usage

| Variable | Required for | Used by | Notes |
|----------|---------------|---------|-------|
| `AWS_PROFILE` | all phases | all bronze tasks/CLI | Real AWS account profile |
| `AWS_REGION` | all phases | all bronze tasks/CLI | Must match service availability (S3 Tables region support) |
| `BRONZE_BUCKET_NAME` | sections 2, 4, 5 | `bronze:glue-setup`, `bronze:load`, `bronze:all` | With **`LAB_USERNAME`**: omit for **`<slug>-balloon-bronze`**, or set a suffix → **`<slug>-<suffix>`**. Without **`LAB_USERNAME`**, set the full global bucket name. |
| `GLUE_DATABASE` | optional | `glue-setup`, `load`, cleanup | If unset and `LAB_USERNAME` is set, CLI derives one |
| `LAB_USERNAME` | optional but recommended in workshops | derivation logic in bronze CLI | Avoids participant collisions; derives DB + S3 Tables bucket defaults |
| `BRONZE_S3TABLES_BUCKET_NAME` | section 3 | `s3tables-setup`, cleanup | With **`LAB_USERNAME`**: omit for **`<slug>-balloon-s3tables`**, or set a suffix → **`<slug>-<suffix>`**. Without **`LAB_USERNAME`**, set the full globally unique table-bucket name. |
| `BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX` | section 3 | **`s3tables-setup` only** | Optional `1`/`true`/… → append **`-<epoch_millis>`** once at the start of **`s3tables-setup`**. After setup, **`snowflake-lab-sql`**, **`snowflake-catalog-iam`**, and **`snowflake-summary`** resolve the table-bucket from **`.aws-config/`** (see [`.aws-config/README.md`](../.aws-config/README.md)). **`bronze:cleanup`** deletes those bronze files after successful teardown. |
| `S3TABLES_NAMESPACE` | optional | `s3tables-setup`, cleanup | Defaults to `balloon_pops` |

**Record (not in git):** account id, chosen bucket names.

---

## 1. Optional — IAM policy template render

**Goal:** Generated JSON lands in `.aws-config/` and substitutes variables.

1. `export AWS_PROFILE=...` and `export AWS_REGION=...`
2. `export GLUE_DATABASE=balloon_pops` (or your DB name), or set **`LAB_USERNAME`** and omit **`GLUE_DATABASE`** so **`task bronze:render-iam`** derives the same DB name as **`glue-setup`**
3. Set **`BRONZE_BUCKET_NAME`** (or **`LAB_USERNAME`** with empty bucket for derived defaults) so **`render-iam`** can fill the policy **`Resource`** ARNs from the resolved warehouse bucket.
4. Run: `task bronze:render-iam`
5. **Expect:** `.aws-config/bronze-glue-writer-policy.rendered.json` exists; open it and confirm `Resource` ARNs contain your account/region/database (no literal `${...}` left unless you forgot `envsubst` deps — use `gettext`’s `envsubst`).

**Pass:** File exists and JSON is valid (`python -m json.tool .aws-config/bronze-glue-writer-policy.rendered.json`).

---

## 2. Glue database (`bronze:glue-setup`)

**Goal:** Glue catalog database exists with `LocationUri` = warehouse.

1. Set warehouse bucket naming:
   - **Workshop (`LAB_USERNAME`):** omit **`BRONZE_BUCKET_NAME`** for default **`<bucket_slug>-balloon-bronze`**, or set a short suffix (CLI prefixes with **`<bucket_slug>-`**). Run **`task bronze:glue-setup-dry-run`** first if you need the exact resolved bucket name before creating it in S3.
   - **Solo account:** `export BRONZE_BUCKET_NAME=<your-global-bucket-name>`
2. Ensure that warehouse bucket already exists and is accessible by your credentials (required before Glue and load).  
   If **`BRONZE_BUCKET_NAME`** is not exported in your shell (common with **`LAB_USERNAME`** only in `.env`), run **`task bronze:glue-setup-dry-run`** and use the printed **`BRONZE_BUCKET_NAME=`** value for **`aws s3api head-bucket --bucket <that-name> ...`** (and create that bucket first if needed).
3. Optional: `export GLUE_DATABASE=balloon_pops`, or set **`LAB_USERNAME`** and omit **`GLUE_DATABASE`** for a derived per-participant name
4. Run: `task bronze:glue-setup`
5. **Expect:** `.aws-config/glue-database.json` and `.aws-config/bronze-warehouse-uri.txt` written; console ends with **Summary — derived Iceberg warehouse** showing `s3://<bucket>/iceberg/`.
6. Verify:  
   `aws glue get-database --profile "$AWS_PROFILE" --region "$AWS_REGION" --name "${GLUE_DATABASE:-${LAB_USERNAME}_balloon_pops}"`

**Pass:** `Database` shows `Name` equal to your **`GLUE_DATABASE`** (e.g. `<glue_slug>_balloon_pops` when **`LAB_USERNAME`** is set and **`GLUE_DATABASE`** was omitted) and `LocationUri` is `s3://<your-bucket>/iceberg/` (same as `cat .aws-config/bronze-warehouse-uri.txt`).

---

## 3. S3 Tables control plane (`bronze:s3tables-setup`)

**Goal:** Table bucket + namespace `balloon_pops` + one `ICEBERG` table `balloon_game_events`.

1. **Workshop (`LAB_USERNAME`):** omit **`BRONZE_S3TABLES_BUCKET_NAME`** for default **`<bucket_slug>-balloon-s3tables`**, or set a short suffix (CLI prefixes with **`<bucket_slug>-`**). **Solo account:** `export BRONZE_S3TABLES_BUCKET_NAME=<unique-63-chars-lowercase-hyphen>` (globally unique).
2. Optional: `export S3TABLES_NAMESPACE=balloon_pops`
3. Run: `task bronze:s3tables-setup` (optional: `BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX=1` or `uv run bronze-cli s3tables-setup --enable-s3tables-bucket-suffix` for a unique **`-<epoch_millis>`** suffix after stuck deletes)
4. **Expect:** `.aws-config/s3tables-table-bucket-arn.txt`, `.aws-config/s3tables-tables-list.json`, and **`.aws-config/bronze-s3tables-last-bucket-name.txt`** (final table-bucket name for cleanup)
5. Verify: open `s3tables-tables-list.json` — tables include **`balloon_game_events`**
6. **AWS Console (optional):** [Verify S3 Tables in the AWS Console](bronze-landing-zone.md#verify-s3-tables-in-the-aws-console) — **S3 Tables** → **Table buckets**; screenshot **`bronze-s3tables-list.png`** ([lab/images/README.md](images/README.md)).

**Pass:** **`balloon_game_events`** listed under namespace `balloon_pops` (or your `S3TABLES_NAMESPACE`).

**If CLI errors:** Confirm region supports S3 Tables and IAM includes `s3tables:*` as needed; upgrade AWS CLI.

---

## 4. PyIceberg sample load (`bronze:load`)

**Goal:** Glue Data Catalog Iceberg **`balloon_game_events`** on **general S3** receives a prebuilt seed dataset (separate from the S3 Tables empty shell unless you later unify).

1. Same `AWS_PROFILE`, `AWS_REGION`, and `BRONZE_BUCKET_NAME` as section 2 (bucket writable by this principal).
2. Optional: `export GLUE_DATABASE=balloon_pops`
3. Run: `task bronze:load`
4. **Expect:** Console prints `info: generator mode` (default) or `info: synthetic mode`, then `loaded … row(s)` for **`balloon_game_events`** and `OK: dataset …` with `events=…` plus timing summary

**Verify (pick one or more):**

- **AWS Console (recommended for learners):** follow [Verify bronze load in the AWS Console](bronze-landing-zone.md#verify-bronze-load-in-the-aws-console) in **`lab/bronze-landing-zone.md`** — Glue **Data catalog** (database + **`balloon_game_events`** + Iceberg table details) and S3 **`iceberg/`** prefix. Screenshot filenames: [lab/images/README.md](images/README.md); copy PNGs into **`sfguides/lakehouse-iceberg-production-pipelines/assets/`** for the quickstart ([assets/README.md](../sfguides/lakehouse-iceberg-production-pipelines/assets/README.md)).
- **CLI:** `aws glue get-tables --database-name "${GLUE_DATABASE:-balloon_pops}" --profile "$AWS_PROFILE" --region "$AWS_REGION" --query 'TableList[*].Name' --output text` — includes **`balloon_game_events`**.
- **CLI:** `aws s3 ls "s3://${BRONZE_BUCKET_NAME}/iceberg/" --profile "$AWS_PROFILE"` — shows `metadata/` / `data/` style prefixes under the warehouse path after writes.

**Pass:** Iceberg table **`balloon_game_events`** in Glue; S3 objects present under the warehouse; console walk-through matches **`GLUE_DATABASE`** and **`BRONZE_BUCKET_NAME`** if you use the UI path above.

**Optional extension:** If learners have time, run `task bronze:load-more` to append a second prebuilt batch, then re-run downstream transforms to observe updates beyond the seed dataset. `task generator-local` can still be used as an advanced optional path for extra event production.

**Common failures:** AccessDenied on S3 → IAM for this principal; Glue create table denied → Glue + S3 IAM paths; wrong `BRONZE_BUCKET_NAME` → fix bucket name and re-run (may need to drop Glue tables if partially created).

---

## 4a. Lake Formation after bronze load

**Goal:** Register **`BRONZE_BUCKET_NAME`** with Lake Formation, clear Glue default IAM-only table permissions on **`GLUE_DATABASE`**, and grant LF data permissions **to** the **Snowflake catalog `SIGV4` IAM role** (ARN from **`task snowflake:create-glue-catalog-read-role`** → **`.aws-config/snowflake-glue-catalog-iam-role-arn.txt`**). Required when using **`ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS`** with Glue Iceberg REST.

**Preferred:** `task bronze:lakeformation-setup-dry-run` then `task bronze:lakeformation-setup` (same **`AWS_PROFILE`** / **`AWS_REGION`** / bucket / DB as bronze load).

**Manual (equivalent):**

1. Create a **separate** IAM role (not **`SIGV4`**) trusted by **`lakeformation.amazonaws.com`** with **S3 read** on **`arn:aws:s3:::$BRONZE_BUCKET_NAME`**—LF uses this role to read objects when vending credentials; **`SIGV4`** must stay distinct to avoid **vending credential errors**.  
2. Run **`aws lakeformation register-resource`** with **`--no-hybrid-access-enabled`**, **`--no-with-federation`**, and **`--role-arn`** = that **data-access** role, then **`aws glue update-database`** with empty **`CreateTableDefaultPermissions`** as in [Lake Formation (after bronze load)](bronze-landing-zone.md#lake-formation-after-bronze-load) (read the **why** table there).  
3. Run **`aws lakeformation grant-permissions`** for **`DESCRIBE`** on the database and **`SELECT`/`DESCRIBE`** on table wildcard for **`SIGV4_ROLE_ARN`** (Snowflake catalog role only).  
4. Optional: grant **`ALL`** to an admin/SSO principal so you cannot lock yourself out of LF.

**Pass:** LF console shows the S3 location registered; **`.aws-config/lake-formation-bronze-data-access-role-arn.txt`** exists after automation; Snowflake **`SELECT`** from CLD succeeds after catalog integration + IAM trust (see **[lab/snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)**).

---

## 5. Orchestrated run (`bronze:all`)

**Goal:** Strictly ordered glue → s3tables → load.

1. Set all required env vars from sections 2–4 (`BRONZE_BUCKET_NAME`, `BRONZE_S3TABLES_BUCKET_NAME`, etc.).
2. Run: `task bronze:all`
3. **Expect:** Each step completes; same checks as sections 2–4.

**Pass:** Same as sections 2–4 combined.

---

## 5b. Optional — Snowflake CLD prep sheet (`bronze:snowflake-summary`)

**Goal:** Read-only summary of resolved ARNs, Glue REST URI, and table names (no AWS writes).

1. Same env as section 2 (`AWS_PROFILE`, `AWS_REGION`, and workshop or explicit bucket names).
2. Run: `task bronze:snowflake-summary` (human-oriented) or `task bronze:snowflake-summary-json` (single JSON object).
3. **Expect:** Exit **0**; output includes `GLUE_ICEBERG_REST_URI`, S3 / Glue ARNs, and **`balloon_game_events`**.

**Pass:** Output is coherent with the buckets and `GLUE_DATABASE` you used in sections 2–4 (useful notes before Snowflake catalog integration SQL).

---

## 6. Regression — repo health

| Check | Command |
|--------|---------|
| Lint loader | `uv run ruff check tools/bronze_preload/load_sample.py` |
| Task list | `task --list \| rg 'check-tools|bronze|snowflake'` — root **`check-tools`** plus `bronze:*` and `snowflake:*` tasks |

---

## 7. Optional — Snowflake CLD (catalog integration + linked database)

**Goal:** Same as **[lab/snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** — Glue Iceberg REST catalog integration, IAM trust on **`SIGV4_IAM_ROLE`**, catalog-linked database, discovery, and read on **`balloon_game_events`**.

1. Use the dedicated checklist: **[lab/snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** (ordered steps, env table, pass/fail). Narrative and SQL scaffolds remain in **[lab/snowflake-catalog-cld.md](snowflake-catalog-cld.md)**.
2. **Pass:** As defined in **section 8** of **[snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md)** (discovery lists **`balloon_game_events`**; **`SELECT event`** succeeds).

---

## 8. Cleanup (recommended after manual test)

**Goal:** Remove bronze metadata resources created during testing.

1. Preview what will be deleted: `task bronze:cleanup-dry-run`
2. If the preview looks correct, run: `task bronze:cleanup`
3. Verify cleanup:
   - `aws glue get-database --profile "$AWS_PROFILE" --region "$AWS_REGION" --name "${GLUE_DATABASE:-balloon_pops}"` should return `EntityNotFoundException`
   - `aws s3tables list-namespaces --table-bucket-arn "$(cat .aws-config/s3tables-table-bucket-arn.txt)" --region "$AWS_REGION"` should not list `balloon_pops`

**Pass:** Glue database/tables and S3 Tables namespace/table-bucket resources used for this run are removed.

**Note:** `bronze:cleanup` is destructive for **Glue + S3 Tables control plane** only. It does **not** delete **`BRONZE_BUCKET_NAME`** (for example **`<slug>-balloon-bronze`**) or objects under **`iceberg/`**; remove those in S3 separately if you want the warehouse empty. Use per-participant names (`LAB_USERNAME`) in shared accounts and run dry-run first.

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|--------|
| Tester | | | Region / account id (internal): |

**Related:** [bronze-landing-zone.md](bronze-landing-zone.md) · [snowflake-catalog-cld.md](snowflake-catalog-cld.md) · [snowflake-cld-MANUAL-TEST.md](snowflake-cld-MANUAL-TEST.md) · [tools/bronze_preload/README.md](../tools/bronze_preload/README.md)
