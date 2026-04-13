# Quick Reference Guide

## 🚀 Deployment Commands

```bash
# Configure Agent Core
agentcore configure --agent-name rag_evaluation_agent --region us-east-1 --disable-memory

# Deploy to AWS
agentcore launch --agent-name rag_evaluation_agent --region us-east-1 --local-build

# Check status
agentcore status

# Invoke agent
agentcore invoke '{"prompt": "What is RAG?"}'

# View logs
aws logs tail /aws/bedrock-agentcore/runtimes/rag_evaluation_agent-*-DEFAULT \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" --follow
```

## 📋 Common Tasks

### Update Deployment

```bash
# Make code changes, then:
agentcore launch --agent-name rag_evaluation_agent --region us-east-1 --local-build
```

### Check Agent Status

```bash
agentcore status
```

### Test Invocation

```bash
# Simple test
agentcore invoke '{"prompt": "What is RAG?"}'

# With session
agentcore invoke '{"prompt": "What is RAG?", "sessionId": "test-123"}'
```

### View Logs

```bash
# Get log group from agent status
LOG_GROUP=$(agentcore status | grep "Logs" | awk '{print $NF}')

# View recent logs
aws logs tail "${LOG_GROUP}" --since 10m --region us-east-1

# Follow logs
aws logs tail "${LOG_GROUP}" --follow --region us-east-1
```

## 🔧 Configuration

### Key Files

- `config/config.yaml` - Main configuration
- `agentcore_entry.py` - Entry point handler
- `Dockerfile.bedrock` - Container image
- `.bedrock_agentcore.yaml` - Agent Core config

### Environment Variables

```bash
AWS_REGION=us-east-1
S3_BUCKET=rag-evaluation-datasets
BEDROCK_REGION=us-east-1
```

## 📊 Monitoring

### CloudWatch Dashboard

- GenAI Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core
- Agent Core Console: https://console.aws.amazon.com/bedrock-agentcore/

### Metrics Namespace

- `RAGEvaluation` (configurable in config.yaml)

## 🔍 Troubleshooting

### Agent Not Found (404)

1. Check ARN format: `arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/AGENT-NAME-ID`
2. Use correct API: `bedrock-agentcore` (not `bedrock-agent-runtime`)
3. Update boto3: `pip install --upgrade boto3 botocore`

### Handler Not Found

1. Verify `agentcore_entry.py` exists
2. Check handler function is named `handler` or `handle`
3. Ensure Dockerfile CMD: `["python", "-m", "agentcore_entry"]`

### Import Errors

1. Check all dependencies in `requirements.txt`
2. Verify `PYTHONPATH` is set
3. Check relative imports are correct

## 📚 Documentation Links

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [AGENT_INVOCATION_FLOW.md](AGENT_INVOCATION_FLOW.md) - Invocation details
- [TROUBLESHOOTING_404.md](TROUBLESHOOTING_404.md) - Fix 404 errors
- [AWS_SDK_SUPPORT.md](AWS_SDK_SUPPORT.md) - SDK requirements

## 🔑 Key Concepts

### Agent Core Runtime

- Service: AWS Bedrock Agent Core Runtime
- Entry Point: `agentcore_entry.py::handler()`
- Protocol: HTTP/JSON events

### Agent Workflow

1. **Retrieval** → Fetch documents from S3
2. **Dev** → Generate responses via external agent
3. **Evaluator** → Evaluate using Ragas + LLM-as-a-Judge

### State Management

- LangGraph manages state transitions
- PipelineState carries data through workflow
- AgentResult stores individual agent outputs

