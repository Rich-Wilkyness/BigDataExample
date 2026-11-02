output "job_names" {
  value = { for key, job in aws_glue_job.pipeline : key => job.name }
}
output "workflow_arns" {
  value = {
    backfill    = aws_sfn_state_machine.backfill.arn
    incremental = aws_sfn_state_machine.incremental.arn
  }
}
output "workflow_glue_resource_arns" {
  value = [for job in aws_glue_job.pipeline : job.arn]
}
output "workflow_trust_source_arns" {
  value = [aws_sfn_state_machine.backfill.arn, aws_sfn_state_machine.incremental.arn]
}
