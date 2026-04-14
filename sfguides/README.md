# Snowflake Quickstart (in progress)

Phase 1 artifacts live here before the published guide file exists.

| Artifact | Purpose |
|----------|---------|
| [EXTRACTION_MAP.md](EXTRACTION_MAP.md) | Source docs/templates → future `sfguides/<id>/<id>.md` sections; Glue table inventory; proposed H2 order |

**Next (Phase 2):** add `sfguides/<id>/<id>.md` with frontmatter (`id` must match folder name), then **reader order**: **`## Overview`** → **`## Tools and prerequisites`** (accounts, `uv`/`snow`/`task`, scripts, `.env.example`) → **`## Bronze landing zone`** (first hands-on: what exists, what to run, link [lab/bronze-landing-zone.md](../lab/bronze-landing-zone.md)) → Snowflake catalog / CLD / DT / SiS H2s per [EXTRACTION_MAP.md](EXTRACTION_MAP.md). Add **Conclusion**, **Appendix**, and **Resources** as in the map.
