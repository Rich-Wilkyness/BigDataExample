data "archive_file" "citibike_coordinator" {
  type        = "zip"
  source_file = "${path.module}/coordinator.py"
  output_path = "${path.module}/coordinator.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "coordinator" {
  name               = "CitiBikeBatchCoordinatorRole"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy" "coordinator" {
  name = "CitiBikeBatchCoordinatorPermissions"
  role = aws_iam_role.coordinator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["redshift-data:ExecuteStatement", "redshift-data:DescribeStatement", "redshift-data:GetStatementResult"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["redshift-serverless:GetCredentials"]
        Resource = "arn:aws:redshift-serverless:us-east-2:866934333672:workgroup/*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "coordinator" {
  function_name    = "citibike-batch-coordinator"
  role             = aws_iam_role.coordinator.arn
  runtime          = "python3.12"
  handler          = "coordinator.handler"
  filename         = data.archive_file.citibike_coordinator.output_path
  source_code_hash = data.archive_file.citibike_coordinator.output_base64sha256
  timeout          = 240
  environment {
    variables = {
      REDSHIFT_WORKGROUP = "citibike-wg"
      REDSHIFT_DATABASE  = "dev"
    }
  }
  depends_on = [aws_iam_role_policy.coordinator]
}
