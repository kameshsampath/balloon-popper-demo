# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Single place for Snowflake lab defaults (CLD chapter + tasks)."""

# Matches examples in lab/snowflake-catalog-cld.md and generated SQL comments.
DEFAULT_CATALOG_INTEGRATION_NAME = "glue_rest_catalog_int"

# Solo-lab default IAM role name for Snowflake Glue REST SIGV4 (`create-read-role` when LAB_USERNAME unset).
# With LAB_USERNAME, the CLI derives ``<glue_slug>_snowflake_glue_catalog_read`` (see bronze_aws).
DEFAULT_GLUE_CATALOG_READ_ROLE_NAME = "snowflake_glue_catalog_read"
