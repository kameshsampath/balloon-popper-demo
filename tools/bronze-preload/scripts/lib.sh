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
