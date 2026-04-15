# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Cross-platform bronze AWS setup (Glue, S3 Tables, IAM render). Replaces bash scripts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import boto3
import click
from botocore.exceptions import ClientError

from .bronze_aws import (
    apply_bronze_from_aws_config,
    apply_cleanup_context_from_aws_config,
    apply_s3tables_millis_suffix_if_enabled,
    remove_bronze_aws_config_artifacts,
    aws_json,
    default_snowflake_glue_catalog_iam_role_name,
    derive_bronze_resource_names,
    ensure_aws_config_dir,
    ensure_bronze_s3_arn_for_policy,
    ensure_bronze_warehouse_s3_bucket,
    envsubst,
    repo_root,
    require_aws_cli_s3tables,
    require_aws_profile,
    glue_database_json_path,
    resolve_bronze_warehouse,
    resolve_aws_account_id,
    resolve_region,
    resolve_s3tables_table_bucket_name,
    sanitize_lab_slug_bucket,
)
from .bronze_tables import BRONZE_GLUE_TABLES as TABLES
from .lakeformation_bronze import run_lakeformation_setup
from tools.snowflake_lab.catalog_iam import delete_tagged_snowflake_glue_catalog_read_role


def _read_text_strip(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").strip()


def _s3tables_cli_ok() -> bool:
    cp = subprocess.run(
        ["aws", "s3tables", "help"],
        capture_output=True,
        text=True,
        check=False,
    )
    return cp.returncode == 0


def _resolve_s3tables_table_bucket_arn(profile: str, region: str, tb_name: str) -> str:
    if not tb_name or not _s3tables_cli_ok():
        return ""
    data = aws_json(profile, region, ["s3tables", "list-table-buckets", "--no-paginate"])
    for b in data.get("tableBuckets") or []:
        if b.get("name") == tb_name:
            return (b.get("arn") or "").strip()
    return ""


def _echo_s3tables_dry_run_plan(
    *,
    profile: str,
    region: str,
    tb_name: str,
    ns: str,
    table_bucket_arn: str,
    tables: tuple[str, ...],
) -> None:
    """Human-oriented summary after a read-only list-table-buckets call."""
    click.echo("")
    click.echo("Dry run — S3 Tables setup")
    click.echo("(read-only: list-table-buckets only; no creates; nothing under .aws-config/)")
    click.echo("")
    click.echo("  Session")
    click.echo(f"    AWS profile     {profile}")
    click.echo(f"    Region          {region}")
    click.echo("")
    click.echo("  AWS call used for this preview")
    click.echo("    aws s3tables list-table-buckets --no-paginate")
    click.echo("")
    click.echo("  What a real run would target")
    if tb_name:
        click.echo(f"    Table bucket    {tb_name}")
        if table_bucket_arn:
            click.echo("    In this account  already present")
            click.echo(f"                      {table_bucket_arn}")
        else:
            click.echo("    In this account  not listed — would create a new table bucket with this name")
    else:
        click.echo("    Table bucket    (not set — cannot create until you name it)")
        click.echo("    Set either")
        click.echo("      LAB_USERNAME           workshop id; repo derives the bucket name, e.g.")
        example_lab = "workshop01"
        ex_bucket = f"{sanitize_lab_slug_bucket(example_lab)}-balloon-s3tables"
        click.echo(f"                         LAB_USERNAME={example_lab}")
        click.echo(f"                         → BRONZE_S3TABLES_BUCKET_NAME={ex_bucket}")
        click.echo("      BRONZE_S3TABLES_BUCKET_NAME   explicit global name ([a-z0-9-], 3–63 chars)")
        click.echo("    (The bucket list above is still shown so you can see what already exists.)")
    click.echo(f"    Namespace       {ns}")
    click.echo("    ICEBERG tables  (would run create-table for each if missing)")
    for t in tables:
        click.echo(f"                      • {ns}.{t}")
    click.echo("")


def apply_overrides(**env: str | None) -> None:
    """Copy non-empty Click option values into ``os.environ`` (after ``envvar`` resolution)."""
    for key, val in env.items():
        if val is not None and val != "":
            os.environ[key] = val


def _load_repo_dotenv() -> None:
    """Load ``<repo>/.env`` so ``task`` / ``uv run`` see the same vars as direnv (``override=False``)."""
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
        # Unreadable .env (permissions / sandbox): rely on the parent environment only.
        return


@click.group()
def cli() -> None:
    """Bronze landing: Glue DB, S3 Tables bucket/tables, IAM policy render (requires AWS CLI + credentials)."""


@cli.command("render-iam")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--aws-account-id",
    envvar="AWS_ACCOUNT_ID",
    show_envvar=True,
    help="12-digit account id (optional; default from STS if unset).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id; derives GLUE_DATABASE, S3 Tables bucket, and warehouse bucket when unset.",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Glue database name (default balloon_pops or derived from LAB_USERNAME).",
)
@click.option(
    "--bronze-bucket-name",
    envvar="BRONZE_BUCKET_NAME",
    show_envvar=True,
    help="Warehouse bucket (same as glue-setup); IAM uses arn:aws:s3:::<bucket> derived automatically.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print resolved env + rendered JSON to stdout; do not write files.",
)
def render_iam_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    aws_account_id: str | None,
    lab_username: str | None,
    glue_database: str | None,
    bronze_bucket_name: str | None,
    dry_run: bool,
) -> None:
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        AWS_ACCOUNT_ID=aws_account_id,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_BUCKET_NAME=bronze_bucket_name,
    )
    require_aws_profile()
    region = resolve_region()
    os.environ.setdefault("AWS_REGION", region)
    derive_bronze_resource_names()
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    os.environ["GLUE_DATABASE"] = glue_db
    profile = os.environ["AWS_PROFILE"]

    if not os.environ.get("AWS_ACCOUNT_ID"):
        os.environ["AWS_ACCOUNT_ID"] = resolve_aws_account_id(profile, region)

    arn = ensure_bronze_s3_arn_for_policy()
    click.echo(f"info: BRONZE_S3_ARN={arn} (derived from BRONZE_BUCKET_NAME for policy template)")

    root = repo_root()
    template_path = root / "lab/aws/bronze-glue-writer-policy.json"
    out_text = envsubst(template_path.read_text(encoding="utf-8"))
    out_path = root / ".aws-config/bronze-glue-writer-policy.rendered.json"

    if dry_run:
        click.echo("[dry-run] Would write:")
        click.echo(f"  {out_path}")
        click.echo("[dry-run] Effective substitutions:")
        for k in (
            "AWS_REGION",
            "AWS_ACCOUNT_ID",
            "GLUE_DATABASE",
            "BRONZE_BUCKET_NAME",
            "BRONZE_S3_ARN",
        ):
            click.echo(f"  {k}={os.environ.get(k, '')}")
        click.echo("[dry-run] Rendered policy JSON:")
        click.echo(out_text)
        return

    ensure_aws_config_dir(root)
    out_path.write_text(out_text, encoding="utf-8")
    click.echo(f"Wrote {out_path}")


