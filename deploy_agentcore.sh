#!/bin/bash
# Deploy to AWS Bedrock Agent Core Runtime
set -e

echo "🚀 Deploying to AWS Bedrock Agent Core Runtime..."
echo ""

# Check if agentcore CLI is installed
if ! command -v agentcore &> /dev/null; then
    echo "❌ agentcore CLI not found. Installing..."
    pip install bedrock-agentcore-starter-toolkit
fi

# Check if entry point exists
if [ ! -f "agentcore_entry.py" ]; then
    echo "❌ agentcore_entry.py not found!"
    echo "Creating it now..."
    # The file should already exist from previous step
    exit 1
fi

echo "📋 Using Agent Core Starter Toolkit to deploy..."
echo ""
echo "This will:"
echo "  1. Configure your agent (creates ECR, IAM roles, etc.)"
echo "  2. Build Docker container"
echo "  3. Push to ECR"
echo "  4. Deploy to Agent Core Runtime"
echo ""
echo "When prompted:"
echo "  - Execution role: Press Enter (auto-create)"
echo "  - ECR repository: Press Enter (auto-create)"
echo "  - Requirements: Confirm requirements.txt"
echo "  - OAuth: Type 'no'"
echo ""

# Configure the agent
echo "⚙️  Step 1: Configuring agent..."
echo "  (If already configured, this will use existing config)"
agentcore configure -e agentcore_entry.py || echo "Configuration may already exist"

echo ""
echo "🚀 Step 2: Launching to Agent Core Runtime..."
echo "  This will build, push, and deploy your agent..."
agentcore launch

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Test your agent:"
echo "     agentcore invoke '{\"prompt\": \"What is RAG?\"}'"
echo ""
echo "  2. List your agents:"
echo "     agentcore list"
echo ""
echo "  3. View logs:"
echo "     agentcore logs <agent-arn>"

