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
  description = "Allow ingest lambda to put objects in S3 under landing/"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["s3:PutObject"],
      Resource = "${aws_s3_bucket.health_data_bucket.arn}/landing/*"
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




