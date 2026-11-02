locals {
  workflow_name = "richard-citibike-incremental-workflow"
  workflow_arn  = "arn:aws:states:us-east-2:866934333672:stateMachine:${local.workflow_name}"
}

resource "aws_iam_role" "workflow" {
  name = "RichardCitiBikeIncrementalWorkflowRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = "866934333672" }
        ArnEquals    = { "aws:SourceArn" = local.workflow_arn }
      }
    }]
  })
}

resource "aws_cloudwatch_log_group" "workflow" {
  name              = "/aws/vendedlogs/states/${local.workflow_name}"
  retention_in_days = 7
}

resource "aws_iam_role_policy" "workflow" {
  name = "RichardCitiBikeIncrementalWorkflowAccess"
  role = aws_iam_role.workflow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "PrepareBatchAndReleaseLock"
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.prepare_batch.arn
      },
      {
        Sid      = "RunIncrementalGlueJobs"
        Effect   = "Allow"
        Action   = ["glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns", "glue:BatchStopJobRun"]
        Resource = [aws_glue_job.bronze_to_silver_incremental.arn, aws_glue_job.silver_to_redshift_incremental.arn]
      },
      {
        Sid      = "SubmitWarehouseAcceptance"
        Effect   = "Allow"
        Action   = ["redshift-data:ExecuteStatement"]
        Resource = "arn:aws:redshift-serverless:us-east-2:866934333672:workgroup/6de8611e-e342-4b21-ac2d-cb2a8ac3e59c"
      },
      {
        Sid      = "ObserveAndCancelOwnStatements"
        Effect   = "Allow"
        Action   = ["redshift-data:DescribeStatement", "redshift-data:CancelStatement"]
        Resource = "*"
      },
      {
        Sid      = "WarehouseCredentials"
        Effect   = "Allow"
        Action   = ["redshift-serverless:GetCredentials"]
        Resource = "arn:aws:redshift-serverless:us-east-2:866934333672:workgroup/6de8611e-e342-4b21-ac2d-cb2a8ac3e59c"
      },
      {
        Sid    = "WorkflowLogDelivery"
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies", "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_sfn_state_machine" "incremental" {
  name     = local.workflow_name
  role_arn = aws_iam_role.workflow.arn
  type     = "STANDARD"
  definition = templatefile("${path.module}/../workflows/incremental.asl.json.tftpl", {
    bronze_job       = aws_glue_job.bronze_to_silver_incremental.name
    silver_job       = aws_glue_job.silver_to_redshift_incremental.name
    prepare_function = aws_lambda_function.prepare_batch.arn
  })
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.workflow.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }
  depends_on = [aws_iam_role_policy.workflow]
}

output "incremental_state_machine_arn" {
  value = aws_sfn_state_machine.incremental.arn
}
