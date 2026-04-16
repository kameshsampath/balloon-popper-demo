# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Deploy the Balloon Game Dashboard Streamlit-in-Snowflake app via Snow CLI.

Follows the same pattern as bronze_cli.py: loads .env, resolves resource names
from LAB_USERNAME + env vars, then delegates to ``snow streamlit deploy``.

Key insight: Snow CLI ``--env KEY=value`` only substitutes ``<% ctx.env.KEY %>``
templates in snowflake.yml (identifier, warehouse). It does NOT modify the
staged artifact content.  silver_config.py reads the staged snowflake.yml
``env:`` block at runtime (SiS warehouse containers have no OS env vars).
So this tool temporarily patches the ``env:`` block with the derived values
before deploying and restores the file afterwards.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import click

from tools.bronze_preload.bronze_aws import repo_root
from tools.snowflake_lab.defaults import (
    DEFAULT_SILVER_DATABASE,
    DEFAULT_SILVER_SCHEMA,
    DEFAULT_SNOWFLAKE_WAREHOUSE,
)

_DEFAULT_APPS_SCHEMA = "apps"
_DEFAULT_ROLE = "ACCOUNTADMIN"
_APP_BASE_NAME = "balloon_game_dashboard"
_SIS_PROJECT_REL = "snowflake/sis"
_YML_FILE = "snowflake.yml"


