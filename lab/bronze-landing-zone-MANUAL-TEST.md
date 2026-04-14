# Manual test plan — bronze landing

Use this checklist to validate **AWS + Glue + optional S3 Tables + optional Snowflake external volume** before learners or CI depend on it. Run from the **repo root** with `uv sync` already done.

---

## 0. Preconditions

| Check | How |
|--------|-----|
| Env template (Phase 0) | `cp .env.example .env` then edit `.env` — or rely on **direnv** + `.env` / `.envrc.local`. Confirm `AWS_PROFILE`, `AWS_REGION`, `BRONZE_WAREHOUSE`, and other vars for the steps you will run. For a **shared workshop AWS account**, set **`LAB_USERNAME`** and leave **`GLUE_DATABASE`** / **`BRONZE_S3TABLES_BUCKET_NAME`** unset so names derive per participant (see `.env.example`). |
| Python | `python --version` shows **3.12+** |
| uv | `uv --version` works |
| AWS CLI | `aws --version` — for S3 Tables steps, **v2.34+** (`aws s3tables help`) |
| Snowflake CLI (optional) | `snow --version` — only if you run **extvolume** tasks |
| Profile | `export AWS_PROFILE=<profile>` (real account, not LocalStack for this plan) |
| Region | `export AWS_REGION=<region>` (or region set on the profile) |

**Record (not in git):** account id, chosen bucket names, any Snowflake connection name you pass to `snow`.

---

## 1. Optional — IAM policy template render

**Goal:** Generated JSON lands in `.aws-config/` and substitutes variables.

1. `export AWS_PROFILE=...` and `export AWS_REGION=...`
2. `export GLUE_DATABASE=balloon_pops` (or your DB name), or set **`LAB_USERNAME`** and omit **`GLUE_DATABASE`** so **`task bronze:render-iam`** derives the same DB name as **`glue-setup`**
3. `export BRONZE_S3_ARN=arn:aws:s3:::your-warehouse-bucket` (no trailing `/*`)
4. Run: `task bronze:render-iam`
5. **Expect:** `.aws-config/bronze-glue-writer-policy.rendered.json` exists; open it and confirm `Resource` ARNs contain your account/region/database (no literal `${...}` left unless you forgot `envsubst` deps — use `gettext`’s `envsubst`).

**Pass:** File exists and JSON is valid (`python -m json.tool .aws-config/bronze-glue-writer-policy.rendered.json`).

---

## 2. Optional — Snowflake external volume + S3 bucket (`sfutils-extvolumes`)

