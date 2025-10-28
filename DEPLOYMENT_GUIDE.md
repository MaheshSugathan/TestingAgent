# AWS Deployment Guide for RAG Agent Evaluation Platform

The deployment package is too large for direct Lambda upload. Here are the recommended deployment strategies:

## 🚀 Deployment Options

### Option 1: AWS Lambda Layers (Recommended)

Deploy dependencies as Lambda Layers to reduce package size:

```bash
# Create Lambda Layer for dependencies
mkdir -p layer/python
pip install -r requirements.txt -t layer/python/

# Package the layer
cd layer
zip -r dependencies-layer.zip python/
cd ..

# Upload to Lambda
aws lambda publish-layer-version \
    --layer-name rag-evaluation-dependencies \
    --zip-file fileb://layer/dependencies-layer.zip \
    --compatible-runtimes python3.11

# Deploy only application code
zip application.zip aws_lambda_handler.py cli.py
zip -r application.zip agents/ config/ evaluation/ observability/ orchestration/

# Create Lambda function with layer
aws lambda create-function \
    --function-name rag-evaluation-pipeline \
    --runtime python3.11 \
    --role arn:aws:iam::890742586186:role/rag-evaluation-lambda-role \
    --handler aws_lambda_handler.handler \
    --zip-file fileb://application.zip \
    --layers arn:aws:lambda:us-east-1:890742586186:layer:rag-evaluation-dependencies:1 \
    --timeout 900 \
    --memory-size 2048
```

### Option 2: AWS ECS Container Deployment

Deploy as Docker container to ECS:

```bash
# Build Docker image
docker build -t rag-evaluation-platform .

# Tag for ECR
export AWS_ACCOUNT_ID=890742586186
export AWS_REGION=us-east-1

aws ecr create-repository --repository-name rag-evaluation || true

docker tag rag-evaluation-platform:latest \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/rag-evaluation:latest

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Push image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/rag-evaluation:latest

# Deploy to ECS
aws ecs create-cluster --cluster-name rag-evaluation-cluster || true

# Create task definition
aws ecs register-task-definition \
    --family rag-evaluation-task \
    --network-mode awsvpc \
    --requires-compatibilities FARGATE \
    --cpu "1024" \
    --memory "2048" \
    --execution-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole \
    --container-definitions name=rag-evaluation,image=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/rag-evaluation:latest
```

### Option 3: Simplify Requirements

Reduce package size by removing heavy dependencies:

```bash
# Create minimal requirements.txt
cat > requirements-lambda.txt << EOF
boto3>=1.28.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
langchain>=0.1.0
langgraph>=0.0.1
EOF

# Build with minimal dependencies
pip install -r requirements-lambda.txt -t package/
zip -r deployment.zip package/
zip deployment.zip aws_lambda_handler.py
```

## 📊 Current Infrastructure

✅ **S3 Bucket**: rag-evaluation-documents-890742586186
- Documents: sample_documents.json
- Queries: sample_queries.txt

✅ **IAM Role**: rag-evaluation-lambda-role
- Lambda execution permissions
- S3 read access
- CloudWatch logging

## 🔧 Configuration

Update environment variables for your deployment:

```env
AWS_REGION=us-east-1
S3_BUCKET_NAME=rag-evaluation-documents-890742586186
BEDROCK_MODEL_ID=anthropic.claude-v2
```

## 📞 Next Steps

1. Choose a deployment option (Lambda Layers, ECS, or Simplified)
2. Configure your AWS environment
3. Deploy using the chosen method
4. Test the deployment
5. Monitor using CloudWatch

## 🔍 Monitoring

```bash
# Check logs
aws logs tail /aws/lambda/rag-evaluation-pipeline --follow

# Check metrics
aws cloudwatch get-metric-statistics \
    --namespace RAGEvaluationPipeline \
    --metric-name RetrievalTime \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Average
```

