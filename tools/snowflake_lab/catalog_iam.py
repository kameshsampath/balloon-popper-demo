# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Create / update IAM role for Snowflake Glue Iceberg REST (``SIGV4_IAM_ROLE``).

Inline permissions follow Snowflake **Step 1** (Glue catalog read + Lake Formation credential vending)
in https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest-glue
using ``lab/aws/snowflake-glue-catalog-read-policy.json``: **Glue** reads on ``GLUE_DATABASE`` (including
``catalog`` / ``catalog/*`` ARNs) plus **Lake Formation** ``GetDataAccess`` and temporary Glue credential
APIs. **S3 object access** for Iceberg files under the warehouse bucket is expected via **Lake Formation**
(``bronze-cli lakeformation-setup`` + a **separate** LF data-access IAM role), not ``s3:GetObject`` on
this SIGV4 role—see ``lab/bronze-landing-zone.md`` (Lake Formation section).

Trust is a two-step lab pattern:

1. **Bootstrap** (``create-read-role``): ``Principal`` = ``arn:aws:iam::<account-id>:root`` so entities in
   the same account (including Snowflake's integration IAM user) can assume the role while you stand up
   ``CREATE CATALOG INTEGRATION``. This is **broader than production** — tighten immediately with step 2.

2. **Snowflake-only trust** (``apply-trust-from-rendered``): after ``task snowflake:render-glue-catalog-trust``,
   replace the assume-role policy with ``GLUE_AWS_IAM_USER_ARN`` + ``sts:ExternalId`` per Snowflake docs.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import boto3
import click
from botocore.exceptions import ClientError

from tools.bronze_preload.bronze_aws import (
    apply_bronze_from_aws_config,
    default_snowflake_glue_catalog_iam_role_name,
    derive_bronze_resource_names,
    ensure_aws_config_dir,
    envsubst,
    glue_database_json_path,
    repo_root,
    require_aws_profile,
    resolve_aws_account_id,
    resolve_region,
)

_ROLE_NAME_RE = re.compile(r"^[\w+=,.@-]{1,64}$")

# Must match Tags on create_role (cleanup deletes only when both match).
_LAB_IAM_ROLE_TAG_PROJECT = ("project", "balloon-popper-demo")
_LAB_IAM_ROLE_TAG_PURPOSE = ("purpose", "snowflake-glue-catalog-read")


def effective_catalog_read_role_name(role_opt: str | None) -> str:
    """Explicit ``--role-name`` / env wins; else derive from ``LAB_USERNAME`` (see bronze_aws)."""
    v = (role_opt or "").strip()
    if v:
        return v
    return default_snowflake_glue_catalog_iam_role_name()


def _parse_role_name_from_arn(arn: str) -> str:
    arn = arn.strip()
    if ":role/" not in arn:
        raise click.ClickException(f"Expected an IAM role ARN, got: {arn!r}")
    rest = arn.split(":role/", 1)[1]
    if not rest:
        raise click.ClickException(f"Could not parse role name from ARN: {arn!r}")
    return rest


def _read_first_config_line(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def _bootstrap_trust_document(account_id: str) -> str:
    doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LabBootstrapSameAccountTrust",
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    return json.dumps(doc)


def _account_id_from_glue_file_or_sts(root: Path, region: str) -> str:
    glue_path = root / ".aws-config" / "glue-database.json"
    if glue_path.is_file():
        try:
            data = json.loads(glue_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        if isinstance(data, dict):
            db = data.get("Database") or {}
            cid = db.get("CatalogId")
            if isinstance(cid, str) and cid.strip().isdigit() and len(cid.strip()) == 12:
                return cid.strip()
    require_aws_profile()
    prof = (os.environ.get("AWS_PROFILE") or "").strip()
    return resolve_aws_account_id(prof, region)


def _load_lab_iam_context(root: Path) -> dict[str, str]:
    gpath = glue_database_json_path(root)
    if not gpath.is_file():
        raise click.ClickException(
            f"Missing {gpath}. Run `task bronze:glue-setup` (or `uv run bronze-cli glue-setup`) "
            "before create-read-role."
        )
    apply_bronze_from_aws_config(root)
    derive_bronze_resource_names()
    region = resolve_region()
    glue_db = (os.environ.get("GLUE_DATABASE") or "").strip()
    if not glue_db:
        raise click.ClickException(
            "GLUE_DATABASE is unset. Run bronze glue-setup or set GLUE_DATABASE "
            "(repo overlays from .aws-config/glue-database.json when present)."
        )
    account = _account_id_from_glue_file_or_sts(root, region)
    return {
        "AWS_REGION": region,
        "AWS_ACCOUNT_ID": account,
        "GLUE_DATABASE": glue_db,
    }


def _iam_client():
    require_aws_profile()
    r = resolve_region()
    prof = (os.environ.get("AWS_PROFILE") or "").strip()
    return boto3.Session(profile_name=prof, region_name=r).client("iam")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """IAM helpers for Snowflake Glue REST catalog (SIGV4 role)."""


@cli.command("create-read-role")
@click.option(
    "--repo-root",
    "repo_root_arg",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
)
@click.option(
    "--role-name",
    "role_name_opt",
    envvar="SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME",
    default=None,
    help="IAM role name (default: <glue_slug>_snowflake_glue_catalog_read with LAB_USERNAME, else "
    "snowflake_glue_catalog_read).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print trust + permissions JSON only; do not call AWS IAM.",
)
@click.option(
    "--no-write-arn-file",
    is_flag=True,
    help="Do not write .aws-config/snowflake-glue-catalog-iam-role-arn.txt.",
)
def create_read_role(
    repo_root_arg: Path | None,
    role_name_opt: str | None,
    dry_run: bool,
    no_write_arn_file: bool,
) -> None:
    """Create IAM role + inline read policy; bootstrap same-account trust; write role ARN for generate-lab-sql."""
    root = repo_root_arg or repo_root()
    ctx = _load_lab_iam_context(root)
    rn = effective_catalog_read_role_name(role_name_opt)
    print(f"info: IAM role name={rn!r} (override with SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME)", file=sys.stderr)
    tpl = root / "lab/aws/snowflake-glue-catalog-read-policy.json"
    if not tpl.is_file():
        raise click.ClickException(f"Missing policy template {tpl}")
    merged = {**os.environ, **ctx}
    policy_text = envsubst(tpl.read_text(encoding="utf-8"), merged)
    try:
        json.loads(policy_text)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Rendered policy is not valid JSON: {e}") from e

    if not _ROLE_NAME_RE.match(rn):
        raise click.ClickException(
            f"Invalid --role-name {rn!r} (IAM names: 1–64 chars, alnum and _+=,.@-)."
        )

    trust_doc = _bootstrap_trust_document(ctx["AWS_ACCOUNT_ID"])
    arn = f"arn:aws:iam::{ctx['AWS_ACCOUNT_ID']}:role/{rn}"

    if dry_run:
        click.echo("--- AssumeRolePolicyDocument (bootstrap; tighten with apply-trust-from-rendered) ---")
        click.echo(trust_doc)
        click.echo("--- Inline policy SnowflakeGlueCatalogRead ---")
        click.echo(policy_text)
        return

    iam = _iam_client()
    created = False
    try:
        iam.create_role(
            Path="/",
            RoleName=rn,
            AssumeRolePolicyDocument=trust_doc,
            Description=(
                "Snowflake Glue Iceberg REST catalog read (lab bootstrap trust; "
                "run apply-trust-from-rendered after render-glue-catalog-trust)"
            ),
            Tags=[
                {"Key": "project", "Value": "balloon-popper-demo"},
                {"Key": "purpose", "Value": "snowflake-glue-catalog-read"},
            ],
        )
        created = True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "EntityAlreadyExists":
            print(
                f"info: IAM role {rn!r} already exists; updating inline policy only.",
                file=sys.stderr,
            )
        else:
            raise

    iam.put_role_policy(RoleName=rn, PolicyName="SnowflakeGlueCatalogRead", PolicyDocument=policy_text)
    if created:
        print(f"created IAM role {arn}", file=sys.stderr)
    else:
        print(f"updated inline policy on IAM role {arn}", file=sys.stderr)

    if not no_write_arn_file:
        cfg = ensure_aws_config_dir(root)
        p = cfg / "snowflake-glue-catalog-iam-role-arn.txt"
        p.write_text(arn + "\n", encoding="utf-8")
        print(f"wrote {p}", file=sys.stderr)

    click.echo(arn)
    print(
        "\nNext:\n"
        "  1) task bronze:lakeformation-setup-dry-run   # after bronze:load; LF + S3 (vended path)\n"
        "  2) task bronze:lakeformation-setup\n"
        "  3) task snowflake:generate-lab-sql   # uses ARN file if SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN unset\n"
        "  4) snow sql … snowflake/lab/generated/01_catalog_integration.generated.sql\n"
        "  5) task snowflake:describe-catalog-integration\n"
        "  6) task snowflake:render-glue-catalog-trust\n"
        f"  7) uv run snowflake-catalog-iam apply-trust-from-rendered --role-name {rn}\n"
        "Bootstrap trust is same-account root (lab convenience). Step 7 locks trust to Snowflake user + external ID.",
        file=sys.stderr,
    )


@cli.command("apply-trust-from-rendered")
@click.option(
    "--repo-root",
    "repo_root_arg",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
)
@click.option("--role-name", "role_name_opt", envvar="SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME", default=None)
@click.option(
    "--role-arn",
    envvar="SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN",
    default="",
    help="Parse IAM role name from this ARN if --role-name is unset.",
)
@click.option(
    "--trust-document",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Trust JSON (default: .aws-config/snowflake-glue-catalog-trust-policy.rendered.json).",
)
@click.option("--dry-run", is_flag=True)
def apply_trust_from_rendered(
    repo_root_arg: Path | None,
    role_name_opt: str | None,
    role_arn: str,
    trust_document: Path | None,
    dry_run: bool,
) -> None:
    """Set AssumeRolePolicyDocument from render-glue-catalog-trust (Snowflake user + external ID)."""
    root = repo_root_arg or repo_root()
    apply_bronze_from_aws_config(root)
    derive_bronze_resource_names()
    path = trust_document or (root / ".aws-config/snowflake-glue-catalog-trust-policy.rendered.json")
    if not path.is_file():
        raise click.ClickException(
            f"Missing {path}. Run: task snowflake:render-glue-catalog-trust"
        )
    text = path.read_text(encoding="utf-8")
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Trust file is not valid JSON: {e}") from e

    rn = (role_name_opt or "").strip()
    if not rn and (role_arn or "").strip():
        rn = _parse_role_name_from_arn(role_arn)
    if not rn:
        rn = effective_catalog_read_role_name(None)

    if dry_run:
        print(f"Would set AssumeRolePolicyDocument for role {rn!r} from {path}", file=sys.stderr)
        click.echo(text)
        return

    _iam_client().update_assume_role_policy(RoleName=rn, PolicyDocument=text)
    print(f"updated AssumeRolePolicyDocument for role {rn!r}", file=sys.stderr)


def delete_tagged_snowflake_glue_catalog_read_role(
    iam,
    role_name: str,
    *,
    root: Path,
    dry_run: bool,
) -> bool:
    """Remove lab-created SIGV4 read role if it exists and has expected tags; remove matching ARN file.

    Returns True if the role was found and deleted (or would be in *dry_run*).
    """
    try:
        g = iam.get_role(RoleName=role_name)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchEntity":
            return False
        raise
    tags = {t["Key"]: t["Value"] for t in g.get("Role", {}).get("Tags", [])}
    if tags.get(_LAB_IAM_ROLE_TAG_PROJECT[0]) != _LAB_IAM_ROLE_TAG_PROJECT[1]:
        print(
            f"  skip: IAM role {role_name!r} missing tag {_LAB_IAM_ROLE_TAG_PROJECT[0]!r}",
            file=sys.stderr,
        )
        return False
    if tags.get(_LAB_IAM_ROLE_TAG_PURPOSE[0]) != _LAB_IAM_ROLE_TAG_PURPOSE[1]:
        print(
            f"  skip: IAM role {role_name!r} missing tag {_LAB_IAM_ROLE_TAG_PURPOSE[0]!r}",
            file=sys.stderr,
        )
        return False
    if dry_run:
        print(
            f"  [dry-run] would delete IAM role {role_name!r} (lab Snowflake Glue catalog read)",
            file=sys.stderr,
        )
        return True
    inline = iam.list_role_policies(RoleName=role_name)
    for pn in inline.get("PolicyNames", []):
        iam.delete_role_policy(RoleName=role_name, PolicyName=pn)
    attached = iam.list_attached_role_policies(RoleName=role_name)
    for ap in attached.get("AttachedPolicies", []):
        arn_pol = ap.get("PolicyArn")
        if isinstance(arn_pol, str) and arn_pol:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=arn_pol)
    iam.delete_role(RoleName=role_name)
    print(f"  deleted IAM role {role_name!r}", file=sys.stderr)
    arn_path = root / ".aws-config" / "snowflake-glue-catalog-iam-role-arn.txt"
    if arn_path.is_file():
        try:
            line = (arn_path.read_text(encoding="utf-8").splitlines() or [""])[0].strip()
        except OSError:
            line = ""
        if line.endswith(f":role/{role_name}") or line.endswith(f"/{role_name}"):
            arn_path.unlink(missing_ok=True)
            print(f"  removed {arn_path}", file=sys.stderr)
    return True


if __name__ == "__main__":
    cli()
