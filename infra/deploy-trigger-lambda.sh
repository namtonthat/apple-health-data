#!/usr/bin/env bash
# deploy-trigger-lambda.sh — deploy the S3-event → GitHub Actions trigger Lambda.
#
# Deploys infra/lambda/trigger_refresh.py as the apple-health-refresh-trigger
# Lambda, wires an S3 event notification (landing/health/*.json on the
# dashboard bucket) to it, and stores the GitHub PAT it dispatches with in SSM
# Parameter Store. Idempotent: safe to re-run to push code/config changes.
#
# Prerequisites: AWS CLI credentials with IAM/Lambda/SSM/S3 access, and a
# fine-grained GitHub PAT (Actions: read and write on the repo). Run
# interactively to be prompted for the PAT (hidden input — preferred, keeps it
# out of shell history); for non-interactive runs export GITHUB_PAT first.
#
# Overridable env vars: GITHUB_PAT, GITHUB_OWNER, GITHUB_REPO.
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

FUNCTION_NAME="apple-health-refresh-trigger"
ROLE_NAME="apple-health-refresh-trigger-role"
SSM_PARAM_NAME="/apple-health-data/github-pat"
NOTIFICATION_ID="apple-health-export-trigger"
S3_STATEMENT_ID="s3-invoke-${NOTIFICATION_ID}"
GITHUB_OWNER="${GITHUB_OWNER:-namtonthat}"
GITHUB_REPO="${GITHUB_REPO:-apple-health-data}"
HANDLER_FILE="$ROOT/infra/lambda/trigger_refresh.py"

# --- 1. Read bucket/region from pyproject.toml [tool.dashboard] -------------
# Use the uv-managed interpreter (3.12): tomllib needs >= 3.11 and a bare
# python3 may be an older system Python (e.g. macOS CLT ships 3.9).
S3_BUCKET=$(cd "$ROOT" && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['dashboard']['s3_bucket_name'])")
AWS_REGION=$(cd "$ROOT" && uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['tool']['dashboard']['aws_region'])")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "==> Deploying $FUNCTION_NAME (bucket: $S3_BUCKET, region: $AWS_REGION)"
echo "    as $CALLER_ARN (account $ACCOUNT_ID)"

# Guard: the active credentials must belong to the account that owns the
# bucket, or every resource below would land in the wrong account.
if ! aws s3api head-bucket --bucket "$S3_BUCKET" \
  --expected-bucket-owner "$ACCOUNT_ID" --region "$AWS_REGION" >/dev/null 2>&1; then
  echo "error: account $ACCOUNT_ID does not own s3://$S3_BUCKET — wrong AWS credentials?" >&2
  exit 1
fi

[[ -f "$HANDLER_FILE" ]] || { echo "error: handler not found at $HANDLER_FILE" >&2; exit 1; }

# Private scratch space (mktemp -d => 700) for the PAT request JSON and the
# Lambda zip; removed on any exit.
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# --- 2. SSM parameter: GitHub PAT --------------------------------------------
if [[ -z "${GITHUB_PAT:-}" ]]; then
  if [[ ! -t 0 ]]; then
    echo "error: GITHUB_PAT not set and stdin is not a terminal (cannot prompt)" >&2
    exit 1
  fi
  read -rs -p "GitHub PAT (fine-grained, Actions read/write on ${GITHUB_OWNER}/${GITHUB_REPO}): " GITHUB_PAT
  echo
fi
[[ -n "$GITHUB_PAT" ]] || { echo "error: no PAT provided" >&2; exit 1; }
echo "==> Storing PAT in SSM parameter $SSM_PARAM_NAME"
# The PAT must stay out of the aws process's argv (readable via ps / shell
# history), but AWS CLI v2 cannot read file:///dev/stdin — its file:// loader
# returns an empty read for non-regular files. So write the request JSON to a
# 600-perm file in the private temp dir and delete it right after. Python
# builds the JSON (json.dumps escapes anything; .strip() drops pasted
# whitespace/CR) and the token travels via the environment, never argv.
PARAM_JSON_FILE="$TMP_DIR/ssm-param.json"
GITHUB_PAT="$GITHUB_PAT" SSM_PARAM_NAME="$SSM_PARAM_NAME" \
  PARAM_JSON_FILE="$PARAM_JSON_FILE" python3 <<'PY'
import json
import os

fd = os.open(os.environ["PARAM_JSON_FILE"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(
        {
            "Name": os.environ["SSM_PARAM_NAME"],
            "Type": "SecureString",
            "Value": os.environ["GITHUB_PAT"].strip(),
            "Overwrite": True,
        },
        f,
    )
PY
aws ssm put-parameter \
  --cli-input-json "file://$PARAM_JSON_FILE" \
  --region "$AWS_REGION" >/dev/null
rm -f "$PARAM_JSON_FILE"
unset GITHUB_PAT

# --- 3. IAM role --------------------------------------------------------------
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

SSM_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "ssm:GetParameter",
    "Resource": "arn:aws:ssm:${AWS_REGION}:${ACCOUNT_ID}:parameter${SSM_PARAM_NAME}"
  }]
}
EOF
)
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name read-github-pat \
  --policy-document "$SSM_POLICY"

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)

