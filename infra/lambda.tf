resource "aws_ecr_repository" "ingest_repo" {
  name = "lambda_ingest_repo"
}

data "aws_ecr_image" "latest_image" {
  repository_name = aws_ecr_repository.ingest_repo.name
  image_tag       = "latest"
}
resource "null_resource" "build_push_ingest" {
  triggers = {
    dockerfile_hash = filesha256("../ingest/Dockerfile")
    pyproject_hash  = filesha256("../pyproject.toml")
    code_hash       = filesha256("../ingest/lambda.py")
  }

  provisioner "local-exec" {
    command = <<EOT
      aws ecr get-login-password --region ${var.aws_region} | podman login --username AWS --password-stdin ${aws_ecr_repository.ingest_repo.repository_url}
      podman build --platform linux/arm64 -f ../ingest/Dockerfile -t ${aws_ecr_repository.ingest_repo.repository_url}:latest ..
      podman push ${aws_ecr_repository.ingest_repo.repository_url}:latest
    EOT
    environment = {
      aws_region = var.aws_region
    }
  }
}
resource "aws_lambda_function" "ingest_lambda" {
  function_name = "ingest_health_data"
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ingest_repo.repository_url}@${data.aws_ecr_image.latest_image.image_digest}"
  role          = aws_iam_role.lambda_ingest_role.arn
  depends_on    = [null_resource.build_push_ingest]
  architectures = ["arm64"]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.health_data_bucket.bucket
    }
  }
}

resource "aws_lambda_function_url" "ingest_lambda_url" {
  function_name      = aws_lambda_function.ingest_lambda.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "ingest_function_url_public" {
  statement_id           = "AllowPublicInvokeForFunctionURL"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.ingest_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
