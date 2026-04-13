#!/bin/bash
# Setup script for MCP Server

echo "Setting up MCP Server for RAG Evaluation Pipeline..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Install dependencies
echo "Installing MCP dependencies..."
pip install --upgrade pip
pip install mcp httpx

# Make MCP server executable
chmod +x mcp_server.py

echo ""
echo "✅ MCP Server setup complete!"
echo ""
echo "Next steps:"
echo "1. Start your FastAPI server: python api_server.py"
echo "2. Verify MCP server in VSCode: Cmd+Shift+P -> 'MCP: List Servers'"
echo "3. Open Copilot Chat and select 'Agent' mode"
echo "4. Use the tools to interact with your RAG evaluation pipeline"
echo ""
echo "For detailed instructions, see MCP_SETUP.md"


