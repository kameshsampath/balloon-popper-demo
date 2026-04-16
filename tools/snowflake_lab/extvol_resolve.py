# Copyright 2024-Present Kamesh Sampath
# Licensed under the Apache License, Version 2.0
"""Resolve silver extvol --bucket / --prefix for ``task dt:extvol-*`` (shell-friendly).

Emits **two lines** to stdout (no extra logging):

1. Short S3 **bucket slug** for ``sfutils-extvolumes`` ``--bucket`` (never empty on success). This is the same
   *kind* of fragment upstream labels a “bucket base name”; the CLI then prefixes it (OS username or ``--prefix``).
2. Optional **global** CLI tokens placed **before** the subcommand (typically ``--prefix <lab_bucket_slug>`` —
   ``sfutils-extvolumes`` defines ``--prefix`` on the top-level group, not on ``create``). Empty line when the caller
   should rely on sfutils defaults (OS username prefix).

Rules:

- ``SILVER_EXTVOLUME_BUCKET_SLUG`` set → line 1 is that value; line 2 empty (caller uses sfutils default prefix unless
  the user passes global flags manually).
- Else ``LAB_USERNAME`` set → line 1 is ``balloon-silver``; line 2 is
  ``--prefix <slug>`` where ``<slug>`` is ``SILVER_EXTVOLUME_PREFIX`` if set, otherwise
  ``sanitize_lab_slug_bucket(LAB_USERNAME)`` (same 24-char workshop slug as bronze buckets).
- Else: stderr message and exit 1.
"""

from __future__ import annotations

import os
import sys

from tools.bronze_preload.bronze_aws import sanitize_lab_slug_bucket


def main() -> None:
    explicit = (os.environ.get("SILVER_EXTVOLUME_BUCKET_SLUG") or "").strip()
    lab = (os.environ.get("LAB_USERNAME") or "").strip()
    if explicit:
        print(explicit)
        print()
        return
    if lab:
        slug = sanitize_lab_slug_bucket(lab)
        if not slug:
            print(
                "error: LAB_USERNAME must yield a non-empty bucket slug "
                "(same rules as bronze workshop id)",
                file=sys.stderr,
            )
            raise SystemExit(1)
        override = (os.environ.get("SILVER_EXTVOLUME_PREFIX") or "").strip()
        prefix_value = override if override else slug
        print("balloon-silver")
        print(f"--prefix {prefix_value}")
        return
    print(
        "error: set SILVER_EXTVOLUME_BUCKET_SLUG or LAB_USERNAME "
        "(workshop: omit SLUG for default --bucket balloon-silver + lab --prefix)",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
