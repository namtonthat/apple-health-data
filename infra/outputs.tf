output "ingest_lambda_url" {
  value = aws_lambda_function_url.ingest_lambda_url.function_url
}

output "s3_bucket" {
  value = aws_s3_bucket.health_data_bucket.bucket
}

output "github_actions_access_key_id" {
  description = "The access key ID for the github_actions IAM user"
  value       = aws_iam_access_key.github_actions_key.id
}

output "github_actions_secret_access_key" {
  description = "The secret access key for the github_actions IAM user"
  value       = aws_iam_access_key.github_actions_key.secret
  sensitive   = true
}

output "streamlit_access_key_id" {
  description = "The access key ID for the streamlit IAM user"
  value       = aws_iam_access_key.streamlit.id
}

output "streamlit_secret_access_key" {
  description = "The access key ID for the streamlit IAM user"
  value       = aws_iam_access_key.streamlit.secret
  sensitive   = true
}
