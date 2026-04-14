#!/usr/bin/env bash
# Render lab/aws/*.json templates into .aws-config/ using envsubst.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_aws_profile
REGION="$(require_region)"
export AWS_REGION="${REGION}"
export GLUE_DATABASE="${GLUE_DATABASE:-balloon_pops}"

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
  export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --profile "${AWS_PROFILE}" --query Account --output text)"
fi

if [[ -z "${BRONZE_S3_ARN:-}" ]]; then
  echo "error: set BRONZE_S3_ARN (e.g. arn:aws:s3:::your-warehouse-bucket) for policy rendering" >&2
  exit 1
fi

REPO_ROOT="$(repo_root)"
export REPO_ROOT
ensure_aws_config_dir

if ! command -v envsubst &>/dev/null; then
  echo "error: envsubst not found (install gettext)" >&2
  exit 1
fi

envsubst < "${REPO_ROOT}/lab/aws/bronze-glue-writer-policy.json" > "${REPO_ROOT}/.aws-config/bronze-glue-writer-policy.rendered.json"
echo "Wrote ${REPO_ROOT}/.aws-config/bronze-glue-writer-policy.rendered.json"
