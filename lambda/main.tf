provider "aws" {
  region = var.aws_region
}

#############################
# S3 Bucket for Raw Data
#############################
resource "aws_s3_bucket" "health_data_bucket" {
  bucket = var.aws_s3_bucket
}

# Versioning and ACLs for above bucket
resource "aws_s3_bucket_versioning" "health_data_bucket" {
  bucket = aws_s3_bucket.health_data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "health_data_bucket" {
  bucket = aws_s3_bucket.health_data_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "health_data_bucket" {
  depends_on = [aws_s3_bucket_ownership_controls.health_data_bucket]

  bucket = aws_s3_bucket.health_data_bucket.id
  acl    = "private"
}

#############################
# ECR Repositories for Lambdas
#############################
resource "aws_ecr_repository" "ingest_repo" {
  name = "lambda_ingest_repo"
}

resource "aws_ecr_repository" "dbt_repo" {
  name = "lambda_dbt_repo"
}


#############################
# IAM Roles and Policies
#############################

## Ingest Lambda Role
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

resource "aws_iam_role_policy_attachment" "lambda_ingest_basic_execution" {
  role       = aws_iam_role.lambda_ingest_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy to allow ingest Lambda to put objects into S3 under the landing/ prefix.
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

## DBT Lambda Role
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

resource "aws_iam_role_policy_attachment" "lambda_dbt_basic_execution" {
  role       = aws_iam_role.lambda_dbt_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#############################
# Build & Push Docker Images Using a Unified Dockerfile
#############################

## Ingest Lambda Image
resource "null_resource" "build_push_ingest" {
  # Trigger rebuild if Dockerfile, pyproject.toml, or ingest_lambda.py changes.
  triggers = {
    dockerfile_hash = filesha256("Dockerfile")
    pyproject_hash  = filesha256("../pyproject.toml")
    code_hash       = filesha256("ingest_lambda.py")
  }

  provisioner "local-exec" {
    command = <<EOT
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.ingest_repo.repository_url}
      docker build --build-arg HANDLER_FILE=ingest_lambda.py -t ${aws_ecr_repository.ingest_repo.repository_url}:latest ./lambda
      docker push ${aws_ecr_repository.ingest_repo.repository_url}:latest
    EOT
    environment = {
      aws_region = var.aws_region
    }
  }
}

## DBT Lambda Image
resource "null_resource" "build_push_dbt" {
  triggers = {
    dockerfile_hash = filesha256("Dockerfile")
    pyproject_hash  = filesha256("../pyproject.toml")
    code_hash       = filesha256("dbt_lambda.py")
  }

  provisioner "local-exec" {
    command = <<EOT
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.dbt_repo.repository_url}
      docker build --build-arg HANDLER_FILE=dbt_lambda.py -t ${aws_ecr_repository.dbt_repo.repository_url}:latest ./lambda
      docker push ${aws_ecr_repository.dbt_repo.repository_url}:latest
    EOT
    environment = {
      aws_region = var.aws_region
    }
  }
}

#############################
# Lambda Functions (Container Images)
#############################

## Ingest Lambda Function
resource "aws_lambda_function" "ingest_lambda" {
  function_name = "ingest_health_data"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ingest_repo.repository_url}:latest"
  role          = aws_iam_role.lambda_ingest_role.arn
  depends_on    = [null_resource.build_push_ingest]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.health_data_bucket.bucket
    }
  }
}

## Expose Ingest Lambda via a Function URL
resource "aws_lambda_function_url" "ingest_lambda_url" {
  function_name      = aws_lambda_function.ingest_lambda.function_name
  authorization_type = "NONE"
}

## DBT Lambda Function
resource "aws_lambda_function" "dbt_lambda" {
  function_name = "trigger_dbt_job"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.dbt_repo.repository_url}:latest"
  role          = aws_iam_role.lambda_dbt_role.arn
  depends_on    = [null_resource.build_push_dbt]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.health_data_bucket.bucket
      # Add any additional environment variables needed for your DBT job.
    }
  }
}

## Expose DBT Lambda via a Function URL
resource "aws_lambda_function_url" "dbt_lambda_url" {
  function_name      = aws_lambda_function.dbt_lambda.function_name
  authorization_type = "NONE"
}
