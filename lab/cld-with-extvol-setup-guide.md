# Catalog-Linked Database Setup: AWS Glue to Snowflake Iceberg

## Prerequisites

- **Glue database**: `ksampath_balloon_pops` (standard Glue, not S3 Tables — SourceCatalog shows just the AWS account ID)
- **S3 bucket**: `ksampath-balloon-bronze`
- **IAM role**: `ksampath_snowflake_glue_catalog_read`
- **Snowflake role**: `ACCOUNTADMIN`

---

## Step 1: Create Catalog Integration

```sql
CREATE OR REPLACE CATALOG INTEGRATION ksampath_glue_rest_catalog_int
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = 'ksampath_balloon_pops'
  REST_CONFIG = (
    CATALOG_URI = 'https://glue.us-west-2.amazonaws.com/iceberg'
    CATALOG_API_TYPE = AWS_GLUE
    CATALOG_NAME = '849350360261'
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = 'arn:aws:iam::849350360261:role/ksampath_snowflake_glue_catalog_read'
    SIGV4_SIGNING_REGION = 'us-west-2'
  )
  ENABLED = TRUE;
```

**Notes:**
- `CATALOG_NAME` = AWS account ID. Only use the extended `accountId:S3tablescatalog/bucket` format for actual S3 Tables databases.
- `CATALOG_NAMESPACE` = Glue database name.
- No `ACCESS_DELEGATION_MODE` specified — defaults to `EXTERNAL_VOLUME_CREDENTIALS`.

---

## Step 2: Create External Volume

```sql
CREATE OR REPLACE EXTERNAL VOLUME ksampath_balloon_ext_vol
  STORAGE_LOCATIONS = (
    (
      NAME = 'balloon-bronze'
      STORAGE_BASE_URL = 's3://ksampath-balloon-bronze/'
      STORAGE_PROVIDER = 'S3'
      STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::849350360261:role/ksampath_snowflake_glue_catalog_read'
    )
  )
  ALLOW_WRITES = FALSE;
```

**Notes:**
- `ALLOW_WRITES = FALSE` is required since the IAM role only has read permissions. Without this, validation attempts `s3:PutObject` and fails with `AccessDenied`.

---

## Step 3: Retrieve External IDs from Snowflake

```sql
DESC INTEGRATION ksampath_glue_rest_catalog_int;
-- Note the API_AWS_EXTERNAL_ID value

DESC EXTERNAL VOLUME ksampath_balloon_ext_vol;
-- Note the STORAGE_AWS_EXTERNAL_ID value
```

These two external IDs are **different** and both must be added to the IAM trust policy.

---

## Step 4: Update IAM Trust Policy

Update the trust policy on `ksampath_snowflake_glue_catalog_read` with **both** external IDs:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "SnowflakeCatalogAndVolume",
            "Effect": "Allow",
            "Principal": {
                "AWS": "<API_AWS_IAM_USER_ARN from DESC INTEGRATION>"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "sts:ExternalId": [
                        "<API_AWS_EXTERNAL_ID from DESC INTEGRATION>",
                        "<STORAGE_AWS_EXTERNAL_ID from DESC EXTERNAL VOLUME>"
                    ]
                }
            }
        }
    ]
}
```

**Critical:** Each `CREATE OR REPLACE` rotates the external ID. Do not re-run those cells after setting the trust policy.

---

## Step 5: IAM Permissions Policy

The IAM role needs these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowGlueCatalogTableAccess",
            "Effect": "Allow",
            "Action": [
                "glue:GetCatalog",
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:GetTable",
                "glue:GetTables"
            ],
            "Resource": [
                "arn:aws:glue:us-west-2:849350360261:table/ksampath_balloon_pops/*",
                "arn:aws:glue:us-west-2:849350360261:catalog",
                "arn:aws:glue:us-west-2:849350360261:database/ksampath_balloon_pops"
            ]
        },
        {
            "Sid": "S3ReadForIceberg",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::ksampath-balloon-bronze",
                "arn:aws:s3:::ksampath-balloon-bronze/*"
            ]
        }
    ]
}
```

---

## Step 6: Grant USAGE on External Volume

```sql
GRANT USAGE ON EXTERNAL VOLUME ksampath_balloon_ext_vol TO ROLE ACCOUNTADMIN;
```

The catalog-linked database owner role needs USAGE on the external volume for automatic table discovery.

---

## Step 7: Create Catalog-Linked Database

```sql
CREATE OR REPLACE DATABASE balloon_game_events
  COMMENT = 'CLD: Glue bronze Iceberg'
  EXTERNAL_VOLUME = 'ksampath_balloon_ext_vol'
  LINKED_CATALOG = (
    CATALOG = 'ksampath_glue_rest_catalog_int'
  );
```

---

## Step 8: Verify

```sql
SELECT SYSTEM$CATALOG_LINK_STATUS('balloon_game_events');
-- Expect: executionState = "RUNNING" with empty failureDetails
```

---

## Querying the Data

```sql
SHOW SCHEMAS IN DATABASE balloon_game_events;
SHOW ICEBERG TABLES IN SCHEMA balloon_game_events."ksampath_balloon_pops";

-- Sample raw events
SELECT event
FROM balloon_game_events."ksampath_balloon_pops"."balloon_game_events"
LIMIT 10;

-- Parse JSON fields
SELECT
  PARSE_JSON(event):player::STRING AS player,
  PARSE_JSON(event):balloon_color::STRING AS balloon_color,
  PARSE_JSON(event):score::INTEGER AS score,
  PARSE_JSON(event):event_ts::TIMESTAMP_TZ AS event_ts
FROM balloon_game_events."ksampath_balloon_pops"."balloon_game_events"
LIMIT 10;
```

---

## Cleanup

```sql
DROP DATABASE IF EXISTS balloon_game_events;
DROP CATALOG INTEGRATION IF EXISTS ksampath_glue_rest_catalog_int;
DROP EXTERNAL VOLUME IF EXISTS ksampath_balloon_ext_vol;
```

---

## Troubleshooting

| Issue | Root Cause | Fix |
|---|---|---|
| "Failed to retrieve credentials from Catalog" | `VENDED_CREDENTIALS` needs Lake Formation setup | Remove `ACCESS_DELEGATION_MODE` to default to `EXTERNAL_VOLUME_CREDENTIALS` |
| "s3:PutObject AccessDenied" during volume validation | External volume tries write validation | Add `ALLOW_WRITES = FALSE` to external volume |
| "not authorized to perform sts:AssumeRole" | Trust policy missing or wrong external ID | Get current external IDs from `DESC INTEGRATION` and `DESC EXTERNAL VOLUME`; don't re-run `CREATE OR REPLACE` after setting trust policy |
| "owner role must have USAGE on external volume" | CLD owner role lacks permission | `GRANT USAGE ON EXTERNAL VOLUME ... TO ROLE <owner_role>` |
| `CATALOG_NAME` confusion | Standard Glue vs S3 Tables | Standard Glue: use AWS account ID. S3 Tables: use `accountId:S3tablescatalog/bucket-name` |
