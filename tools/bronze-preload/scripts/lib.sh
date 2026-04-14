#!/usr/bin/env bash
# Shared helpers for bronze AWS scripts. Source with: source "$(dirname "$0")/lib.sh"
set -euo pipefail

require_aws_profile() {
  if [[ -z "${AWS_PROFILE:-}" ]]; then
    echo "error: set AWS_PROFILE to a real AWS credential profile" >&2
    exit 1
  fi
}

aws_region() {
  if [[ -n "${AWS_REGION:-}" ]]; then
    echo "$AWS_REGION"
    return
  fi
  aws configure get region --profile "${AWS_PROFILE}" 2>/dev/null || true
}

require_region() {
  local r
  r="$(aws_region)"
  if [[ -z "$r" ]]; then
    echo "error: set AWS_REGION or configure region for AWS_PROFILE=${AWS_PROFILE}" >&2
    exit 1
  fi
  echo "$r"
}

ensure_aws_config_dir() {
  mkdir -p "${REPO_ROOT:-.}/.aws-config"
}

repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
  echo "$here"
}

# For Glue database / Iceberg namespace parts: [a-z0-9_], max 20 chars.
sanitize_lab_slug_glue() {
  local u="${LAB_USERNAME:-}"
  u=$(echo "$u" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_' | sed 's/__*/_/g' | sed 's/^_\|_$//g')
  if [[ ${#u} -gt 20 ]]; then
    u="${u:0:20}"
  fi
  echo "$u"
}

# S3 table bucket names: [0-9a-z-]{3,63} — hyphens only (no underscores).
sanitize_lab_slug_bucket() {
  local u="${LAB_USERNAME:-}"
  u=$(echo "$u" | tr '[:upper:]' '[:lower:]' | tr '_' '-' | tr -c 'a-z0-9-' '-' | sed 's/--*/-/g' | sed 's/^-\|-$//g')
  if [[ ${#u} -gt 24 ]]; then
    u="${u:0:24}"
  fi
  echo "$u"
}

# sfutils-extvolumes --prefix: letters and digits only (conservative).
sanitize_lab_prefix_sfutils() {
  local u="${LAB_USERNAME:-}"
  u=$(echo "$u" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9' | cut -c1-20)
  echo "$u"
}

# When LAB_USERNAME is set, default unique names for shared-account workshops.
# Override any time by exporting GLUE_DATABASE / BRONZE_S3TABLES_BUCKET_NAME yourself.
derive_bronze_resource_names() {
  if [[ -z "${LAB_USERNAME:-}" ]]; then
    return 0
  fi
  local gslug bslug
  gslug="$(sanitize_lab_slug_glue)"
  bslug="$(sanitize_lab_slug_bucket)"
  if [[ -z "$gslug" ]]; then
    echo "error: LAB_USERNAME must yield a non-empty slug (use letters, numbers, underscore, hyphen)" >&2
    exit 1
  fi
  if [[ -z "$bslug" ]]; then
    echo "error: LAB_USERNAME must yield a valid S3 table bucket slug (letters, numbers, hyphen)" >&2
    exit 1
  fi
  if [[ -z "${GLUE_DATABASE:-}" ]]; then
    export GLUE_DATABASE="${gslug}_balloon_pops"
    echo "info: GLUE_DATABASE=${GLUE_DATABASE} (default from LAB_USERNAME)"
  fi
  if [[ -z "${BRONZE_S3TABLES_BUCKET_NAME:-}" ]]; then
    export BRONZE_S3TABLES_BUCKET_NAME="${bslug}-balloon-s3tables"
    echo "info: BRONZE_S3TABLES_BUCKET_NAME=${BRONZE_S3TABLES_BUCKET_NAME} (default from LAB_USERNAME)"
  fi
}