def _load_repo_dotenv() -> None:
    """Load ``<repo>/.env`` (override=False) so uv run sees the same vars as direnv."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    path = repo_root() / ".env"
    if not path.is_file():
        return
    try:
        load_dotenv(path, override=False)
    except OSError:
        return


def apply_overrides(**env: str | None) -> None:
    """Copy non-empty Click option values into ``os.environ`` (after envvar resolution)."""
    for key, val in env.items():
        if val is not None and val != "":
            os.environ[key] = val


def _derive_resource_names(lab_username: str | None) -> dict[str, str]:
    """Resolve all SiS deployment resource names from env + lab_username.

    Resolution order for silver database:
    1. Explicit ``SNOWFLAKE_SILVER_DATABASE`` env var (set by user in .env or CLI flag)
    2. ``<lab_username>_balloon_silver`` when LAB_USERNAME is set
    3. ``balloon_silver`` (default)
    """
    user = (lab_username or os.environ.get("LAB_USERNAME") or "").strip()

    silver_db = (os.environ.get("SNOWFLAKE_SILVER_DATABASE") or "").strip()
    if not silver_db:
        silver_db = f"{user}_{DEFAULT_SILVER_DATABASE}" if user else DEFAULT_SILVER_DATABASE

    silver_schema = (os.environ.get("SNOWFLAKE_SILVER_SCHEMA") or DEFAULT_SILVER_SCHEMA).strip()
    warehouse = (os.environ.get("SNOWFLAKE_WAREHOUSE") or DEFAULT_SNOWFLAKE_WAREHOUSE).strip()
    apps_schema = (os.environ.get("SNOWFLAKE_APPS_SCHEMA") or _DEFAULT_APPS_SCHEMA).strip()
    role = (os.environ.get("SNOWFLAKE_ROLE") or _DEFAULT_ROLE).strip()

    prefix = f"{user}_" if user else ""
    app_name = f"{prefix}{_APP_BASE_NAME}"

    return {
        "lab_username": user,
        "prefix": prefix,
        "app_name": app_name,
        "silver_db": silver_db,
        "silver_schema": silver_schema,
        "warehouse": warehouse,
        "apps_schema": apps_schema,
        "role": role,
    }


@contextmanager
def _patched_snowflake_yml(yml_path: Path, env_patches: dict[str, str]) -> Iterator[None]:
    """Temporarily bake *env_patches* into the ``env:`` block of snowflake.yml.

    Restores the original content in all cases (including exceptions / SystemExit).
    Only scalar values on the matching key lines are replaced; YAML structure is preserved.
    """
    original = yml_path.read_text(encoding="utf-8")
    patched = original
    for key, value in env_patches.items():
        patched = re.sub(
            rf"^(\s+{re.escape(key)}:\s*).*$",
            rf"\g<1>{value}",
            patched,
            flags=re.MULTILINE,
        )
    try:
        yml_path.write_text(patched, encoding="utf-8")
        yield
    finally:
        yml_path.write_text(original, encoding="utf-8")


def _ensure_schema_and_stage(names: dict[str, str]) -> None:
    """Create the apps schema and dashboard stage if they don't exist.

    Runs two ``CREATE … IF NOT EXISTS`` statements via ``snow sql`` before
    deploying so a fresh lab environment doesn't fail with
    "Schema '…APPS' does not exist or not authorized."
    """
    db = names["silver_db"]
    schema = names["apps_schema"]
    role = names["role"]
    stage = "dashboard_src"

    sql = (
        f"CREATE SCHEMA IF NOT EXISTS {db}.{schema}; "
        f"CREATE STAGE IF NOT EXISTS {db}.{schema}.{stage};"
    )
    cmd = ["snow", "sql", "-q", sql, "--role", role]
    click.echo(f"Ensuring {db}.{schema} and stage {stage} exist ...")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _print_config(names: dict[str, str], project_dir: Path) -> None:
    click.echo("Resolved SiS deployment config:")
    click.echo(f"  lab_username    {names['lab_username'] or '(none)'}")
    click.echo(f"  app_name        {names['app_name']}")
    click.echo(f"  silver_database {names['silver_db']}")
    click.echo(f"  silver_schema   {names['silver_schema']}")
    click.echo(f"  warehouse       {names['warehouse']}")
    click.echo(f"  apps_schema     {names['apps_schema']}")
    click.echo(f"  role            {names['role']}")
    click.echo(f"  project_dir     {project_dir}")


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """Deploy and inspect the Balloon Game Dashboard Streamlit-in-Snowflake app."""
    _load_repo_dotenv()


# ---------------------------------------------------------------------------
# show-config
# ---------------------------------------------------------------------------

@cli.command("show-config")
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop participant id; derives app name prefix and silver database.",
)
@click.option(
    "--silver-database",
    envvar="SNOWFLAKE_SILVER_DATABASE",
    show_envvar=True,
    help="Silver database (default balloon_silver or <lab>_balloon_silver).",
)
@click.option(
    "--silver-schema",
    envvar="SNOWFLAKE_SILVER_SCHEMA",
    show_envvar=True,
    help="Silver schema (default silver).",
)
@click.option(
    "--warehouse",
    envvar="SNOWFLAKE_WAREHOUSE",
    show_envvar=True,
    help="Query warehouse (default COMPUTE_WH).",
)
@click.option(
    "--apps-schema",
    envvar="SNOWFLAKE_APPS_SCHEMA",
    show_envvar=True,
    help="Schema where the Streamlit object lives (default apps).",
)
@click.option(
    "--role",
    envvar="SNOWFLAKE_ROLE",
    show_envvar=True,
    help="Snowflake role for deployment (default ACCOUNTADMIN).",
)
def show_config_cmd(
    lab_username: str | None,
    silver_database: str | None,
    silver_schema: str | None,
    warehouse: str | None,
    apps_schema: str | None,
    role: str | None,
) -> None:
    """Print resolved deployment config without running snow."""
    apply_overrides(
        LAB_USERNAME=lab_username,
        SNOWFLAKE_SILVER_DATABASE=silver_database,
        SNOWFLAKE_SILVER_SCHEMA=silver_schema,
        SNOWFLAKE_WAREHOUSE=warehouse,
        SNOWFLAKE_APPS_SCHEMA=apps_schema,
        SNOWFLAKE_ROLE=role,
    )
    names = _derive_resource_names(lab_username)
    project_dir = repo_root() / _SIS_PROJECT_REL
    _print_config(names, project_dir)


# ---------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------

@cli.command(
    "deploy",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop participant id; derives app name prefix and silver database.",
)
@click.option(
    "--silver-database",
    envvar="SNOWFLAKE_SILVER_DATABASE",
    show_envvar=True,
    help="Silver database (default balloon_silver or <lab>_balloon_silver).",
)
@click.option(
    "--silver-schema",
    envvar="SNOWFLAKE_SILVER_SCHEMA",
    show_envvar=True,
    help="Silver schema (default silver).",
)
@click.option(
    "--warehouse",
    envvar="SNOWFLAKE_WAREHOUSE",
    show_envvar=True,
    help="Query warehouse (default COMPUTE_WH).",
)
@click.option(
    "--apps-schema",
    envvar="SNOWFLAKE_APPS_SCHEMA",
    show_envvar=True,
    help="Schema where the Streamlit object lives (default apps).",
)
@click.option(
    "--role",
    envvar="SNOWFLAKE_ROLE",
    show_envvar=True,
    help="Snowflake role for deployment (default ACCOUNTADMIN).",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Open the app in the browser after a successful deploy.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the resolved config and snow command without running anything.",
)
@click.pass_context
def deploy_cmd(
    ctx: click.Context,
    lab_username: str | None,
    silver_database: str | None,
    silver_schema: str | None,
    warehouse: str | None,
    apps_schema: str | None,
    role: str | None,
    open_browser: bool,
    dry_run: bool,
) -> None:
    """Deploy the Balloon Game Dashboard SiS app via snow streamlit deploy.

    Any unrecognised flags (e.g. ``--connection myconn``) are forwarded directly
    to ``snow streamlit deploy``.

    \b
    Examples:
      uv run sis-deploy deploy
      uv run sis-deploy deploy --dry-run
      uv run sis-deploy deploy --open
      uv run sis-deploy deploy --connection myconn
    """
    apply_overrides(
        LAB_USERNAME=lab_username,
        SNOWFLAKE_SILVER_DATABASE=silver_database,
        SNOWFLAKE_SILVER_SCHEMA=silver_schema,
        SNOWFLAKE_WAREHOUSE=warehouse,
        SNOWFLAKE_APPS_SCHEMA=apps_schema,
        SNOWFLAKE_ROLE=role,
    )
    names = _derive_resource_names(lab_username)
    root = repo_root()
    project_dir = root / _SIS_PROJECT_REL
    yml_path = project_dir / _YML_FILE

    # Extra args forwarded verbatim to snow (e.g. --connection, --account, etc.)
    extra_args: list[str] = list(ctx.args)

    cmd: list[str] = [
        "snow", "streamlit", "deploy",
        _APP_BASE_NAME,          # entity key in snowflake.yml; LAB_USERNAME_PREFIX template sets the deployed name
        "--project", str(project_dir),
        "--replace",
        "--role", names["role"],
        # Template substitution in snowflake.yml identifier / query_warehouse fields
        "--env", f"LAB_USERNAME_PREFIX={names['prefix']}",
        "--env", f"SNOWFLAKE_SILVER_DATABASE={names['silver_db']}",
        "--env", f"SNOWFLAKE_WAREHOUSE={names['warehouse']}",
        "--env", f"SNOWFLAKE_APPS_SCHEMA={names['apps_schema']}",
    ]
    if open_browser:
        cmd.append("--open")
    cmd.extend(extra_args)

    _print_config(names, project_dir)
    click.echo("")

    if dry_run:
        click.echo("[dry-run] Would run:")
        click.echo("  " + " ".join(cmd))
        return

    if not yml_path.is_file():
        click.echo(f"error: {yml_path} not found", err=True)
        raise SystemExit(1)

    # Ensure the apps schema and stage exist before deploying.
    _ensure_schema_and_stage(names)

    # Bake derived values into the env: block of snowflake.yml before staging.
    # Snow CLI stages the file as-is; silver_config.py reads the env: block at
    # runtime (SiS warehouse containers have no OS env vars injected).
    env_patches = {
        "SNOWFLAKE_SILVER_DATABASE": names["silver_db"],
        "SNOWFLAKE_SILVER_SCHEMA": names["silver_schema"],
        "SNOWFLAKE_WAREHOUSE": names["warehouse"],
    }
    click.echo(f"Deploying {names['app_name']} ...")
    with _patched_snowflake_yml(yml_path, env_patches):
        result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    cli()
