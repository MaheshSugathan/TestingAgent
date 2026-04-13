#!/bin/bash
# Deploy Lambda function with Cognito authentication for Agent Core

set -e

echo "🚀 Deploying Lambda + Cognito infrastructure for Agent Core access..."

# Check if agent_arn is provided
if [ -z "$1" ]; then
    echo "❌ Error: Agent ARN is required"
    echo "Usage: ./deploy_lambda_cognito.sh <AGENT_ARN>"
    echo ""
    echo "Get your Agent ARN with:"
    echo "  agentcore list"
    echo "  # or"
    echo "  aws bedrock-agentcore list-runtimes --region us-east-1"
    exit 1
fi

AGENT_ARN=$1

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "📝 Creating terraform.tfvars from example..."
    if [ -f "terraform.tfvars.example" ]; then
        cp terraform.tfvars.example terraform.tfvars
    else
        cat > terraform.tfvars <<EOF
aws_region = "us-east-1"
agent_name = "rag_evaluation_agent"
project_name = "rag-evaluation"
agent_arn = "${AGENT_ARN}"
EOF
    fi
else
    # Update agent_arn in terraform.tfvars
    if grep -q "agent_arn" terraform.tfvars; then
        sed -i.bak "s|agent_arn = .*|agent_arn = \"${AGENT_ARN}\"|" terraform.tfvars
    else
        echo "agent_arn = \"${AGENT_ARN}\"" >> terraform.tfvars
    fi
fi

echo "✅ Agent ARN configured: ${AGENT_ARN}"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "🔧 Initializing Terraform..."
    terraform init
fi

# Plan
echo "📋 Planning Terraform deployment..."
terraform plan -out=tfplan

# Apply
echo "🚀 Applying Terraform configuration..."
terraform apply tfplan

# Get outputs
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Outputs:"
terraform output

echo ""
echo "📝 Next steps:"
echo "1. Create a test user:"
echo "   USER_POOL_ID=\$(terraform output -raw cognito_user_pool_id)"
echo "   aws cognito-idp admin-create-user \\"
echo "     --user-pool-id \$USER_POOL_ID \\"
echo "     --username testuser \\"
echo "     --user-attributes Name=email,Value=test@example.com \\"
echo "     --temporary-password TempPass123! \\"
echo "     --message-action SUPPRESS"
echo ""
echo "2. Set permanent password:"
echo "   aws cognito-idp admin-set-user-password \\"
echo "     --user-pool-id \$USER_POOL_ID \\"
echo "     --username testuser \\"
echo "     --password YourSecurePass123! \\"
echo "     --permanent"
echo ""
echo "3. Test the API:"
echo "   export COGNITO_USER_POOL_ID=\$(terraform output -raw cognito_user_pool_id)"
echo "   export COGNITO_CLIENT_ID=\$(terraform output -raw cognito_user_pool_client_id)"
echo "   export API_GATEWAY_URL=\$(terraform output -raw api_gateway_url)"
echo "   export COGNITO_PASSWORD='YourSecurePass123!'"
echo "   python3 ../lambda/test_lambda_api.py"

