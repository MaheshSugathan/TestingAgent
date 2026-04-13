# Deploying LangGraph Agents to AWS Bedrock Agent Core

This guide explains how to deploy your LangGraph-based RAG evaluation pipeline to AWS Bedrock Agent Core.

## 📋 Prerequisites

1. **AWS CLI** installed and configured with credentials
   ```bash
   aws configure
   ```

2. **Docker** installed and running
   ```bash
   docker --version
   ```

3. **AWS Bedrock Access** enabled in your AWS account
   - Go to AWS Console → Bedrock → Model access
   - Request access to foundation models (e.g., Claude)

4. **IAM Permissions** - Your AWS user/role needs:
   - `ecr:*` (for pushing Docker images)
   - `bedrock:*` (for creating agents)
   - `iam:*` (for creating roles)
   - `s3:*` (for data access)

## 🚀 Deployment Steps

### Step 1: Update Dockerfile.bedrock

The `Dockerfile.bedrock` should run the API server, not the dev agent directly:

```dockerfile
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 2: Run Deployment Script

```bash
chmod +x deploy_to_bedrock_agentcore.sh
./deploy_to_bedrock_agentcore.sh
```

This script will:
1. ✅ Create ECR repository
2. ✅ Build Docker image
3. ✅ Push image to ECR
4. ✅ Create IAM role
5. ⚠️  Generate configuration files (you need to manually create the agent)

### Step 3: Create Bedrock Agent Core Agent

After the script runs, create the agent using AWS CLI:

```bash
# Get your account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPO="rag-evaluation-agent-core"
IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

# Create the agent using Bedrock Agent Core API
aws bedrock-agent create-agent \
    --agent-name "rag-evaluation-agent" \
    --agent-resource-role-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/BedrockAgentRole" \
    --instruction "You are an AI agent that evaluates RAG (Retrieval-Augmented Generation) systems. You analyze retrieval performance, response quality, and overall system effectiveness using LangGraph orchestration." \
    --description "RAG evaluation agent for testing agents using Bedrock Agent Core" \
    --region ${AWS_REGION}

# Note the agent ID from the output, then create an alias
AGENT_ID="<agent-id-from-above>"

aws bedrock-agent create-agent-alias \
    --agent-id ${AGENT_ID} \
    --agent-alias-name "test" \
    --region ${AWS_REGION}
```

### Step 4: Configure Agent Container

Bedrock Agent Core requires you to specify the container configuration. You can do this via:

**Option A: AWS Console**
1. Go to AWS Bedrock Console → Agents
2. Select your agent
3. Go to "Runtime" tab
4. Configure container:
   - Container Image: ECR image URI
   - Port: 8080
   - Health Check Path: `/health`

**Option B: Update via API (if supported)**
```bash
aws bedrock-agent update-agent \
    --agent-id ${AGENT_ID} \
    --runtime-configuration "{
        \"container\": {
            \"image\": \"${IMAGE_URI}\",
            \"port\": 8080,
            \"healthCheck\": {
                \"path\": \"/health\",
                \"interval\": 30,
                \"timeout\": 10
            }
        }
    }" \
    --region ${AWS_REGION}
```

### Step 5: Prepare Agent for Use

```bash
# Prepare the agent (this makes it ready to use)
aws bedrock-agent prepare-agent \
    --agent-id ${AGENT_ID} \
    --region ${AWS_REGION}
```

Wait for the agent status to become `PREPARED`:

```bash
# Check agent status
aws bedrock-agent get-agent \
    --agent-id ${AGENT_ID} \
    --region ${AWS_REGION} \
    --query 'agent.agentStatus' \
    --output text
```

## 📝 Complete Deployment Script

Here's an improved deployment script that includes agent creation:

```bash
#!/bin/bash
set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="rag-evaluation-agent-core"
IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"
AGENT_NAME="rag-evaluation-agent"

echo "🚀 Deploying to AWS Bedrock Agent Core..."

# Step 1: Create ECR repository
echo "📦 Creating ECR repository..."
aws ecr create-repository \
    --repository-name ${ECR_REPO} \
    --region ${AWS_REGION} 2>/dev/null || echo "✅ Repository already exists"

# Step 2: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 3: Build and push Docker image
echo "🏗️  Building Docker image..."
docker build -f Dockerfile.bedrock -t ${ECR_REPO}:latest .
docker tag ${ECR_REPO}:latest ${IMAGE_NAME}

echo "📤 Pushing to ECR..."
docker push ${IMAGE_NAME}

# Step 4: Create IAM role (if needed)
echo "🔐 Setting up IAM role..."
ROLE_NAME="BedrockAgentRole"

if ! aws iam get-role --role-name ${ROLE_NAME} &>/dev/null; then
    cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    aws iam create-role \
        --role-name ${ROLE_NAME} \
        --assume-role-policy-document file:///tmp/trust-policy.json
    
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess
    
    echo "✅ IAM role created"
else
    echo "✅ IAM role already exists"
