variable "region" {
  type    = string
  default = "us-east-2"
}
variable "account_id" {
  type    = string
  default = "866934333672"
}
variable "name_prefix" {
  type    = string
  default = "richard-citibike-v2-lab"
}
variable "bucket" {
  type    = string
  default = "richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an"
}
variable "glue_role_arn" {
  type    = string
  default = "arn:aws:iam::866934333672:role/AWSGlueServiceRole-RichardCitiBike"
}
variable "redshift_s3_role_arn" {
  type    = string
  default = "arn:aws:iam::866934333672:role/RichardCitiBikeRedshiftRole"
}
variable "workflow_role_arn" {
  type        = string
  description = "Administrator-reviewed Step Functions role; see ../iam/README.md. No role is silently assumed to exist."
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+$", var.workflow_role_arn)) && !strcontains(var.workflow_role_arn, "REPLACE")
    error_message = "Supply the actual reviewed IAM role ARN."
  }
}
variable "connection_name" {
  type    = string
  default = "richard-citibike-redshift-connection"
}
variable "workgroup_name" {
  type    = string
  default = "richard-citibike-wg"
}
variable "glue_version" {
  type    = string
  default = "5.0"
}
