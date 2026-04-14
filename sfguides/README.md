# Snowflake Quickstart (in progress)

Phase 1 artifacts live here before the published guide file exists.

| Artifact | Purpose |
|----------|---------|
| [EXTRACTION_MAP.md](EXTRACTION_MAP.md) | Source docs/templates → future `sfguides/<id>/<id>.md` sections; Glue table inventory; proposed H2 order |

**Next (Phase 2):** add `sfguides/<id>/<id>.md` with frontmatter (`id` must match folder name), then **reader order**: **`## Overview`** → **`## Tools and prerequisites`** → **`## Bronze landing zone`** → later Snowflake H2s per [EXTRACTION_MAP.md](EXTRACTION_MAP.md). **Grow the Quickstart incrementally** as each phase lands (see **Incremental Quickstart delivery** in that file)—commit guide updates with the lab/SQL they document so content stays validatable while you build.
