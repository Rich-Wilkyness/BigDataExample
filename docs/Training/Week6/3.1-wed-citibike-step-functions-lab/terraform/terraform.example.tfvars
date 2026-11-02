# Copy to terraform.tfvars, which is gitignored. Replace with a reviewed role ARN.
workflow_role_arn = "arn:aws:iam::866934333672:role/REPLACE_WITH_REVIEWED_WORKFLOW_ROLE"
# Existing resources are reused through variables; they are not imported/managed.
# Defaults already select Richard's bucket, connection, Glue role and workgroup.
