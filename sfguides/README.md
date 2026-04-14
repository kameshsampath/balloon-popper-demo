# Snowflake Quickstart (in progress)

Phase 1 artifacts live here before the published guide file exists.

| Artifact | Purpose |
|----------|---------|
| [EXTRACTION_MAP.md](EXTRACTION_MAP.md) | Source docs/templates → future `sfguides/<id>/<id>.md` sections; Glue table inventory; proposed H2 order |

**Phase 2 scaffold created:** [sfguides/lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md](lakehouse-iceberg-production-pipelines/lakehouse-iceberg-production-pipelines.md) with frontmatter + **`## Overview`** + **`## Tools and prerequisites`** + **`## Bronze landing zone`**.

**Next (Phase 3):** add Snowflake pipeline H2s (catalog integration → linked DB → Dynamic Iceberg Tables → Streamlit in Snowflake) per [EXTRACTION_MAP.md](EXTRACTION_MAP.md). Continue incremental updates by committing quickstart sections with the corresponding `lab/` and `snowflake/lab/` changes they document.

## Sync into local `sfquickstarts`

Requires **`rsync`** on `PATH`. Defaults target this machine’s clone:

`/Users/ksampath/git-sfc/Snowflake-Labs/sfquickstarts/site/sfguides/src`

| Task | What it does |
|------|----------------|
| `task sfquickstarts:sync-guide-dry-run` | Dry-run: mirror **`sfguides/<SFGUIDE_ID>/`** → **`…/src/<SFGUIDE_ID>/`** |
| `task sfquickstarts:sync-guide` | Same with **`--delete`** only **inside** that destination folder (removes stale files in that guide only) |
| `task sfquickstarts:sync-sfguides-dry-run` | Dry-run: copy **all** top-level children of **`sfguides/`** into **`…/src/`**, excluding **`EXTRACTION_MAP.md`** and **`README.md`** |
| `task sfquickstarts:sync-sfguides` | Same, **without** `--delete` (safer when `src/` already has other guides) |

Override paths / id from the shell, for example:

```bash
task SFQUICKSTARTS_SRC=/path/to/sfquickstarts/site/sfguides/src SFGUIDE_ID=lakehouse-iceberg-production-pipelines sfquickstarts:sync-guide-dry-run
```
