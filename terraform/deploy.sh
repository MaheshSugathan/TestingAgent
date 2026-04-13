#!/bin/bash
# Script to deploy infrastructure and agent

set -e

echo "🚀 Deploying infrastructure with Terraform..."
cd "$(dirname "$0")"

# Initialize if needed
if [ ! -d ".terraform" ]; then
    echo "📦 Initializing Terraform..."
    terraform init
fi

# Plan
echo "📋 Planning infrastructure changes..."
terraform plan

# Apply
echo ""
read -p "Apply these changes? (type 'yes' to continue): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🏗️  Creating infrastructure..."
terraform apply -auto-approve

# Get outputs
echo ""
echo "📊 Infrastructure created! Outputs:"
terraform output

echo ""
echo "✅ Infrastructure is ready!"
echo ""
echo "Next steps:"
echo "  1. Update .bedrock_agentcore.yaml with the output values above"
echo "  2. Deploy your agent: cd .. && agentcore launch"
echo ""

