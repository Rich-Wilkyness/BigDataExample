# This is a reconstruction for Richard, not recovered instructor Terraform.
# Existing bucket, Glue/Redshift roles, JDBC connection and workgroup are inputs.
# This configuration manages only four new jobs, four script objects, and two
# state machines. It creates no schedules and starts no executions.
locals {
  lab_root = "${path.module}/.."
  jobs = {
    backfill-silver      = { source = "backfill/bronze-to-silver.py", redshift = false }
    backfill-redshift    = { source = "backfill/silver-to-redshift.py", redshift = true }
    incremental-silver   = { source = "incremental/bronze-to-silver.py", redshift = false }
    incremental-redshift = { source = "incremental/silver-to-redshift.py", redshift = true }
  }
  workflows = {
    backfill    = jsondecode(file("${local.lab_root}/workflows/backfill.asl.json"))
    incremental = jsondecode(file("${local.lab_root}/workflows/incremental.asl.json"))
  }
  # ASL files remain readable standalone. Replace only deployment-specific fields.
  backfill_definition = merge(local.workflows.backfill, {
    States = merge(local.workflows.backfill.States, {
      BuildHistory = merge(local.workflows.backfill.States.BuildHistory, {
        Parameters = merge(local.workflows.backfill.States.BuildHistory.Parameters, {
          JobName = aws_glue_job.pipeline["backfill-silver"].name
        })
      })
      LoadHistory = merge(local.workflows.backfill.States.LoadHistory, {
        Parameters = { JobName = aws_glue_job.pipeline["backfill-redshift"].name }
      })
    })
  })
  incremental_definition = merge(local.workflows.incremental, {
    States = merge(local.workflows.incremental.States, {
      BuildSilver = merge(local.workflows.incremental.States.BuildSilver, {
        Parameters = merge(local.workflows.incremental.States.BuildSilver.Parameters, {
          JobName = aws_glue_job.pipeline["incremental-silver"].name
        })
      })
      LoadLanding = merge(local.workflows.incremental.States.LoadLanding, {
        Parameters = merge(local.workflows.incremental.States.LoadLanding.Parameters, {
          JobName = aws_glue_job.pipeline["incremental-redshift"].name
        })
      })
      SubmitAcceptance = merge(local.workflows.incremental.States.SubmitAcceptance, {
        Parameters = merge(local.workflows.incremental.States.SubmitAcceptance.Parameters, {
          WorkgroupName = var.workgroup_name
        })
      })
    })
  })
}

resource "aws_s3_object" "script" {
  for_each     = local.jobs
  bucket       = var.bucket
  key          = "scripts/glue/v2-lab/${each.key}.py"
  source       = "${local.lab_root}/${each.value.source}"
  source_hash  = filemd5("${local.lab_root}/${each.value.source}")
  content_type = "text/x-python"
}

resource "aws_glue_job" "pipeline" {
  for_each          = local.jobs
  name              = "${var.name_prefix}-${each.key}"
  role_arn          = var.glue_role_arn
  glue_version      = var.glue_version
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 15
  max_retries       = 0
  connections       = each.value.redshift ? [var.connection_name] : []
  execution_property {
    max_concurrent_runs = 1
  }
  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${var.bucket}/${aws_s3_object.script[each.key].key}"
  }
  default_arguments = merge({
    "--BUCKET"              = var.bucket
    "--TempDir"             = "s3://${var.bucket}/glue-temp/v2-lab/"
    "--job-language"        = "python"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--conf"                = "spark.sql.shuffle.partitions=4"
    }, each.value.redshift ? {
    "--CONNECTION"    = var.connection_name
    "--REDSHIFT_ROLE" = var.redshift_s3_role_arn
  } : {})
}

resource "aws_sfn_state_machine" "backfill" {
  name       = "${var.name_prefix}-backfill"
  role_arn   = var.workflow_role_arn
  type       = "STANDARD"
  definition = jsonencode(local.backfill_definition)
}

resource "aws_sfn_state_machine" "incremental" {
  name       = "${var.name_prefix}-incremental"
  role_arn   = var.workflow_role_arn
  type       = "STANDARD"
  definition = jsonencode(local.incremental_definition)
}
