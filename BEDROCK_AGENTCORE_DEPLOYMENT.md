# AWS Bedrock Agent Core Deployment Guide

This guide explains how to deploy your RAG evaluation platform to AWS Bedrock Agent Core using Docker containers.

## 📋 Prerequisites

- Docker installed
- AWS CLI configured with appropriate credentials
- AWS Account with Bedrock enabled
- Python 3.11+
- Access to ECR (Elastic Container Registry)

## 🏗️ Architecture

```
AWS Bedrock Agent Core
    ↓
Docker Container (Your Agents)
    ↓
ECR (Docker Image Storage)
    ↓
AWS Services (S3, Bedrock, CloudWatch)
```

## 🚀 Deployment Steps

### Step 1: Build and Push Docker Image

```bash
# Run the deployment script
./deploy_to_bedrock_agentcore.sh
```

This script will:
1. ✅ Create ECR repository
2. ✅ Build Docker image from Dockerfile.bedrock
3. ✅ Push image to ECR
4. ✅ Create agent configuration files
5. ✅ Set up IAM roles and permissions

### Step 2: Enable Bedrock (If Not Enabled)

```bash
# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1

# If not enabled, request model access
aws bedrock request-model-access \
    --model-id anthropic.claude-v2 \
    --region us-east-1
```

Or enable in AWS Console:
https://console.aws.amazon.com/bedrock

### Step 3: Create Bedrock Agent

After running the deployment script, you'll have:

1. **agent-config.json** - Agent configuration
2. **bedrock-agent-config.json** - Bedrock agent setup
3. **Docker image** in ECR

Create the agent using AWS Console:
1. Go to Bedrock Console
2. Navigate to "Agents"
3. Click "Create agent"
4. Upload `agent-config.json`
5. Configure runtime settings
6. Review and create

### Step 4: Test the Agent

```bash
# Test the agent
aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-v2 \
    --body '{"inputText": "What is machine learning?"}' \
    output.json

cat output.json
```

## 📁 What Gets Deployed

### Docker Container
- Your agent code (from `agents/` folder)
- All dependencies (from `requirements.txt`)
- Configuration files
- Health check endpoint

### ECR Image
- Repository: `rag-evaluation-agent-core`
- Image: `${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/rag-evaluation-agent-core:latest`
- All your code packaged and ready

### Agent Configuration
- **agent-config.json**: Runtime configuration
  - Port: 8080
  - Health check: /health
  - Resources: 1 vCPU, 2GB memory
  - Environment variables: AWS_REGION, S3_BUCKET_NAME

- **bedrock-agent-config.json**: Bedrock agent setup
  - Foundation model: anthropic.claude-v2
  - Instructions for the agent
  - Lambda integration for processing

## 🔧 Configuration

### Environment Variables

The agent will have access to:
```env
AWS_REGION=us-east-1
S3_BUCKET_NAME=rag-evaluation-documents-890742586186
BEDROCK_MODEL_ID=anthropic.claude-v2
```

### S3 Bucket

Documents are stored in:
- **Bucket**: `rag-evaluation-documents-890742586186`
- **Documents**: `sample_documents.json`
- **Queries**: `sample_queries.txt`

### IAM Permissions

The agent needs:
- S3 read/write access
- Bedrock invoke model access
- CloudWatch logging
- Lambda invocation (if using)

## 📊 Monitoring

### CloudWatch Logs
```bash
# View logs
aws logs tail /aws/bedrock/agents/rag-evaluation --follow
```

### CloudWatch Metrics
- Request count
- Latency
- Error rate
- Token usage

## 🔄 Updates

### Update Deployment

```bash
# Rebuild and push
docker build -f Dockerfile.bedrock -t rag-evaluation-platform:latest .
docker tag rag-evaluation-platform:latest ${IMAGE_NAME}
docker push ${IMAGE_NAME}

# Update agent (in AWS Console)
# Navigate to agent → Update → Select new image
```

### Rollback

```bash
# List image versions
aws ecr describe-images --repository-name rag-evaluation-agent-core

# Rollback to previous version in AWS Console
```

## 🧪 Testing

### Local Testing
```bash
# Build locally
docker build -f Dockerfile.bedrock -t rag-test .

# Run locally
docker run -p 8080:8080 \
  -e AWS_REGION=us-east-1 \
  -e S3_BUCKET_NAME=rag-evaluation-documents-890742586186 \
  rag-test

# Test health endpoint
curl http://localhost:8080/health
```

### Production Testing

```bash
# Test agent endpoint
curl https://your-bedrock-agent-url/invoke \
  -H "Content-Type: application/json" \
  -d '{"inputText": "Test query"}'
```

## 🐛 Troubleshooting

### Common Issues

1. **ECR Login Failed**
```bash
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    890742586186.dkr.ecr.us-east-1.amazonaws.com
```

2. **Bedrock Not Enabled**
- Enable in AWS Console
- Request model access
- Wait for approval

3. **Agent Not Responding**
- Check CloudWatch logs
- Verify IAM permissions
- Check health endpoint

4. **Image Too Large**
- Optimize Docker image
- Use multi-stage builds
- Remove unnecessary dependencies

## 📚 Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Agent Core Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [ECS with Bedrock](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)

## ✅ Success Checklist

- [ ] Docker image built successfully
- [ ] Image pushed to ECR
- [ ] Bedrock enabled and accessible
- [ ] Agent created in Bedrock
- [ ] IAM permissions configured
- [ ] Health check passing
- [ ] Test query successful
- [ ] Monitoring setup complete

## 🎉 Deployment Complete!

Your RAG evaluation platform is now running on AWS Bedrock Agent Core!

Next steps:
1. Test with real queries
2. Monitor performance
3. Set up alerts
4. Scale as needed

