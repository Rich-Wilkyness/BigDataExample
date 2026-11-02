variable "capture_events_enabled" {
  description = "Enable only after the marker-producing ingestion code and event-aware workflow are deployed"
  type        = bool
  default     = false
}

locals {
  capture_rule_name = "richard-citibike-capture-complete"
  capture_rule_arn  = "arn:aws:events:us-east-2:866934333672:rule/${local.capture_rule_name}"
}

# Preflight found the existing bucket notification configuration empty.
# S3 has one bucket-wide configuration: preserve any later external destinations.
resource "aws_s3_bucket_notification" "capture_events" {
  bucket      = data.aws_s3_bucket.pipeline.id
  eventbridge = true
}

resource "aws_cloudwatch_event_rule" "capture_complete" {
  name        = local.capture_rule_name
  description = "Start Richard's workflow only for a completed ingestion capture"
  state       = var.capture_events_enabled ? "ENABLED" : "DISABLED"
  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    account       = ["866934333672"]
    region        = ["us-east-2"]
    detail = {
      bucket = { name = [data.aws_s3_bucket.pipeline.id] }
      object = { key = [{ prefix = "bronze/citibike/completed/capture_" }] }
    }
  })
}

resource "aws_iam_role" "capture_events" {
  name = "RichardCitiBikeCaptureEventRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = "866934333672" }
        ArnEquals    = { "aws:SourceArn" = local.capture_rule_arn }
      }
    }]
  })
}

resource "aws_iam_role_policy" "capture_events" {
  name = "RichardCitiBikeCaptureEventAccess"
  role = aws_iam_role.capture_events.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = local.workflow_arn
    }]
  })
}

resource "aws_sqs_queue" "capture_delivery_dlq" {
  name                      = "richard-citibike-capture-delivery-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue_policy" "capture_delivery_dlq" {
  queue_url = aws_sqs_queue.capture_delivery_dlq.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.capture_delivery_dlq.arn
      Condition = {
        ArnEquals    = { "aws:SourceArn" = local.capture_rule_arn }
        StringEquals = { "aws:SourceAccount" = "866934333672" }
      }
    }]
  })
}

resource "aws_cloudwatch_event_target" "capture_complete" {
  rule      = aws_cloudwatch_event_rule.capture_complete.name
  target_id = "RichardIncrementalWorkflow"
  arn       = aws_sfn_state_machine.incremental.arn
  role_arn  = aws_iam_role.capture_events.arn
  input_transformer {
    input_paths    = { completion_key = "$.detail.object.key" }
    input_template = "{\"completion_key\":<completion_key>}"
  }
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 12
  }
  dead_letter_config {
    arn = aws_sqs_queue.capture_delivery_dlq.arn
  }
  depends_on = [aws_iam_role_policy.capture_events, aws_sqs_queue_policy.capture_delivery_dlq]
}

output "capture_event_rule" {
  value = aws_cloudwatch_event_rule.capture_complete.name
}

output "capture_delivery_dlq_url" {
  value = aws_sqs_queue.capture_delivery_dlq.url
}
