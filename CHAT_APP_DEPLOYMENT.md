# Chat App Deployment Guide

Deploy the RAGLens Chat UI to AWS with secure access via Cognito.

## Prerequisites

- AWS CLI configured
- Terraform 1.0+
- Node.js 18+
- Agent Core deployed (RAGLens)
- Agent HTTP URL or Agent ARN for invocation

## Step 1: Configure Terraform

Create or update `terraform/terraform.tfvars`:

```hcl
aws_region   = "us-east-1"
project_name = "rag-evaluation"

# Agent Core - use ONE of these:
agent_arn      = "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/xxx"  # If using boto3
agent_http_url = "https://your-agent-runtime-url"  # If Agent exposes HTTP (recommended)

# After first deploy, add CloudFront URL for Cognito login:
cognito_callback_urls = [
  "http://localhost:3000/callback",
  "http://localhost:5173/callback",
  "https://YOUR_CLOUDFRONT_ID.cloudfront.net/callback"
]
cognito_logout_urls = [
  "http://localhost:3000",
  "http://localhost:5173",
  "https://YOUR_CLOUDFRONT_ID.cloudfront.net"
]
```

## Step 2: Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This creates:
- Cognito User Pool
- Lambda + API Gateway (Cognito auth)
- S3 + CloudFront for Chat UI
- IAM roles

## Step 3: Build and Deploy Chat UI

```bash
# Get outputs
BUCKET=$(terraform -chdir=terraform output -raw chat_ui_bucket_name)
CF_ID=$(terraform -chdir=terraform output -raw chat_ui_cloudfront_id)

# Deploy
chmod +x scripts/deploy_chat_ui.sh
./scripts/deploy_chat_ui.sh "$BUCKET" "$CF_ID"
```

Or manually:

```bash
cd web_ui
npm install
npm run build
aws s3 sync dist/ s3://$BUCKET/ --delete
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

## Step 4: Get URLs

```bash
terraform -chdir=terraform output
```

- **Chat UI**: `chat_ui_cloudfront_url` (e.g. https://xxx.cloudfront.net)
- **API Gateway**: `api_gateway_url` (e.g. https://xxx.execute-api.us-east-1.amazonaws.com/prod/invoke)
- **Cognito**: `cognito_user_pool_id`, `cognito_user_pool_client_id`

## Step 5: Create User and Configure App

1. Create a user in Cognito:
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id $USER_POOL_ID \
     --username your@email.com \
     --user-attributes Name=email,Value=your@email.com Name=email_verified,Value=true \
     --temporary-password TempPass123!
   ```

2. Open the Chat UI URL in a browser.

3. In Settings:
   - **API URL**: Your API Gateway URL (e.g. `https://xxx.execute-api.us-east-1.amazonaws.com/prod`)
   - **Cognito Token**: Log in via Cognito Hosted UI, copy the `id_token` from the callback URL or browser dev tools, paste in Settings.

4. Enter an evaluation query and use the Human-in-the-loop toggle as needed.

## Local Development

```bash
# Terminal 1 - API server (runs pipeline)
python api_server.py
# or agentcore_entry for Agent Core

# Terminal 2 - Chat backend proxy (optional, if using api_server)
cd web_ui/backend
export API_SERVER_URL=http://localhost:8080
python main.py

# Terminal 3 - Frontend
cd web_ui
npm run dev
```

Open http://localhost:3000 (or 5173). Configure API URL to `http://localhost:8000` if using backend proxy, or `http://localhost:8080` to call api_server directly (adjust vite proxy if needed).

## Architecture

```
User → CloudFront (HTTPS) → S3 (static UI)
  ↓
  API calls with Bearer token
  ↓
API Gateway (Cognito Authorizer) → Lambda → Agent Core / Pipeline
```
