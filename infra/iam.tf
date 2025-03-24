data "aws_caller_identity" "current" {}

resource "aws_iam_role" "lambda_ingest_role" {
  name = "lambda_ingest_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "lambda_dbt_role" {
  name = "lambda_dbt_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# IAM Policy Attachments for Lambda Functions
resource "aws_iam_role_policy_attachment" "lambda_ingest_basic_execution" {
  role       = aws_iam_role.lambda_ingest_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_ingest_s3_policy" {
  name        = "lambda_ingest_s3_policy"
  description = "Allow ingest lambda to put objects in S3 under landing/health"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["s3:PutObject"],
      Resource = "${aws_s3_bucket.health_data_bucket.arn}/landing/health/*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_ingest_s3_attach" {
  role       = aws_iam_role.lambda_ingest_role.name
  policy_arn = aws_iam_policy.lambda_ingest_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_dbt_basic_execution" {
  role       = aws_iam_role.lambda_dbt_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


## Github Actions
resource "aws_iam_user" "github_actions" {
  name = "github_actions"
}

data "aws_iam_policy_document" "github_actions_policy" {
  statement {
    sid = "S3ReadAccess"
    actions = [
      "s3:*",
      "s3-object-lambda:*"
    ]
    resources = [
      aws_s3_bucket.health_data_bucket.arn,
      "${aws_s3_bucket.health_data_bucket.arn}/*",
    ]
  }

  statement {
    sid = "ECRAccess"
    actions = [
      "ecr:*"
    ]
    resources = [
      aws_ecr_repository.dbt_repo.arn,
      aws_ecr_repository.ingest_repo.arn
    ]
  }
  statement {
    sid = "IAMReadAccess"
    actions = [
      "iam:GetRole",
      "iam:GetUser",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListRolePolicies",
      "iam:ListAccessKeys",
      "iam:ListAttachedRolePolicies",
      "iam:ListAttachedUserPolicies",
    ]
    resources = [
      aws_iam_user.github_actions.arn,
      aws_iam_user.streamlit.arn,
      aws_iam_role.lambda_ingest_role.arn,
      aws_iam_role.lambda_dbt_role.arn,
      aws_iam_policy.lambda_ingest_s3_policy.arn,
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.github_actions_policy_name}",
    ]
  }
  statement {
    sid = "LambdaAccess"
    actions = [
      "lambda:*"
    ]
    resources = [
      "arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:*"
    ]
  }
}

resource "aws_iam_policy" "github_actions_policy" {
  name        = var.github_actions_policy_name
  description = "Policy for github_actions to access S3 and ECR resources"
  policy      = data.aws_iam_policy_document.github_actions_policy.json
}

resource "aws_iam_user_policy_attachment" "github_actions_attach" {
  user       = aws_iam_user.github_actions.name
  policy_arn = aws_iam_policy.github_actions_policy.arn
}

resource "aws_iam_access_key" "github_actions_key" {
  user = aws_iam_user.github_actions.name
}

resource "aws_iam_user" "streamlit" {
  name = "streamlit"
}

resource "aws_iam_access_key" "streamlit" {
  user = aws_iam_user.streamlit.name
}

resource "aws_iam_user_policy" "streamlit_policy" {
  name = "streamlit_policy"
  user = aws_iam_user.streamlit.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3GetObject",
        Effect = "Allow",
        Action = "s3:GetObject",
        Resource = [
          "${aws_s3_bucket.health_data_bucket.arn}/*"
        ]
      }
    ]
  })
}