fi

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 5: Create Bedrock Agent
echo "🤖 Creating Bedrock Agent..."
AGENT_OUTPUT=$(aws bedrock-agent create-agent \
    --agent-name ${AGENT_NAME} \
    --agent-resource-role-arn ${ROLE_ARN} \
    --instruction "You are an AI agent that evaluates RAG systems using LangGraph orchestration." \
    --description "RAG evaluation agent with LangGraph multi-agent pipeline" \
    --region ${AWS_REGION} 2>&1)

if echo "$AGENT_OUTPUT" | grep -q "already exists"; then
    echo "✅ Agent already exists, getting ID..."
    AGENT_ID=$(aws bedrock-agent list-agents \
        --region ${AWS_REGION} \
        --query "agentSummaries[?agentName=='${AGENT_NAME}'].agentId" \
        --output text | head -1)
else
    AGENT_ID=$(echo "$AGENT_OUTPUT" | grep -oP '"agentId":\s*"\K[^"]+' | head -1)
fi

echo "✅ Agent ID: ${AGENT_ID}"

# Step 6: Create Agent Alias
echo "📌 Creating agent alias..."
aws bedrock-agent create-agent-alias \
    --agent-id ${AGENT_ID} \
    --agent-alias-name "test" \
    --region ${AWS_REGION} 2>/dev/null || echo "✅ Alias already exists"

# Step 7: Prepare Agent
echo "⚙️  Preparing agent..."
aws bedrock-agent prepare-agent \
    --agent-id ${AGENT_ID} \
    --region ${AWS_REGION}

echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "📊 Summary:"
echo "  Agent ID: ${AGENT_ID}"
echo "  Image: ${IMAGE_NAME}"
echo "  Region: ${AWS_REGION}"
echo ""
echo "🔍 Next Steps:"
echo "  1. Wait for agent to be PREPARED (check status)"
echo "  2. Configure container runtime in AWS Console"
echo "  3. Test the agent"
echo ""
echo "📚 Useful Commands:"
echo "  # Check agent status"
echo "  aws bedrock-agent get-agent --agent-id ${AGENT_ID} --region ${AWS_REGION}"
echo ""
echo "  # Test agent"
echo "  aws bedrock-agent-runtime invoke-agent \\"
echo "    --agent-id ${AGENT_ID} \\"
echo "    --agent-alias-id test \\"
echo "    --session-id test-session \\"
echo "    --input-text 'What is RAG?' \\"
echo "    --region ${AWS_REGION} \\"
echo "    output.json"
```

## 🧪 Testing the Deployed Agent

### Using AWS CLI

```bash
# Get agent and alias IDs
AGENT_ID="<your-agent-id>"
ALIAS_ID="test"

# Invoke the agent
aws bedrock-agent-runtime invoke-agent \
    --agent-id ${AGENT_ID} \
    --agent-alias-id ${ALIAS_ID} \
    --session-id "session-$(date +%s)" \
    --input-text "Evaluate this RAG system" \
    --region us-east-1 \
    response.json

# View response
cat response.json | jq
```

### Using Python SDK

```python
import boto3
import json

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId="YOUR_AGENT_ID",
    agentAliasId="test",
    sessionId="session-123",
    inputText="What is RAG?"
)

for event in response.get('completion', []):
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
```

### Using AWS Console

1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
2. Select your agent
3. Click "Test alias"
4. Start chatting

## 🔧 Important Notes

### Container Requirements

Your container must:
- ✅ Expose port 8080
- ✅ Have `/health` endpoint returning 200
- ✅ Handle POST requests to `/` or `/invoke`
- ✅ Accept Bedrock Agent Core request format
- ✅ Return responses in expected format

### Request/Response Format

Bedrock Agent Core sends requests in a specific format. Your `api_server.py` needs to handle:

```python
# Request format (from Bedrock)
{
    "sessionId": "string",
    "inputText": "string",
    "messageVersion": "1.0"
}

# Expected response format
{
    "messageVersion": "1.0",
    "response": {
        "text": "string"
    }
}
```

You may need to create a Bedrock-specific endpoint or adapter.

### Environment Variables

Set these in the Bedrock agent configuration:
- `AWS_REGION`: us-east-1
- `PYTHONPATH`: /app
- `S3_BUCKET`: your-bucket-name
- `AGENTCORE_BASE_URL`: URL to external agent (if used)

## 🐛 Troubleshooting

### Agent Status Issues

```bash
# Check agent status
aws bedrock-agent get-agent --agent-id <ID> --region us-east-1

# Common statuses:
# - DRAFT: Agent being created
# - PREPARING: Agent is being prepared
# - PREPARED: Ready to use ✅
# - FAILED: Something went wrong ❌
# - NOT_PREPARED: Need to call prepare-agent
```

### Container Issues

Check CloudWatch logs:
```bash
aws logs tail /aws/bedrock/agents/rag-evaluation --follow
```

### Common Errors

1. **"Container failed to start"**
   - Check Dockerfile CMD is correct
   - Verify port 8080 is exposed
   - Check health endpoint works

2. **"Agent not PREPARED"**
   - Run `prepare-agent` command
   - Wait a few minutes
   - Check agent status

3. **"Permission denied"**
   - Verify IAM role has correct policies
   - Check ECR image permissions

## 📚 Additional Resources

- [AWS Bedrock Agent Core Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AWS Bedrock Agent API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_CreateAgent.html)
- [Docker Container Deployment Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-containers.html)

