# Add this file to the EXISTING Terraform directory. Do not create a new state.
variable "dashboard_allowed_cidr" {
  description = "Your public IPv4 address as CIDR, e.g. 203.0.113.4/32. Never use 0.0.0.0/0 for a private classroom demo."
  type        = string
  validation {
    condition     = can(cidrhost(var.dashboard_allowed_cidr, 0))
    error_message = "Provide a valid CIDR, e.g. 203.0.113.4/32."
  }
}
variable "dashboard_instance_type" {
  type    = string
  default = "t3.small"
}
variable "dashboard_enable_redshift" {
  type    = bool
  default = true
}

# Uses the default VPC and a default subnet. Confirm your account has them.
data "aws_vpc" "dashboard_default" { default = true }
data "aws_subnets" "dashboard_default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.dashboard_default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}
data "aws_ami" "dashboard_al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
resource "aws_security_group" "dashboard" {
  name_prefix = "citibike-dashboard-"
  description = "Citi Bike Streamlit demo inbound"
  vpc_id      = data.aws_vpc.dashboard_default.id
  ingress {
    description = "Streamlit classroom access"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = [var.dashboard_allowed_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_iam_role" "dashboard" {
  name_prefix        = "CitiBikeDashboardRole-"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "dashboard_ssm" {
  role       = aws_iam_role.dashboard.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "dashboard_redshift" {
  count = var.dashboard_enable_redshift ? 1 : 0
  name  = "CitiBikeDashboardRedshiftData"
  role  = aws_iam_role.dashboard.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["redshift-data:ExecuteStatement", "redshift-data:DescribeStatement", "redshift-data:GetStatementResult", "redshift-data:CancelStatement"], Resource = "*" },
    { Effect = "Allow", Action = ["redshift-serverless:GetCredentials"], Resource = "arn:aws:redshift-serverless:${data.aws_region.dashboard.name}:${data.aws_caller_identity.dashboard.account_id}:workgroup/*" }
  ] })
}
resource "aws_iam_role_policy" "dashboard_bedrock" {
  name = "CitiBikeDashboardBedrock"
  role = aws_iam_role.dashboard.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "dashboard_s3_deployment" {
  name = "CitiBikeDashboardS3Deployment"
  role = aws_iam_role.dashboard.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadDashboardDeploymentFiles"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::citi-bike-nyc-pipeline/scripts/dashboard/*"
        ]
      }
    ]
  })
}

data "aws_region" "dashboard" {}
data "aws_caller_identity" "dashboard" {}
resource "aws_iam_instance_profile" "dashboard" {
  name_prefix = "citibike-dashboard-"
  role        = aws_iam_role.dashboard.name
}
resource "aws_instance" "dashboard" {
  ami                         = "ami-0938c21410d9519c6"
  instance_type               = var.dashboard_instance_type
  subnet_id                   = sort(data.aws_subnets.dashboard_default.ids)[0]
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.dashboard.id]
  iam_instance_profile        = aws_iam_instance_profile.dashboard.name
  user_data = templatefile("${path.module}/dashboard-user-data.sh.tftpl", {
    app_base64          = filebase64("${path.module}/app.py")
    requirements_base64 = filebase64("${path.module}/requirements.txt")
  })
  user_data_replace_on_change = true
  metadata_options { http_tokens = "required" }
  root_block_device {
    volume_size = 12
    volume_type = "gp3"
    encrypted   = true
  }
  tags = { Name = "citibike-streamlit-dashboard", Project = "CitiBikeClass" }
}
output "dashboard_url" { value = "http://${aws_instance.dashboard.public_ip}:8501" }
output "dashboard_instance_id" { value = aws_instance.dashboard.id }
