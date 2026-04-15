# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Lake Formation setup for bronze warehouse + Glue DB (Snowflake vended-credentials path)."""
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
    derive_bronze_resource_names,
    ensure_aws_config_dir,
    envsubst,
    glue_database_json_path,
    repo_root,
    require_aws_profile,
    resolve_aws_account_id,
    resolve_region,
    sanitize_lab_slug_bucket,
)

_ROLE_NAME_RE = re.compile(r"^[\w+=,.@-]{1,64}$")
_LAB_TAG_PROJECT = ("project", "balloon-popper-demo")
_LAB_TAG_PURPOSE = ("purpose", "lake-formation-bronze-data-access")


def _read_first_line(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                return line
    except OSError:
        return ""
    return ""


def _account_id_from_glue_or_sts(root: Path, region: str) -> str:
    gpath = root / ".aws-config" / "glue-database.json"
    if gpath.is_file():
        try:
            data = json.loads(gpath.read_text(encoding="utf-8"))
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


def default_lf_bronze_data_access_role_name() -> str:
    explicit = (os.environ.get("LAKE_FORMATION_BRONZE_DATA_ACCESS_ROLE_NAME") or "").strip()
    if explicit:
        return explicit
    lab = (os.environ.get("LAB_USERNAME") or "").strip()
    if lab:
        return f"{sanitize_lab_slug_bucket(lab)}-lf-data-access"
    return "lf-bronze-data-access"


def _resolve_sigv4_role_arn(root: Path) -> str:
    env_arn = (os.environ.get("SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN") or "").strip()
    if env_arn:
        return env_arn
    return _read_first_line(root / ".aws-config" / "snowflake-glue-catalog-iam-role-arn.txt")


def _load_context(root: Path) -> dict[str, str]:
    gpath = glue_database_json_path(root)
    if not gpath.is_file():
        raise click.ClickException(
            f"Missing {gpath}. Run `task bronze:glue-setup` before lakeformation-setup."
        )
    apply_bronze_from_aws_config(root)
    derive_bronze_resource_names()
    region = resolve_region()
    glue_db = (os.environ.get("GLUE_DATABASE") or "").strip()
    bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    if not glue_db:
        raise click.ClickException(
            "GLUE_DATABASE is unset. Run bronze glue-setup or set GLUE_DATABASE."
        )
    if not bucket:
        raise click.ClickException(
            "BRONZE_BUCKET_NAME is unset. Required for S3 registration and LF data-access policy."
        )
    account = _account_id_from_glue_or_sts(root, region)
    return {
        "AWS_REGION": region,
        "AWS_ACCOUNT_ID": account,
        "GLUE_DATABASE": glue_db,
        "BRONZE_BUCKET_NAME": bucket,
    }


def _iam_policy_doc(root: Path, ctx: dict[str, str]) -> str:
    tpl = root / "lab/aws" / "lake-formation-bronze-warehouse-data-access-policy.json"
    if not tpl.is_file():
        raise click.ClickException(f"Missing {tpl}")
    text = envsubst(tpl.read_text(encoding="utf-8"), {**os.environ, **ctx})
    json.loads(text)  # validate
    return text


def _iam_trust_doc(root: Path) -> str:
    tpl = root / "lab/aws" / "lake-formation-bronze-warehouse-data-access-trust.json"
    if not tpl.is_file():
        raise click.ClickException(f"Missing {tpl}")
    text = tpl.read_text(encoding="utf-8").strip()
    json.loads(text)
    return text


def _safe_grant(lf, *, principal: str, resource: dict, permissions: list[str]) -> None:
    try:
        lf.grant_permissions(
            Principal={"DataLakePrincipalIdentifier": principal},
            Resource=resource,
            Permissions=permissions,
        )
    except ClientError as e:
        msg = str(e)
        if "already" in msg.lower() or "AlreadyGranted" in msg:
            print(f"info: grant already present (skip): {permissions}", file=sys.stderr)
            return
        raise


def run_lakeformation_setup(*, root: Path | None, dry_run: bool) -> None:
    """Create LF data-access role, register S3, update Glue DB, grant LF to SIGV4 (+ optional admin)."""
    root = root or repo_root()
    ctx = _load_context(root)
    region = ctx["AWS_REGION"]
    account = ctx["AWS_ACCOUNT_ID"]
    glue_db = ctx["GLUE_DATABASE"]
    bucket = ctx["BRONZE_BUCKET_NAME"]
    lf_role_name = default_lf_bronze_data_access_role_name()
    if not _ROLE_NAME_RE.match(lf_role_name):
        raise click.ClickException(
            f"Invalid LAKE_FORMATION_BRONZE_DATA_ACCESS_ROLE_NAME / derived name {lf_role_name!r}"
        )
    lf_role_arn = f"arn:aws:iam::{account}:role/{lf_role_name}"
    sigv4_arn = _resolve_sigv4_role_arn(root)
    if not sigv4_arn:
        raise click.ClickException(
            "Missing Snowflake SIGV4 role ARN. Run `task snowflake:create-glue-catalog-read-role` "
            "or set SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN / .aws-config/snowflake-glue-catalog-iam-role-arn.txt"
        )
    sigv4_arn_n = sigv4_arn.rstrip("/")
    lf_role_arn_n = lf_role_arn.rstrip("/")
    if sigv4_arn_n == lf_role_arn_n:
        raise click.ClickException(
            "SIGV4 catalog role ARN and Lake Formation data-access role ARN must not be the same IAM role. "
            "Use a dedicated LF data-access role for register-resource (see lab/bronze-landing-zone.md)."
        )
    policy_doc = _iam_policy_doc(root, ctx)
    trust_doc = _iam_trust_doc(root)
    s3_resource_arn = f"arn:aws:s3:::{bucket}"
    admin_arn = (os.environ.get("LAKE_FORMATION_ADMIN_ESCAPE_PRINCIPAL_ARN") or "").strip()

    require_aws_profile()
    prof = os.environ["AWS_PROFILE"].strip()
    session = boto3.Session(profile_name=prof, region_name=region)
    iam = session.client("iam")
    lf = session.client("lakeformation")
    glue = session.client("glue")

    click.echo("")
    click.echo("Lake Formation — bronze warehouse (vended-credentials prep)")
    click.echo(f"  Region           {region}")
    click.echo(f"  Glue database    {glue_db}")
    click.echo(f"  S3 bucket        {bucket}")
    click.echo(f"  LF data role     {lf_role_arn}")
    click.echo(f"  SIGV4 principal  {sigv4_arn}")
    if admin_arn:
        click.echo(f"  Admin escape     {admin_arn}")
    click.echo("")

    if dry_run:
        click.echo("[dry-run] No AWS writes. Planned steps:")
        click.echo("  1) IAM create/update role + inline policy on LF data-access role")
        click.echo("  2) lakeformation.register-resource (LF-only: no hybrid, no federation)")
        click.echo("  3) glue.update-database (CreateTableDefaultPermissions=[])")
        click.echo("  4) lakeformation.grant-permissions → SIGV4 (database + tables)")
        if admin_arn:
            click.echo("  5) lakeformation.grant-permissions → admin (ALL)")
        return

    # 1) IAM LF data-access role
    try:
        iam.create_role(
            Path="/",
            RoleName=lf_role_name,
            AssumeRolePolicyDocument=trust_doc,
            Description="Lake Formation S3 data access for bronze Iceberg warehouse (lab)",
            Tags=[
                {"Key": _LAB_TAG_PROJECT[0], "Value": _LAB_TAG_PROJECT[1]},
                {"Key": _LAB_TAG_PURPOSE[0], "Value": _LAB_TAG_PURPOSE[1]},
            ],
        )
        print(f"info: created IAM role {lf_role_name!r}", file=sys.stderr)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "EntityAlreadyExists":
            print(f"info: IAM role {lf_role_name!r} exists; updating policies.", file=sys.stderr)
        else:
            raise
    iam.put_role_policy(
        RoleName=lf_role_name,
        PolicyName="LfBronzeWarehouseS3Read",
        PolicyDocument=policy_doc,
    )

    # 2) Register S3
    try:
        lf.register_resource(
            ResourceArn=s3_resource_arn,
            RoleArn=lf_role_arn,
            HybridAccessEnabled=False,
            WithFederation=False,
        )
    except ClientError as e:
        err = e.response.get("Error", {})
        code, msg = err.get("Code", ""), err.get("Message", "")
        if code == "InvalidInputException" and "already" in msg.lower():
            print(f"info: S3 location likely already registered: {msg}", file=sys.stderr)
        else:
            raise

    # 3) Glue database — merge from current
    gdb = glue.get_database(Name=glue_db).get("Database") or {}
    db_in: dict[str, object] = {"Name": glue_db, "CreateTableDefaultPermissions": []}
    for key in ("Description", "LocationUri", "Parameters", "TargetDatabase", "FederatedDatabase"):
        if key in gdb and gdb[key] is not None:
            db_in[key] = gdb[key]
    glue.update_database(Name=glue_db, DatabaseInput=db_in)

    # 4) Grants to SIGV4
    _safe_grant(
        lf,
        principal=sigv4_arn,
        resource={"Database": {"Name": glue_db}},
        permissions=["DESCRIBE"],
    )
    _safe_grant(
        lf,
        principal=sigv4_arn,
        resource={"Table": {"DatabaseName": glue_db, "TableWildcard": {}}},
        permissions=["SELECT", "DESCRIBE"],
    )

    if admin_arn:
        _safe_grant(
            lf,
            principal=admin_arn,
            resource={"Database": {"Name": glue_db}},
            permissions=["ALL"],
        )
        _safe_grant(
            lf,
            principal=admin_arn,
            resource={"Table": {"DatabaseName": glue_db, "TableWildcard": {}}},
            permissions=["ALL"],
        )

    out = ensure_aws_config_dir(root) / "lake-formation-bronze-data-access-role-arn.txt"
    out.write_text(lf_role_arn + "\n", encoding="utf-8")
    print(f"wrote {out}", file=sys.stderr)
    click.echo("")
    click.echo(f"OK: Lake Formation prep complete (LF data-access role={lf_role_arn}).")