@cli.command("glue-setup")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id; derives GLUE_DATABASE, BRONZE_S3TABLES_BUCKET_NAME, and BRONZE_BUCKET_NAME when unset (see bronze_aws).",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Glue database name (default balloon_pops or derived from LAB_USERNAME).",
)
@click.option(
    "--bronze-bucket-name",
    envvar="BRONZE_BUCKET_NAME",
    show_envvar=True,
    help="General-purpose S3 warehouse bucket; created by glue-setup if missing. With LAB_USERNAME, default or prefix is applied for collision safety.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show plan (read-only Glue GetDatabase + S3 HeadBucket); no S3/Glue creates and no .aws-config glue writes.",
)
def glue_setup_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    lab_username: str | None,
    glue_database: str | None,
    bronze_bucket_name: str | None,
    dry_run: bool,
) -> None:
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_BUCKET_NAME=bronze_bucket_name,
    )
    require_aws_profile()
    region = resolve_region()
    derive_bronze_resource_names()
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    warehouse = resolve_bronze_warehouse()
    profile = os.environ["AWS_PROFILE"]
    root = repo_root()
    out_json_path = root / ".aws-config/glue-database.json"

    session = boto3.Session(profile_name=profile, region_name=region)
    s3_client = session.client("s3")
    warehouse_bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    wh_bucket_status = ensure_bronze_warehouse_s3_bucket(
        s3_client,
        bucket=warehouse_bucket,
        region=region,
        dry_run=dry_run,
    )
    glue = session.client("glue")

    exists = False
    try:
        glue.get_database(Name=glue_db)
        exists = True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code != "EntityNotFoundException":
            raise

    if dry_run:
        click.echo("[dry-run] glue-setup:")
        click.echo(f"  profile={profile} region={region}")
        click.echo(f"  BRONZE_BUCKET_NAME={os.environ.get('BRONZE_BUCKET_NAME', '')}")
        click.echo(f"  warehouse_s3_bucket={wh_bucket_status}")
        click.echo(f"  database={glue_db!r} LocationUri={warehouse!r}")
        click.echo(f"  exists={exists}")
        click.echo(f"  would write: {out_json_path}")
        if not exists:
            click.echo("  action: would call glue.create_database")
        else:
            click.echo("  action: would only refresh get-database JSON")
        click.echo("")
        click.echo("Summary — derived Iceberg warehouse (Glue LocationUri)")
        click.echo(f"  {warehouse}")
        return

    ensure_aws_config_dir(root)
    if not exists:
        click.echo(f"Creating Glue database '{glue_db}' (LocationUri={warehouse})")
        glue.create_database(
            DatabaseInput={
                "Name": glue_db,
                "Description": "Balloon bronze Iceberg",
                "LocationUri": warehouse,
            }
        )
    else:
        click.echo(f"Glue database '{glue_db}' already exists")

    resp = glue.get_database(Name=glue_db)
    out_json_path.write_text(json.dumps(resp, indent=2, default=str), encoding="utf-8")
    click.echo(f"Wrote {out_json_path}")
    warehouse_txt = root / ".aws-config/bronze-warehouse-uri.txt"
    warehouse_txt.write_text(warehouse + "\n", encoding="utf-8")
    click.echo(f"Wrote {warehouse_txt}")
    click.echo("")
    click.echo("Summary — derived Iceberg warehouse (Glue LocationUri)")
    click.echo(f"  BRONZE_BUCKET_NAME={os.environ.get('BRONZE_BUCKET_NAME', '')}")
    click.echo(f"  warehouse_uri={warehouse}")


