# Extend the existing role without replacing its baseline policies.
resource "aws_iam_role_policy" "incremental_silver_access" {
  name = "RichardCitiBikeIncrementalSilverAccess"
  role = "AWSGlueServiceRole-RichardCitiBike"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "IncrementalSilverObjects"
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ]
      Resource = "${data.aws_s3_bucket.pipeline.arn}/silver/citibike/incremental_batches/*"
    }]
  })
}
