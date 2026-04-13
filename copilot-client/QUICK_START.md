# Quick Start Guide

Get up and running in 5 minutes!

## 1. Install Dependencies

```bash
cd copilot-client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure VS Code

```bash
cp .vscode/settings.json.example .vscode/settings.json
```

Edit `.vscode/settings.json`:
- Update Python path if needed
- Set `RAG_API_URL` for local server (default: `http://localhost:8080`)
- Set `AGENT_RUNTIME_ARN` for Agent Core (when ready)

## 3. Make Scripts Executable

```bash
chmod +x mcp_server.py mcp_server_agentcore.py
```

## 4. Open in VS Code

```bash
code .
```

## 5. Reload VS Code

Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux) and type "Reload Window"

## 6. Test in Copilot Chat

Press `Cmd+L` (Mac) or `Ctrl+L` (Windows/Linux) to open Copilot Chat, then ask:

```
Check the health of the RAG evaluator
```

## ✅ You're Done!

The RAG Evaluator agent should now be available in Copilot Chat.

## Next Steps

- **Local Testing**: Ensure your API server is running on port 8080
- **Agent Core**: Configure `AGENT_RUNTIME_ARN` in settings.json
- **See README.md** for detailed usage examples

## Troubleshooting

- **Agent not loading?** Reload VS Code window
- **Connection errors?** Check API server is running (local) or AWS credentials (Agent Core)
- **Tools not available?** Check Copilot output panel for MCP server errors
