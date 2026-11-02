terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}

provider "aws" {
  region              = "us-east-2"
  profile             = "company"
  allowed_account_ids = ["866934333672"]
}

locals {
  account_id = "866934333672"
  region     = "us-east-2"
  bronze_job = "CitiBikeBronzeToSilverIncrementalV2"
  silver_job = "CitiBikeSilverToRedshiftIncrementalV2"
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/vendedlogs/states/citibike-class-orchestration"
  retention_in_days = 7
}

data "aws_iam_policy_document" "assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "CitiBikeStepFunctionsClassRole"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "permissions" {
  statement {
    sid       = "InvokeBatchCoordinator"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.coordinator.arn, "${aws_lambda_function.coordinator.arn}:*"]
  }
  statement {
    sid     = "RunIncrementalGlueJobs"
    actions = ["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"]
    resources = [
      "arn:aws:glue:${local.region}:${local.account_id}:job/${local.bronze_job}",
      "arn:aws:glue:${local.region}:${local.account_id}:job/${local.silver_job}"
    ]
  }
  statement {
    sid       = "GlueSyncEvents"
    actions   = ["events:PutRule", "events:PutTargets", "events:DescribeRule"]
    resources = ["arn:aws:events:${local.region}:${local.account_id}:rule/StepFunctionsGetEventsForGlueJobRule"]
  }
  statement {
    sid = "StepFunctionsLogDelivery"
    actions = [
      "logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies", "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "CitiBikeStepFunctionsClassPermissions"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.permissions.json
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "citibike-class-orchestration"
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD"
  definition = jsonencode({
    Comment = "Citi Bike: checkpoint -> incremental Glue -> Redshift stored procedure via coordinator"
    StartAt = "PrepareBatch"
    States = {
      PrepareBatch = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.coordinator.arn
          Payload      = { "execution_name.$" = "$$.Execution.Name", phase = "prepare" }
        }
        ResultSelector = { "batch.$" = "$.Payload" }
        ResultPath     = "$.prepared"
        Next           = "BronzeToSilver"
      }
      BronzeToSilver = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = local.bronze_job
          Arguments = {
            "--BATCH_ID.$"        = "$.prepared.batch.batch_id"
            "--START_AFTER_UTC.$" = "$.prepared.batch.start_after_utc"
            "--END_BEFORE_UTC.$"  = "$.prepared.batch.end_before_utc"
          }
        }
        ResultPath = "$.bronze_result"
        Next       = "SilverToRedshift"
      }
      SilverToRedshift = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName   = local.silver_job
          Arguments = { "--BATCH_ID.$" = "$.prepared.batch.batch_id" }
        }
        ResultPath = "$.silver_result"
        Next       = "CompleteBatch"
      }
      CompleteBatch = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.coordinator.arn
          Payload = {
            phase              = "complete"
            "batch_id.$"       = "$.prepared.batch.batch_id"
            "window_end_sql.$" = "$.prepared.batch.window_end_sql"
          }
        }
        ResultSelector = { "completion.$" = "$.Payload" }
        ResultPath     = "$.redshift_completion"
        Next           = "PipelineSucceeded"
      }
      PipelineSucceeded = { Type = "Succeed" }
    }
  })
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  depends_on = [aws_iam_role_policy.sfn]
}

output "state_machine_arn" { value = aws_sfn_state_machine.pipeline.arn }
output "log_group_name" { value = aws_cloudwatch_log_group.sfn.name }
