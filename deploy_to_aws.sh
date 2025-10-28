#!/bin/bash
# AWS Deployment Script for RAG Evaluation Platform
# This script deploys the code from Git to AWS

set -e

echo "🚀 Starting AWS Deployment..."

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check Docker (for containerized deployment)
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. Skipping containerized deployment."
fi

# Step 1: Configure AWS
echo "📋 Step 1: Checking AWS Configuration..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "✅ AWS Account: $AWS_ACCOUNT_ID"
echo "✅ AWS Region: $AWS_REGION"

# Step 2: Create S3 Bucket
echo ""
echo "📦 Step 2: Setting up S3 Bucket..."
BUCKET_NAME="rag-evaluation-documents-${AWS_ACCOUNT_ID}"

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: $BUCKET_NAME"
    aws s3 mb "s3://$BUCKET_NAME" --region $AWS_REGION
    
    # Upload test documents
    echo "Uploading test documents..."
    aws s3 cp tests/data/sample_documents.json "s3://$BUCKET_NAME/" --region $AWS_REGION
    aws s3 cp tests/data/sample_queries.txt "s3://$BUCKET_NAME/" --region $AWS_REGION
else
    echo "✅ S3 bucket already exists: $BUCKET_NAME"
fi

# Step 3: Build Lambda Package
echo ""
echo "📦 Step 3: Building Lambda Deployment Package..."
mkdir -p package
pip install -r requirements.txt -t package/

cd package
zip -r9 ../deployment.zip .
cd ..

# Add application code
zip -g deployment.zip aws_lambda_handler.py cli.py
zip -g deployment.zip -r agents/ config/ evaluation/ observability/ orchestration/

echo "✅ Lambda package created: deployment.zip"

# Step 4: Deploy Lambda Function
echo ""
echo "📦 Step 4: Deploying Lambda Function..."

# Check if function already exists
if aws lambda get-function --function-name rag-evaluation-pipeline &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name rag-evaluation-pipeline \
        --zip-file fileb://deployment.zip
else
    echo "Creating new Lambda function..."
    
    # Create IAM role if it doesn't exist
    ROLE_NAME="rag-evaluation-lambda-role"
    
    if ! aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
        echo "Creating IAM role: $ROLE_NAME"
        
        # Create trust policy
        cat > /tmp/trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        aws iam create-role \
            --role-name $ROLE_NAME \
            --assume-role-policy-document file:///tmp/trust-policy.json
        
        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        # Attach S3 read policy
        aws iam attach-role-policy \
            --role-name $ROLE_NAME \
            --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
        
        # Attach Bedrock policy
        cat > /tmp/bedrock-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "*"
    }
  ]
}
EOF
        
        aws iam put-role-policy \
            --role-name $ROLE_NAME \
            --policy-name BedrockAccessPolicy \
            --policy-document file:///tmp/bedrock-policy.json
        
        sleep 10  # Wait for IAM role to propagate
    fi
    
    ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
    
    aws lambda create-function \
        --function-name rag-evaluation-pipeline \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler aws_lambda_handler.handler \
        --zip-file fileb://deployment.zip \
        --timeout 900 \
        --memory-size 2048 \
        --environment Variables="{AWS_REGION=$AWS_REGION,S3_BUCKET_NAME=$BUCKET_NAME}"
fi

echo "✅ Lambda function deployed successfully"

# Step 5: Deploy CloudFormation Stack
echo ""
echo "📦 Step 5: Deploying CloudWatch Dashboard..."

if aws cloudformation describe-stacks --stack-name rag-evaluation-dashboard &> /dev/null; then
    echo "Updating existing CloudFormation stack..."
    aws cloudformation update-stack \
        --stack-name rag-evaluation-dashboard \
        --template-body file://cloudformation/dashboard.yaml \
        --capabilities CAPABILITY_NAMED_IAM
else
    echo "Creating new CloudFormation stack..."
    aws cloudformation create-stack \
        --stack-name rag-evaluation-dashboard \
        --template-body file://cloudformation/dashboard.yaml \
        --capabilities CAPABILITY_NAMED_IAM
fi

echo "✅ CloudWatch Dashboard deployed"

# Step 6: Test Deployment
echo ""
echo "🧪 Step 6: Testing Deployment..."

# Test Lambda function
aws lambda invoke \
    --function-name rag-evaluation-pipeline \
    --payload '{"queries": ["What is machine learning?"], "session_id": "test-123"}' \
    response.json

echo "✅ Lambda function test completed"
cat response.json

# Cleanup
rm -rf package deployment.zip response.json /tmp/trust-policy.json /tmp/bedrock-policy.json

echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "📊 Deployment Summary:"
echo "  • Lambda Function: rag-evaluation-pipeline"
echo "  • S3 Bucket: $BUCKET_NAME"
echo "  • CloudWatch Dashboard: rag-evaluation-dashboard"
echo ""
echo "🔍 Next Steps:"
echo "  1. Test your Lambda function in the AWS Console"
echo "  2. Monitor metrics in CloudWatch Dashboard"
echo "  3. Upload documents to S3: aws s3 cp your-doc.json s3://$BUCKET_NAME/"
echo "  4. Check logs: aws logs tail /aws/lambda/rag-evaluation-pipeline --follow"