# --- 4. Package + create/update the function ---------------------------------
ZIP_FILE="$TMP_DIR/trigger_refresh.zip"
# Zip from inside the dir so the entry is flat (trigger_refresh.py at the root).
(cd "$(dirname "$HANDLER_FILE")" && zip -q "$ZIP_FILE" "$(basename "$HANDLER_FILE")")

LAMBDA_ENV="Variables={GITHUB_OWNER=${GITHUB_OWNER},GITHUB_REPO=${GITHUB_REPO},SSM_PARAM_NAME=${SSM_PARAM_NAME}}"

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
    --handler trigger_refresh.lambda_handler \
    --role "$ROLE_ARN" \
    --timeout 30 \
    --memory-size 128 \
    --environment "$LAMBDA_ENV" \
    --region "$AWS_REGION" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCTION_NAME" --region "$AWS_REGION"
else
  echo "==> Creating function $FUNCTION_NAME"
  # A freshly created role can take a few seconds to become assumable by
  # Lambda; retry create-function until propagation completes.
  [[ "$ROLE_CREATED" == 1 ]] && sleep 10
  created=0
  for attempt in 1 2 3 4 5 6 7 8; do
    if out=$(aws lambda create-function \
      --function-name "$FUNCTION_NAME" \
      --runtime python3.12 \
      --handler trigger_refresh.lambda_handler \
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

FUNCTION_ARN=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query Configuration.FunctionArn \
  --output text)

# --- 5. Allow S3 to invoke the function --------------------------------------
echo "==> Ensuring S3 invoke permission ($S3_STATEMENT_ID)"
# Remove any existing statement first: add-permission tolerates a duplicate
# statement-id but never updates it, so re-runs would otherwise keep a stale
# condition (e.g. one missing SourceAccount).
aws lambda remove-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$S3_STATEMENT_ID" \
  --region "$AWS_REGION" >/dev/null 2>&1 || true
# --source-account pins the invoker to this account's bucket: bucket ARNs
# carry no account ID, so without it a same-named bucket created in another
# account (after this one is deleted) could invoke the function.
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$S3_STATEMENT_ID" \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${S3_BUCKET}" \
  --source-account "$ACCOUNT_ID" \
  --region "$AWS_REGION" >/dev/null
echo "  permission set"

# --- 6. Bucket notification (read-modify-write) -------------------------------
echo "==> Merging S3 event notification ($NOTIFICATION_ID) into bucket config"
EXISTING_CONFIG=$(aws s3api get-bucket-notification-configuration \
  --bucket "$S3_BUCKET" \
  --region "$AWS_REGION")
MERGED_CONFIG=$(EXISTING_CONFIG="$EXISTING_CONFIG" LAMBDA_ARN="$FUNCTION_ARN" \
  NOTIFICATION_ID="$NOTIFICATION_ID" python3 <<'PY'
import json
import os

# Keep every existing notification (other lambda configs, queue/topic configs,
# EventBridgeConfiguration); replace only our entry, matched by Id.
config = json.loads(os.environ["EXISTING_CONFIG"] or "{}")
entry = {
    "Id": os.environ["NOTIFICATION_ID"],
    "LambdaFunctionArn": os.environ["LAMBDA_ARN"],
    "Events": ["s3:ObjectCreated:*"],
    "Filter": {
        "Key": {
            "FilterRules": [
                {"Name": "prefix", "Value": "landing/health/"},
                {"Name": "suffix", "Value": ".json"},
            ]
        }
    },
}
lambda_configs = [
    c
    for c in config.get("LambdaFunctionConfigurations", [])
    if c.get("Id") != entry["Id"]
]
lambda_configs.append(entry)
config["LambdaFunctionConfigurations"] = lambda_configs
print(json.dumps(config))
PY
)
# S3 validates at put time that it may invoke the Lambda, and the resource
# policy added above is eventually consistent — retry the transient
# "Unable to validate the following destination configurations" error.
put_ok=0
for attempt in 1 2 3 4 5 6 7 8; do
  if out=$(aws s3api put-bucket-notification-configuration \
    --bucket "$S3_BUCKET" \
    --notification-configuration "$MERGED_CONFIG" \
    --region "$AWS_REGION" 2>&1); then
    put_ok=1
    break
  fi
  if [[ "$out" == *"Unable to validate the following destination configurations"* ]]; then
    echo "  invoke permission not yet propagated; retrying ($attempt/8)..."
    sleep 5
  else
    echo "$out" >&2
    exit 1
  fi
done
if [[ "$put_ok" != 1 ]]; then
  echo "error: put-bucket-notification-configuration failed after retries: $out" >&2
  exit 1
fi

# --- Summary -------------------------------------------------------------------
cat <<EOF

Done.
  Function:     $FUNCTION_ARN
  Role:         $ROLE_ARN
  SSM param:    $SSM_PARAM_NAME
  Trigger:      s3://${S3_BUCKET}/landing/health/*.json (s3:ObjectCreated:*)
  Dispatches:   ${GITHUB_OWNER}/${GITHUB_REPO} .github/workflows/refresh-data.yml (ref: main)

Smoke test:
  echo '{}' > /tmp/trigger-test.json
  aws s3 cp /tmp/trigger-test.json s3://${S3_BUCKET}/landing/health/trigger-test.json
  gh run list --workflow refresh-data.yml --limit 3   # a new run should appear
  aws s3 rm s3://${S3_BUCKET}/landing/health/trigger-test.json
EOF
