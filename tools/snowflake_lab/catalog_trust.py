#!/usr/bin/env python3
# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Render IAM **trust policy** for the Glue role used in Snowflake Glue Iceberg REST catalog integration.

After ``CREATE CATALOG INTEGRATION`` (``CATALOG_SOURCE = ICEBERG_REST``, ``CATALOG_API_TYPE = AWS_GLUE``), Snowflake
exposes trust material via ``DESCRIBE CATALOG INTEGRATION``: some accounts return ``API_AWS_IAM_USER_ARN`` and
``API_AWS_EXTERNAL_ID``; older docs show ``GLUE_AWS_IAM_USER_ARN`` / ``GLUE_AWS_EXTERNAL_ID`` (same use in IAM trust).
Attach the rendered JSON to the **same IAM role** you passed as ``SIGV4_IAM_ROLE``. See Snowflake
`Configure a catalog integration for AWS Glue Iceberg REST` (trust policy example).

This mirrors the automation style of **sfutils-extvolumes** (``snow sql`` + templated IAM JSON) but targets catalog
integration trust, not external volumes.

Env:
  SNOWFLAKE_CATALOG_INTEGRATION_NAME — optional; defaults to the repo lab name (``glue_rest_catalog_int``).
  SNOWFLAKE_DEFAULT_CONNECTION_NAME — optional; selects the named ``snow`` connection (see Snowflake CLI
  *Managing Snowflake connections*). ``SNOWFLAKE_ROLE`` and ``SNOWFLAKE_WAREHOUSE`` are also honored when
  passed through the environment for ``snow sql``.
Optional overrides (skip ``snow`` describe when both set):
  GLUE_AWS_IAM_USER_ARN / API_AWS_IAM_USER_ARN, GLUE_AWS_EXTERNAL_ID / API_AWS_EXTERNAL_ID
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import click

from tools.bronze_preload.bronze_aws import envsubst, repo_root
from tools.snowflake_lab.defaults import DEFAULT_CATALOG_INTEGRATION_NAME


def _mask_external_id(val: str) -> str:
    if len(val) <= 6:
        return "*" * len(val)
    return f"{val[:3]}{'*' * (len(val) - 6)}{val[-3:]}"


def run_snow_sql_json(query: str) -> object:
    """Run ``snow sql --format json``; return parsed JSON or raise."""
    cmd = ["snow", "sql", "--query", query, "--format", "json"]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        raise click.ClickException(
            f"snow sql failed (exit {cp.returncode}): {cp.stderr or cp.stdout or '(no output)'}"
        )
    raw = (cp.stdout or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON from snow sql: {e}") from e


def _canon_prop_key(key: str) -> str:
    """Normalize property names for comparisons (handles spaces / dots in metadata keys)."""
    return re.sub(r"[\s.\-]+", "_", str(key).strip()).upper()


def _pair_from_describe_row(row: dict[str, object]) -> tuple[str | None, str | None]:
    """Extract (property name, property value) from one ``snow sql --format json`` row."""
    k: str | None = None
    v: str | None = None
    for kk, vv in sorted(row.items(), key=lambda kv: str(kv[0]).lower()):
        lk = str(kk).lower()
        if lk in ("property", "name", "key", "property_name"):
            if k is None:
                k = str(vv).strip() if vv is not None else ""
        elif lk in ("property_value", "propertyvalue", "value", "val"):
            if v is None:
                v = "" if vv is None else str(vv).strip()
    return k, v


def _normalize_describe_rows(parsed: object) -> list[dict[str, object]]:
    """Normalize ``snow sql`` JSON into a list of row dicts."""
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [r for r in parsed if isinstance(r, dict)]
    if isinstance(parsed, dict):
        for key in ("result", "data", "rows", "statement_response"):
            v = parsed.get(key)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
        # single row object
        if "property" in parsed or "PROPERTY" in parsed:
            return [parsed]
    return []


def _looks_like_flat_catalog_describe_row(d: dict) -> bool:
    """True when ``snow sql`` JSON is one object whose keys are integration property names."""
    if not d:
        return False
    keyu = {str(k).upper() for k in d}
    if "PROPERTY" in keyu and "PROPERTY_VALUE" in keyu:
        return False
    markers = {
        "ENABLED",
        "CATALOG_SOURCE",
        "API_AWS_IAM_USER_ARN",
        "GLUE_AWS_IAM_USER_ARN",
        "REST_CONFIG",
        "REST_AUTHENTICATION",
    }
    return bool(keyu & markers)


def _props_from_flat_describe_dict(d: dict) -> dict[str, str]:
    """Upper-case keys and string values for a single-row property map."""
    out: dict[str, str] = {}
    for k, v in d.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, (dict, list)):
            continue
        out[k.upper()] = "" if v is None else str(v).strip()
    return out


