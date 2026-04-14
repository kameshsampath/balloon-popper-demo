# Snowflake Quickstart (in progress)

Phase 1 artifacts live here before the published guide file exists.

| Artifact | Purpose |
|----------|---------|
| [EXTRACTION_MAP.md](EXTRACTION_MAP.md) | Source docs/templates → future `sfguides/<id>/<id>.md` sections; Glue table inventory; proposed H2 order |

**Phase 2 scaffold created:** [sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md](lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md) with frontmatter + **`## Overview`** + **`## Tools and prerequisites`** + **`## Bronze landing zone`**.

**Next (Phase 3):** add Snowflake pipeline H2s (catalog integration → linked DB → Dynamic Iceberg Tables → Streamlit in Snowflake) per [EXTRACTION_MAP.md](EXTRACTION_MAP.md). Continue incremental updates by committing quickstart sections with the corresponding `lab/` and `snowflake/lab/` changes they document.

