# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Single place for Snowflake lab defaults (CLD chapter + tasks)."""

# Matches examples in lab/snowflake-catalog-cld.md and generated SQL comments.
DEFAULT_CATALOG_INTEGRATION_NAME = "glue_rest_catalog_int"

# Solo-lab default IAM role name for Snowflake Glue REST SIGV4 (`create-read-role` when LAB_USERNAME unset).
# With LAB_USERNAME, the CLI derives ``<glue_slug>_snowflake_glue_catalog_read`` (see bronze_aws).
DEFAULT_GLUE_CATALOG_READ_ROLE_NAME = "snowflake_glue_catalog_read"

# Dynamic Iceberg Tables chapter (silver) — native DB/schema for Snowflake-managed Iceberg outputs.
DEFAULT_SILVER_DATABASE = "balloon_silver"
DEFAULT_SILVER_SCHEMA = "silver"
# Warehouse for DT refresh (override with SNOWFLAKE_WAREHOUSE).
DEFAULT_SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
