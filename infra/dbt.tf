resource "aws_ecr_repository" "dbt_repo" {
  name = "apple_health_dbt"
}

data "aws_ecr_image" "latest_dbt_image" {
  repository_name = aws_ecr_repository.dbt_repo.name
  image_tag       = "latest"
}

resource "null_resource" "build_push_dbt" {
  triggers = {
    dockerfile_hash = filesha256("../transforms/Dockerfile")
    pyproject_hash  = filesha256("../pyproject.toml")
    code_hash       = filesha256("../transforms/lambda.py")
  }

  provisioner "local-exec" {
    command = <<EOT
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.dbt_repo.repository_url}
      docker build --platform linux/arm64 --provenance=false -f ../transforms/Dockerfile -t ${aws_ecr_repository.dbt_repo.repository_url}:latest ..
      docker push ${aws_ecr_repository.dbt_repo.repository_url}:latest
    EOT
    environment = {
      aws_region = var.aws_region
    }
  }
}

resource "aws_lambda_function" "dbt_lambda" {
  function_name = "trigger_dbt_job"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.dbt_repo.repository_url}@${data.aws_ecr_image.latest_dbt_image.image_digest}"
  role          = aws_iam_role.lambda_dbt_role.arn
  depends_on    = [null_resource.build_push_dbt]
  timeout       = 300
  architectures = ["arm64"]
  memory_size   = 1024

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.health_data_bucket.bucket
    }
  }
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.health_data_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.dbt_lambda.arn
    events              = ["s3:ObjectCreated:*"]

    filter_prefix = "landing/"
    filter_suffix = ".json"
  }

  depends_on = [aws_lambda_permission.s3_invoke_dbt_lambda]
}

# Grant S3 permission to invoke the DBT Lambda
resource "aws_lambda_permission" "s3_invoke_dbt_lambda" {
  statement_id  = "AllowS3InvokeDBTLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dbt_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.health_data_bucket.arn
}
