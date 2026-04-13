#!/bin/bash
# Complete deployment script for AWS Bedrock Agent Core
set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="rag-evaluation-agent-core"
IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"
AGENT_NAME="rag-evaluation-agent"

echo "🚀 Deploying LangGraph Agents to AWS Bedrock Agent Core..."
echo ""
echo "📋 Configuration:"
echo "  AWS Account: ${AWS_ACCOUNT_ID}"
echo "  Region: ${AWS_REGION}"
echo "  ECR Repository: ${ECR_REPO}"
echo "  Agent Name: ${AGENT_NAME}"
echo "  Image: ${IMAGE_NAME}"
echo ""

# Step 1: Create ECR repository
echo "📦 Step 1: Creating ECR repository..."
aws ecr create-repository \
    --repository-name ${ECR_REPO} \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 2>/dev/null || echo "✅ Repository already exists"

# Step 2: Login to ECR
echo ""
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 3: Build Docker image
echo ""
echo "🏗️  Step 3: Building Docker image..."
docker build -f Dockerfile.bedrock -t ${ECR_REPO}:latest .
docker tag ${ECR_REPO}:latest ${IMAGE_NAME}

# Step 4: Push to ECR
echo ""
echo "📤 Step 4: Pushing to ECR..."
docker push ${IMAGE_NAME}

# Step 5: Create IAM role
echo ""
echo "🔐 Step 5: Creating IAM Role..."
ROLE_NAME="BedrockAgentRole"
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"

if ! aws iam get-role --role-name ${ROLE_NAME} &>/dev/null; then
    echo "Creating IAM role: ${ROLE_NAME}"
    
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
    
    # Attach policies
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
    
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess
    
    # Add Bedrock invoke permissions
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
    
    echo "✅ IAM role created"
else
    echo "✅ IAM role already exists"
fi

# Step 6: Create or get Bedrock Agent
echo ""
echo "🤖 Step 6: Creating Bedrock Agent..."
AGENT_OUTPUT=$(aws bedrock-agent create-agent \
    --agent-name ${AGENT_NAME} \
    --agent-resource-role-arn ${ROLE_ARN} \
    --instruction "You are an AI agent that evaluates RAG (Retrieval-Augmented Generation) systems using a LangGraph multi-agent pipeline. The pipeline includes: 1. Document retrieval from S3, 2. Response generation using external agents, 3. Evaluation using Ragas and LLM-as-a-Judge metrics." \
    --description "RAG evaluation agent with LangGraph orchestration for multi-agent RAG system evaluation" \
    --region ${AWS_REGION} 2>&1)

if echo "$AGENT_OUTPUT" | grep -q "already exists" || echo "$AGENT_OUTPUT" | grep -q "ConflictException"; then
    echo "✅ Agent already exists, retrieving ID..."
    AGENT_ID=$(aws bedrock-agent list-agents \
        --region ${AWS_REGION} \
        --query "agentSummaries[?agentName=='${AGENT_NAME}'].agentId" \
        --output text | head -1)
    
    if [ -z "$AGENT_ID" ]; then
        echo "❌ Could not find agent. Please check AWS Console."
        exit 1
    fi
else
    AGENT_ID=$(echo "$AGENT_OUTPUT" | jq -r '.agent.agentId' 2>/dev/null || \
               echo "$AGENT_OUTPUT" | grep -oP '"agentId":\s*"\K[^"]+' | head -1)
fi

echo "✅ Agent ID: ${AGENT_ID}"

# Step 7: Create Agent Alias
echo ""
echo "📌 Step 7: Creating agent alias..."
aws bedrock-agent create-agent-alias \
    --agent-id ${AGENT_ID} \
    --agent-alias-name "test" \
    --region ${AWS_REGION} 2>/dev/null || echo "✅ Alias already exists"

# Step 8: Prepare Agent
echo ""
echo "⚙️  Step 8: Preparing agent..."
PREPARE_OUTPUT=$(aws bedrock-agent prepare-agent \
    --agent-id ${AGENT_ID} \
    --region ${AWS_REGION} 2>&1)

if echo "$PREPARE_OUTPUT" | grep -q "already prepared" || echo "$PREPARE_OUTPUT" | grep -q "PREPARED"; then
    echo "✅ Agent is already prepared"
else
    echo "⏳ Agent preparation initiated..."
fi

# Step 9: Check Agent Status
echo ""
echo "🔍 Step 9: Checking agent status..."
sleep 3
AGENT_STATUS=$(aws bedrock-agent get-agent \
    --agent-id ${AGENT_ID} \
    --region ${AWS_REGION} \
    --query 'agent.agentStatus' \
    --output text 2>/dev/null || echo "UNKNOWN")

echo "   Current Status: ${AGENT_STATUS}"

# Step 10: Summary
echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Deployment Summary"
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Docker Image: ${IMAGE_NAME}"
echo "  ✅ ECR Repository: ${ECR_REPO}"
echo "  ✅ Agent ID: ${AGENT_ID}"
echo "  ✅ Agent Name: ${AGENT_NAME}"
echo "  ✅ Region: ${AWS_REGION}"
echo "  ✅ Status: ${AGENT_STATUS}"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📝 Important Next Steps"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "1. ⚠️  CONFIGURE CONTAINER RUNTIME (Required):"
echo "   - Go to AWS Console: https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/agents/${AGENT_ID}"
echo "   - Click on your agent"
echo "   - Go to 'Runtime' or 'Container' tab"
echo "   - Set Container Image URI: ${IMAGE_NAME}"
echo "   - Set Port: 8080"
echo "   - Set Health Check Path: /health"
echo ""
echo "2. ⏳ WAIT FOR PREPARED STATUS:"
echo "   - Agent status should be 'PREPARED'"
echo "   - Check status: aws bedrock-agent get-agent --agent-id ${AGENT_ID} --region ${AWS_REGION}"
echo ""
echo "3. 🧪 TEST THE AGENT:"
echo ""
echo "   # Using AWS CLI:"
echo "   aws bedrock-agent-runtime invoke-agent \\"
echo "     --agent-id ${AGENT_ID} \\"
echo "     --agent-alias-id test \\"
echo "     --session-id test-session-$(date +%s) \\"
echo "     --input-text 'What is RAG?' \\"
echo "     --region ${AWS_REGION} \\"
echo "     response.json"
echo ""
echo "   # Using Python:"
echo "   import boto3"
echo "   client = boto3.client('bedrock-agent-runtime', region_name='${AWS_REGION}')"
echo "   response = client.invoke_agent("
echo "       agentId='${AGENT_ID}',"
echo "       agentAliasId='test',"
echo "       sessionId='session-123',"
echo "       inputText='Evaluate this RAG system'"
echo "   )"
echo ""
echo "4. 📚 VIEW LOGS:"
echo "   aws logs tail /aws/bedrock/agents/rag-evaluation --follow --region ${AWS_REGION}"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🔗 Useful Links"
echo "═══════════════════════════════════════════════════════════"
echo "  Agent Console: https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/agents/${AGENT_ID}"
echo "  CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups"
echo "  ECR Repository: https://console.aws.amazon.com/ecr/repositories/private/${AWS_ACCOUNT_ID}/${ECR_REPO}?region=${AWS_REGION}"
echo ""
echo "✅ Done! Remember to configure the container runtime in AWS Console."

