# AWS Deployment Guide for RAG Agent Evaluation Platform

This guide provides step-by-step instructions for deploying the RAG Agent Evaluation Platform to AWS.

## 📋 Prerequisites

- AWS CLI installed and configured
- Docker installed (for containerized deployment)
- AWS credentials with appropriate permissions
- Python 3.11+ installed
- Access to AWS Bedrock, S3, CloudWatch, Lambda, ECS, and AgentCore

## 🚀 Deployment Steps

### 1. AWS Account Setup

```bash
# Configure AWS CLI
aws configure

# Set default region
export AWS_REGION=us-east-1
```

### 2. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Update .env with your AWS credentials
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
# AWS_REGION=us-east-1
```

### 3. S3 Bucket Setup

```bash
# Create S3 bucket for documents
aws s3 mb s3://rag-evaluation-documents --region us-east-1

# Upload test documents
aws s3 cp tests/data/sample_documents.json s3://rag-evaluation-documents/

# Upload configuration
aws s3 cp config/config.yaml s3://rag-evaluation-documents/config/
```

### 4. Lambda Function Deployment

```bash
# Build Lambda deployment package
pip install -r requirements.txt -t package/

# Create deployment package
cd package
zip -r9 ../deployment.zip .
cd ..

# Add application code
zip -g deployment.zip lambda_handler.py

# Deploy Lambda function
aws lambda create-function \
    --function-name rag-evaluation-pipeline \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
    --handler lambda_handler.handler \
    --zip-file fileb://deployment.zip \
    --timeout 900 \
    --memory-size 2048
```

### 5. ECS Deployment (Alternative)

```bash
# Build Docker image
docker build -t rag-evaluation-platform .

# Tag for ECR
docker tag rag-evaluation-platform:latest \
    123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-evaluation:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    123456789012.dkr.ecr.us-east-1.amazonaws.com

# Push to ECR
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-evaluation:latest

# Deploy ECS service
aws ecs create-service \
    --cluster rag-evaluation-cluster \
    --service-name rag-evaluation-service \
    --task-definition rag-evaluation-task \
    --desired-count 1 \
    --launch-type FARGATE
```

### 6. CloudFormation Stack Deployment

```bash
# Deploy CloudWatch Dashboard
aws cloudformation create-stack \
    --stack-name rag-evaluation-dashboard \
    --template-body file://cloudformation/dashboard.yaml \
    --capabilities CAPABILITY_NAMED_IAM
```

### 7. Bedrock Setup

```bash
# Enable Bedrock models (if not already enabled)
aws bedrock list-foundation-models \
    --region us-east-1

# Configure model access in IAM
aws iam create-policy --policy-name BedrockAccessPolicy \
    --policy-document file://bedrock-policy.json
```

### 8. AgentCore Integration

```bash
# Update AgentCore configuration
# Edit agentcore_agents/config.yaml with your AgentCore endpoint

# Deploy agents to AgentCore
python -m agentcore_agents.deploy

# Verify agent deployment
curl https://your-agentcore-url/agents/health
```

## 🔧 Configuration

### Environment Variables

Update `.env` with the following:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# S3 Configuration
S3_BUCKET_NAME=rag-evaluation-documents
S3_DOCUMENTS_PATH=documents/

# AgentCore Configuration
AGENTCORE_ENABLED=true
AGENTCORE_BASE_URL=https://your-agentcore-url
AGENTCORE_BILL_AGENT_NAME=bill

# CloudWatch Configuration
CLOUDWATCH_ENABLED=true
CLOUDWATCH_NAMESPACE=RAGEvaluationPipeline

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-v2
BEDROCK_REGION=us-east-1
```

### IAM Permissions

Required IAM policies:

1. **S3 Access**: Read/write access to S3 bucket
2. **Bedrock Access**: Invoke model access
3. **CloudWatch**: Put metrics and logs
4. **Lambda/ECS**: Execution permissions

## 📊 Monitoring

### CloudWatch Dashboard

Access the CloudWatch dashboard:
- Navigate to CloudWatch → Dashboards
- Open "RAG Evaluation Dashboard"

### Metrics Tracked

- **Retrieval Time**: Average time for document retrieval
- **Agent Response Time**: Time to generate responses
- **Evaluation Scores**: Quality scores (faithfulness, relevance, correctness)
- **Token Usage**: LLM token consumption
- **Error Rate**: Failure rate across components

## 🔍 Troubleshooting

### Common Issues

1. **Lambda Timeout**: Increase timeout to 900 seconds
2. **Bedrock Access**: Verify IAM permissions
3. **S3 Connection**: Check bucket policies
4. **AgentCore Connection**: Verify endpoint URL

### Debugging

```bash
# Check Lambda logs
aws logs tail /aws/lambda/rag-evaluation-pipeline --follow

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
    --namespace RAGEvaluationPipeline \
    --metric-name RetrievalTime \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Average

# Test deployment
aws lambda invoke \
    --function-name rag-evaluation-pipeline \
    --payload '{"test": "data"}' \
    response.json
```

## 🔄 Updates and Maintenance

### Update Lambda Function

```bash
# Update code
zip -g deployment.zip your_updated_file.py

# Update function
aws lambda update-function-code \
    --function-name rag-evaluation-pipeline \
    --zip-file fileb://deployment.zip
```

### Update ECS Service

```bash
# Update task definition
aws ecs update-service \
    --cluster rag-evaluation-cluster \
    --service rag-evaluation-service \
    --force-new-deployment
```

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)

## 📞 Support

For issues or questions:
- Create an issue on GitHub
- Check CloudWatch logs for errors
- Review IAM permissions
- Verify AgentCore connectivity

