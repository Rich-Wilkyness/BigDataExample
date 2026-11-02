resource "aws_iam_role" "scheduler" {
  name = "CitiBikeStepFunctionsSchedulerRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "scheduler.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "CitiBikeStepFunctionsSchedulerPermissions"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "states:StartExecution"
      ]
      Resource = aws_sfn_state_machine.pipeline.arn
    }]
  })
}

resource "aws_scheduler_schedule" "citibike_incremental" {
  name                         = "citibike-incremental-every-30-min"
  description                  = "Run Citi Bike incremental processing every 30 minutes"
  schedule_expression          = "rate(30 minutes)"
  schedule_expression_timezone = "UTC"
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.pipeline.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({})

    retry_policy {
      maximum_retry_attempts       = 0
      maximum_event_age_in_seconds = 60
    }
  }

  depends_on = [
    aws_iam_role_policy.scheduler
  ]
}