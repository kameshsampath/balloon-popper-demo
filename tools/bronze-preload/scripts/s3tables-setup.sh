#!/usr/bin/env bash
# Provision Amazon S3 Tables: table bucket, namespace balloon_pops, five ICEBERG tables (names align with legacy sinks).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

require_aws_profile
REGION="$(require_region)"
REPO_ROOT="$(repo_root)"
export REPO_ROOT
ensure_aws_config_dir

derive_bronze_resource_names

if ! aws s3tables help &>/dev/null; then
  echo "error: AWS CLI does not support 's3tables' commands. Upgrade to AWS CLI v2.34+ (https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)." >&2
  exit 1
fi

TB_NAME="${BRONZE_S3TABLES_BUCKET_NAME:?Set BRONZE_S3TABLES_BUCKET_NAME (3-63 chars, [0-9a-z-])}"
NS="${S3TABLES_NAMESPACE:-balloon_pops}"

LIST_JSON="${REPO_ROOT}/.aws-config/s3tables-list-table-buckets.json"
aws s3tables list-table-buckets --profile "${AWS_PROFILE}" --region "${REGION}" --no-paginate --output json > "${LIST_JSON}"

TABLE_BUCKET_ARN="$(
  python3 -c "
import json, sys
name = sys.argv[1]
data = json.load(open(sys.argv[2]))
for b in data.get('tableBuckets', []):
    if b.get('name') == name:
        print(b['arn'])
        sys.exit(0)
sys.exit(2)
" "${TB_NAME}" "${LIST_JSON}"
)" || TABLE_BUCKET_ARN=""

OUT_JSON="${REPO_ROOT}/.aws-config/s3tables-create-table-bucket.json"
if [[ -n "${TABLE_BUCKET_ARN}" ]]; then
  echo "Table bucket '${TB_NAME}' already exists: ${TABLE_BUCKET_ARN}"
  aws s3tables get-table-bucket \
    --table-bucket-arn "${TABLE_BUCKET_ARN}" \
    --profile "${AWS_PROFILE}" \
    --region "${REGION}" \
    --output json > "${OUT_JSON}"
else
  echo "Creating S3 table bucket '${TB_NAME}' in ${REGION}..."
  aws s3tables create-table-bucket \
    --name "${TB_NAME}" \
    --profile "${AWS_PROFILE}" \
    --region "${REGION}" \
    --encryption-configuration "sseAlgorithm=AES256" \
    --output json | tee "${OUT_JSON}"
  TABLE_BUCKET_ARN="$(python3 -c "import json; print(json.load(open('${OUT_JSON}'))['arn'])")"
fi

echo "${TABLE_BUCKET_ARN}" > "${REPO_ROOT}/.aws-config/s3tables-table-bucket-arn.txt"
echo "Table bucket ARN -> .aws-config/s3tables-table-bucket-arn.txt"

echo "Creating namespace '${NS}' if missing..."
set +e
aws s3tables create-namespace \
  --table-bucket-arn "${TABLE_BUCKET_ARN}" \
  --namespace "${NS}" \
  --profile "${AWS_PROFILE}" \
  --region "${REGION}" 2>/dev/null
NS_RC=$?
set -e
if [[ "$NS_RC" -ne 0 ]]; then
  echo "(namespace may already exist; continuing)"
fi

TABLES=(leaderboard balloon_color_stats realtime_scores balloon_colored_pops color_performance_trends)
for t in "${TABLES[@]}"; do
  echo "Ensuring ICEBERG table ${NS}.${t} ..."
  set +e
  aws s3tables create-table \
    --table-bucket-arn "${TABLE_BUCKET_ARN}" \
    --namespace "${NS}" \
    --name "${t}" \
    --format ICEBERG \
    --profile "${AWS_PROFILE}" \
    --region "${REGION}" 2>/dev/null
  CT_RC=$?
  set -e
  if [[ "$CT_RC" -ne 0 ]]; then
    echo "  (table may already exist)"
  fi
done

aws s3tables list-tables \
  --table-bucket-arn "${TABLE_BUCKET_ARN}" \
  --namespace "${NS}" \
  --profile "${AWS_PROFILE}" \
  --region "${REGION}" \
  --output json > "${REPO_ROOT}/.aws-config/s3tables-tables-list.json"
echo "Wrote ${REPO_ROOT}/.aws-config/s3tables-tables-list.json"