@cli.command("s3tables-setup")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id; derives GLUE_DATABASE, S3 Tables bucket, and general S3 warehouse bucket when unset.",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Optional Glue database name before LAB_USERNAME derivation.",
)
@click.option(
    "--s3tables-bucket",
    envvar="BRONZE_S3TABLES_BUCKET_NAME",
    show_envvar=True,
    help="Globally unique S3 table bucket name ([0-9a-z-]{3,63}).",
)
@click.option(
    "--s3tables-namespace",
    envvar="S3TABLES_NAMESPACE",
    show_envvar=True,
    help="Namespace inside the table bucket (default balloon_pops).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print a readable plan (after read-only list-table-buckets); no creates or .aws-config/ writes.",
)
@click.option(
    "--enable-s3tables-bucket-suffix",
    "enable_s3tables_bucket_suffix",
    is_flag=True,
    default=False,
    envvar="BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX",
    show_envvar=True,
    help="Append epoch millis to BRONZE_S3TABLES_BUCKET_NAME (testing; env is truthy like 1/true/yes).",
)
def s3tables_setup_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    lab_username: str | None,
    glue_database: str | None,
    s3tables_bucket: str | None,
    s3tables_namespace: str | None,
    dry_run: bool,
    enable_s3tables_bucket_suffix: bool,
) -> None:
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_S3TABLES_BUCKET_NAME=s3tables_bucket,
        S3TABLES_NAMESPACE=s3tables_namespace,
    )
    if enable_s3tables_bucket_suffix:
        os.environ["BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX"] = "1"
    require_aws_profile()
    region = resolve_region()
    derive_bronze_resource_names()
    apply_s3tables_millis_suffix_if_enabled()
    tb_name = (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip()
    if not tb_name and not dry_run:
        print(
            "error: set BRONZE_S3TABLES_BUCKET_NAME (3-63 chars, [0-9a-z-]) "
            "or LAB_USERNAME to derive it",
            file=sys.stderr,
        )
        raise SystemExit(1)
    ns = os.environ.get("S3TABLES_NAMESPACE", "balloon_pops")
    profile = os.environ["AWS_PROFILE"]
    root = repo_root()
    require_aws_cli_s3tables()

    data = aws_json(profile, region, ["s3tables", "list-table-buckets", "--no-paginate"])
    if not dry_run:
        ensure_aws_config_dir(root)
        list_path = root / ".aws-config/s3tables-list-table-buckets.json"
        list_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    table_bucket_arn = ""
    for b in data.get("tableBuckets") or []:
        if b.get("name") == tb_name:
            table_bucket_arn = b.get("arn") or ""
            break

    out_json_path = root / ".aws-config/s3tables-create-table-bucket.json"

    if dry_run:
        _echo_s3tables_dry_run_plan(
            profile=profile,
            region=region,
            tb_name=tb_name,
            ns=ns,
            table_bucket_arn=table_bucket_arn,
            tables=TABLES,
        )
        return

    if table_bucket_arn:
        click.echo(f"Table bucket '{tb_name}' already exists: {table_bucket_arn}")
        cp = subprocess.run(
            [
                "aws",
                "s3tables",
                "get-table-bucket",
                "--table-bucket-arn",
                table_bucket_arn,
                "--profile",
                profile,
                "--region",
                region,
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout, file=sys.stderr)
            raise SystemExit(cp.returncode or 1)
        out_json_path.write_text(cp.stdout or "{}", encoding="utf-8")
    else:
        click.echo(f"Creating S3 table bucket '{tb_name}' in {region}...")
        cp = subprocess.run(
            [
                "aws",
                "s3tables",
                "create-table-bucket",
                "--name",
                tb_name,
                "--encryption-configuration",
                "sseAlgorithm=AES256",
                "--profile",
                profile,
                "--region",
                region,
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout, file=sys.stderr)
            raise SystemExit(cp.returncode or 1)
        out_json_path.write_text(cp.stdout or "{}", encoding="utf-8")
        created = json.loads(cp.stdout or "{}")
        table_bucket_arn = created.get("arn") or ""

    arn_path = root / ".aws-config/s3tables-table-bucket-arn.txt"
    arn_path.write_text(table_bucket_arn + "\n", encoding="utf-8")
    click.echo(f"Table bucket ARN -> {arn_path}")

    click.echo(f"Creating namespace '{ns}' if missing...")
    subprocess.run(
        [
            "aws",
            "s3tables",
            "create-namespace",
            "--table-bucket-arn",
            table_bucket_arn,
            "--namespace",
            ns,
            "--profile",
            profile,
            "--region",
            region,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    for t in TABLES:
        click.echo(f"Ensuring ICEBERG table {ns}.{t} ...")
        subprocess.run(
            [
                "aws",
                "s3tables",
                "create-table",
                "--table-bucket-arn",
                table_bucket_arn,
                "--namespace",
                ns,
                "--name",
                t,
                "--format",
                "ICEBERG",
                "--profile",
                profile,
                "--region",
                region,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    tables_list_path = root / ".aws-config/s3tables-tables-list.json"
    tl = subprocess.run(
        [
            "aws",
            "s3tables",
            "list-tables",
            "--table-bucket-arn",
            table_bucket_arn,
            "--namespace",
            ns,
            "--profile",
            profile,
            "--region",
            region,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if tl.returncode != 0:
        print(tl.stderr or tl.stdout, file=sys.stderr)
        raise SystemExit(tl.returncode or 1)
    tables_list_path.write_text(tl.stdout or "{}", encoding="utf-8")
    click.echo(f"Wrote {tables_list_path}")
    last_name_path = root / ".aws-config/bronze-s3tables-last-bucket-name.txt"
    last_name_path.write_text(
        (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip() + "\n",
        encoding="utf-8",
    )
    click.echo(
        f"S3 table bucket name (cleanup / reuse) -> {last_name_path} "
        "(one line; for cleanup after millis suffix, unset "
        "BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX and point BRONZE_S3TABLES_BUCKET_NAME here)"
    )


@cli.command("snowflake-summary")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id; same derivation rules as glue-setup / s3tables-setup.",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Glue database name (default balloon_pops or derived from LAB_USERNAME).",
)
@click.option(
    "--bronze-bucket-name",
    envvar="BRONZE_BUCKET_NAME",
    show_envvar=True,
    help="Warehouse S3 bucket (must resolve after LAB_USERNAME rules for warehouse exports).",
)
@click.option(
    "--s3tables-bucket",
    envvar="BRONZE_S3TABLES_BUCKET_NAME",
    show_envvar=True,
    help="S3 Tables table-bucket name (optional; derived with LAB_USERNAME).",
)
@click.option(
    "--s3tables-namespace",
    envvar="S3TABLES_NAMESPACE",
    show_envvar=True,
    help="S3 Tables namespace inside the table bucket (default balloon_pops).",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit one JSON object instead of human-oriented copy/paste text.",
)
def snowflake_summary_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    lab_username: str | None,
    glue_database: str | None,
    bronze_bucket_name: str | None,
    s3tables_bucket: str | None,
    s3tables_namespace: str | None,
    as_json: bool,
) -> None:
    """Print resolved bronze AWS names/URIs/ARNs for Snowflake catalog integration / CLD prep.

    Read-only (STS + optional S3 Tables list-table-buckets). Does not write ``.aws-config/``.
    Aligns with ``lab/bronze-landing-zone.md`` Glue Iceberg REST host pattern; confirm
    ``CREATE CATALOG INTEGRATION`` fields against current Snowflake documentation.
    """
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_BUCKET_NAME=bronze_bucket_name,
        BRONZE_S3TABLES_BUCKET_NAME=s3tables_bucket,
        S3TABLES_NAMESPACE=s3tables_namespace,
    )
    require_aws_profile()
    region = resolve_region()
    os.environ.setdefault("AWS_REGION", region)
    root = repo_root()
    gdb = glue_database_json_path(root)
    if not gdb.is_file():
        print(
            f"error: missing {gdb}. Run `task bronze:glue-setup` (or `uv run bronze-cli glue-setup`) "
            "before snowflake-summary.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    apply_bronze_from_aws_config(root)
    derive_bronze_resource_names()
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    os.environ["GLUE_DATABASE"] = glue_db
    profile = os.environ["AWS_PROFILE"]
    account = resolve_aws_account_id(profile, region)

    bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    if not bucket:
        print(
            "error: set BRONZE_BUCKET_NAME or LAB_USERNAME so the warehouse bucket resolves "
            "(same requirement as glue-setup).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    warehouse = resolve_bronze_warehouse()
    s3_bucket_arn = ensure_bronze_s3_arn_for_policy()
    s3_objects_arn = f"{s3_bucket_arn}/*"
    glue_rest = f"https://glue.{region}.amazonaws.com/iceberg"
    glue_db_arn = f"arn:aws:glue:{region}:{account}:database/{glue_db}"
    glue_catalog_arn = f"arn:aws:glue:{region}:{account}:catalog"

    tb_name = resolve_s3tables_table_bucket_name(
        root, cli_bucket=(s3tables_bucket or "").strip()
    )
    ns = os.environ.get("S3TABLES_NAMESPACE", "balloon_pops")
    table_bucket_arn = _resolve_s3tables_table_bucket_arn(profile, region, tb_name)

    cfg = root / ".aws-config"
    file_warehouse = _read_text_strip(cfg / "bronze-warehouse-uri.txt")
    file_tb_arn = _read_text_strip(cfg / "s3tables-table-bucket-arn.txt")

    fq_tables = [f"{glue_db}.{t}" for t in TABLES]
    fq_s3tables = [f"{ns}.{t}" for t in TABLES] if tb_name else []

    payload: dict[str, object] = {
        "aws_profile": profile,
        "aws_region": region,
        "aws_account_id": account,
        "glue_database": glue_db,
        "glue_database_arn": glue_db_arn,
        "glue_catalog_arn": glue_catalog_arn,
        "glue_iceberg_rest_uri": glue_rest,
        "bronze_bucket_name": bucket,
        "iceberg_warehouse_uri": warehouse,
        "bronze_s3_bucket_arn": s3_bucket_arn,
        "bronze_s3_objects_arn": s3_objects_arn,
        "glue_iceberg_tables": list(TABLES),
        "glue_fully_qualified_tables": fq_tables,
        "bronze_s3tables_bucket_name": tb_name or None,
        "s3tables_namespace": ns if tb_name else None,
        "s3tables_table_bucket_arn": table_bucket_arn or None,
        "s3tables_fully_qualified_tables": fq_s3tables or None,
        "dotenv_snippet": {
            "AWS_REGION": region,
            "AWS_ACCOUNT_ID": account,
            "GLUE_DATABASE": glue_db,
            "BRONZE_BUCKET_NAME": bucket,
            "BRONZE_WAREHOUSE": warehouse,
            "BRONZE_S3TABLES_BUCKET_NAME": tb_name or "",
            "S3TABLES_NAMESPACE": ns,
        },
        "aws_config_files": {
            "bronze_warehouse_uri_txt": file_warehouse,
            "s3tables_table_bucket_arn_txt": file_tb_arn,
        },
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo("")
    click.echo("Bronze → Snowflake / CLD quick reference (read-only; no writes)")
    click.echo(f"  AWS_PROFILE={profile}  AWS_REGION={region}  AWS_ACCOUNT_ID={account}")
    click.echo("")
    click.echo("--- Shell exports (warehouse / Glue identifiers) ---")
    click.echo(f"export AWS_REGION={region!s}")
    click.echo(f"export AWS_ACCOUNT_ID={account!s}")
    click.echo(f"export GLUE_DATABASE={glue_db!s}")
    click.echo(f"export BRONZE_BUCKET_NAME={bucket!s}")
    click.echo(f"export BRONZE_WAREHOUSE={warehouse!s}")
    click.echo("")
    click.echo("--- ARNs / URIs often needed next to Snowflake SQL / IAM ---")
    click.echo(f"export BRONZE_S3_BUCKET_ARN={s3_bucket_arn!s}")
    click.echo(f"export BRONZE_S3_OBJECTS_ARN={s3_objects_arn!s}")
    click.echo(f"export GLUE_DATABASE_ARN={glue_db_arn!s}")
    click.echo(f"export GLUE_CATALOG_ARN={glue_catalog_arn!s}")
    click.echo(f"export GLUE_ICEBERG_REST_URI={glue_rest!s}")
    click.echo("")
    click.echo("--- Iceberg table names (Glue Data Catalog database above) ---")
    click.echo(" ".join(TABLES))
    click.echo("")
    click.echo("Fully qualified (for checklists):")
    for line in fq_tables:
        click.echo(f"  {line}")
    click.echo("")
    if tb_name:
        click.echo("--- S3 Tables (optional; control-plane bucket + namespace) ---")
        click.echo(f"export BRONZE_S3TABLES_BUCKET_NAME={tb_name!s}")
        click.echo(f"export S3TABLES_NAMESPACE={ns!s}")
        if table_bucket_arn:
            click.echo(f"export S3TABLES_TABLE_BUCKET_ARN={table_bucket_arn!s}")
        else:
            click.echo(
                "# S3TABLES_TABLE_BUCKET_ARN: (not found via list-table-buckets — "
                "create with task bronze:s3tables-setup or fix name/region/profile)"
            )
        click.echo("")
        click.echo("Logical tables in namespace (empty until you load elsewhere):")
        for line in fq_s3tables:
            click.echo(f"  {line}")
        click.echo("")
    else:
        click.echo(
            "--- S3 Tables: BRONZE_S3TABLES_BUCKET_NAME unset "
            "(set LAB_USERNAME or BRONZE_S3TABLES_BUCKET_NAME to include) ---"
        )
        click.echo("")

    click.echo("--- On-disk artifacts from prior bronze tasks (if present) ---")
    p_wh = cfg / "bronze-warehouse-uri.txt"
    p_arn = cfg / "s3tables-table-bucket-arn.txt"
    if file_warehouse:
        click.echo(f"  {p_wh}: {file_warehouse}")
    else:
        click.echo(f"  {p_wh}: (missing — run task bronze:glue-setup)")
    if file_tb_arn:
        click.echo(f"  {p_arn}: {file_tb_arn}")
    else:
        click.echo(f"  {p_arn}: (missing — run task bronze:s3tables-setup after naming bucket)")
    click.echo("")
    click.echo(
        "Hint: paste `GLUE_ICEBERG_REST_URI` / ARNs into notes or IAM alongside "
        "`CREATE CATALOG INTEGRATION` / `LINKED_CATALOG` per Snowflake docs; "
        "Snowflake-side `API_AWS_IAM_USER_ARN` + external id come from "
        "`DESCRIBE CATALOG INTEGRATION` (not shown here)."
    )
    click.echo("")


@cli.command("lakeformation-setup")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id; derives BRONZE_BUCKET_NAME / GLUE_DATABASE when unset.",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Glue database name (default balloon_pops or derived from LAB_USERNAME).",
)
@click.option(
    "--bronze-bucket-name",
    envvar="BRONZE_BUCKET_NAME",
    show_envvar=True,
    help="Warehouse S3 bucket (required for register-resource and LF data-access policy).",
)
@click.option(
    "--repo-root",
    "repo_root_arg",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    default=None,
    help="Repository root (default: auto-detect).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print planned actions only; no IAM/Lake Formation/Glue writes.",
)
def lakeformation_setup_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    lab_username: str | None,
    glue_database: str | None,
    bronze_bucket_name: str | None,
    repo_root_arg: Path | None,
    dry_run: bool,
) -> None:
    """Lake Formation prep for Snowflake vended reads: LF data-access role, register S3, Glue DB, grants.

    Requires ``.aws-config/glue-database.json`` and Snowflake catalog role ARN in
    ``.aws-config/snowflake-glue-catalog-iam-role-arn.txt`` (or ``SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_ARN``).
    Optional: ``LAKE_FORMATION_BRONZE_DATA_ACCESS_ROLE_NAME``, ``LAKE_FORMATION_ADMIN_ESCAPE_PRINCIPAL_ARN``.
    """
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_BUCKET_NAME=bronze_bucket_name,
    )
    require_aws_profile()
    region = resolve_region()
    os.environ.setdefault("AWS_REGION", region)
    run_lakeformation_setup(root=repo_root_arg, dry_run=dry_run)


@cli.command("cleanup")
@click.option(
    "--aws-profile",
    envvar="AWS_PROFILE",
    show_envvar=True,
    help="AWS credential profile (or set AWS_PROFILE).",
)
@click.option(
    "--aws-region",
    envvar="AWS_REGION",
    show_envvar=True,
    help="AWS region (or set AWS_REGION / profile default).",
)
@click.option(
    "--lab-username",
    envvar="LAB_USERNAME",
    show_envvar=True,
    help="Workshop id for derived BRONZE_S3TABLES_BUCKET_NAME / GLUE_DATABASE when unset.",
)
@click.option(
    "--glue-database",
    envvar="GLUE_DATABASE",
    show_envvar=True,
    help="Glue database to clean up (default balloon_pops or derived from LAB_USERNAME).",
)
@click.option(
    "--s3tables-bucket",
    envvar="BRONZE_S3TABLES_BUCKET_NAME",
    show_envvar=True,
    help="S3 Tables bucket name to clean up (or derived from LAB_USERNAME).",
)
@click.option(
    "--s3tables-namespace",
    envvar="S3TABLES_NAMESPACE",
    show_envvar=True,
    help="S3 Tables namespace to clean up (default balloon_pops).",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Skip interactive confirmation for destructive cleanup.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print cleanup plan only; no deletes.",
)
@click.option(
    "--delete-snowflake-catalog-iam-role",
    is_flag=True,
    default=False,
    help="After Glue/S3 Tables steps, delete lab-tagged Snowflake Glue catalog SIGV4 IAM role "
    "(same name as create-read-role: LAB_USERNAME → <glue_slug>_snowflake_glue_catalog_read).",
)
@click.option(
    "--no-aws-config",
    "cleanup_no_aws_config",
    is_flag=True,
    default=False,
    help="Do not overlay targets from <repo>/.aws-config/ (use env / LAB_USERNAME only).",
)
def cleanup_cmd(
    aws_profile: str | None,
    aws_region: str | None,
    lab_username: str | None,
    glue_database: str | None,
    s3tables_bucket: str | None,
    s3tables_namespace: str | None,
    yes: bool,
    dry_run: bool,
    delete_snowflake_catalog_iam_role: bool,
    cleanup_no_aws_config: bool,
) -> None:
    """Remove Glue database/tables and S3 Tables control-plane resources.

    Does **not** delete or empty **``BRONZE_BUCKET_NAME``** (the general-purpose warehouse
    bucket, for example ``<slug>-balloon-bronze``): Iceberg files under ``s3://…/iceberg/``
    stay until you remove them in S3 separately.

    By default, after name derivation, overlays **``GLUE_DATABASE``**, **``BRONZE_BUCKET_NAME``**
    (warehouse host from LocationUri), and **``BRONZE_S3TABLES_BUCKET_NAME``** from the
    repo **``.aws-config/``** files written by **``glue-setup``** / **``s3tables-setup``**
    so teardown matches the last local run (not ``~/.aws-config``). Passing **``--glue-database``**
    or **``--s3tables-bucket``** skips the on-disk hint for that target only.

    Optional **``--delete-snowflake-catalog-iam-role``** removes the lab-created SIGV4 read role
    (tags ``project=balloon-popper-demo``, ``purpose=snowflake-glue-catalog-read``) only when the
    resolved role name matches; skips otherwise.
    """
    apply_overrides(
        AWS_PROFILE=aws_profile,
        AWS_REGION=aws_region,
        LAB_USERNAME=lab_username,
        GLUE_DATABASE=glue_database,
        BRONZE_S3TABLES_BUCKET_NAME=s3tables_bucket,
        S3TABLES_NAMESPACE=s3tables_namespace,
    )
    require_aws_profile()
    region = resolve_region()
    derive_bronze_resource_names()
    if not cleanup_no_aws_config:
        root = repo_root()
        skip_glue = glue_database is not None and str(glue_database).strip() != ""
        skip_tb = s3tables_bucket is not None and str(s3tables_bucket).strip() != ""
        applied = apply_cleanup_context_from_aws_config(
            root,
            skip_glue_database_from_file=skip_glue,
            skip_s3tables_bucket_from_file=skip_tb,
        )
        for key in ("GLUE_DATABASE", "BRONZE_BUCKET_NAME", "BRONZE_S3TABLES_BUCKET_NAME"):
            if key in applied:
                click.echo(
                    f"info: cleanup {key}={applied[key]!r} "
                    f"(from {root / '.aws-config'}/ — last bronze run in this repo)"
                )
    profile = os.environ["AWS_PROFILE"]
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    ns = os.environ.get("S3TABLES_NAMESPACE", "balloon_pops")
    tb_name = (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip()

    session = boto3.Session(profile_name=profile, region_name=region)
    glue = session.client("glue")

    glue_tables: list[str] = []
    glue_exists = True
    try:
        paginator = glue.get_paginator("get_tables")
        for page in paginator.paginate(DatabaseName=glue_db):
            for t in page.get("TableList", []):
                name = t.get("Name")
                if isinstance(name, str) and name:
                    glue_tables.append(name)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("EntityNotFoundException", "DatabaseNotFoundException"):
            glue_exists = False
        else:
            raise

    table_bucket_arn = ""
    s3tables_present = False
    s3tables_tables: list[str] = []
    if tb_name:
        require_aws_cli_s3tables()
        buckets = aws_json(profile, region, ["s3tables", "list-table-buckets", "--no-paginate"])
        for b in buckets.get("tableBuckets") or []:
            if b.get("name") == tb_name:
                table_bucket_arn = b.get("arn") or ""
                s3tables_present = True
                break
        if table_bucket_arn:
            cp = subprocess.run(
                [
                    "aws",
                    "s3tables",
                    "list-tables",
                    "--table-bucket-arn",
                    table_bucket_arn,
                    "--namespace",
                    ns,
                    "--profile",
                    profile,
                    "--region",
                    region,
                    "--output",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if cp.returncode == 0:
                listed = json.loads(cp.stdout or "{}")
                for t in listed.get("tables") or []:
                    name = t.get("name")
                    if isinstance(name, str) and name:
                        s3tables_tables.append(name)
            else:
                click.echo(
                    f"  note: could not list S3 tables for namespace {ns!r}; "
                    "cleanup will still try namespace and bucket deletes"
                )

    click.echo("Cleanup plan — bronze resources")
    click.echo(f"  profile={profile} region={region}")
    click.echo(f"  Glue database={glue_db!r} exists={glue_exists} tables={len(glue_tables)}")
    if glue_tables:
        click.echo("    Glue tables to delete:")
        for name in glue_tables:
            click.echo(f"      • {name}")
    if tb_name:
        click.echo(f"  S3 Tables bucket={tb_name!r} namespace={ns!r} present={s3tables_present}")
        if table_bucket_arn:
            click.echo(f"    table_bucket_arn={table_bucket_arn}")
            click.echo(f"    S3 Tables to delete={len(s3tables_tables)}")
            for name in s3tables_tables:
                click.echo(f"      • {ns}.{name}")
        else:
            click.echo("    bucket not found; S3 Tables delete steps will be skipped")
    else:
        click.echo("  S3 Tables bucket not set; skipping S3 Tables cleanup")
    wh_bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    click.echo(f"  Warehouse bucket BRONZE_BUCKET_NAME={wh_bucket!r} — never deleted or emptied by this command.")
    click.echo(
        "  Note: Glue + S3 Tables control-plane deletes only. "
        "Objects under s3://<BRONZE_BUCKET_NAME>/iceberg/ are unchanged; empty that prefix in S3 if you want a hard reset."
    )
    sf_catalog_role = default_snowflake_glue_catalog_iam_role_name()
    click.echo(f"  Snowflake Glue catalog SIGV4 IAM role target={sf_catalog_role!r}.")
    if delete_snowflake_catalog_iam_role:
        click.echo(
            "  Snowflake catalog IAM role: will delete after Glue/S3 Tables (only if role exists "
            "with tags project=balloon-popper-demo, purpose=snowflake-glue-catalog-read)."
        )
    else:
        click.echo(
            "  (Optional) --delete-snowflake-catalog-iam-role removes that lab-tagged IAM role after Glue/S3 Tables."
        )

    if dry_run:
        if delete_snowflake_catalog_iam_role:
            iam = session.client("iam")
            delete_tagged_snowflake_glue_catalog_read_role(
                iam, sf_catalog_role, root=repo_root(), dry_run=True
            )
        click.echo("[dry-run] No deletes executed.")
        return

    if not yes:
        click.confirm(
            "Proceed with cleanup of the resources above?",
            default=False,
            abort=True,
        )

    if table_bucket_arn:
        for name in s3tables_tables:
            click.echo(f"Deleting S3 table {ns}.{name} ...")
            cp = subprocess.run(
                [
                    "aws",
                    "s3tables",
                    "delete-table",
                    "--table-bucket-arn",
                    table_bucket_arn,
                    "--namespace",
                    ns,
                    "--name",
                    name,
                    "--profile",
                    profile,
                    "--region",
                    region,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if cp.returncode != 0:
                print(cp.stderr or cp.stdout, file=sys.stderr)
                raise SystemExit(cp.returncode or 1)

        click.echo(f"Deleting S3 namespace {ns!r} ...")
        cp = subprocess.run(
            [
                "aws",
                "s3tables",
                "delete-namespace",
                "--table-bucket-arn",
                table_bucket_arn,
                "--namespace",
                ns,
                "--profile",
                profile,
                "--region",
                region,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout, file=sys.stderr)
            raise SystemExit(cp.returncode or 1)

        click.echo(f"Deleting S3 table bucket {tb_name!r} ...")
        cp = subprocess.run(
            [
                "aws",
                "s3tables",
                "delete-table-bucket",
                "--table-bucket-arn",
                table_bucket_arn,
                "--profile",
                profile,
                "--region",
                region,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout, file=sys.stderr)
            raise SystemExit(cp.returncode or 1)

    if glue_exists:
        for name in glue_tables:
            click.echo(f"Deleting Glue table {glue_db}.{name} ...")
            glue.delete_table(DatabaseName=glue_db, Name=name)
        click.echo(f"Deleting Glue database {glue_db!r} ...")
        glue.delete_database(Name=glue_db)

    if delete_snowflake_catalog_iam_role:
        iam = session.client("iam")
        delete_tagged_snowflake_glue_catalog_read_role(
            iam, sf_catalog_role, root=repo_root(), dry_run=False
        )

    removed = remove_bronze_aws_config_artifacts(repo_root())
    if removed:
        click.echo("Removed local bronze .aws-config/ artifacts:")
        for p in removed:
            click.echo(f"  • {p}")

    click.echo("Bronze cleanup completed (warehouse bucket untouched).")


def main() -> None:
    _load_repo_dotenv()
    cli()


if __name__ == "__main__":
    main()
