# RAGLens Chat (Web UI)

A simple web interface to invoke any AWS Bedrock Agent Core Runtime agent and view responses.

## Features

- 🚀 Invoke any Agent Core Runtime agent by ARN
- 💬 Send prompts/queries to agents
- 📊 View formatted responses
- 🔄 Session management support
- ⚡ Real-time response streaming
- 🎨 Modern, responsive UI

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS credentials configured (via `~/.aws/credentials` or environment variables)
- AWS Bedrock Agent Core access

## Setup

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
npm install
```

### 3. Configure AWS Credentials

Ensure your AWS credentials are configured:

```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

## Running the Application

### Option 1: Run Both Services Separately

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
# Or: uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

### Option 2: Use the Start Script

```bash
# Make script executable
chmod +x start.sh
./start.sh
```

## Usage

1. Open http://localhost:3000 in your browser
2. Enter your Agent ARN (e.g., `arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-name-id`)
3. Enter your prompt/query
4. Optionally provide a session ID for conversation continuity
5. Click "Invoke Agent"
6. View the response in the formatted output area

## Getting Your Agent ARN

You can get your agent ARN using:

```bash
agentcore status
# Or
aws bedrock-agentcore list-runtimes --region us-east-1
```

## API Endpoints

### POST `/api/invoke`

Invoke an Agent Core Runtime agent.

**Request:**
```json
{
  "agentArn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-name-id",
  "prompt": "What is RAG?",
  "sessionId": "optional-session-id"
}
```

**Response:**
```json
{
  "success": true,
  "output": "Agent response text...",
  "response": {
    "sessionId": "session-123",
    "agentArn": "...",
    "prompt": "...",
    "response": [...]
  },
  "metadata": {
    "sessionId": "session-123",
    "executionTime": 1.23,
    "agentArn": "..."
  }
}
```

## Troubleshooting

### Backend Issues

- **Import errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
- **AWS credentials**: Verify credentials with `aws sts get-caller-identity`
- **Region**: Set `AWS_REGION` environment variable if needed

### Frontend Issues

- **CORS errors**: Ensure backend is running on port 8000
- **Connection refused**: Check that backend is running: `curl http://localhost:8000/api/health`

### Agent Invocation Issues

- **Invalid ARN**: Verify the ARN format: `arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/AGENT-NAME-ID`
- **Permission denied**: Check IAM permissions for `bedrock-agentcore:InvokeAgentRuntime`
- **Agent not found**: Verify agent exists and is in READY state

## Development

### Backend Development

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
npm run dev
```

### Building for Production

```bash
# Build frontend
npm run build

# Frontend files will be in dist/
# Serve with any static file server
```

## Project Structure

```
web_ui/
├── backend/
│   ├── main.py              # FastAPI backend
│   └── requirements.txt     # Python dependencies
├── src/
│   ├── App.jsx              # Main React component
│   ├── main.jsx             # React entry point
│   └── index.css            # Styles
├── index.html               # HTML template
├── package.json             # Node dependencies
├── vite.config.js           # Vite configuration
└── README.md                # This file
```

## License

MIT

