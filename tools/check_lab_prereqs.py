#!/usr/bin/env python3
# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Verify common lab CLIs are on PATH and AWS credentials work (STS). Stdlib only."""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    binary: str
    version_cmd: list[str] | None
    doc_url: str
    note: str = ""


# Order: required for upcoming Snowflake + bronze lab flows.
TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "aws",
        ["aws", "--version"],
        "https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
    ),
    ToolSpec(
        "snow",
        ["snow", "--version"],
        "https://docs.snowflake.com/developer-guide/snowflake-cli/installation/installation",
        note="Provided by this repo's venv (snowflake-cli); run `uv sync` and use direnv or activate .venv.",
    ),
    ToolSpec(
        "task",
        ["task", "--version"],
        "https://taskfile.dev/installation/",
        note="Taskfile runner (this check is started via task).",
    ),
    ToolSpec(
        "envsubst",
        None,
        "https://www.gnu.org/software/gettext/manual/gettext.html#envsubst-invocation",
        note="gettext; optional if you only use Python render-iam, still useful for shell snippets.",
    ),
    ToolSpec(
        "jq",
        ["jq", "--version"],
        "https://jqlang.github.io/jq/download/",
    ),
    ToolSpec(
        "cortex",
        ["cortex", "--version"],
        "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli",
        note="Snowflake Cortex Code CLI.",
    ),
    ToolSpec(
        "uv",
        ["uv", "--version"],
        "https://docs.astral.sh/uv/getting-started/installation/",
        note="Python package runner used by this repo.",
    ),
)

# Strongly suggested for this repo’s .envrc / downloads / TLS; does not fail check-tools.
RECOMMENDED: tuple[ToolSpec, ...] = (
    ToolSpec(
        "direnv",
        ["direnv", "version"],
        "https://direnv.net/docs/installation.html",
        note="Auto-loads .env / .envrc when you cd into the repo.",
    ),
    ToolSpec(
        "curl",
        ["curl", "--version"],
        "https://curl.se/download.html",
        note="Install scripts, health checks, and copy-paste flows from docs.",
    ),
    ToolSpec(
        "openssl",
        ["openssl", "version"],
        "https://wiki.openssl.org/index.php/Binaries",
        note="TLS clients and common crypto one-liners.",
    ),
)

OPTIONAL: tuple[ToolSpec, ...] = (
    ToolSpec(
        "git",
        ["git", "--version"],
        "https://git-scm.com/downloads",
        note="Version control.",
    ),
)


def _run_version(cmd: list[str]) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"(could not run: {e})"
    line = (r.stdout or r.stderr or "").strip().splitlines()
    return line[0][:100] if line else f"(exit {r.returncode})"


def _check_one(spec: ToolSpec, *, optional: bool) -> bool:
    path = shutil.which(spec.binary)
    if not path:
        tag = "WARN" if optional else "MISS"
        print(f"{tag}  {spec.binary:12} not on PATH")
        print(f"      → {spec.doc_url}")
        if spec.note:
            print(f"      {spec.note}")
        return optional
    ver = ""
    if spec.version_cmd:
        ver = _run_version(spec.version_cmd)
    else:
        ver = f"(found: {path})"
    print(f"ok   {spec.binary:12} {path}")
    if ver:
        print(f"      {ver}")
    return True


def _check_aws_sts_caller_identity() -> bool:
    """Run ``aws sts get-caller-identity`` when the AWS CLI is on PATH (valid session / profile)."""
    if not shutil.which("aws"):
        return True
    print("\nAWS credentials (required for bronze / IAM tasks):\n")
    try:
        r = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"MISS  aws sts get-caller-identity  (could not run: {e})")
        print("      → https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html")
        return False
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "").strip()
        print("MISS  aws sts get-caller-identity  (invalid or expired credentials / no profile)")
        for line in err.splitlines()[:8]:
            if line.strip():
                print(f"      {line}")
        print(
            "      → Set AWS_PROFILE to a configured profile (see .env.example), or run "
            "`aws configure login` / refresh SSO, then re-run: task check-tools"
        )
        print(
            "      → https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
        )
        return False
    out = (r.stdout or "").strip()
    print("ok   aws sts get-caller-identity")
    for line in out.splitlines()[:12]:
        if line.strip():
            print(f"      {line}")
    return True


def main() -> int:
    if sys.version_info < (3, 12):
        print(
            f"WARN  Python {sys.version_info.major}.{sys.version_info.minor} "
            f"(repo expects >= 3.12 per pyproject.toml)",
            file=sys.stderr,
        )

    print("Required tools:\n")
    ok = True
    for spec in TOOLS:
        if not _check_one(spec, optional=False):
            ok = False

    print("\nRecommended (lab comfort; install if WARN):\n")
    for spec in RECOMMENDED:
        _check_one(spec, optional=True)

    print("\nOptional:\n")
    for spec in OPTIONAL:
        _check_one(spec, optional=True)

    if shutil.which("aws") and not _check_aws_sts_caller_identity():
        ok = False

    print()
    if ok:
        print("All required tools are available.")
        return 0
    print("Install missing tools and re-run: task check-tools", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
