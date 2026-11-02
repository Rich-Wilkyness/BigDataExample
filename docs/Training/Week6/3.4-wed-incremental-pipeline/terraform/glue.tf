# Publish the learner-edited incremental script at a separate S3 key.
resource "aws_s3_object" "bronze_to_silver_script" {
  bucket       = data.aws_s3_bucket.pipeline.id
  key          = "scripts/glue/incremental/bronze-to-silver.py"
  source       = "${path.module}/../glue/bronze-to-silver.py"
  source_hash  = filemd5("${path.module}/../glue/bronze-to-silver.py")
  content_type = "text/x-python"
}

resource "aws_glue_job" "bronze_to_silver_incremental" {
  depends_on = [aws_iam_role_policy.incremental_silver_access, aws_iam_role_policy.prepared_input_access]

  name              = "richard-citibike-bronze-to-silver-incremental"
  description       = "Process a prepared frozen source manifest into one isolated Silver batch"
  role_arn          = "arn:aws:iam::866934333672:role/AWSGlueServiceRole-RichardCitiBike"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_object.bronze_to_silver_script.bucket}/${aws_s3_object.bronze_to_silver_script.key}"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  # Batch identity and boundaries are required per-run arguments.
  default_arguments = {
    "--BUCKET"              = data.aws_s3_bucket.pipeline.id
    "--job-bookmark-option" = "job-bookmark-disable"
    "--job-language"        = "python"
    "--TempDir"             = "s3://${data.aws_s3_bucket.pipeline.id}/glue-temp/incremental/"
    "--conf"                = "spark.sql.shuffle.partitions=4"
  }
}

output "bronze_to_silver_incremental_job" {
  value = aws_glue_job.bronze_to_silver_incremental.name
}

resource "aws_s3_object" "silver_to_redshift_script" {
  bucket       = data.aws_s3_bucket.pipeline.id
  key          = "scripts/glue/incremental/silver-to-redshift.py"
  source       = "${path.module}/../glue/silver-to-redshift.py"
  source_hash  = filemd5("${path.module}/../glue/silver-to-redshift.py")
  content_type = "text/x-python"
}

resource "aws_glue_job" "silver_to_redshift_incremental" {
  depends_on = [aws_iam_role_policy.incremental_silver_access]

  name              = "richard-citibike-silver-to-redshift-incremental"
  description       = "Load one Silver batch into Redshift landing with its batch ID"
  role_arn          = "arn:aws:iam::866934333672:role/AWSGlueServiceRole-RichardCitiBike"
  glue_version      = "5.1"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0
  connections       = ["richard-citibike-redshift-connection"]

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_object.silver_to_redshift_script.bucket}/${aws_s3_object.silver_to_redshift_script.key}"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  # BATCH_ID is supplied at execution; keep it aligned with accepted Silver output.
  default_arguments = {
    "--BUCKET"              = data.aws_s3_bucket.pipeline.id
    "--job-bookmark-option" = "job-bookmark-disable"
    "--job-language"        = "python"
    "--TempDir"             = "s3://${data.aws_s3_bucket.pipeline.id}/glue-temp/incremental/"
    "--conf"                = "spark.sql.shuffle.partitions=4"
  }
}

output "silver_to_redshift_incremental_job" {
  value = aws_glue_job.silver_to_redshift_incremental.name
}
