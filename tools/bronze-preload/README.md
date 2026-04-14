# Bronze preload (PyIceberg / Glue)

Land **synthetic or generated** balloon game events into **Iceberg** on **S3** using the same **REST catalog** (e.g. Apache Polaris) Snowflake will **catalog-link**.

## Inputs (environment)

Typical variables (names may change when the script is implemented):

- `REST_CATALOG_URI` — Polaris or compatible Iceberg REST base URL
- `AWS_REGION`, bucket/prefix for warehouse
- Catalog / namespace matching **`balloon_pops`** tables in [lab/bronze-landing-zone.md](../../lab/bronze-landing-zone.md)

## Relationship to `packages/generator`

Reuse event shapes from `packages/generator` (player, balloon_color, score, …) so downstream **Dynamic Iceberg Table** SQL matches [polaris-forge-setup/templates/source.sql.j2](../../polaris-forge-setup/templates/source.sql.j2) semantics.

## Next step

Implement a small Python entrypoint (e.g. `uv run` from repo root) and invoke it from `task bronze:load`.
