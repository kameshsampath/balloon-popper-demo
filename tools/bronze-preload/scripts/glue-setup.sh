#!/usr/bin/env bash
# Create Glue database for classic Iceberg metadata (PyIceberg + Glue catalog path).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_aws_profile
REGION="$(require_region)"
REPO_ROOT="$(repo_root)"
export REPO_ROOT
ensure_aws_config_dir

GLUE_DATABASE="${GLUE_DATABASE:-balloon_pops}"
WAREHOUSE="${BRONZE_WAREHOUSE:?Set BRONZE_WAREHOUSE to s3://bucket/prefix/ for Iceberg files}"

if aws glue get-database --profile "${AWS_PROFILE}" --region "${REGION}" --name "${GLUE_DATABASE}" &>/dev/null; then
  echo "Glue database '${GLUE_DATABASE}' already exists"
else
  echo "Creating Glue database '${GLUE_DATABASE}' (LocationUri=${WAREHOUSE})"
  aws glue create-database \
    --profile "${AWS_PROFILE}" \
    --region "${REGION}" \
    --database-input "{\"Name\":\"${GLUE_DATABASE}\",\"Description\":\"Balloon bronze Iceberg\",\"LocationUri\":\"${WAREHOUSE}\"}"
fi

aws glue get-database \
  --profile "${AWS_PROFILE}" \
  --region "${REGION}" \
  --name "${GLUE_DATABASE}" \
  --output json > "${REPO_ROOT}/.aws-config/glue-database.json"
echo "Wrote ${REPO_ROOT}/.aws-config/glue-database.json"
