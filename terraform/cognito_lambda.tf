# ============================================================================
# Cognito User Pool and Identity Pool for Authentication
# ============================================================================

# Cognito User Pool
resource "aws_cognito_user_pool" "agentcore_users" {
  name = "${var.project_name}-agentcore-users"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # User attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }

  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = false
    mutable             = true
  }

  # Auto-verify email
  auto_verified_attributes = ["email"]

  # MFA configuration (optional - can be enabled)
  mfa_configuration = "OFF"

  tags = var.tags
}

# Cognito User Pool Client (for API Gateway)
resource "aws_cognito_user_pool_client" "agentcore_client" {
  name         = "${var.project_name}-agentcore-client"
  user_pool_id = aws_cognito_user_pool.agentcore_users.id

  # OAuth settings
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  # Token validity
  access_token_validity  = 60  # minutes
  id_token_validity      = 60  # minutes
  refresh_token_validity = 30  # days

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"
}

# Cognito Identity Pool (for unauthenticated access if needed)
resource "aws_cognito_identity_pool" "agentcore_identity" {
  identity_pool_name               = "${var.project_name}-agentcore-identity"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.agentcore_client.id
    provider_name           = aws_cognito_user_pool.agentcore_users.endpoint
    server_side_token_check = false
  }

  tags = var.tags
}

# IAM Role for authenticated Cognito users
resource "aws_iam_role" "cognito_authenticated" {
  name = "${var.project_name}-cognito-authenticated"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.agentcore_identity.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for authenticated users (minimal - they access via API Gateway)
resource "aws_iam_role_policy" "cognito_authenticated" {
  name = "${var.project_name}-cognito-authenticated-policy"
  role = aws_iam_role.cognito_authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "mobileanalytics:PutEvents",
          "cognito-sync:*",
          "cognito-identity:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach authenticated role to identity pool
resource "aws_cognito_identity_pool_roles_attachment" "agentcore_identity_roles" {
  identity_pool_id = aws_cognito_identity_pool.agentcore_identity.id

  roles = {
    "authenticated" = aws_iam_role.cognito_authenticated.arn
  }
}

# ============================================================================
# Lambda Function for Agent Core Invocation
# ============================================================================

# IAM Role for Lambda
resource "aws_iam_role" "lambda_agentcore" {
  name = "${var.project_name}-lambda-agentcore"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Lambda to invoke Bedrock Agent Core
resource "aws_iam_role_policy" "lambda_agentcore" {
  name = "${var.project_name}-lambda-agentcore-policy"
  role = aws_iam_role.lambda_agentcore.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agent-runtime:InvokeAgent"
        ]
        Resource = "*"  # Update with specific agent ARN if needed
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Archive Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/lambda_function.zip"
  excludes    = ["__pycache__", "*.pyc", ".pytest_cache"]
}

# Lambda function
resource "aws_lambda_function" "agentcore_invoker" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-agentcore-invoker"
  role            = aws_iam_role.lambda_agentcore.arn
  handler         = "agentcore_invoker.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      AGENT_ARN      = var.agent_arn
      AGENT_HTTP_URL = var.agent_http_url
      AWS_REGION     = var.aws_region
    }
  }

  tags = var.tags
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_agentcore" {
  name              = "/aws/lambda/${aws_lambda_function.agentcore_invoker.function_name}"
  retention_in_days = 7
  tags              = var.tags
}

# ============================================================================
# API Gateway with Cognito Authorizer
# ============================================================================

# API Gateway REST API
resource "aws_api_gateway_rest_api" "agentcore_api" {
  name        = "${var.project_name}-agentcore-api"
  description = "API Gateway for secure Agent Core access via Cognito"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = var.tags
}

# Cognito Authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name                   = "CognitoAuthorizer"
  rest_api_id            = aws_api_gateway_rest_api.agentcore_api.id
  type                   = "COGNITO_USER_POOLS"
  provider_arns          = [aws_cognito_user_pool.agentcore_users.arn]
  authorizer_credentials = null
}

# API Gateway Resource
resource "aws_api_gateway_resource" "invoke" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  parent_id   = aws_api_gateway_rest_api.agentcore_api.root_resource_id
  path_part   = "invoke"
}

# API Gateway Method (POST)
resource "aws_api_gateway_method" "invoke_post" {
  rest_api_id   = aws_api_gateway_rest_api.agentcore_api.id
  resource_id   = aws_api_gateway_resource.invoke.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# API Gateway Method (OPTIONS for CORS)
resource "aws_api_gateway_method" "invoke_options" {
  rest_api_id   = aws_api_gateway_rest_api.agentcore_api.id
  resource_id   = aws_api_gateway_resource.invoke.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Lambda Integration
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.agentcore_invoker.invoke_arn
}

# OPTIONS Integration (for CORS)
resource "aws_api_gateway_integration" "options" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Method Response for POST
resource "aws_api_gateway_method_response" "invoke_post_200" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_post.http_method
  status_code  = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

# Integration Response for POST
resource "aws_api_gateway_integration_response" "invoke_post" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_post.http_method
  status_code  = aws_api_gateway_method_response.invoke_post_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
  }
}

# Method Response for OPTIONS
resource "aws_api_gateway_method_response" "invoke_options_200" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_options.http_method
  status_code  = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }
}

# Integration Response for OPTIONS
resource "aws_api_gateway_integration_response" "invoke_options" {
  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method  = aws_api_gateway_method.invoke_options.http_method
  status_code  = aws_api_gateway_method_response.invoke_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
  }

  response_templates = {
    "application/json" = ""
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agentcore_invoker.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.agentcore_api.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "agentcore_api" {
  depends_on = [
    aws_api_gateway_integration.lambda,
    aws_api_gateway_integration.options,
    aws_api_gateway_method_response.invoke_post_200,
    aws_api_gateway_integration_response.invoke_post,
    aws_api_gateway_method_response.invoke_options_200,
    aws_api_gateway_integration_response.invoke_options
  ]

  rest_api_id = aws_api_gateway_rest_api.agentcore_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.invoke.id,
      aws_api_gateway_method.invoke_post.id,
      aws_api_gateway_method.invoke_options.id,
      aws_api_gateway_integration.lambda.id,
      aws_api_gateway_integration.options.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "agentcore_api" {
  deployment_id = aws_api_gateway_deployment.agentcore_api.id
  rest_api_id   = aws_api_gateway_rest_api.agentcore_api.id
  stage_name    = "prod"

  tags = var.tags
}

# ============================================================================
# Variables
# ============================================================================

variable "agent_arn" {
  description = "ARN of the Bedrock Agent Core agent to invoke"
  type        = string
  default     = ""
}

variable "agent_http_url" {
  description = "HTTP URL for Agent Core invocations (e.g. agent runtime endpoint). If set, Lambda uses HTTP instead of boto3."
  type        = string
  default     = ""
}

# ============================================================================
# Outputs
# ============================================================================

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.agentcore_users.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.agentcore_client.id
  sensitive   = false
}

output "cognito_user_pool_domain" {
  description = "Cognito User Pool Domain (for OAuth endpoints)"
  value       = aws_cognito_user_pool.agentcore_users.endpoint
}

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = aws_cognito_identity_pool.agentcore_identity.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.agentcore_invoker.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.agentcore_invoker.arn
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_deployment.agentcore_api.invoke_url}/invoke"
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.agentcore_api.id
}

