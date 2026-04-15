# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Shared helpers for bronze AWS CLI (cross-platform; replaces scripts/lib.sh)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
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


def sanitize_general_s3_bucket_fragment(fragment: str) -> str:
    """Fragment for S3 bucket names: lowercase ``[a-z0-9-]``, non-empty."""
    u = fragment.lower().replace("_", "-")
    u = re.sub(r"[^a-z0-9-]+", "-", u)
    u = re.sub(r"-+", "-", u).strip("-")
    return u[:40] if u else "bronze"


def sanitize_lab_slug_bucket(lab: str) -> str:
    """Lowercase hyphen slug for S3 Tables bucket prefix; max 24 chars (workshop collision guard).

    Similar intent to ``sfutils_extvolumes.extvolume.to_aws_name`` (installed with this
    repo); that helper does not apply this length cap—do not assume parity.
    """
    u = lab.lower().replace("_", "-")
    u = re.sub(r"[^a-z0-9-]+", "-", u)
    u = re.sub(r"-+", "-", u).strip("-")
    return u[:24] if u else ""


def _env_truthy(key: str) -> bool:
    v = (os.environ.get(key) or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _apply_optional_s3tables_millis_suffix() -> None:
    """Append ``-<epoch_millis>`` to ``BRONZE_S3TABLES_BUCKET_NAME`` when enabled.

    Controlled by ``BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX`` (empty / false → no change).
    Clamps the final name to 63 characters for S3 Tables bucket naming limits.
    """
    if not _env_truthy("BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX"):
        return
    base = (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip()
    if not base:
        return
    millis = str(int(time.time() * 1000))
    sep = "-"
    max_total = 63
    room = max_total - len(sep) - len(millis)
    if room < 1:
        print(
            "error: BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX set but base table-bucket name is too long "
            "to append epoch millis within 63 characters",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if len(base) > room:
        base = base[:room].rstrip("-")
    if not base:
        print(
            "error: BRONZE_S3TABLES_BUCKET_NAME became empty after trimming for millis suffix",
            file=sys.stderr,
        )
        raise SystemExit(1)
    final_name = f"{base}{sep}{millis}"
    os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = final_name
    print(
        "info: BRONZE_S3TABLES_BUCKET_NAME="
        f"{final_name!r} (epoch millis suffix; BRONZE_S3TABLES_BUCKET_ENABLE_SUFFIX)"
    )


def derive_bronze_resource_names() -> None:
    """When LAB_USERNAME is set, default Glue DB and apply lab-scoped S3 names.

    ``BRONZE_S3TABLES_BUCKET_NAME`` (S3 Tables control-plane bucket):
    - If unset or only the bare lab slug → ``<bucket_slug>-balloon-s3tables``.
    - If set → ``<bucket_slug>-<sanitized-fragment>`` unless already prefixed with
      ``<bucket_slug>-``.

    ``BRONZE_BUCKET_NAME`` (general-purpose S3 warehouse bucket):
    - Same rules with suffix ``balloon-bronze`` when unset / bare slug.

    Optional ``-<epoch_millis>`` on ``BRONZE_S3TABLES_BUCKET_NAME`` is **not** applied here;
    call :func:`apply_s3tables_millis_suffix_if_enabled` from ``s3tables-setup`` only so IAM
    and generated SQL do not drift on every ``derive`` invocation.
    """
    lab = os.environ.get("LAB_USERNAME", "").strip()
    if lab:
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
        prefix = f"{bslug}-"

        raw_tables = (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip()
        if not raw_tables or raw_tables == bslug:
            os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = f"{bslug}-balloon-s3tables"
            print(
                "info: BRONZE_S3TABLES_BUCKET_NAME="
                f"{os.environ['BRONZE_S3TABLES_BUCKET_NAME']} (default from LAB_USERNAME)"
            )
        elif raw_tables.startswith(prefix) and 3 <= len(raw_tables) <= 63:
            pass
        else:
            frag_t = sanitize_general_s3_bucket_fragment(raw_tables)
            candidate_t = prefix + frag_t
            if len(candidate_t) > 63:
                keep_t = 63 - len(prefix)
                frag_t = frag_t[: max(keep_t, 1)].rstrip("-")
                candidate_t = prefix + frag_t
            os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = candidate_t
            if candidate_t != raw_tables:
                print(
                    "info: BRONZE_S3TABLES_BUCKET_NAME="
                    f"{candidate_t!r} (LAB_USERNAME prefix; was {raw_tables!r})"
                )

        raw_bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
        if not raw_bucket or raw_bucket == bslug:
            os.environ["BRONZE_BUCKET_NAME"] = f"{bslug}-balloon-bronze"
            print(
                "info: BRONZE_BUCKET_NAME="
                f"{os.environ['BRONZE_BUCKET_NAME']} (default from LAB_USERNAME)"
            )
        elif raw_bucket.startswith(prefix) and 3 <= len(raw_bucket) <= 63:
            # Already lab-namespaced
            pass
        else:
            frag = sanitize_general_s3_bucket_fragment(raw_bucket)
            candidate = prefix + frag
            if len(candidate) > 63:
                keep = 63 - len(prefix)
                frag = frag[: max(keep, 1)].rstrip("-")
                candidate = prefix + frag
            os.environ["BRONZE_BUCKET_NAME"] = candidate
            if candidate != raw_bucket:
                print(
                    "info: BRONZE_BUCKET_NAME="
                    f"{candidate!r} (LAB_USERNAME prefix; was {raw_bucket!r})"
                )


def apply_s3tables_millis_suffix_if_enabled() -> None:
    """Apply millis suffix to ``BRONZE_S3TABLES_BUCKET_NAME`` when enabled (``s3tables-setup`` only)."""
    _apply_optional_s3tables_millis_suffix()


def default_snowflake_glue_catalog_iam_role_name() -> str:
    """IAM role name for Snowflake Glue REST ``SIGV4`` read (``create-glue-catalog-read-role``).

    When ``LAB_USERNAME`` is set (after :func:`derive_bronze_resource_names`), uses the same
    **Glue slug** prefix as ``GLUE_DATABASE`` (``<glue_slug>_…``) so workshop roles do not collide:
    ``{glue_slug}_snowflake_glue_catalog_read``. Otherwise returns the solo default
    ``snowflake_glue_catalog_read``. Clamped to 64 characters for IAM.
    """
    lab = os.environ.get("LAB_USERNAME", "").strip()
    if lab:
        gslug = sanitize_lab_slug_glue(lab)
        if gslug:
            name = f"{gslug}_snowflake_glue_catalog_read"
            return name[:64] if len(name) > 64 else name
    return "snowflake_glue_catalog_read"


def ensure_bronze_s3_arn_for_policy() -> str:
    """Set ``BRONZE_S3_ARN`` from ``BRONZE_BUCKET_NAME`` for IAM policy templates (envsubst)."""
    wb = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    if not wb:
        print(
            "error: BRONZE_BUCKET_NAME is required for IAM render "
            "(set it, or set LAB_USERNAME for derived <slug>-balloon-bronze)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    arn = f"arn:aws:s3:::{wb}"
    os.environ["BRONZE_S3_ARN"] = arn
    return arn


def resolve_bronze_warehouse() -> str:
    """Derive Glue / PyIceberg warehouse URI from ``BRONZE_BUCKET_NAME`` only.

    Sets ``BRONZE_WAREHOUSE`` in the environment to ``s3://<bucket>/iceberg/`` for
    libraries that read that variable; learners configure only the bucket name.
    """
    bucket = (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    if not bucket:
        print(
            "error: set BRONZE_BUCKET_NAME to your general-purpose S3 warehouse bucket, "
            "or run `task bronze:glue-setup` (creates the bucket if missing and writes "
            ".aws-config/) so load can resolve the name",
            file=sys.stderr,
        )
        raise SystemExit(1)
    derived = f"s3://{bucket}/iceberg/"
    os.environ["BRONZE_WAREHOUSE"] = derived
    return derived


def ensure_bronze_warehouse_s3_bucket(
    s3,
    *,
    bucket: str,
    region: str,
    dry_run: bool,
) -> str:
    """Create the general-purpose warehouse S3 bucket if it does not exist.

    Used by ``bronze-cli glue-setup``. Idempotent. For ``us-east-1``, omits
    ``CreateBucketConfiguration`` (S3 API requirement).

    Returns ``exists``, ``created``, or ``would_create`` (missing bucket and
    ``dry_run``). Exits on HeadBucket/CreateBucket errors that block the lab.
    """
    from botocore.exceptions import ClientError

    try:
        s3.head_bucket(Bucket=bucket)
        print(f"info: S3 warehouse bucket {bucket!r} already exists")
        return "exists"
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "")
        if code == "403":
            print(
                f"error: cannot access S3 bucket {bucket!r} (HeadBucket 403). "
                "It may be owned by another account, or this principal lacks "
                "s3:ListBucket. Use another BRONZE_BUCKET_NAME or fix IAM.",
                file=sys.stderr,
            )
            raise SystemExit(1)
        if code not in ("404", "NoSuchBucket"):
            raise

    if dry_run:
        print(
            f"info: would create S3 warehouse bucket {bucket!r} in region {region} "
            "(run glue-setup without --dry-run)"
        )
        return "would_create"

    create_kw: dict = {"Bucket": bucket}
    if region != "us-east-1":
        create_kw["CreateBucketConfiguration"] = {"LocationConstraint": region}
    try:
        s3.create_bucket(**create_kw)
    except ClientError as e:
        err = e.response.get("Error") or {}
        code = err.get("Code", "")
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"info: S3 warehouse bucket {bucket!r} already exists (concurrent create)")
            return "exists"
        msg = err.get("Message", str(e))
        print(f"error: CreateBucket failed ({code}): {msg}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"info: created S3 warehouse bucket {bucket!r}")
    return "created"


def _s3_uri_bucket(uri: str) -> str | None:
    """Bucket host of ``s3://bucket/...`` or ``s3://bucket``; None if not parseable."""
    u = (uri or "").strip()
    if not u.startswith("s3://"):
        return None
    rest = u[5:]
    if not rest:
        return None
    return rest.split("/", 1)[0] or None


def read_aws_config_first_line(path: Path) -> str:
    """First non-empty, non-``#`` line of a file; empty string if missing/unreadable."""
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


def parse_s3tables_table_bucket_name_from_arn(arn: str) -> str | None:
    """Table-bucket **name** from ``arn:aws:s3tables:region:account:bucket/<name>``."""
    arn = (arn or "").strip()
    if not arn.startswith("arn:aws:s3tables:") or ":bucket/" not in arn:
        return None
    name = arn.split(":bucket/", 1)[1].strip()
    return name or None


def resolve_s3tables_table_bucket_from_aws_config_files(root: Path | None = None) -> str:
    """S3 Tables table-bucket name from ``.aws-config/`` only (ARN file, then last-bucket line)."""
    cfg = (root or repo_root()) / ".aws-config"
    arn_line = read_aws_config_first_line(cfg / "s3tables-table-bucket-arn.txt")
    if arn_line:
        parsed = parse_s3tables_table_bucket_name_from_arn(arn_line)
        if parsed:
            return parsed
    return read_aws_config_first_line(cfg / "bronze-s3tables-last-bucket-name.txt")


def resolve_s3tables_table_bucket_name(
    root: Path | None = None,
    *,
    cli_bucket: str = "",
) -> str:
    """Resolve S3 **table bucket** name for Snowflake Glue REST + S3 Tables.

    Precedence: ``cli_bucket`` → ``SNOWFLAKE_S3TABLES_BUCKET_NAME`` → parse
    ``.aws-config/s3tables-table-bucket-arn.txt`` →
    ``.aws-config/bronze-s3tables-last-bucket-name.txt`` → ``BRONZE_S3TABLES_BUCKET_NAME``.
    Prefer on-disk artifacts from ``s3tables-setup`` over bare ``.env`` so IAM and
    ``generate-lab-sql`` stay aligned.
    """
    b = (cli_bucket or "").strip()
    if b:
        return b
    v = (os.environ.get("SNOWFLAKE_S3TABLES_BUCKET_NAME") or "").strip()
    if v:
        return v
    from_files = resolve_s3tables_table_bucket_from_aws_config_files(root)
    if from_files:
        return from_files
    return (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip()


def glue_database_json_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / ".aws-config" / "glue-database.json"


# Written by bronze ``glue-setup`` / ``s3tables-setup`` / ``render-iam`` — removed after successful ``cleanup``.
_BRONZE_AWS_CONFIG_ARTIFACT_NAMES: tuple[str, ...] = (
    "glue-database.json",
    "bronze-warehouse-uri.txt",
    "s3tables-table-bucket-arn.txt",
    "bronze-s3tables-last-bucket-name.txt",
    "s3tables-list-table-buckets.json",
    "s3tables-create-table-bucket.json",
    "s3tables-tables-list.json",
    "bronze-glue-writer-policy.rendered.json",
)


def remove_bronze_aws_config_artifacts(root: Path | None = None) -> list[str]:
    """Delete repo-local bronze outputs under ``.aws-config/`` (not ``snowflake-*`` files).

    Returns paths removed (as strings) for logging.
    """
    cfg = (root or repo_root()) / ".aws-config"
    removed: list[str] = []
    for name in _BRONZE_AWS_CONFIG_ARTIFACT_NAMES:
        p = cfg / name
        if p.is_file():
            try:
                p.unlink()
                removed.append(str(p))
            except OSError:
                pass
    if cfg.is_dir():
        for extra in sorted(cfg.glob("s3tables-*.json")):
            if extra.name in _BRONZE_AWS_CONFIG_ARTIFACT_NAMES:
                continue
            if extra.is_file():
                try:
                    extra.unlink()
                    removed.append(str(extra))
                except OSError:
                    pass
    return removed


def apply_bronze_from_aws_config(root: Path | None = None) -> None:
    """Fill unset ``BRONZE_BUCKET_NAME`` / ``GLUE_DATABASE`` / ``BRONZE_S3TABLES_BUCKET_NAME`` from ``.aws-config/``.

    Written by ``bronze-cli glue-setup`` / ``s3tables-setup``. Explicit environment variables
    always win for the warehouse and Glue DB; for **S3 Tables**, on-disk ARN / last-bucket-name
    files backfill ``BRONZE_S3TABLES_BUCKET_NAME`` when unset so Snowflake/IAM match the last
    successful ``s3tables-setup``. Call before ``derive_bronze_resource_names()`` in tooling
    that needs stable names (e.g. ``snowflake-summary``, ``create-read-role``).
    """
    cfg = (root or repo_root()) / ".aws-config"
    uri_path = cfg / "bronze-warehouse-uri.txt"
    glue_path = cfg / "glue-database.json"

    need_bucket = not (os.environ.get("BRONZE_BUCKET_NAME") or "").strip()
    need_db = not (os.environ.get("GLUE_DATABASE") or "").strip()

    if need_bucket and uri_path.is_file():
        raw = uri_path.read_text(encoding="utf-8").strip()
        bucket = _s3_uri_bucket(raw)
        if bucket:
            os.environ["BRONZE_BUCKET_NAME"] = bucket
            need_bucket = False
            print(
                "info: BRONZE_BUCKET_NAME="
                f"{bucket!r} (from .aws-config/bronze-warehouse-uri.txt)"
            )

    glue_data: dict | None = None
    if (need_bucket or need_db) and glue_path.is_file():
        try:
            parsed = json.loads(glue_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: could not read {glue_path}: {e}", file=sys.stderr)
            parsed = None
        glue_data = parsed if isinstance(parsed, dict) else None

    if need_db and glue_data:
        name = (glue_data.get("Database") or {}).get("Name")
        if isinstance(name, str) and name.strip():
            os.environ["GLUE_DATABASE"] = name.strip()
            print(
                "info: GLUE_DATABASE="
                f"{os.environ['GLUE_DATABASE']!r} (from .aws-config/glue-database.json)"
            )

    if need_bucket and glue_data:
        loc = (glue_data.get("Database") or {}).get("LocationUri")
        if isinstance(loc, str) and loc.strip():
            bucket = _s3_uri_bucket(loc.strip())
            if bucket:
                os.environ["BRONZE_BUCKET_NAME"] = bucket
                print(
                    "info: BRONZE_BUCKET_NAME="
                    f"{bucket!r} (from .aws-config/glue-database.json LocationUri)"
                )

    if not (os.environ.get("BRONZE_S3TABLES_BUCKET_NAME") or "").strip():
        tb = resolve_s3tables_table_bucket_from_aws_config_files(root)
        if tb:
            os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = tb
            print(
                "info: BRONZE_S3TABLES_BUCKET_NAME="
                f"{tb!r} (from .aws-config/s3tables-table-bucket-arn.txt or "
                "bronze-s3tables-last-bucket-name.txt)"
            )


def apply_cleanup_context_from_aws_config(
    root: Path | None = None,
    *,
    skip_glue_database_from_file: bool = False,
    skip_s3tables_bucket_from_file: bool = False,
) -> dict[str, str]:
    """Overlay cleanup targets from the repo ``.aws-config/`` (not ``~/.aws-config``).

    Reads ``glue-database.json`` (``Database.Name``, ``Database.LocationUri``) and
    ``bronze-s3tables-last-bucket-name.txt`` (first non-empty line) when present so
    ``cleanup`` matches the last successful ``glue-setup`` / ``s3tables-setup`` in this
    clone (e.g. millis-suffixed S3 table bucket names).

    Skips ``glue-database.json`` fields when ``skip_glue_database_from_file`` is True
    (caller passed ``--glue-database``). Skips the last table-bucket file when
    ``skip_s3tables_bucket_from_file`` is True (caller passed ``--s3tables-bucket``).

    Returns a map of environment keys applied for logging; skips missing/invalid files.
    """
    cfg = (root or repo_root()) / ".aws-config"
    applied: dict[str, str] = {}
    glue_path = cfg / "glue-database.json"
    if glue_path.is_file() and not skip_glue_database_from_file:
        try:
            glue_data = json.loads(glue_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"warning: could not read {glue_path}: {e}", file=sys.stderr)
            glue_data = None
        if isinstance(glue_data, dict):
            db = glue_data.get("Database") or {}
            name = db.get("Name")
            if isinstance(name, str) and name.strip():
                v = name.strip()
                os.environ["GLUE_DATABASE"] = v
                applied["GLUE_DATABASE"] = v
            loc = db.get("LocationUri")
            if isinstance(loc, str) and loc.strip():
                bucket = _s3_uri_bucket(loc.strip())
                if bucket:
                    os.environ["BRONZE_BUCKET_NAME"] = bucket
                    applied["BRONZE_BUCKET_NAME"] = bucket
    last_tb = cfg / "bronze-s3tables-last-bucket-name.txt"
    if last_tb.is_file() and not skip_s3tables_bucket_from_file:
        try:
            text = last_tb.read_text(encoding="utf-8")
        except OSError as e:
            print(f"warning: could not read {last_tb}: {e}", file=sys.stderr)
            text = ""
        line = (text.strip().splitlines() or [""])[0].strip()
        if line:
            os.environ["BRONZE_S3TABLES_BUCKET_NAME"] = line
            applied["BRONZE_S3TABLES_BUCKET_NAME"] = line
    return applied


def assert_bronze_warehouse_bucket_exists(bucket: str) -> None:
    """Verify ``bucket`` exists via HeadBucket before PyIceberg writes metadata to S3."""
    import boto3
    from botocore.exceptions import ClientError

    session_kwargs: dict[str, str] = {}
    profile = os.environ.get("AWS_PROFILE", "").strip()
    if profile:
        session_kwargs["profile_name"] = profile
    region = os.environ.get("AWS_REGION", "").strip()
    if region:
        session_kwargs["region_name"] = region
    s3 = boto3.Session(**session_kwargs).client("s3")
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            print(
                "error: BRONZE_BUCKET_NAME="
                f"{bucket!r} does not exist (HeadBucket). Run `task bronze:glue-setup` "
                "to create it (and the Glue database), or create the bucket yourself. "
                f"Example: aws s3 mb s3://{bucket} --region \"$AWS_REGION\"",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
        if code == "403":
            print(
                "error: access denied calling HeadBucket on "
                f"BRONZE_BUCKET_NAME={bucket!r}. Check IAM and bucket ownership.",
                file=sys.stderr,
            )
            raise SystemExit(1) from None
        raise


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
