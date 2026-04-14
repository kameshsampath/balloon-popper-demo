#!/usr/bin/env python3
# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Verify common lab CLIs are on PATH (Windows, Linux, macOS). Stdlib only."""
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

# Only if you still run legacy k3d / generator tasks from the root Taskfile.
LEGACY_OPTIONAL: tuple[ToolSpec, ...] = (
    ToolSpec(
        "git",
        ["git", "--version"],
        "https://git-scm.com/downloads",
        note="Version control.",
    ),
    ToolSpec(
        "docker",
        ["docker", "--version"],
        "https://docs.docker.com/get-docker/",
        note="Legacy k3d / generator tasks in this Taskfile.",
    ),
    ToolSpec(
        "kubectl",
        ["kubectl", "version", "--client=true"],
        "https://kubernetes.io/docs/tasks/tools/",
        note="Legacy generator / Kafka tasks.",
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

    print("\nOptional (legacy stack only):\n")
    for spec in LEGACY_OPTIONAL:
        _check_one(spec, optional=True)

    print()
    if ok:
        print("All required tools are available.")
        return 0
    print("Install missing tools and re-run: task check-tools", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
