output "ingest_lambda_url" {
  value = aws_lambda_function_url.ingest_lambda_url.function_url
}

output "s3_bucket" {
  value = aws_s3_bucket.health_data_bucket.bucket
}