def _merge_snow_describe_to_props(parsed: object, rows: list[dict[str, object]]) -> dict[str, str]:
    """Build property map from row-shaped or flat ``snow sql --format json`` output."""
    props: dict[str, str] = {}
    for row in rows:
        k, v = _pair_from_describe_row(row)
        if k:
            props[k.upper()] = v if v is not None else ""
    if props:
        return props
    for row in rows:
        if isinstance(row, dict) and _looks_like_flat_catalog_describe_row(row):
            return _props_from_flat_describe_dict(row)
    if isinstance(parsed, dict) and _looks_like_flat_catalog_describe_row(parsed):
        return _props_from_flat_describe_dict(parsed)
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        sole = parsed[0]
        if _looks_like_flat_catalog_describe_row(sole):
            return _props_from_flat_describe_dict(sole)
    return props


def describe_catalog_integration_properties(name: str) -> dict[str, str]:
    """Return upper-cased property names → values from ``DESC CATALOG INTEGRATION``."""
    ident = name.strip()
    if not ident:
        raise click.ClickException(
            "integration name is empty; set SNOWFLAKE_CATALOG_INTEGRATION_NAME or pass --integration"
        )
    # Double-quote if not simple identifier
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", ident):
        qident = '"' + ident.replace('"', '""') + '"'
    else:
        qident = ident
    q = f"DESC CATALOG INTEGRATION {qident}"
    parsed = run_snow_sql_json(q)
    rows = _normalize_describe_rows(parsed)
    props = _merge_snow_describe_to_props(parsed, rows)
    if props:
        return props
    # Some ``snow sql`` builds return a list of per-statement objects; merge any flat describe maps.
    if isinstance(parsed, list):
        merged: dict[str, str] = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            sub_rows = _normalize_describe_rows(item)
            merged.update(_merge_snow_describe_to_props(item, sub_rows))
        if merged:
            return merged
    return props


