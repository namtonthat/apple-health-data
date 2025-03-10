output "ingest_lambda_url" {
  description = "URL for invoking the ingest lambda function"
  value       = aws_lambda_function_url.ingest_lambda_url.function_url
}

output "dbt_lambda_url" {
  description = "URL for invoking the DBT lambda function"
  value       = aws_lambda_function_url.dbt_lambda_url.function_url
}
