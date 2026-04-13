#!/bin/bash
# Complete cleanup script - destroys Terraform infrastructure AND Agent Core runtime

set -e

echo "⚠️  COMPLETE CLEANUP - This will remove EVERYTHING!"
echo ""
echo "This will destroy:"
echo "  ✅ Terraform infrastructure (ECR, IAM, S3, CloudWatch)"
echo "  ✅ Bedrock Agent Core runtime (if exists)"
echo ""
read -p "Are you absolutely sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Get agent name from terraform or use default
AGENT_NAME=${1:-rag_evaluation_agent}

echo ""
echo "🗑️  Step 1: Deleting Bedrock Agent Core runtime..."
cd "$(dirname "$0")/.."
if command -v agentcore &> /dev/null; then
    echo "   Attempting to delete agent: $AGENT_NAME"
    agentcore delete --agent-name "$AGENT_NAME" 2>/dev/null || echo "   Agent not found or already deleted"
else
    echo "   agentcore CLI not found, skipping agent deletion"
fi

echo ""
echo "🗑️  Step 2: Destroying Terraform infrastructure..."
cd terraform
terraform destroy -auto-approve

echo ""
echo "✅ Complete cleanup finished!"
echo ""
echo "All resources have been removed. You should no longer be charged for:"
echo "  - Agent Core Runtime"
echo "  - ECR storage"
echo "  - S3 storage"
echo "  - CloudWatch logs"
echo ""

