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

variable "show_sensitive_outputs" {
  description = "Whether to show sensitive outputs. Set to false in CI."
  type        = bool
  default     = true
}

variable "aws_s3_bucket_powerlifting" {
  description = "Data to hold powerlifting-ml-progress"
  type        = string
  default     = "powerlifting-ml-progress"

}
