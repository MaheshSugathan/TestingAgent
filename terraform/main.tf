terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current AWS region
data "aws_region" "current" {}

# Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "agent_name" {
  description = "Name of the Bedrock Agent Core agent"
  type        = string
  default     = "rag_evaluation_agent"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rag-evaluation"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "RAG-Evaluation"
    Environment = "test"
    ManagedBy   = "terraform"
  }
}

variable "cognito_callback_urls" {
  description = "Cognito callback URLs for the app (add CloudFront URL after chat UI deploy)"
  type        = list(string)
  default     = ["http://localhost:3000/callback", "http://localhost:5173/callback"]
}

variable "cognito_logout_urls" {
  description = "Cognito logout URLs"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:5173"]
}

# ECR Repository for container images
resource "aws_ecr_repository" "agentcore" {
  name                 = "bedrock-agentcore-${var.agent_name}"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even if images exist

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# IAM Role for Bedrock Agent Core Runtime
resource "aws_iam_role" "agentcore_runtime" {
  name = "AmazonBedrockAgentCoreSDKRuntime-${data.aws_region.current.name}-${substr(md5("${var.agent_name}-${data.aws_caller_identity.current.account_id}"), 0, 8)}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock-agentcore.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Agent Core Runtime
resource "aws_iam_role_policy" "agentcore_runtime" {
  name = "BedrockAgentCoreRuntimeExecutionPolicy-${substr(md5("${var.agent_name}-${data.aws_caller_identity.current.account_id}"), 0, 8)}"
  role = aws_iam_role.agentcore_runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:*",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "cloudwatch:PutMetricData",
          "s3:GetObject",
          "s3:ListBucket",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for CodeBuild (if using CodeBuild for building)
resource "aws_iam_role" "codebuild" {
  name = "AmazonBedrockAgentCoreSDKCodeBuild-${data.aws_region.current.name}-${substr(md5("${var.agent_name}-${data.aws_caller_identity.current.account_id}"), 0, 8)}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for CodeBuild
resource "aws_iam_role_policy" "codebuild" {
  name = "CodeBuildExecutionPolicy-${substr(md5("${var.agent_name}-${data.aws_caller_identity.current.account_id}"), 0, 8)}"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "s3:GetObject",
          "s3:PutObject",
          "s3:GetObjectVersion"
        ]
        Resource = "*"
      }
    ]
  })
}

# S3 Bucket for CodeBuild sources (if needed)
resource "aws_s3_bucket" "codebuild_sources" {
  bucket = "bedrock-agentcore-codebuild-sources-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.name}"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "codebuild_sources" {
  bucket = aws_s3_bucket.codebuild_sources.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "codebuild_sources" {
  bucket = aws_s3_bucket.codebuild_sources.id

  rule {
    id     = "cleanup-old-sources"
    status = "Enabled"

    filter {}

    expiration {
      days = 7
    }
  }
}

# CloudWatch Log Group for agent logs
# Note: Bedrock Agent Core creates log groups automatically, so we'll skip this
# or create a generic one. The actual runtime logs are created by Agent Core.
# resource "aws_cloudwatch_log_group" "agentcore" {
#   name              = "/aws/bedrock-agentcore/runtimes/${var.agent_name}"
#   retention_in_days = 7
#   tags = var.tags
# }

# Outputs
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.agentcore.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.agentcore.name
}

output "runtime_execution_role_arn" {
  description = "ARN of the IAM role for Agent Core Runtime"
  value       = aws_iam_role.agentcore_runtime.arn
}

output "codebuild_role_arn" {
  description = "ARN of the IAM role for CodeBuild"
  value       = aws_iam_role.codebuild.arn
}

output "codebuild_source_bucket" {
  description = "Name of the S3 bucket for CodeBuild sources"
  value       = aws_s3_bucket.codebuild_sources.id
}

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

