# Lambda Function with Cognito Authentication for Agent Core

This guide explains how to deploy and use a Lambda function that securely accesses your Bedrock Agent Core runtime using AWS Cognito for authentication.

## 📋 Architecture Overview

```
User → API Gateway (Cognito Auth) → Lambda → Bedrock Agent Core Runtime
```

1. **User authenticates** with Cognito User Pool
2. **API Gateway** validates the Cognito token
3. **Lambda function** receives the authenticated request
4. **Lambda invokes** Bedrock Agent Core Runtime using IAM permissions
5. **Response** is returned to the user

## 🚀 Prerequisites

1. **Agent Core already deployed** - You need the Agent ARN from your deployed agentcore
2. **Terraform installed** (>= 1.0)
3. **AWS CLI configured** with appropriate permissions
4. **Python 3.11** (for Lambda function)

## 📦 Step 1: Get Your Agent ARN

First, get the ARN of your deployed Bedrock Agent Core agent:

```bash
# List your agents
agentcore list

# Or use AWS CLI
aws bedrock-agentcore list-runtimes --region us-east-1
```

The ARN will look like:
```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/your-runtime-id
```

## ⚙️ Step 2: Configure Terraform Variables

Update `terraform/terraform.tfvars` (or create it if it doesn't exist):

```hcl
aws_region = "us-east-1"
agent_name = "rag_evaluation_agent"
project_name = "rag-evaluation"

# REQUIRED: Add your Agent ARN here
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/your-runtime-id"
```

## 🏗️ Step 3: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform (if not already done)
terraform init

# Review the plan
terraform plan

# Deploy
terraform apply
```

This will create:
- ✅ Cognito User Pool and Client
- ✅ Cognito Identity Pool
- ✅ Lambda function with IAM role
- ✅ API Gateway with Cognito authorizer
- ✅ All necessary IAM policies and permissions

## 📝 Step 4: Create a Test User

After deployment, create a test user in Cognito:

```bash
# Get the User Pool ID from Terraform output
terraform output cognito_user_pool_id

# Create a user (replace USER_POOL_ID and email)
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username testuser \
  --user-attributes Name=email,Value=test@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id <USER_POOL_ID> \
  --username testuser \
  --password YourSecurePass123! \
  --permanent
```

## 🧪 Step 5: Test the API

### Option A: Using curl with Cognito Authentication

1. **Get API Gateway URL**:
```bash
terraform output api_gateway_url
```

2. **Authenticate and get tokens**:
```bash
# Get User Pool ID and Client ID
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)
CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)

# Initiate authentication
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=testuser,PASSWORD=YourSecurePass123! \
  --query 'AuthenticationResult.IdToken' \
  --output text > id_token.txt

ID_TOKEN=$(cat id_token.txt)
```

3. **Invoke the API**:
```bash
API_URL=$(terraform output -raw api_gateway_url)

curl -X POST $API_URL \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "What is RAG evaluation?",
    "sessionId": "test-session-123"
  }'
```

### Option B: Using Python Script

Create a test script `test_lambda_api.py`:

```python
import boto3
import requests
import json
import sys

# Configuration
USER_POOL_ID = "your-user-pool-id"  # From terraform output
CLIENT_ID = "your-client-id"         # From terraform output
API_URL = "https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/invoke"
USERNAME = "testuser"
PASSWORD = "YourSecurePass123!"

# Authenticate
cognito = boto3.client('cognito-idp')
response = cognito.initiate_auth(
    ClientId=CLIENT_ID,
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': USERNAME,
        'PASSWORD': PASSWORD
    }
)

id_token = response['AuthenticationResult']['IdToken']

# Invoke API
headers = {
    'Authorization': f'Bearer {id_token}',
    'Content-Type': 'application/json'
}

payload = {
    'inputText': 'What is RAG evaluation?',
    'sessionId': 'test-session-123'
}

response = requests.post(API_URL, headers=headers, json=payload)
print(json.dumps(response.json(), indent=2))
```

## 🔐 Step 6: Frontend Integration

### JavaScript/React Example

```javascript
import { CognitoUserPool, AuthenticationDetails, CognitoUser } from 'amazon-cognito-identity-js';

// Configuration
const userPoolId = 'your-user-pool-id';
const clientId = 'your-client-id';
const apiUrl = 'https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/invoke';

