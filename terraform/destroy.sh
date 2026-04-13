#!/bin/bash
# Script to safely destroy all infrastructure

set -e

echo "⚠️  WARNING: This will destroy all AWS infrastructure created by Terraform!"
echo ""
echo "This includes:"
echo "  - ECR repository and all container images"
echo "  - IAM roles and policies"
echo "  - S3 bucket and all contents"
echo "  - CloudWatch log groups"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🗑️  Destroying Terraform infrastructure..."
cd "$(dirname "$0")"
terraform destroy

echo ""
echo "⚠️  Note: You may also need to delete the Bedrock Agent Core runtime:"
echo "   cd .. && agentcore delete --agent-name rag_evaluation_agent"
echo ""
echo "✅ Infrastructure destroyed!"

