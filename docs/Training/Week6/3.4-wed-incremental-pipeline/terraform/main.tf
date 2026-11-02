terraform {
  required_version = ">= 1.5, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Use the same credential chain as your working AWS CLI.
# Provider 5.x matches the instructor reference configuration.
provider "aws" {
  region              = "us-east-2"
  allowed_account_ids = ["866934333672"]
}

data "aws_caller_identity" "current" {}

# Read an existing bucket; this does not create or take ownership of it.
data "aws_s3_bucket" "pipeline" {
  bucket = "richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an"
}

output "aws_identity" {
  value = data.aws_caller_identity.current.arn
}

output "pipeline_bucket" {
  value = data.aws_s3_bucket.pipeline.id
}