// Initialize Cognito
const poolData = {
  UserPoolId: userPoolId,
  ClientId: clientId
};
const userPool = new CognitoUserPool(poolData);

// Authenticate
function authenticate(username, password) {
  return new Promise((resolve, reject) => {
    const authenticationDetails = new AuthenticationDetails({
      Username: username,
      Password: password
    });

    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool
    });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (result) => {
        resolve(result.getIdToken().getJwtToken());
      },
      onFailure: (err) => {
        reject(err);
      }
    });
  });
}

// Invoke Agent Core
async function invokeAgentCore(inputText, sessionId) {
  const idToken = await authenticate('testuser', 'YourSecurePass123!');
  
  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${idToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      inputText: inputText,
      sessionId: sessionId
    })
  });

  return await response.json();
}

// Usage
invokeAgentCore('What is RAG?', 'session-123')
  .then(result => console.log(result))
  .catch(error => console.error(error));
```

## 📊 Monitoring and Logs

### View Lambda Logs

```bash
# Get function name
FUNCTION_NAME=$(terraform output -raw lambda_function_name)

# View logs
aws logs tail /aws/lambda/$FUNCTION_NAME --follow
```

### View API Gateway Logs

Enable API Gateway logging in the AWS Console or via Terraform.

### CloudWatch Metrics

- Lambda invocations, errors, duration
- API Gateway request count, latency, 4xx/5xx errors
- Cognito sign-in attempts

## 🔧 Configuration Options

### Update CORS Settings

Edit `terraform/cognito_lambda.tf` and update the CORS headers in:
- `aws_api_gateway_method_response.invoke_post_200`
- `aws_api_gateway_integration_response.invoke_post`
- `aws_api_gateway_method_response.invoke_options_200`
- `aws_api_gateway_integration_response.invoke_options`

Replace `'*'` with your specific domain:
```hcl
"method.response.header.Access-Control-Allow-Origin" = "'https://yourdomain.com'"
```

### Update Cognito Callback URLs

Edit `aws_cognito_user_pool_client.agentcore_client` in `terraform/cognito_lambda.tf`:

```hcl
callback_urls = [
  "https://yourdomain.com/callback",
  "http://localhost:3000/callback"  # For local development
]
```

### Adjust Lambda Timeout/Memory

Edit `aws_lambda_function.agentcore_invoker` in `terraform/cognito_lambda.tf`:

```hcl
timeout     = 300  # 5 minutes (max)
memory_size = 512  # MB
```

## 🛡️ Security Best Practices

1. **Use HTTPS only** in production
2. **Restrict CORS** to specific domains
3. **Enable MFA** in Cognito User Pool (set `mfa_configuration = "ON"`)
4. **Use least privilege** IAM policies
5. **Rotate Cognito client secrets** regularly
6. **Enable API Gateway throttling** to prevent abuse
7. **Monitor CloudWatch** for suspicious activity

## 🧹 Cleanup

To remove all resources:

```bash
cd terraform
terraform destroy
```

**Note**: This will delete:
- Cognito User Pool (and all users)
- Lambda function
- API Gateway
- IAM roles and policies
- CloudWatch log groups

## 📚 Additional Resources

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [API Gateway Cognito Authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Bedrock Agent Core Runtime](https://docs.aws.amazon.com/bedrock-agentcore/)

## 🐛 Troubleshooting

### Error: "User does not exist"
- Verify the user was created in Cognito
- Check the User Pool ID matches

### Error: "Invalid token"
- Token may have expired (default: 60 minutes)
- Re-authenticate to get a new token

### Error: "Access Denied" from Lambda
- Check Lambda IAM role has `bedrock-agent-runtime:InvokeAgent` permission
- Verify the Agent ARN is correct

### Error: "CORS" issues
- Check API Gateway CORS configuration
- Verify preflight OPTIONS request is configured

### Lambda timeout
- Increase Lambda timeout in Terraform
- Check Agent Core logs for performance issues

## 📝 Terraform Outputs Reference

After deployment, use these outputs:

```bash
terraform output
```

Key outputs:
- `api_gateway_url` - API endpoint URL
- `cognito_user_pool_id` - User Pool ID
- `cognito_user_pool_client_id` - Client ID for authentication
- `lambda_function_name` - Lambda function name
- `lambda_function_arn` - Lambda ARN