def _human_describe_key_order(props: dict[str, str]) -> list[str]:
    """Stable property order: catalog + trust (``API_AWS_*`` / ``GLUE_*``) + REST, then remaining keys."""
    if not props:
        return []
    canon_to_orig: dict[str, str] = {}
    for k in props:
        canon_to_orig[_canon_prop_key(k)] = k
    preferred = [
        "ENABLED",
        "CATALOG_SOURCE",
        "TABLE_FORMAT",
        "CATALOG_NAMESPACE",
        "API_AWS_IAM_USER_ARN",
        "API_AWS_EXTERNAL_ID",
        "GLUE_AWS_IAM_USER_ARN",
        "GLUE_AWS_EXTERNAL_ID",
        "GLUE_ICEBERG_REST_URI",
        "GLUE_DATABASE",
        "REST_CONFIG",
        "REST_AUTHENTICATION",
        "REFRESH_INTERVAL_SECONDS",
        "COMMENT",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for c in preferred:
        orig = canon_to_orig.get(c)
        if orig is not None and orig not in seen:
            out.append(orig)
            seen.add(orig)
    for orig in sorted(props.keys(), key=lambda k: _canon_prop_key(k)):
        if orig not in seen:
            out.append(orig)
            seen.add(orig)
    return out


def extract_glue_trust_fields(props: dict[str, str]) -> tuple[str, str]:
    """Principal ARN + external ID for SIGV4 IAM trust (from ``DESC CATALOG INTEGRATION``).

    Snowflake may return either ``GLUE_AWS_*`` (older docs) or ``API_AWS_IAM_USER_ARN`` /
    ``API_AWS_EXTERNAL_ID`` for ``ICEBERG_REST`` catalog integrations — same trust policy use.
    """
    arn = (
        (props.get("GLUE_AWS_IAM_USER_ARN") or "").strip()
        or (props.get("API_AWS_IAM_USER_ARN") or "").strip()
    )
    ext = (
        (props.get("GLUE_AWS_EXTERNAL_ID") or "").strip()
        or (props.get("API_AWS_EXTERNAL_ID") or "").strip()
    )
    if not arn or not ext:
        missing: list[str] = []
        if not arn:
            missing.append("GLUE_AWS_IAM_USER_ARN or API_AWS_IAM_USER_ARN")
        if not ext:
            missing.append("GLUE_AWS_EXTERNAL_ID or API_AWS_EXTERNAL_ID")
        raise click.ClickException(
            "DESC CATALOG INTEGRATION did not return "
            + ", ".join(missing)
            + ". Confirm CATALOG_SOURCE is ICEBERG_REST with AWS Glue (see Snowflake Iceberg REST + AWS_GLUE docs) "
            "and the integration name is correct."
        )
    return arn, ext


@click.group()
def cli() -> None:
    """Snowflake catalog integration → IAM trust policy helpers."""


@cli.command("describe-catalog-integration")
@click.option(
    "--integration",
    envvar="SNOWFLAKE_CATALOG_INTEGRATION_NAME",
    default=DEFAULT_CATALOG_INTEGRATION_NAME,
    show_default=True,
    help="Catalog integration name (override with SNOWFLAKE_CATALOG_INTEGRATION_NAME if you used another).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit full property map as JSON (includes non-trust fields).",
)
def describe_cmd(integration: str, as_json: bool) -> None:
    """Print catalog integration properties (trust ``API_AWS_*`` / ``GLUE_*``, REST, …) from ``DESC``."""
    props = describe_catalog_integration_properties(integration)
    if as_json:
        click.echo(json.dumps(props, indent=2))
        return
    keys = _human_describe_key_order(props)
    if not keys:
        click.echo(
            "DESC CATALOG INTEGRATION returned no parseable properties. "
            "Check ``snow`` auth and ``SNOWFLAKE_CATALOG_INTEGRATION_NAME``; try ``--json`` after a successful DESC.",
            err=True,
        )
        return
    for key in keys:
        val = props[key]
        ck = _canon_prop_key(key)
        if ck.endswith("_EXTERNAL_ID") and val:
            click.echo(f"{key}={_mask_external_id(val)}")
        else:
            click.echo(f"{key}={val}")


@cli.command("render-glue-catalog-trust")
@click.option(
    "--integration",
    envvar="SNOWFLAKE_CATALOG_INTEGRATION_NAME",
    default=DEFAULT_CATALOG_INTEGRATION_NAME,
    show_default=True,
    help="Catalog integration name; used to run DESC when GLUE_* env vars are unset.",
)
@click.option(
    "--iam-user-arn",
    "iam_user_arn",
    envvar=["GLUE_AWS_IAM_USER_ARN", "API_AWS_IAM_USER_ARN"],
    default="",
    help="Override Snowflake IAM user ARN (otherwise from DESC: API_AWS_* or GLUE_AWS_*).",
)
@click.option(
    "--external-id",
    "external_id",
    envvar=["GLUE_AWS_EXTERNAL_ID", "API_AWS_EXTERNAL_ID"],
    default="",
    help="Override external ID (otherwise from DESC: API_AWS_* or GLUE_AWS_*).",
)
@click.option(
    "--template",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Trust policy template (default: lab/aws/snowflake-glue-catalog-trust-policy.json).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print rendered JSON only; do not write .aws-config/.",
)
def render_glue_catalog_trust_cmd(
    integration: str,
    iam_user_arn: str,
    external_id: str,
    template: Path | None,
    dry_run: bool,
) -> None:
    """Render trust policy JSON for the SIGV4 IAM role (Snowflake Glue Iceberg REST)."""
    arn = (iam_user_arn or "").strip()
    ext = (external_id or "").strip()
    if not arn or not ext:
        integ = (
            (integration or os.environ.get("SNOWFLAKE_CATALOG_INTEGRATION_NAME") or "").strip()
            or DEFAULT_CATALOG_INTEGRATION_NAME
        )
        props = describe_catalog_integration_properties(integ)
        arn, ext = extract_glue_trust_fields(props)

    root = repo_root()
    tpl_path = template or (root / "lab/aws/snowflake-glue-catalog-trust-policy.json")
    text = tpl_path.read_text(encoding="utf-8")
    out_text = envsubst(
        text,
        {
            **os.environ,
            "GLUE_AWS_IAM_USER_ARN": arn,
            "GLUE_AWS_EXTERNAL_ID": ext,
        },
    )
    # Validate JSON
    try:
        json.loads(out_text)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Rendered output is not valid JSON: {e}") from e

    if dry_run:
        click.echo(out_text)
        return

    cfg = root / ".aws-config"
    cfg.mkdir(parents=True, exist_ok=True)
    out_path = cfg / "snowflake-glue-catalog-trust-policy.rendered.json"
    out_path.write_text(out_text + "\n", encoding="utf-8")
    click.echo(f"Wrote {out_path}")
    click.echo(
        "Attach this document as the **trust policy** on the IAM role you set in "
        "REST_AUTHENTICATION (SIGV4_IAM_ROLE). See Snowflake: "
        "https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue"
    )


if __name__ == "__main__":
    cli()
