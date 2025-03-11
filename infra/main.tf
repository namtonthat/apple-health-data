terraform {
  backend "s3" {
    bucket  = var.aws_s3_bucket
    key     = "terraform/state.tfstate"
    region  = var.aws_region
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}
