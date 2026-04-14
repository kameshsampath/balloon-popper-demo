# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Cross-platform bronze AWS setup (Glue, S3 Tables, IAM render). Replaces bash scripts."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import boto3
import click
from botocore.exceptions import ClientError

from bronze_aws import (
    aws_json,
    derive_bronze_resource_names,
    ensure_aws_config_dir,
    envsubst,
    repo_root,
    require_aws_cli_s3tables,
    require_aws_profile,
    resolve_aws_account_id,
    resolve_region,
)

TABLES = (
    "leaderboard",
    "balloon_color_stats",
    "realtime_scores",
    "balloon_colored_pops",
    "color_performance_trends",
)


@click.group()
def cli() -> None:
    """Bronze landing: Glue DB, S3 Tables bucket/tables, IAM policy render (requires AWS CLI + credentials)."""


@cli.command("render-iam")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print resolved env + rendered JSON to stdout; do not write files.",
)
def render_iam_cmd(dry_run: bool) -> None:
    require_aws_profile()
    region = resolve_region()
    os.environ.setdefault("AWS_REGION", region)
    derive_bronze_resource_names()
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    os.environ["GLUE_DATABASE"] = glue_db
    profile = os.environ["AWS_PROFILE"]

    if not os.environ.get("AWS_ACCOUNT_ID"):
        os.environ["AWS_ACCOUNT_ID"] = resolve_aws_account_id(profile, region)

    if not os.environ.get("BRONZE_S3_ARN"):
        print(
            "error: set BRONZE_S3_ARN (e.g. arn:aws:s3:::your-warehouse-bucket) for policy rendering",
            file=sys.stderr,
        )
        raise SystemExit(1)

    root = repo_root()
    template_path = root / "lab/aws/bronze-glue-writer-policy.json"
    out_text = envsubst(template_path.read_text(encoding="utf-8"))
    out_path = root / ".aws-config/bronze-glue-writer-policy.rendered.json"

    if dry_run:
        click.echo("[dry-run] Would write:")
        click.echo(f"  {out_path}")
        click.echo("[dry-run] Effective substitutions:")
        for k in ("AWS_REGION", "AWS_ACCOUNT_ID", "GLUE_DATABASE", "BRONZE_S3_ARN"):
            click.echo(f"  {k}={os.environ.get(k, '')}")
        click.echo("[dry-run] Rendered policy JSON:")
        click.echo(out_text)
        return

    ensure_aws_config_dir(root)
    out_path.write_text(out_text, encoding="utf-8")
    click.echo(f"Wrote {out_path}")


@cli.command("glue-setup")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show plan (uses read-only Glue GetDatabase); no create and no glue-database.json.",
)
def glue_setup_cmd(dry_run: bool) -> None:
    require_aws_profile()
    region = resolve_region()
    derive_bronze_resource_names()
    glue_db = os.environ.get("GLUE_DATABASE", "balloon_pops")
    warehouse = os.environ.get("BRONZE_WAREHOUSE")
    if not warehouse:
        print(
            "error: set BRONZE_WAREHOUSE to s3://bucket/prefix/ for Iceberg files",
            file=sys.stderr,
        )
        raise SystemExit(1)
    profile = os.environ["AWS_PROFILE"]
    root = repo_root()
    out_json_path = root / ".aws-config/glue-database.json"

    session = boto3.Session(profile_name=profile, region_name=region)
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
        click.echo(f"  database={glue_db!r} LocationUri={warehouse!r}")
        click.echo(f"  exists={exists}")
        click.echo(f"  would write: {out_json_path}")
        if not exists:
            click.echo("  action: would call glue.create_database")
        else:
            click.echo("  action: would only refresh get-database JSON")
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


@cli.command("s3tables-setup")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print plan (and read-only list); no creates and no files under .aws-config/.",
)
def s3tables_setup_cmd(dry_run: bool) -> None:
    require_aws_profile()
    region = resolve_region()
    derive_bronze_resource_names()
    tb_name = os.environ.get("BRONZE_S3TABLES_BUCKET_NAME")
    if not tb_name:
        print(
            "error: set BRONZE_S3TABLES_BUCKET_NAME (3-63 chars, [0-9a-z-])",
            file=sys.stderr,
        )
        raise SystemExit(1)
    ns = os.environ.get("S3TABLES_NAMESPACE", "balloon_pops")
    profile = os.environ["AWS_PROFILE"]
    root = repo_root()
    require_aws_cli_s3tables()

    data = aws_json(profile, region, ["s3tables", "list-table-buckets", "--no-paginate"])
    if dry_run:
        click.echo("[dry-run] s3tables-setup plan:")
        click.echo(f"  profile={profile} region={region}")
        click.echo(f"  table_bucket_name={tb_name!r} namespace={ns!r}")
        click.echo("[dry-run] (read-only) list-table-buckets completed")
    else:
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
        if table_bucket_arn:
            click.echo(f"  table bucket: already exists arn={table_bucket_arn}")
        else:
            click.echo(f"  table bucket: would create name={tb_name!r}")
        click.echo(f"  namespace: would ensure {ns!r}")
        for t in TABLES:
            click.echo(f"  table: would ensure {ns}.{t} (ICEBERG)")
        click.echo("[dry-run] No writes to .aws-config/ in dry-run mode.")
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
