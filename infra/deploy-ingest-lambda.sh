#!/usr/bin/env bash
# deploy-ingest-lambda.sh — deploy the phone-upload receiver Lambda + Function URL.
#
# Deploys infra/lambda/ingest_health_data.py as the apple-health-ingest Lambda
# behind a public Function URL. Health Auto Export POSTs the export JSON to
# that URL; the handler writes it to s3://<bucket>/landing/health/, which in
# turn fires the refresh trigger Lambda. Idempotent: safe to re-run.
#
# Auth: requests must carry a shared token (?token=... or x-api-key header).
# A token is generated on first deploy and kept on re-runs; set ROTATE_TOKEN=1
# to mint a new one. The script prints the full URL to paste into the app.
#
# Prerequisites: personal-account AWS credentials in the repo's .env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export AWS_PAGER=""

# Use the personal-account credentials from the repo's .env (the same ones the
# pipeline uses) — never an ambient shell profile, which may point at a work
# account. The head-bucket ownership guard below backstops this.
unset AWS_PROFILE AWS_DEFAULT_PROFILE
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

FUNCTION_NAME="apple-health-ingest"
ROLE_NAME="apple-health-ingest-role"
HANDLER_FILE="$ROOT/infra/lambda/ingest_health_data.py"

S3_BUCKET=$(cd "$ROOT" && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['dashboard']['s3_bucket_name'])")
AWS_REGION=$(cd "$ROOT" && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['dashboard']['aws_region'])")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "==> Deploying $FUNCTION_NAME (bucket: $S3_BUCKET, region: $AWS_REGION)"
echo "    as $CALLER_ARN (account $ACCOUNT_ID)"

if ! aws s3api head-bucket --bucket "$S3_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "error: account $ACCOUNT_ID does not own s3://$S3_BUCKET — wrong AWS credentials?" >&2
  exit 1
fi

[[ -f "$HANDLER_FILE" ]] || { echo "error: handler not found at $HANDLER_FILE" >&2; exit 1; }

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# --- Shared token: keep the existing one unless rotating -----------------
EXISTING_TOKEN=$(aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query "Environment.Variables.INGEST_TOKEN" \
  --output text 2>/dev/null || true)
if [[ -n "$EXISTING_TOKEN" && "$EXISTING_TOKEN" != "None" && "${ROTATE_TOKEN:-0}" != 1 ]]; then
  INGEST_TOKEN="$EXISTING_TOKEN"
  echo "==> Reusing existing ingest token (ROTATE_TOKEN=1 to mint a new one)"
else
  INGEST_TOKEN=$(openssl rand -hex 24)
  echo "==> Generated new ingest token"
fi

# --- IAM role -------------------------------------------------------------
echo "==> Ensuring IAM role $ROLE_NAME"
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'
ROLE_CREATED=0
if out=$(aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" 2>&1); then
  ROLE_CREATED=1
  echo "  created role"
elif [[ "$out" == *EntityAlreadyExists* ]]; then
  echo "  role already exists"
else
  echo "$out" >&2
  exit 1
fi

aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

WRITE_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::${S3_BUCKET}/landing/health/*"
  }]
}
EOF
)
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name write-health-exports \
  --policy-document "$WRITE_POLICY"

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)

# --- Package + create/update the function ---------------------------------
ZIP_FILE="$TMP_DIR/ingest_health_data.zip"
(cd "$(dirname "$HANDLER_FILE")" && zip -q "$ZIP_FILE" "$(basename "$HANDLER_FILE")")

LAMBDA_ENV="Variables={S3_BUCKET=${S3_BUCKET},INGEST_TOKEN=${INGEST_TOKEN}}"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "==> Updating existing function $FUNCTION_NAME"
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.12 \
    --handler ingest_health_data.lambda_handler \
    --role "$ROLE_ARN" \
    --timeout 30 \
    --memory-size 128 \
    --environment "$LAMBDA_ENV" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
else
  echo "==> Creating function $FUNCTION_NAME"
  [[ "$ROLE_CREATED" == 1 ]] && sleep 10
  created=0
  for attempt in 1 2 3 4 5 6 7 8; do
    if out=$(aws lambda create-function \
      --function-name "$FUNCTION_NAME" \
      --runtime python3.12 \
      --handler ingest_health_data.lambda_handler \
      --role "$ROLE_ARN" \
      --zip-file "fileb://$ZIP_FILE" \
      --timeout 30 \
      --memory-size 128 \
      --environment "$LAMBDA_ENV" \
      --region "$AWS_REGION" 2>&1); then
      created=1
      break
    fi
    if [[ "$out" == *"cannot be assumed"* || "$out" == *InvalidParameterValueException* ]]; then
      echo "  role not yet propagated; retrying ($attempt/8)..."
      sleep 5
    else
      echo "$out" >&2
      exit 1
    fi
  done
  if [[ "$created" != 1 ]]; then
    echo "error: create-function failed after retries: $out" >&2
    exit 1
  fi
  aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
fi

# --- Function URL ----------------------------------------------------------
echo "==> Ensuring Function URL"
if ! FUNCTION_URL=$(aws lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query FunctionUrl --output text 2>/dev/null); then
  FUNCTION_URL=$(aws lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --region "$AWS_REGION" \
    --query FunctionUrl --output text)
fi
# Public URLs with AuthType NONE need an explicit InvokeFunctionUrl grant.
aws lambda remove-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id public-function-url \
  --region "$AWS_REGION" >/dev/null 2>&1 || true
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id public-function-url \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE \
  --region "$AWS_REGION" >/dev/null

# --- Summary ---------------------------------------------------------------
cat <<EOF

Done.
  Function:  $FUNCTION_NAME
  Writes to: s3://${S3_BUCKET}/landing/health/

Health Auto Export → Automations → API Export URL (POST, JSON):
  ${FUNCTION_URL}?token=${INGEST_TOKEN}

Smoke test:
  curl -sS -X POST "${FUNCTION_URL}?token=${INGEST_TOKEN}" \\
    -H 'Content-Type: application/json' -d '{"data": {"metrics": []}}'
EOF
