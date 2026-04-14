# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Shared helpers for bronze AWS CLI (cross-platform; replaces scripts/lib.sh)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    """Repository root (parent of ``tools/``)."""
    return Path(__file__).resolve().parent.parent.parent


def ensure_aws_config_dir(root: Path | None = None) -> Path:
    d = (root or repo_root()) / ".aws-config"
    d.mkdir(parents=True, exist_ok=True)
    return d


def require_aws_profile() -> None:
    if not os.environ.get("AWS_PROFILE"):
        print("error: set AWS_PROFILE to a real AWS credential profile", file=sys.stderr)
        raise SystemExit(1)


def resolve_region() -> str:
    r = os.environ.get("AWS_REGION", "").strip()
    if r:
        return r
    profile = os.environ["AWS_PROFILE"]
    cp = subprocess.run(
        ["aws", "configure", "get", "region", "--profile", profile],
        capture_output=True,
        text=True,
        check=False,
    )
    r = (cp.stdout or "").strip()
    if not r:
        print(
            f"error: set AWS_REGION or configure region for AWS_PROFILE={profile}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return r


def sanitize_lab_slug_glue(lab: str) -> str:
    u = lab.lower()
    u = re.sub(r"[^a-z0-9_]+", "_", u)
    u = re.sub(r"_+", "_", u).strip("_")
    return u[:20] if u else ""


def sanitize_lab_slug_bucket(lab: str) -> str:
    u = lab.lower().replace("_", "-")
    u = re.sub(r"[^a-z0-9-]+", "-", u)
    u = re.sub(r"-+", "-", u).strip("-")
    return u[:24] if u else ""


def derive_bronze_resource_names() -> None:
    """When LAB_USERNAME is set, default GLUE_DATABASE and BRONZE_S3TABLES_BUCKET_NAME if unset."""
    lab = os.environ.get("LAB_USERNAME", "").strip()
    if not lab:
        return
    gslug = sanitize_lab_slug_glue(lab)
    bslug = sanitize_lab_slug_bucket(lab)
    if not gslug:
        print(
            "error: LAB_USERNAME must yield a non-empty Glue slug "
            "(letters, numbers, underscore, hyphen)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not bslug:
        print(
            "error: LAB_USERNAME must yield a valid S3 table bucket slug "
            "(letters, numbers, hyphen)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not os.environ.get("GLUE_DATABASE"):
        os.environ["GLUE_DATABASE"] = f"{gslug}_balloon_pops"
        print(f"info: GLUE_DATABASE={os.environ['GLUE_DATABASE']} (default from LAB_USERNAME)")
    if not os.environ.get("BRONZE_S3TABLES_BUCKET_NAME"):
        os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = f"{bslug}-balloon-s3tables"
        print(
            "info: BRONZE_S3TABLES_BUCKET_NAME="
            f"{os.environ['BRONZE_S3TABLES_BUCKET_NAME']} (default from LAB_USERNAME)"
        )


def envsubst(template: str, environ: dict[str, str] | None = None) -> str:
    """Replace ``${VAR}`` placeholders like ``gettext envsubst`` (shell-style names only)."""
    env = environ if environ is not None else os.environ

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in env or env[key] is None:
            return ""
        return env[key]

    return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, template)


def resolve_aws_account_id(profile: str, region: str) -> str:
    cp = subprocess.run(
        [
            "aws",
            "sts",
            "get-caller-identity",
            "--profile",
            profile,
            "--region",
            region,
            "--query",
            "Account",
            "--output",
            "text",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    aid = (cp.stdout or "").strip()
    if cp.returncode != 0 or not aid:
        print(cp.stderr or "error: sts get-caller-identity failed", file=sys.stderr)
        raise SystemExit(1)
    return aid


def aws_json(profile: str, region: str, args: list[str]) -> dict:
    """Run ``aws`` with JSON output; return parsed dict or exit on failure."""
    cmd = ["aws", *args, "--profile", profile, "--region", region, "--output", "json"]
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        print(cp.stderr or cp.stdout or "aws command failed", file=sys.stderr)
        raise SystemExit(cp.returncode or 1)
    if not (cp.stdout or "").strip():
        return {}
    return json.loads(cp.stdout)


def require_aws_cli_s3tables() -> None:
    cp = subprocess.run(["aws", "s3tables", "help"], capture_output=True, text=True, check=False)
    if cp.returncode != 0:
        print(
            "error: AWS CLI does not support 's3tables' commands. "
            "Upgrade to AWS CLI v2.34+ "
            "(https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).",
            file=sys.stderr,
        )
        raise SystemExit(1)
