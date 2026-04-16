# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Generate Snowflake lab SQL from bronze ``.aws-config`` + env (Glue Iceberg REST, gist-style S3 Tables by default)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

import click

from tools.bronze_preload.bronze_aws import (
    glue_database_json_path,
    repo_root,
    require_aws_profile,
    resolve_aws_account_id,
    resolve_region,
    resolve_s3tables_table_bucket_name,
)
from tools.bronze_preload.bronze_tables import BRONZE_RAW_EVENTS_TABLE
from tools.snowflake_lab.defaults import (
    DEFAULT_CATALOG_INTEGRATION_NAME,
    DEFAULT_SILVER_DATABASE,
    DEFAULT_SILVER_SCHEMA,
    DEFAULT_SNOWFLAKE_WAREHOUSE,
)

# Optional one-line file (repo-local, gitignored): same idea as bronze-warehouse-uri.txt.
SIGV4_ROLE_ARN_REL = Path(".aws-config") / "snowflake-glue-catalog-iam-role-arn.txt"
S3TABLES_LAST_BUCKET_REL = Path(".aws-config") / "bronze-s3tables-last-bucket-name.txt"
DEFAULT_S3TABLES_NAMESPACE = "balloon_pops"


def _sql_single_quoted(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _sql_object_identifier(name: str, *, fallback: str) -> str:
    """Snowflake object name (warehouse, database, …): bare identifier when safe, else double-quoted."""
    n = (name or "").strip()
    if not n:
        n = fallback
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", n):
        return n
    return '"' + n.replace('"', '""') + '"'


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _load_glue_database_block(root: Path) -> dict:
    path = glue_database_json_path(root)
    if not path.is_file():
        raise click.ClickException(
            f"Missing {path}. Run `task bronze:glue-setup` (or `uv run bronze-cli glue-setup`) "
            "so Glue metadata is written to .aws-config/."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise click.ClickException(f"Could not read {path}: {e}") from e
    if not isinstance(data, dict):
        raise click.ClickException(f"{path} must be a JSON object.")
    db = data.get("Database")
    if not isinstance(db, dict):
        raise click.ClickException(f"{path} must contain a Database object.")
    return db


def _resolve_account_id(db: dict, region: str) -> str:
    cid = db.get("CatalogId")
    if isinstance(cid, str) and cid.strip().isdigit() and len(cid.strip()) == 12:
        return cid.strip()
    require_aws_profile()
    prof = os.environ.get("AWS_PROFILE", "").strip()
    return resolve_aws_account_id(prof, region)


def read_sigv4_role_arn_from_aws_config(root: Path) -> str | None:
    """First line of ``.aws-config/snowflake-glue-catalog-iam-role-arn.txt`` if it looks like an IAM role ARN."""
    path = root / SIGV4_ROLE_ARN_REL
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("arn:aws:iam:") and ":role/" in line:
            return line
    return None


def _glue_database_name(db: dict) -> str:
    name = db.get("Name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    raise click.ClickException(
        "glue-database.json has no Database.Name. Re-run bronze glue-setup or fix the file."
    )


def resolve_s3tables_table_bucket(root: Path, cli_bucket: str) -> str:
    """Table-bucket name for ``<account>:S3tablescatalog/<bucket>`` (S3 Tables REST shape).

    Delegates to :func:`tools.bronze_preload.bronze_aws.resolve_s3tables_table_bucket_name`.
    """
    return resolve_s3tables_table_bucket_name(root, cli_bucket=cli_bucket)


def _require_s3tables_bucket_for_s3tables_mode(
    root: Path,
    *,
    cli_bucket: str,
    placeholder_role: bool,
) -> None:
    """Fail fast if Glue Iceberg REST + S3 Tables shape cannot resolve the table-bucket."""
    if placeholder_role:
        return
    b = resolve_s3tables_table_bucket(root, cli_bucket)
    if b:
        return
    cfg = (root / ".aws-config").as_posix()
    raise click.ClickException(
        "S3 Tables catalog shape requires a table-bucket name. Populate one of: "
        f"`{cfg}/s3tables-table-bucket-arn.txt` (from `task bronze:s3tables-setup`), "
        f"`{cfg}/bronze-s3tables-last-bucket-name.txt`, "
        "or set SNOWFLAKE_S3TABLES_BUCKET_NAME / BRONZE_S3TABLES_BUCKET_NAME, "
        "or pass --s3tables-bucket. "
        "Or use default Glue Data Catalog mode (omit --glue-s3tables-catalog; "
        "do not set SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG)."
    )


def resolve_catalog_namespace(*, use_data_catalog: bool, glue_database: str) -> str:
    if use_data_catalog:
        return glue_database
    v = (
        (os.environ.get("SNOWFLAKE_S3TABLES_CATALOG_NAMESPACE") or "").strip()
        or (os.environ.get("S3TABLES_NAMESPACE") or "").strip()
    )
    return v or DEFAULT_S3TABLES_NAMESPACE


def resolve_rest_catalog_params(
    *,
    account: str,
    glue_database: str,
    root: Path,
    rest_catalog_override: str,
    use_data_catalog: bool,
    cli_s3tables_bucket: str,
    placeholder_role: bool,
) -> tuple[str, str, Literal["gist", "classic", "override"]]:
    """Return (CATALOG_NAME, CATALOG_NAMESPACE, mode) for REST_CONFIG + top-level namespace."""
    o = (rest_catalog_override or "").strip()
    if o:
        return (
            o,
            resolve_catalog_namespace(
                use_data_catalog=use_data_catalog, glue_database=glue_database
            ),
            "override",
        )
    if use_data_catalog:
        return account, glue_database, "classic"
    bucket = resolve_s3tables_table_bucket(root, cli_s3tables_bucket)
    if not bucket:
        if placeholder_role:
            bucket = "REPLACE_ME_TABLE_BUCKET"
            print(
                "warning: no S3 Tables table-bucket resolved; "
                "CATALOG_NAME uses REPLACE_ME_TABLE_BUCKET (set BRONZE_S3TABLES_BUCKET_NAME or run s3tables-setup).",
                file=sys.stderr,
            )
        else:
            raise click.ClickException(
                "Glue Iceberg REST + S3 Tables shape needs the table-bucket for "
                "CATALOG_NAME = '<account>:S3tablescatalog/<bucket>'. Run `task bronze:s3tables-setup` "
                f"(writes `.aws-config/s3tables-table-bucket-arn.txt` and `{S3TABLES_LAST_BUCKET_REL.as_posix()}`), "
                "or set SNOWFLAKE_S3TABLES_BUCKET_NAME / BRONZE_S3TABLES_BUCKET_NAME, pass --s3tables-bucket, "
                "or use --glue-data-catalog for Glue Data Catalog only (CATALOG_NAME = account id)."
            )
    catalog_name = f"{account}:S3tablescatalog/{bucket}"
    ns = resolve_catalog_namespace(use_data_catalog=False, glue_database=glue_database)
    return catalog_name, ns, "gist"


def render_catalog_integration_sql(
    *,
    integration_name: str,
    catalog_namespace: str,
    catalog_name_rest: str,
    catalog_mode: Literal["gist", "classic", "override"],
    region: str,
    sigv4_role_arn: str,
) -> str:
    catalog_uri = f"https://glue.{region}.amazonaws.com/iceberg"
    lines = [
        "-- Generated by `task snowflake:generate-lab-sql` (tools/snowflake_lab/sql_generate.py).",
    ]
    if catalog_mode == "override":
        lines.append(
            "-- CATALOG_NAME: explicit SNOWFLAKE_GLUE_REST_CATALOG_NAME / --rest-catalog-name override."
        )
    elif catalog_mode == "classic":
        lines.append(
            "-- AWS Glue Data Catalog (Snowflake doc Step 2): CATALOG_NAME = 12-digit AWS account id; "
            "CATALOG_NAMESPACE = Glue database (Database.Name from glue-database.json). "
            "https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue#step-2-create-a-catalog-integration-in-snowflake"
        )
    else:
        lines.append(
            "-- Glue Iceberg REST + Amazon S3 Tables (opt-in): CATALOG_NAME = '<account>:S3tablescatalog/<table_bucket>'; "
            "CATALOG_NAMESPACE = S3 Tables namespace (e.g. balloon_pops). "
            "CATALOG_URI stays https://glue.<region>.amazonaws.com/iceberg (AWS Glue REST — catalog id / prefix rules: "
            "https://docs.aws.amazon.com/glue/latest/dg/connect-glu-iceberg-rest.html ). "
            "Not the standalone S3 Tables REST host ( https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-open-source.html ). "
            "Generate with --glue-s3tables-catalog or SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1."
        )
    lines.extend(
        [
            "-- Re-run after bronze glue-setup if Glue database or region changes.",
            "-- Docs: https://docs.snowflake.com/en/sql-reference/sql/create-catalog-integration-rest",
            "--       https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue",
            "--       https://docs.snowflake.com/en/sql-reference/sql/create-database-catalog-linked",
            "-- ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS: use vended creds for Iceberg files (CREATE CATALOG INTEGRATION REST; "
            "default would be EXTERNAL_VOLUME_CREDENTIALS — set if you use a Snowflake external volume instead).",
            "",
            f"CREATE OR REPLACE CATALOG INTEGRATION {integration_name}",
            "  CATALOG_SOURCE = ICEBERG_REST",
            "  TABLE_FORMAT = ICEBERG",
            f"  CATALOG_NAMESPACE = {_sql_single_quoted(catalog_namespace)}",
            "  REST_CONFIG = (",
            f"    CATALOG_URI = {_sql_single_quoted(catalog_uri)}",
            "    CATALOG_API_TYPE = AWS_GLUE",
            f"    CATALOG_NAME = {_sql_single_quoted(catalog_name_rest)}",
            "    ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS",
            "  )",
            "  REST_AUTHENTICATION = (",
            "    TYPE = SIGV4",
            f"    SIGV4_IAM_ROLE = {_sql_single_quoted(sigv4_role_arn)}",
            f"    SIGV4_SIGNING_REGION = {_sql_single_quoted(region)}",
            "  )",
            "  ENABLED = TRUE;",
            "",
            f"-- After IAM trust is correct: DESC CATALOG INTEGRATION {integration_name};",
            "",
        ]
    )
    return "\n".join(lines)


def render_cld_verify_sql(
    *,
    integration_name: str,
    linked_database: str,
    remote_schema_lower: str,
    raw_table: str,
) -> str:
    lines = [
        "-- Generated by `task snowflake:generate-lab-sql` (tools/snowflake_lab/sql_generate.py).",
        "-- Docs: https://docs.snowflake.com/en/sql-reference/sql/create-database-catalog-linked",
        "--       https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog-linked-database",
        "",
        f"CREATE OR REPLACE DATABASE {linked_database}",
        "  COMMENT = 'CLD: Glue bronze Iceberg (lab DB name matches raw table balloon_game_events)'",
        "  LINKED_CATALOG = (",
        f"    CATALOG = {_sql_single_quoted(integration_name)}",
        "  );",
        "",
        f"SELECT SYSTEM$CATALOG_LINK_STATUS({_sql_single_quoted(linked_database)});",
        "",
        f"USE DATABASE {linked_database};",
        f"SHOW SCHEMAS IN DATABASE {linked_database};",
        f'SHOW ICEBERG TABLES IN SCHEMA {linked_database}."{remote_schema_lower}";',
        "",
        "-- Sample read (bronze JSON column `event`)",
        f'SELECT event FROM {linked_database}."{remote_schema_lower}"."{raw_table}" LIMIT 10;',
        "",
        "-- Optional: project JSON in Snowflake",
        "SELECT",
        "  PARSE_JSON(event):player::STRING AS player,",
        "  PARSE_JSON(event):balloon_color::STRING AS balloon_color,",
        "  PARSE_JSON(event):score::INTEGER AS score,",
        "  PARSE_JSON(event):event_ts::TIMESTAMP_TZ AS event_ts",
        f'FROM {linked_database}."{remote_schema_lower}"."{raw_table}"',
        "LIMIT 10;",
        "",
    ]
    return "\n".join(lines)


def render_dt_pipelines_sql(
    *,
    linked_database: str,
    remote_schema_lower: str,
    raw_table: str,
    silver_database: str,
    silver_schema: str,
    warehouse: str,
    external_volume: str,
    path_prefix: str,
) -> str:
    """Dynamic Iceberg Tables mirroring legacy RisingWave MVs (docs/implementing_data_pipeline.md)."""
    fq_bronze = f'{linked_database}."{remote_schema_lower}"."{raw_table}"'
    wh = _sql_object_identifier(warehouse, fallback=DEFAULT_SNOWFLAKE_WAREHOUSE)
    ev = _sql_single_quoted(external_volume)
    pp = path_prefix.strip().strip("/") or "balloon_lab"

    def _dt_block(
        table: str,
        base_suffix: str,
        col_defs: list[str],
        as_select_lines: list[str],
    ) -> str:
        bl = f"{pp}/{base_suffix}"
        cols = "\n".join(col_defs)
        body = "\n".join(as_select_lines)
        return (
            f"CREATE OR REPLACE DYNAMIC ICEBERG TABLE {table} (\n{cols}\n)\n"
            "  TARGET_LAG = '5 minutes'\n"
            f"  WAREHOUSE = {wh}\n"
            f"  EXTERNAL_VOLUME = {ev}\n"
            "  CATALOG = 'SNOWFLAKE'\n"
            f"  BASE_LOCATION = {_sql_single_quoted(bl)}\n"
            "AS\n"
            f"{body};\n"
        )

    # Parsed bronze rows (RisingWave ``balloon_game_events`` as VARIANT paths).
    inner_from = (
        "SELECT\n"
        "  v:player::STRING AS player,\n"
        "  v:balloon_color::STRING AS balloon_color,\n"
        "  v:score::INTEGER AS score_i,\n"
        "  v:favorite_color_bonus::BOOLEAN AS fav_bonus,\n"
        "  v:event_ts::TIMESTAMP_TZ AS ts\n"
        "FROM (\n"
        "  SELECT PARSE_JSON(event) AS v\n"
        f"  FROM {fq_bronze}\n"
        ") q"
    )

    lines: list[str] = [
        "-- Generated by `task dt:generate-sql` / `uv run snowflake-lab-sql generate --dt-pipelines-only`.",
        "-- Maps legacy RisingWave MVs: mv_leaderboard, mv_balloon_color_stats, mv_realtime_scores,",
        "-- mv_balloon_colored_pops, mv_color_performance_trends (15s windows via TIME_SLICE).",
        "-- Prereq: CLD reads OK; USAGE on warehouse + external volume; role can create DT + read bronze.",
        "-- Docs: https://docs.snowflake.com/en/sql-reference/sql/create-dynamic-table",
        "--       https://docs.snowflake.com/en/user-guide/dynamic-tables-create-iceberg",
        "",
        f"CREATE DATABASE IF NOT EXISTS {silver_database}",
        "  COMMENT = 'Snowflake-managed silver (Dynamic Iceberg Tables over CLD bronze)';",
        "",
        f"USE DATABASE {silver_database};",
        "",
        f"CREATE SCHEMA IF NOT EXISTS {silver_schema}",
        "  COMMENT = 'Aggregates from bronze balloon_game_events (JSON column event)';",
        "",
        f"USE SCHEMA {silver_schema};",
        "",
    ]

    # 1 — mv_leaderboard
    lines.append(
        _dt_block(
            "dt_player_leaderboard",
            "dt_player_leaderboard",
            [
                "  player STRING,",
                "  total_score NUMBER(38,0),",
                "  bonus_pops NUMBER(38,0),",
                "  last_event_ts TIMESTAMP_TZ",
            ],
            [
                "SELECT",
                "  e.player AS player,",
                "  SUM(e.score_i) AS total_score,",
                "  COUNT_IF(e.fav_bonus) AS bonus_pops,",
                "  MAX(e.ts) AS last_event_ts",
                "FROM (",
                f"  {inner_from}",
                ") e",
                "GROUP BY e.player",
            ],
        )
    )

    # 2 — mv_balloon_color_stats
    lines.append(
        _dt_block(
            "dt_balloon_color_stats",
            "dt_balloon_color_stats",
            [
                "  player STRING,",
                "  balloon_color STRING,",
                "  balloon_pops NUMBER(38,0),",
                "  points_by_color NUMBER(38,0),",
                "  bonus_hits NUMBER(38,0),",
                "  last_event_ts TIMESTAMP_TZ",
            ],
            [
                "SELECT",
                "  e.player,",
                "  e.balloon_color,",
                "  COUNT(*) AS balloon_pops,",
                "  SUM(e.score_i) AS points_by_color,",
                "  COUNT_IF(e.fav_bonus) AS bonus_hits,",
                "  MAX(e.ts) AS last_event_ts",
                "FROM (",
                f"  {inner_from}",
                ") e",
                "GROUP BY e.player, e.balloon_color",
            ],
        )
    )

    # 3 — mv_realtime_scores (15s tumble)
    lines.append(
        _dt_block(
            "dt_realtime_scores",
            "dt_realtime_scores",
            [
                "  player STRING,",
                "  total_score NUMBER(38,0),",
                "  window_start TIMESTAMP_TZ,",
                "  window_end TIMESTAMP_TZ",
            ],
            [
                "SELECT",
                "  w.player,",
                "  w.total_score,",
                "  w.window_start,",
                "  DATEADD(second, 15, w.window_start) AS window_end",
                "FROM (",
                "  SELECT",
                "    e.player,",
                "    SUM(e.score_i) AS total_score,",
                "    TIME_SLICE(e.ts, 15, 'SECOND') AS window_start",
                "  FROM (",
                f"    {inner_from}",
                "  ) e",
                "  GROUP BY e.player, TIME_SLICE(e.ts, 15, 'SECOND')",
                ") w",
            ],
        )
    )

    # 4 — mv_balloon_colored_pops
    lines.append(
        _dt_block(
            "dt_balloon_colored_pops",
            "dt_balloon_colored_pops",
            [
                "  player STRING,",
                "  balloon_color STRING,",
                "  balloon_pops NUMBER(38,0),",
                "  points_by_color NUMBER(38,0),",
                "  bonus_hits NUMBER(38,0),",
                "  window_start TIMESTAMP_TZ,",
                "  window_end TIMESTAMP_TZ",
            ],
            [
                "SELECT",
                "  w.player,",
                "  w.balloon_color,",
                "  w.balloon_pops,",
                "  w.points_by_color,",
                "  w.bonus_hits,",
                "  w.window_start,",
                "  DATEADD(second, 15, w.window_start) AS window_end",
                "FROM (",
                "  SELECT",
                "    e.player,",
                "    e.balloon_color,",
                "    COUNT(*) AS balloon_pops,",
                "    SUM(e.score_i) AS points_by_color,",
                "    COUNT_IF(e.fav_bonus) AS bonus_hits,",
                "    TIME_SLICE(e.ts, 15, 'SECOND') AS window_start",
                "  FROM (",
                f"    {inner_from}",
                "  ) e",
                "  GROUP BY e.player, e.balloon_color, TIME_SLICE(e.ts, 15, 'SECOND')",
                ") w",
            ],
        )
    )

    # 5 — mv_color_performance_trends
    lines.append(
        _dt_block(
            "dt_color_performance_trends",
            "dt_color_performance_trends",
            [
                "  balloon_color STRING,",
                "  avg_score_per_pop NUMBER(38,6),",
                "  total_pops NUMBER(38,0),",
                "  window_start TIMESTAMP_TZ,",
                "  window_end TIMESTAMP_TZ",
            ],
            [
                "SELECT",
                "  w.balloon_color,",
                "  w.avg_score_per_pop,",
                "  w.total_pops,",
                "  w.window_start,",
                "  DATEADD(second, 15, w.window_start) AS window_end",
                "FROM (",
                "  SELECT",
                "    e.balloon_color,",
                "    AVG(e.score_i) AS avg_score_per_pop,",
                "    COUNT(*) AS total_pops,",
                "    TIME_SLICE(e.ts, 15, 'SECOND') AS window_start",
                "  FROM (",
                f"    {inner_from}",
                "  ) e",
                "  GROUP BY e.balloon_color, TIME_SLICE(e.ts, 15, 'SECOND')",
                ") w",
            ],
        )
    )

    lines.extend(
        [
            "-- Verify (after refresh; see Snowflake Dynamic Tables monitoring docs)",
            "SHOW DYNAMIC TABLES LIKE 'dt_%' IN SCHEMA;",
            "",
        ]
    )
    return "\n".join(lines)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Snowflake CLD lab helpers: generate SQL from ``.aws-config``, print default env hints."""


@cli.command("generate")
@click.option(
    "--repo-root",
    "repo_root_opt",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Repository root (default: inferred from this package).",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Directory for *.generated.sql (default: snowflake/lab/generated under repo root).",
)
@click.option(
    "--integration-name",
    envvar="SNOWFLAKE_CATALOG_INTEGRATION_NAME",
    default=DEFAULT_CATALOG_INTEGRATION_NAME,
    show_default=True,
    help="Catalog integration object name (repo default matches trust tasks and lab docs).",
)
@click.option(
    "--sigv4-role-arn",
    envvar="SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN",
    default="",
    help="Override signer IAM role ARN for SIGV4_IAM_ROLE. If unset, uses first line of "
    ".aws-config/snowflake-glue-catalog-iam-role-arn.txt (written by create-glue-catalog-read-role). "
    "Required only if neither is set (unless --placeholder-role).",
)
@click.option(
    "--linked-database",
    envvar="SNOWFLAKE_LINKED_DATABASE_NAME",
    default=BRONZE_RAW_EVENTS_TABLE,
    show_default=True,
    help="Catalog-linked database name (lab default matches bronze table name for clarity).",
)
@click.option(
    "--placeholder-role",
    is_flag=True,
    help="If set, emit SIGV4_IAM_ROLE = 'arn:aws:iam::<account>:role/REPLACE_ME_GLUE_CATALOG_READ' "
    "(no SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN required).",
)
@click.option(
    "--rest-catalog-name",
    "rest_catalog_name",
    envvar="SNOWFLAKE_GLUE_REST_CATALOG_NAME",
    default="",
    show_envvar=True,
    help="Full REST_CONFIG CATALOG_NAME override (replaces computed gist or classic value).",
)
@click.option(
    "--glue-data-catalog",
    "glue_data_catalog",
    is_flag=True,
    help="Force AWS Glue Data Catalog shape (same as default): CATALOG_NAME = 12-digit account id; "
    "CATALOG_NAMESPACE = Glue Database.Name. Or set SNOWFLAKE_GLUE_REST_USE_DATA_CATALOG=1.",
)
@click.option(
    "--glue-s3tables-catalog",
    "glue_s3tables_catalog",
    is_flag=True,
    help="Use Amazon S3 Tables Glue catalog id: CATALOG_NAME = '<account>:S3tablescatalog/<table_bucket>'. "
    "Default without this flag follows Snowflake Step 2 (account id only). "
    "Or set SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1/true/yes/on.",
)
@click.option(
    "--s3tables-bucket",
    "s3tables_bucket",
    default="",
    help="S3 **table bucket** name when using --glue-s3tables-catalog / SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG. "
    "If unset, resolves from .aws-config/ (s3tables-table-bucket-arn.txt, then "
    "bronze-s3tables-last-bucket-name.txt), then SNOWFLAKE_S3TABLES_BUCKET_NAME / BRONZE_S3TABLES_BUCKET_NAME.",
)
@click.option(
    "--silver-database",
    envvar="SNOWFLAKE_SILVER_DATABASE",
    default=DEFAULT_SILVER_DATABASE,
    show_default=True,
    help="Native Snowflake database for Dynamic Iceberg Table outputs (not the CLD name).",
)
@click.option(
    "--silver-schema",
    envvar="SNOWFLAKE_SILVER_SCHEMA",
    default=DEFAULT_SILVER_SCHEMA,
    show_default=True,
    help="Schema inside --silver-database for silver DT objects.",
)
@click.option(
    "--warehouse",
    envvar="SNOWFLAKE_WAREHOUSE",
    default=DEFAULT_SNOWFLAKE_WAREHOUSE,
    show_default=True,
    help="Warehouse name for TARGET_LAG refresh (USAGE required).",
)
@click.option(
    "--external-volume",
    envvar="SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME",
    default="",
    show_envvar=True,
    help="EXTERNAL_VOLUME for CREATE DYNAMIC ICEBERG TABLE. If unset, emits REPLACE_ME_ICEBERG_EXTERNAL_VOLUME.",
)
@click.option(
    "--dt-path-prefix",
    envvar="SNOWFLAKE_DT_PATH_PREFIX",
    default="",
    help="Directory prefix under the external volume for all DT BASE_LOCATION paths (default: balloon_lab).",
)
@click.option(
    "--catalog-cld-only",
    "catalog_cld_only",
    is_flag=True,
    help="Emit only 01_catalog_integration + 02_cld_verify (use with task snowflake:generate-lab-sql).",
)
@click.option(
    "--dt-pipelines-only",
    "dt_pipelines_only",
    is_flag=True,
    help="Emit only 03_dt_pipelines.generated.sql (use with task dt:generate-sql).",
)
@click.option(
    "--stdout",
    "to_stdout",
    is_flag=True,
    help="Print generated scripts to stdout instead of writing files.",
)
def generate_cmd(
    repo_root_opt: Path | None,
    output_dir: Path | None,
    integration_name: str,
    sigv4_role_arn: str,
    linked_database: str,
    placeholder_role: bool,
    rest_catalog_name: str,
    glue_data_catalog: bool,
    glue_s3tables_catalog: bool,
    s3tables_bucket: str,
    silver_database: str,
    silver_schema: str,
    warehouse: str,
    external_volume: str,
    dt_path_prefix: str,
    catalog_cld_only: bool,
    dt_pipelines_only: bool,
    to_stdout: bool,
) -> None:
    if catalog_cld_only and dt_pipelines_only:
        raise click.ClickException("Use only one of --catalog-cld-only and --dt-pipelines-only.")

    root = repo_root_opt or repo_root()
    write_catalog = not dt_pipelines_only
    write_dt = not catalog_cld_only

    db = _load_glue_database_block(root)
    glue_db = _glue_database_name(db)
    region = resolve_region()
    account = _resolve_account_id(db, region)
    use_s3tables_shape = bool(glue_s3tables_catalog) or _env_truthy(
        "SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG"
    )
    use_data_catalog = (
        bool(glue_data_catalog)
        or _env_truthy("SNOWFLAKE_GLUE_REST_USE_DATA_CATALOG")
        or not use_s3tables_shape
    )

    if write_catalog and use_s3tables_shape:
        _require_s3tables_bucket_for_s3tables_mode(
            root, cli_bucket=s3tables_bucket, placeholder_role=placeholder_role
        )

    role_arn = ""
    if write_catalog:
        if placeholder_role:
            role_arn = f"arn:aws:iam::{account}:role/REPLACE_ME_GLUE_CATALOG_READ"
        else:
            role_arn = (sigv4_role_arn or "").strip()
            if not role_arn:
                role_arn = (read_sigv4_role_arn_from_aws_config(root) or "").strip()
            if not role_arn:
                rel = SIGV4_ROLE_ARN_REL.as_posix()
                raise click.ClickException(
                    "No SIGV4 IAM role ARN: not in env, not in "
                    f"{rel}. Default: run `task snowflake:create-glue-catalog-read-role` (writes that file). "
                    "Override only if you use another signer role: "
                    "SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN, --sigv4-role-arn, or edit the .txt file. "
                    "Or use --placeholder-role for a stub ARN in generated SQL."
                )

    catalog_name_rest, catalog_namespace, catalog_mode = resolve_rest_catalog_params(
        account=account,
        glue_database=glue_db,
        root=root,
        rest_catalog_override=rest_catalog_name,
        use_data_catalog=use_data_catalog,
        cli_s3tables_bucket=s3tables_bucket,
        placeholder_role=placeholder_role,
    )
    sql_01 = ""
    sql_02 = ""
    if write_catalog:
        sql_01 = render_catalog_integration_sql(
            integration_name=integration_name.strip(),
            catalog_namespace=catalog_namespace,
            catalog_name_rest=catalog_name_rest,
            catalog_mode=catalog_mode,
            region=region,
            sigv4_role_arn=role_arn,
        )
        sql_02 = render_cld_verify_sql(
            integration_name=integration_name.strip(),
            linked_database=linked_database.strip(),
            remote_schema_lower=catalog_namespace.lower(),
            raw_table=BRONZE_RAW_EVENTS_TABLE,
        )

    sql_03 = ""
    if write_dt:
        vol = (external_volume or "").strip()
        if not vol:
            vol = "REPLACE_ME_ICEBERG_EXTERNAL_VOLUME"
            print(
                "warning: SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME / --external-volume not set; "
                f"using placeholder {vol!r}. Edit generated SQL or set env before running.",
                file=sys.stderr,
            )
        prefix = (dt_path_prefix or "").strip() or "balloon_lab"
        sql_03 = render_dt_pipelines_sql(
            linked_database=linked_database.strip(),
            remote_schema_lower=catalog_namespace.lower(),
            raw_table=BRONZE_RAW_EVENTS_TABLE,
            silver_database=silver_database.strip(),
            silver_schema=silver_schema.strip(),
            warehouse=warehouse.strip(),
            external_volume=vol,
            path_prefix=prefix,
        )

    if to_stdout:
        if write_catalog:
            click.echo("-- === 01_catalog_integration.generated.sql ===\n")
            click.echo(sql_01)
            click.echo("-- === 02_cld_verify.generated.sql ===\n")
            click.echo(sql_02)
        if write_dt:
            click.echo("-- === 03_dt_pipelines.generated.sql ===\n")
            click.echo(sql_03)
        return

    out = output_dir or (root / "snowflake" / "lab" / "generated")
    out.mkdir(parents=True, exist_ok=True)
    p1 = out / "01_catalog_integration.generated.sql"
    p2 = out / "02_cld_verify.generated.sql"
    p3 = out / "03_dt_pipelines.generated.sql"
    if write_catalog:
        p1.write_text(sql_01, encoding="utf-8")
        p2.write_text(sql_02, encoding="utf-8")
        print(f"wrote {p1}", file=sys.stderr)
        print(f"wrote {p2}", file=sys.stderr)
        print(
            "Run: snow sql --connection <conn> --filename "
            f"{p1.relative_to(root) if p1.is_relative_to(root) else p1}",
            file=sys.stderr,
        )
    if write_dt:
        p3.write_text(sql_03, encoding="utf-8")
        print(f"wrote {p3}", file=sys.stderr)
        print(
            "DT pipelines: snow sql --connection <conn> --filename "
            f"{p3.relative_to(root) if p3.is_relative_to(root) else p3}",
            file=sys.stderr,
        )


@cli.command("print-env-hints")
def print_env_hints_cmd() -> None:
    """Print repo defaults; SIGV4 ARN is optional in env if create-read-role wrote the .txt file."""
    rel_arn = SIGV4_ROLE_ARN_REL.as_posix()
    click.echo("# Snowflake CLD — defaults (nothing to export unless you override)")
    click.echo(f"#   SNOWFLAKE_CATALOG_INTEGRATION_NAME={DEFAULT_CATALOG_INTEGRATION_NAME!r}  # default")
    click.echo(
        f"#   SNOWFLAKE_LINKED_DATABASE_NAME={BRONZE_RAW_EVENTS_TABLE!r}  # default in generate-lab-sql"
    )
    click.echo("# SIGV4 / signer role (default: no env var — use create-read-role, then generate-lab-sql reads file):")
    click.echo("#   task snowflake:create-glue-catalog-read-role   # writes .aws-config/…arn.txt")
    click.echo("# Override signer role only if you use a different IAM role:")
    click.echo("#   SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN='arn:aws:iam::<account>:role/<role>'")
    click.echo(f"#   # or first non-comment line in {rel_arn}")
    click.echo(
        "# Default: AWS Glue Data Catalog (Snowflake Step 2) — CATALOG_NAME = account id from glue-database.json; "
        "CATALOG_NAMESPACE = Glue database name."
    )
    click.echo("# Optional S3 Tables catalog shape: SNOWFLAKE_GLUE_REST_USE_S3TABLES_CATALOG=1 or generate --glue-s3tables-catalog")
    click.echo(
        "#   BRONZE_S3TABLES_BUCKET_NAME=…   # or first line of .aws-config/bronze-s3tables-last-bucket-name.txt"
    )
    click.echo(f"#   S3TABLES_NAMESPACE={DEFAULT_S3TABLES_NAMESPACE!r}   # or SNOWFLAKE_S3TABLES_CATALOG_NAMESPACE")
    click.echo("# Optional full CATALOG_NAME override: SNOWFLAKE_GLUE_REST_CATALOG_NAME='…'")
    click.echo("# Optional (trial / multi-connection; see Snowflake CLI docs):")
    click.echo("#   SNOWFLAKE_DEFAULT_CONNECTION_NAME=…  SNOWFLAKE_ROLE=ACCOUNTADMIN  SNOWFLAKE_WAREHOUSE=COMPUTE_WH")
    click.echo("# Dynamic Iceberg Tables (task dt:generate-sql → 03_dt_pipelines.generated.sql):")
    click.echo(f"#   SNOWFLAKE_SILVER_DATABASE={DEFAULT_SILVER_DATABASE!r}  # default")
    click.echo(f"#   SNOWFLAKE_SILVER_SCHEMA={DEFAULT_SILVER_SCHEMA!r}  # default")
    click.echo("#   SNOWFLAKE_ICEBERG_EXTERNAL_VOLUME='your_ext_vol'  # required for real runs")
    click.echo("#   SNOWFLAKE_DT_PATH_PREFIX=balloon_lab  # optional BASE_LOCATION prefix for all DTs")
    click.echo(
        "# Tasks: task snowflake:create-glue-catalog-read-role | task snowflake:generate-lab-sql | "
        "task dt:generate-sql | task snowflake:describe-catalog-integration"
    )


if __name__ == "__main__":
    cli()
