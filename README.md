# RAG Agent Evaluation Platform

A modular Python project implementing a multi-agent RAG (Retrieval-Augmented Generation) evaluation pipeline deployed on AWS Bedrock Agent Core.

## 🏗️ Architecture

### **Deployed Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│          AWS Bedrock Agent (rag-evaluation-agent)         │
│                   Status: PREPARED                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓
        ┌──────────────────────────────────┐
        │      Docker Container            │
        │  (Your RAG Evaluation Code)     │
        │                                  │
        │  ┌──────────────────────────┐   │
        │  │   LangGraph Pipeline      │   │
        │  │                          │   │
        │  │  Step 1: Retrieval       │   │
        │  │  ├─ Load from S3         │   │
        │  │  └─ Return docs          │   │
        │  │       ↓                    │   │
        │  │  Step 2: Dev Agent        │   │
        │  │  ├─ Use documents         │   │
        │  │  ├─ Call external agent   │   │
        │  │  └─ Generate response     │   │
        │  │       ↓                    │   │
        │  │  Step 3: Evaluator       │   │
        │  │  ├─ Evaluate response     │   │
        │  │  └─ Return scores         │   │
        │  └──────────────────────────┘   │
        └──────────────────────────────────┘
```

### **Agent Components:**

1. **S3RetrievalAgent** (`agents/retrieval_agent.py`)
   - Loads documents from S3
   - Returns LangChain Document objects

2. **DevAgent** (`agents/dev_agent.py`)
   - Uses documents from retrieval
   - Integrates with external agents via AgentCore
   - Generates responses

3. **RAGEvaluatorAgent** (`agents/evaluator_agent.py`)
   - Evaluates responses from DevAgent
   - Uses Ragas and LLM-as-a-Judge
   - Returns evaluation scores

4. **LangGraph Orchestration** (`orchestration/workflow.py`)
   - Coordinates the three agents
   - Manages pipeline flow
   - Handles state transitions

## 🚀 Deployment

### **Deployment Status:**

- **Agent ID**: `DBW5ST5EOA`
- **Alias ID**: `57RZ07YLVI`
- **Status**: ✅ PREPARED
- **Region**: us-east-1
- **Image**: `890742586186.dkr.ecr.us-east-1.amazonaws.com/rag-evaluation-agent-core:latest`

### **Deploy Command:**

```bash
./deploy_to_bedrock_agentcore.sh
```

This script:
1. Creates ECR repository
2. Builds Docker image
3. Pushes to ECR
4. Creates Bedrock agent
5. Sets up IAM roles
6. Configures S3 bucket

## 📋 Prerequisites

- AWS CLI configured
- Docker installed
- Python 3.11+
- AWS Bedrock access enabled

## 🔧 Configuration

Main configuration in `config/config.yaml`:

```yaml
agents:
  retrieval-agent:
    # S3 configuration
  dev-agent:
    # AgentCore integration
  evaluator-agent:
    # Evaluation settings
```

## 📖 Usage

### **Via AWS Console:**

https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/DBW5ST5EOA

### **Via Python SDK:**

```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId="DBW5ST5EOA",
    agentAliasId="57RZ07YLVI",
    sessionId="session-123",
    inputText="What is RAG?"
)

for event in response.get('completion', []):
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
```

## 📁 Project Structure

```
.
├── agents/                  # Agent implementations
│   ├── retrieval_agent.py   # S3 document retrieval
│   ├── dev_agent.py          # Response generation with external agent
│   ├── evaluator_agent.py    # RAG evaluation
│   └── external_agent_interface.py  # External agent integration
├── orchestration/            # LangGraph workflow
│   ├── workflow.py          # Agent orchestration
│   ├── pipeline.py          # Pipeline execution
│   └── state.py             # State management
├── evaluation/              # Evaluation logic
│   ├── ragas_evaluator.py   # Ragas evaluation
│   └── llm_judge.py         # LLM-as-a-Judge
├── observability/           # Logging and metrics
│   ├── cloudwatch_handler.py
│   ├── logger.py
│   └── metrics.py
├── config/                  # Configuration
│   └── config.yaml
├── tests/                   # Test data
│   └── data/
├── cloudformation/          # CloudFormation templates
│   └── dashboard.yaml
├── Dockerfile.bedrock       # Docker image for Bedrock
├── deploy_to_bedrock_agentcore.sh  # Deployment script
└── requirements.txt         # Python dependencies
```

## 🤝 External Agent Integration

The platform supports integration with external agents:

- **DevAgent** uses `BillAgentInterface` to connect to external agents
- HTTP-based communication
- Retry logic and error handling
- Configurable via `agentcore_base_url`

## 📊 Monitoring

- **CloudWatch Logs**: `/aws/bedrock/agents/rag-evaluation`
- **CloudWatch Metrics**: Custom metrics for evaluation scores
- **Console**: https://console.aws.amazon.com/cloudwatch/

## 🔗 Key URLs

- **Agent Console**: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/DBW5ST5EOA
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- **S3 Bucket**: `rag-evaluation-documents-890742586186`
- **ECR Repository**: `rag-evaluation-agent-core`

## 📝 License

MIT License

## 🎯 Status

✅ **Deployed and Ready**
- Agent is PREPARED and ready to receive queries
- All three internal agents orchestrated by LangGraph
- External agent connectivity configured
- Monitoring and logging enabled
