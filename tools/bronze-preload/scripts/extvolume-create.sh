#!/usr/bin/env bash
# Run sfutils-extvolumes create; pass --prefix from LAB_USERNAME when set.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_aws_profile
export AWS_REGION="$(require_region)"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

BUCKET="${BRONZE_EXTVOLUME_BUCKET:-balloon-bronze-warehouse}"
CMD=(uv run sfutils-extvolumes)

if [[ -n "${LAB_USERNAME:-}" ]]; then
  p="$(sanitize_lab_prefix_sfutils)"
  if [[ -z "$p" ]]; then
    echo "error: LAB_USERNAME must contain at least one letter or digit for --prefix" >&2
    exit 1
  fi
  CMD+=(--prefix "$p")
fi

CMD+=(create --bucket "$BUCKET")
if [[ "$DRY_RUN" -eq 1 ]]; then
  CMD+=(--dry-run)
fi

exec "${CMD[@]}"
