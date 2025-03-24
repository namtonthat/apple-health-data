variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-2"
}

variable "aws_s3_bucket" {
  description = "Data to hold apple-health-data"
  type        = string
  default     = "api-health-data-ntonthat"
}

variable "github_actions_policy_name" {
  description = "Policy name for github_actions role"
  type        = string
  default     = "github_actions_policy"
}
