# ============================================================================
# Chat UI - S3 + CloudFront for static hosting
# ============================================================================

variable "deploy_chat_ui" {
  description = "Deploy the chat UI to S3 and CloudFront"
  type        = bool
  default     = true
}

variable "chat_ui_cognito_callback_urls" {
  description = "Cognito callback URLs for the deployed chat UI"
  type        = list(string)
  default     = []
}

locals {
  chat_ui_bucket_name = "rag-eval-chat-ui-${data.aws_caller_identity.current.account_id}"
}

# S3 bucket for chat UI static files
resource "aws_s3_bucket" "chat_ui" {
  count  = var.deploy_chat_ui ? 1 : 0
  bucket = local.chat_ui_bucket_name

  tags = merge(var.tags, {
    Name = "RAGLens Chat UI"
  })
}

resource "aws_s3_bucket_versioning" "chat_ui" {
  count = var.deploy_chat_ui ? 1 : 0

  bucket = aws_s3_bucket.chat_ui[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "chat_ui" {
  count = var.deploy_chat_ui ? 1 : 0

  bucket = aws_s3_bucket.chat_ui[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "chat_ui" {
  count = var.deploy_chat_ui ? 1 : 0

  name                              = "rag-eval-chat-ui-oac"
  description                       = "OAC for Chat UI S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "chat_ui" {
  count = var.deploy_chat_ui ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "RAGLens Chat UI"
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.chat_ui[0].bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.chat_ui[0].id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.chat_ui[0].id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.chat_ui[0].id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # SPA fallback - serve index.html for 404
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = var.tags
}

# S3 bucket policy - allow CloudFront only
resource "aws_s3_bucket_policy" "chat_ui" {
  count = var.deploy_chat_ui ? 1 : 0

  bucket = aws_s3_bucket.chat_ui[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.chat_ui[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.chat_ui[0].arn
          }
        }
      }
    ]
  })
}

# Outputs
output "chat_ui_bucket_name" {
  description = "S3 bucket name for Chat UI"
  value       = var.deploy_chat_ui ? aws_s3_bucket.chat_ui[0].id : null
}

output "chat_ui_cloudfront_url" {
  description = "CloudFront URL for Chat UI"
  value       = var.deploy_chat_ui ? "https://${aws_cloudfront_distribution.chat_ui[0].domain_name}" : null
}

output "chat_ui_cloudfront_domain" {
  description = "CloudFront domain name"
  value       = var.deploy_chat_ui ? aws_cloudfront_distribution.chat_ui[0].domain_name : null
}

output "chat_ui_cloudfront_id" {
  description = "CloudFront distribution ID"
  value       = var.deploy_chat_ui ? aws_cloudfront_distribution.chat_ui[0].id : null
}