**Goal:** One command path creates **S3 + IAM + Snowflake external volume** (see [sfutils-extvolumes](https://github.com/Snowflake-Labs/sfutils-extvolumes)).

1. Configure **`snow`** for the target account (connection / default as per Snowflake docs).
2. `export AWS_PROFILE=...` `export AWS_REGION=...`
3. `export BRONZE_EXTVOLUME_BUCKET=my-bronze-base` (or rely on default `balloon-bronze-warehouse`)
4. Optional workshop collision guard: `export LAB_USERNAME=yourhandle` — dry-run/create pass **`--prefix`** to sfutils (letters/digits from the handle).
5. Run: `task bronze:extvolume-dry-run`  
   **Expect:** Plan prints; no AWS/Snowflake mutations.
6. Run: `task bronze:extvolume-create`  
   **Expect:** Success output; note **actual S3 bucket name** (often `{prefix}-{bucket}` when prefix is set).
7. Set warehouse for later steps, e.g.  
   `export BRONZE_WAREHOUSE=s3://<actual-bucket>/iceberg/`
8. In Snowflake (worksheet or `snow sql`), confirm external volume exists (name pattern per sfutils README, e.g. `{PREFIX}_{BUCKET}_EXTERNAL_VOLUME`).

**Pass:** Bucket visible in S3 console; external volume exists and `sfutils-extvolumes verify` succeeds if you run it per upstream README.

**Skip this section** if you are **not** using Snowflake yet — create an S3 bucket manually and set `BRONZE_WAREHOUSE` + `BRONZE_S3_ARN` instead.

---

## 3. Glue database (`bronze:glue-setup`)

**Goal:** Glue catalog database exists with `LocationUri` = warehouse.

1. `export BRONZE_WAREHOUSE=s3://<bucket>/<prefix>/` (must end with `/` or script normalizes — your bucket must exist and be writable by credentials used later in §6)
2. Optional: `export GLUE_DATABASE=balloon_pops`, or set **`LAB_USERNAME`** and omit **`GLUE_DATABASE`** for a derived per-participant name
3. Run: `task bronze:glue-setup`
4. **Expect:** `.aws-config/glue-database.json` written.
5. Verify:  
   `aws glue get-database --profile "$AWS_PROFILE" --region "$AWS_REGION" --name "${GLUE_DATABASE:-balloon_pops}"`

**Pass:** `Database` shows `Name` = `balloon_pops` (or your override) and `LocationUri` matches `BRONZE_WAREHOUSE`.

---

## 4. S3 Tables control plane (`bronze:s3tables-setup`)

**Goal:** Table bucket + namespace `balloon_pops` + five `ICEBERG` tables.

1. Pick a **globally unique** table bucket name:  
   `export BRONZE_S3TABLES_BUCKET_NAME=<unique-63-chars-lowercase-hyphen>`
2. Optional: `export S3TABLES_NAMESPACE=balloon_pops`
3. Run: `task bronze:s3tables-setup`
4. **Expect:** `.aws-config/s3tables-table-bucket-arn.txt` and `.aws-config/s3tables-tables-list.json`
5. Verify: open `s3tables-tables-list.json` — tables include  
   `leaderboard`, `balloon_color_stats`, `realtime_scores`, `balloon_colored_pops`, `color_performance_trends`

**Pass:** Five tables listed under namespace `balloon_pops` (or your `S3TABLES_NAMESPACE`).

**If CLI errors:** Confirm region supports S3 Tables and IAM includes `s3tables:*` as needed; upgrade AWS CLI.

---

## 5. PyIceberg sample load (`bronze:load`)

**Goal:** Glue Data Catalog Iceberg tables on **general S3** receive sample rows (separate from S3 Tables empty tables unless you later unify).

1. Same `AWS_PROFILE`, `AWS_REGION`, `BRONZE_WAREHOUSE` as §3 (bucket writable by this principal).
2. Optional: `export GLUE_DATABASE=balloon_pops`
3. Run: `task bronze:load`
4. **Expect:** Console prints `OK: appended sample rows...`

**Verify (pick one or more):**

- `aws glue get-tables --database-name "${GLUE_DATABASE:-balloon_pops}" --profile "$AWS_PROFILE" --region "$AWS_REGION" --query 'TableList[*].Name' --output text` — includes the five table names.
- `aws s3 ls "s3://<bucket>/<prefix>/" --profile "$AWS_PROFILE"` — shows `metadata/` / `data/` style prefixes under the warehouse path after writes.

**Pass:** Five Iceberg tables in Glue; S3 objects present for at least one table.

**Common failures:** AccessDenied on S3 → IAM for this principal; Glue create table denied → Glue + S3 IAM paths; wrong `BRONZE_WAREHOUSE` → fix URI and re-run (may need to drop Glue tables if partially created).

---

## 6. Orchestrated run (`bronze:all`)

**Goal:** Ordered glue → s3tables → load without extvolume (extvolume is **not** in `all`).

1. Set all required env vars from §3–5 (`BRONZE_WAREHOUSE`, `BRONZE_S3TABLES_BUCKET_NAME`, etc.).
2. Run: `task bronze:all`
3. **Expect:** Each step completes; same checks as §3–5.

**Pass:** Same as §3–5 combined.

---

## 7. Regression — repo health

| Check | Command |
|--------|---------|
| Lint loader | `uv run ruff check tools/bronze-preload/load_sample.py` |
| Task list | `task --list \| rg bronze` — shows `extvolume-*`, `render-iam`, `glue-setup`, `s3tables-setup`, `load`, `all` |

---

## 8. Teardown (optional lab reset)

- **S3 Tables:** delete tables / namespace / table bucket via AWS console or CLI (no automated `task` yet — document what you used).
- **Glue / S3 warehouse:** drop Glue tables + database if safe; empty or delete warehouse prefix (mind lifecycle rules).
- **sfutils-extvolumes:** use upstream **`sfutils-extvolumes delete`** / `task down` from that repo if you used **extvolume-create**.

---

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|--------|
| Tester | | | Region / account id (internal): |

---

**Related:** [bronze-landing-zone.md](bronze-landing-zone.md) · [tools/bronze-preload/README.md](../tools/bronze-preload/README.md)
