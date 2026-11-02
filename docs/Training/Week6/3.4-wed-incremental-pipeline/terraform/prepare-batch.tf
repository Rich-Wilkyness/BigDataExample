locals {
  prepare_name = "richard-citibike-prepare-batch"
  control      = "control/citibike/incremental"
}

resource "aws_iam_role" "prepare_batch" {
  name = "RichardCitiBikePrepareBatchRole"
  # Lambda's documented execution-role trust uses its service principal.
  # The dedicated permissions policy is scoped to Richard's pipeline resources.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "prepare_batch" {
  name              = "/aws/lambda/${local.prepare_name}"
  retention_in_days = 7
}

resource "aws_iam_role_policy" "prepare_batch" {
  name = "RichardCitiBikePrepareBatchAccess"
  role = aws_iam_role.prepare_batch.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadSourceAndPreparedObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${data.aws_s3_bucket.pipeline.arn}/bronze/citibike/station_status/*", "${data.aws_s3_bucket.pipeline.arn}/bronze/citibike/station_information/*", "${data.aws_s3_bucket.pipeline.arn}/bronze/citibike/system_information/*", "${data.aws_s3_bucket.pipeline.arn}/bronze/citibike/gbfs_discovery/*", "${data.aws_s3_bucket.pipeline.arn}/bronze/citibike/completed/*", "${data.aws_s3_bucket.pipeline.arn}/${local.control}/*"]
      },
      {
        # Also permits 404 rather than 403 for absent lock/manifest objects.
        Sid      = "ListOwnedPipelineBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = data.aws_s3_bucket.pipeline.arn
      },
      {
        Sid       = "CreateFrozenInputsOnly"
        Effect    = "Allow"
        Action    = ["s3:PutObject"]
        Resource  = "${data.aws_s3_bucket.pipeline.arn}/${local.control}/batches/*"
        Condition = { StringEquals = { "s3:if-none-match" = "*" } }
      },
      {
        Sid      = "MaintainSingleWorkflowLock"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${data.aws_s3_bucket.pipeline.arn}/${local.control}/active.json"
      },
      {
        Sid      = "ReadWarehouseCheckpoint"
        Effect   = "Allow"
        Action   = ["redshift-data:ExecuteStatement", "redshift-serverless:GetCredentials"]
        Resource = "arn:aws:redshift-serverless:us-east-2:866934333672:workgroup/6de8611e-e342-4b21-ac2d-cb2a8ac3e59c"
      },
      {
        Sid      = "ReadOwnStatementResults"
        Effect   = "Allow"
        Action   = ["redshift-data:DescribeStatement", "redshift-data:GetStatementResult", "redshift-data:CancelStatement"]
        Resource = "*"
      },
      {
        Sid      = "FunctionLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.prepare_batch.arn}:*"
      }
    ]
  })
}

# Built by lambda/package.py using the Python standard library. No new provider.
resource "aws_lambda_function" "prepare_batch" {
  function_name    = local.prepare_name
  role             = aws_iam_role.prepare_batch.arn
  runtime          = "python3.13"
  architectures    = ["arm64"]
  handler          = "prepare_batch.lambda_handler"
  filename         = "${path.module}/.build/prepare-batch.zip"
  source_code_hash = filebase64sha256("${path.module}/.build/prepare-batch.zip")
  timeout          = 300
  memory_size      = 512
  environment {
    variables = {
      BUCKET               = data.aws_s3_bucket.pipeline.id
      REDSHIFT_WORKGROUP   = "richard-citibike-wg"
      REDSHIFT_DATABASE    = "dev"
      EXECUTION_ARN_PREFIX = "arn:aws:states:us-east-2:866934333672:execution:${local.workflow_name}:"
    }
  }
  depends_on = [aws_iam_role_policy.prepare_batch, aws_cloudwatch_log_group.prepare_batch]
}

resource "aws_iam_role_policy" "prepared_input_access" {
  name = "RichardCitiBikePreparedInputAccess"
  role = "AWSGlueServiceRole-RichardCitiBike"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${data.aws_s3_bucket.pipeline.arn}/${local.control}/batches/*"
      },
      {
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = data.aws_s3_bucket.pipeline.arn
        Condition = { StringLike = { "s3:prefix" = ["${local.control}/batches/*"] } }
      }
    ]
  })
}

output "prepare_batch_function" {
  value = aws_lambda_function.prepare_batch.function_name
}
