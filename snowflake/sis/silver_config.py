# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Silver database/schema for SiS queries.

Reads ``SILVER_DB`` and ``SILVER_SCHEMA`` from the ``env`` block in **snowflake.yml**
(staged next to this file). Optional runtime overrides: ``os.environ["SILVER_DB"]`` /
``os.environ["SILVER_SCHEMA"]`` (if your account injects them).

Keep the ``env`` keys in **snowflake.yml** aligned with lab defaults from
``task dt:generate-sql`` / ``SNOWFLAKE_SILVER_*``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DEFAULT_DB = "balloon_silver"
_DEFAULT_SCHEMA = "silver"


def _parse_env_block(yaml_text: str) -> dict[str, str]:
    """Parse a minimal top-level ``env:`` mapping (no PyYAML dependency)."""
    out: dict[str, str] = {}
    lines = yaml_text.splitlines()
    in_env = False
    for line in lines:
        raw = line.split("#", 1)[0]
        stripped = raw.strip()
        if not in_env:
            if stripped == "env:":
                in_env = True
            continue
        # End env block at next top-level key (no leading whitespace)
        if stripped and not (raw.startswith(" ") or raw.startswith("\t")):
            break
        m = re.match(r"^[\s\t]+([A-Za-z_][A-Za-z0-9_]*):\s*(.+?)\s*$", raw.rstrip())
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[key] = val
    return out


def _from_snowflake_yml() -> tuple[str, str]:
    path = _ROOT / "snowflake.yml"
    if not path.is_file():
        return (_DEFAULT_DB, _DEFAULT_SCHEMA)
    env = _parse_env_block(path.read_text(encoding="utf-8"))
    return (
        env.get("SILVER_DB", _DEFAULT_DB),
        env.get("SILVER_SCHEMA", _DEFAULT_SCHEMA),
    )


def silver_ids() -> tuple[str, str]:
    """Return (database, schema) for Dynamic Iceberg Table FQNs."""
    db, sch = _from_snowflake_yml()
    return (
        os.environ.get("SILVER_DB", db).strip(),
        os.environ.get("SILVER_SCHEMA", sch).strip(),
    )


def fq_table(table: str) -> str:
    db, sch = silver_ids()
    return f'"{db}"."{sch}".{table}'
