# Quick Start: Lambda + Cognito for Agent Core

## 🚀 Quick Deployment

### 1. Get Your Agent ARN

```bash
# Option A: Using agentcore CLI
agentcore list

# Option B: Using AWS CLI
aws bedrock-agentcore list-runtimes --region us-east-1
```

### 2. Deploy Infrastructure

```bash
cd terraform

# Deploy with Agent ARN
./deploy_lambda_cognito.sh <YOUR_AGENT_ARN>
```

### 3. Create Test User

```bash
# Get User Pool ID
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username testuser \
  --user-attributes Name=email,Value=test@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username testuser \
  --password YourSecurePass123! \
  --permanent
```

### 4. Test the API

```bash
# Set environment variables
export COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
export COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
export API_GATEWAY_URL=$(terraform output -raw api_gateway_url)
export COGNITO_PASSWORD='YourSecurePass123!'

# Run test script
python3 ../lambda/test_lambda_api.py
```

## 📋 What Gets Created

- ✅ **Cognito User Pool** - User authentication
- ✅ **Cognito User Pool Client** - OAuth client
- ✅ **Cognito Identity Pool** - Identity federation
- ✅ **Lambda Function** - Invokes Bedrock Agent Core
- ✅ **API Gateway** - REST API with Cognito authorizer
- ✅ **IAM Roles & Policies** - Secure permissions

## 🔗 Key Outputs

After deployment, get these values:

```bash
terraform output
```

- `api_gateway_url` - Your API endpoint
- `cognito_user_pool_id` - User Pool ID
- `cognito_user_pool_client_id` - Client ID for auth
- `lambda_function_name` - Lambda function name

## 📚 Full Documentation

See [LAMBDA_COGNITO_SETUP.md](./LAMBDA_COGNITO_SETUP.md) for:
- Detailed architecture
- Frontend integration examples
- Security best practices
- Troubleshooting guide

