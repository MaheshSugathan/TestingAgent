# RAG Evaluation Platform

A production-ready multi-agent RAG (Retrieval-Augmented Generation) evaluation pipeline deployed on **AWS Bedrock Agent Core Runtime**.

## 🎯 Overview

The RAG Evaluation Platform orchestrates three specialized agents using LangGraph to:
1. **Retrieve** documents from S3
2. **Generate** responses using external agents
3. **Evaluate** response quality using Ragas and LLM-as-a-Judge

All deployed and running on AWS Bedrock Agent Core Runtime.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           AWS Bedrock Agent Core Runtime                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Entry Point (agentcore_entry.py)         │ │
│  └───────────────────────┬────────────────────────────────┘ │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         LangGraph Workflow (orchestration/)          │ │
│  │                                                       │ │
│  │  Retrieval → Dev → Evaluator                         │ │
│  │     ↓         ↓         ↓                            │ │
│  │   S3      External   Ragas+LLM                       │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Retrieval Agent**: Fetches documents from S3
- **Dev Agent**: Generates responses via external agent integration
- **Evaluator Agent**: Evaluates responses using Ragas and LLM-as-a-Judge
- **LangGraph**: Orchestrates the multi-agent workflow

📖 **Detailed Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker 20.10+
- AWS CLI configured
- Bedrock Agent Core access enabled

### Installation

```bash
# Clone repository
git clone <repository-url>
cd TestingAgents

# Install dependencies
pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit
```

### Deployment

```bash
# 1. Configure Agent Core
agentcore configure \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --disable-memory

# 2. Deploy to AWS
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --local-build

# 3. Verify deployment
agentcore status

# 4. Test invocation
agentcore invoke '{"prompt": "What is RAG?"}'
```

📖 **Complete Deployment Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## 📋 Usage

### Via Agent Core CLI

```bash
agentcore invoke '{"prompt": "What is RAG?"}'
```

### Via AWS SDK (Python)

```python
import boto3

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Get agent ARN from: agentcore status
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:...',
    runtimeSessionId='session-123',
    payload=json.dumps({"prompt": "What is RAG?"}).encode()
)

# Process streaming response
for line in response['response'].iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Via AWS CLI

```bash
AGENT_ARN=$(agentcore status | grep "Agent ARN" | tail -1 | awk '{print $NF}')

aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn "${AGENT_ARN}" \
  --input-text "What is RAG?" \
  --session-id "session-$(date +%s)" \
  --region us-east-1 \
  output.json
```

## 📁 Project Structure

```
TestingAgents/
├── agentcore_entry.py          # Entry point for Agent Core Runtime
├── Dockerfile.bedrock          # Docker image for deployment
├── requirements.txt            # Python dependencies
│
├── agents/                     # Agent implementations
│   ├── base.py                # Base agent class
│   ├── retrieval_agent.py     # S3 document retrieval
│   ├── dev_agent.py           # Response generation
│   ├── evaluator_agent.py     # Response evaluation
│   └── external_agent_interface.py  # External agent integration
│
├── orchestration/              # LangGraph workflow
│   ├── pipeline.py            # Pipeline coordinator
│   ├── workflow.py            # Workflow definition
│   └── state.py               # State management
│
├── evaluation/                 # Evaluation modules
│   ├── ragas_evaluator.py     # Ragas metrics
│   └── llm_judge.py          # LLM-as-a-Judge
│
├── observability/              # Logging and metrics
│   ├── logger.py              # Structured logging
│   └── metrics.py             # CloudWatch metrics
│
└── config/                     # Configuration
    ├── config.yaml            # YAML configuration
    └── config_manager.py      # Config loader
```

## 🔧 Configuration

### Environment Variables

Create `.env` file (optional):

```bash
AWS_REGION=us-east-1
S3_BUCKET=rag-evaluation-datasets
BEDROCK_REGION=us-east-1
```

### Configuration File

Edit `config/config.yaml`:

```yaml
aws:
  region: "us-east-1"

s3:
  bucket: "rag-evaluation-datasets"
  key_prefix: "test-data/"

bedrock:
  region: "us-east-1"
  models:
    judge: "anthropic.claude-3-sonnet-20240229-v1:0"

agentcore:
  enabled: true
  base_url: "http://localhost:8000"
  bill:
    agent_name: "bill"
    timeout: 60
```

## 📊 Monitoring

### CloudWatch Logs

```bash
LOG_GROUP="/aws/bedrock-agentcore/runtimes/rag_evaluation_agent-*-DEFAULT"

aws logs tail "${LOG_GROUP}" \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --follow \
  --region us-east-1
```

### CloudWatch Dashboard

- **GenAI Dashboard**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core
- **Agent Core Console**: https://console.aws.amazon.com/bedrock-agentcore/

## 🔍 Troubleshooting

### Common Issues

1. **404 Error**: Wrong API client or ARN format
   - See [TROUBLESHOOTING_404.md](TROUBLESHOOTING_404.md)

2. **boto3 Method Not Found**: Update boto3
   - See [AWS_SDK_SUPPORT.md](AWS_SDK_SUPPORT.md)

3. **Invocation Flow**: How agents are invoked
   - See [AGENT_INVOCATION_FLOW.md](AGENT_INVOCATION_FLOW.md)

## 📚 Documentation

- **[BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md)** - Business scenario, solution, uniqueness, benefits
- **[CASE_STUDY.md](CASE_STUDY.md)** - Case study: automated RAG evaluation at scale
- **[HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md)** - Human-in-the-loop (HITL) usage guide
- **[SITEMAP_QA_TESTING.md](SITEMAP_QA_TESTING.md)** - Sitemap-based Q&A generation and follow-up testing for help/support agents
- **[SITEMAP_QA_IMPLEMENTATION_PROMPT.md](SITEMAP_QA_IMPLEMENTATION_PROMPT.md)** - Copy-paste prompt to implement this QA flow in another project
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture
- **[SOLUTION_OVERVIEW.md](SOLUTION_OVERVIEW.md)** - Technical solution overview
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[AGENT_INVOCATION_FLOW.md](AGENT_INVOCATION_FLOW.md)** - How agents are invoked
- **[TROUBLESHOOTING_404.md](TROUBLESHOOTING_404.md)** - Fix 404 errors
- **[AWS_SDK_SUPPORT.md](AWS_SDK_SUPPORT.md)** - AWS SDK version requirements

## 🔐 Security

- IAM role-based authentication
- Non-root container user
- CloudWatch encrypted logs
- VPC isolation support

## 📝 License

MIT License

## 🎯 Status

✅ **Deployed and Operational**
- Agent Core Runtime: READY
- All agents: Functional
- Monitoring: Enabled
- Logs: Available in CloudWatch
