#!/bin/bash
# Deploy to AWS Bedrock Agent Core using Docker
set -e

echo "🚀 Starting Bedrock Agent Core Deployment..."

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="rag-evaluation-agent-core"
IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest"

echo "📋 Configuration:"
echo "  AWS Account: ${AWS_ACCOUNT_ID}"
echo "  Region: ${AWS_REGION}"
echo "  ECR Repository: ${ECR_REPO}"
echo "  Image: ${IMAGE_NAME}"

# Step 1: Create ECR Repository
echo ""
echo "📦 Step 1: Creating ECR Repository..."
aws ecr create-repository \
    --repository-name ${ECR_REPO} \
    --region ${AWS_REGION} || echo "✅ Repository already exists"

# Step 2: Login to ECR
echo ""
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 3: Build Docker Image
echo ""
echo "🏗️  Step 3: Building Docker Image..."
docker build -f Dockerfile.bedrock -t rag-evaluation-platform:latest .
docker tag rag-evaluation-platform:latest ${IMAGE_NAME}

# Step 4: Push to ECR
echo ""
echo "📤 Step 4: Pushing to ECR..."
docker push ${IMAGE_NAME}

# Step 5: Create Bedrock Agent
echo ""
echo "🤖 Step 5: Creating Bedrock Agent..."

# Create agent configuration
cat > agent-config.json << EOF
{
  "name": "rag-evaluation-agent",
  "version": "1.0.0",
  "runtime": {
    "image": "${IMAGE_NAME}",
    "ports": [
      {
        "containerPort": 8080,
        "name": "http"
      }
    ],
    "environment": [
      {
        "name": "AWS_REGION",
        "value": "${AWS_REGION}"
      },
      {
        "name": "S3_BUCKET_NAME",
        "value": "rag-evaluation-documents-${AWS_ACCOUNT_ID}"
      },
      {
        "name": "BEDROCK_MODEL_ID",
        "value": "anthropic.claude-v2"
      }
    ],
    "resources": {
      "cpu": "1 vCPU",
      "memory": "2 GB"
    },
    "healthCheck": {
      "path": "/health",
      "interval": 30,
      "timeout": 10,
      "retries": 3
    }
  },
  "instrumentation": {
    "logs": {
      "level": "INFO",
      "destination": {
        "cloudWatch": {
          "logGroup": "/aws/bedrock/agents/rag-evaluation"
        }
      }
    },
    "metrics": {
      "enabled": true,
      "destination": "cloudWatch"
    }
  },
  "connections": {
    "s3": {
      "bucket": "rag-evaluation-documents-${AWS_ACCOUNT_ID}",
      "permissions": ["read", "write"]
    },
    "bedrock": {
      "models": ["anthropic.claude-v2"],
      "permissions": ["invokeModel"]
    }
  }
}
EOF

echo "✅ Agent configuration created: agent-config.json"

# Step 6: Deploy to Bedrock
echo ""
echo "🚀 Step 6: Deploying to Bedrock..."

# Create Bedrock foundation model agent
cat > bedrock-agent-config.json << EOF
{
  "agentName": "rag-evaluation-agent",
  "agentResourceRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/BedrockAgentRole",
  "foundationModel": "anthropic.claude-v2",
  "description": "RAG evaluation agent for testing agents",
  "instruction": "You are an AI agent that evaluates RAG (Retrieval-Augmented Generation) systems. You analyze retrieval performance, response quality, and overall system effectiveness.",
  "promptOverrideConfiguration": {
    "promptTemplate": {
      "completionLambdaArn": "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:rag-evaluation-pipeline"
    }
  }
}
EOF

echo "✅ Bedrock agent configuration created"

# Step 7: Enable Bedrock (if needed)
echo ""
echo "🔧 Step 7: Checking Bedrock access..."
BEDROCK_MODELS=$(aws bedrock list-foundation-models \
    --region ${AWS_REGION} \
    --query 'modelSummaries[*].modelId' \
    --output text 2>/dev/null || echo "")

if [ -z "$BEDROCK_MODELS" ]; then
    echo "⚠️  Bedrock not enabled. Run: aws bedrock request-model-access request-model-access --region ${AWS_REGION}"
    echo "Or enable in AWS Console: https://console.aws.amazon.com/bedrock"
else
    echo "✅ Bedrock access confirmed"
fi

# Step 8: Create IAM Role for Bedrock Agent
echo ""
echo "🔐 Step 8: Creating IAM Role..."
ROLE_NAME="BedrockAgentRole"

if ! aws iam get-role --role-name ${ROLE_NAME} &> /dev/null; then
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
    
    echo "✅ IAM role created"
else
    echo "✅ IAM role already exists"
fi

echo ""
echo "🎉 Bedrock Agent Core Deployment Ready!"
echo ""
echo "📊 Deployment Summary:"
echo "  ✅ Docker Image: ${IMAGE_NAME}"
echo "  ✅ ECR Repository: ${ECR_REPO}"
echo "  ✅ Agent Configuration: agent-config.json"
echo "  ✅ Bedrock Configuration: bedrock-agent-config.json"
echo ""
echo "🔍 Next Steps:"
echo "  1. Enable Bedrock in AWS Console: https://console.aws.amazon.com/bedrock"
echo "  2. Review agent-config.json and bedrock-agent-config.json"
echo "  3. Create the agent using AWS Console or CLI"
echo "  4. Test the agent with sample queries"
echo ""
echo "📚 Documentation:"
echo "  - AWS Bedrock: https://docs.aws.amazon.com/bedrock/"
echo "  - Agent Core: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html"


