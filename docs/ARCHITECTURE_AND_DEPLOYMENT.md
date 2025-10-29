# 🏗️ Architecture & Deployment Guide

## 📋 Project Overview

RAG Agent Evaluation Platform - A multi-agent system for evaluating RAG (Retrieval-Augmented Generation) systems deployed on AWS Bedrock.

## 🎯 Current Deployment

- **Status**: ✅ PREPARED
- **Agent ID**: `DBW5ST5EOA`
- **Alias**: `test` (ID: `57RZ07YLVI`)
- **Region**: us-east-1
- **Foundation Model**: anthropic.claude-v2

---

## 🏗️ Architecture

### **System Components**

```
┌─────────────────────────────────────────────────────────────┐
│  AWS Bedrock Agent (rag-evaluation-agent)                  │
│  - Agent ID: DBW5ST5EOA                                    │
│  - Status: PREPARED                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓
        ┌──────────────────────────────────┐
        │   Docker Container               │
        │   Image: rag-evaluation-...     │
        │                                  │
        │   LangGraph Pipeline:            │
        │                                  │
        │   1. S3RetrievalAgent           │
        │      ↓                           │
        │   2. DevAgent                    │
        │      ↓                           │
        │   3. RAGEvaluatorAgent           │
        └──────────────────────────────────┘
```

### **Agent Descriptions**

#### **1. S3RetrievalAgent** (`agents/retrieval_agent.py`)
- Loads documents from S3 bucket
- Retrieves evaluation datasets
- Returns LangChain Document objects

#### **2. DevAgent** (`agents/dev_agent.py`)
- Receives documents from retrieval
- Generates responses using external agents
- Integrates with Bill agent via HTTP
- Uses AgentCore interface

#### **3. RAGEvaluatorAgent** (`agents/evaluator_agent.py`)
- Evaluates DevAgent responses
- Uses Ragas for metrics (faithfulness, relevance)
- Uses LLM-as-a-Judge for quality assessment
- Returns evaluation scores

#### **4. LangGraph Orchestration** (`orchestration/workflow.py`)
- Coordinates the three agents
- Manages state transitions
- Handles error conditions
- Implements retry logic

---

## 🚀 Deployment

### **Deployment Script**

Run: `./deploy_to_bedrock_agentcore.sh`

This script:
1. Creates ECR repository
2. Builds Docker image (`Dockerfile.bedrock`)
3. Pushes image to ECR
4. Creates S3 bucket with test documents
5. Creates IAM role for Bedrock
6. Creates Bedrock agent
7. Prepares agent for use

### **Configuration Files**

- `bedrock-agent-simple.json` - Agent configuration
- `Dockerfile.bedrock` - Container image
- `config/config.yaml` - Application configuration
- `requirements.txt` - Python dependencies

---

## 💻 Usage

### **1. AWS Console (Easiest)**

https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/DBW5ST5EOA

1. Click "Test alias"
2. Select "test" alias
3. Start chatting

### **2. Python SDK**

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

---

## 📁 Essential Files

### **Core Architecture**

- `agents/` - Agent implementations
  - `retrieval_agent.py` - S3 document retrieval
  - `dev_agent.py` - Response generation
  - `evaluator_agent.py` - Evaluation logic
  - `external_agent_interface.py` - External agent integration

- `orchestration/` - LangGraph workflow
  - `workflow.py` - Agent orchestration
  - `pipeline.py` - Pipeline execution
  - `state.py` - State management

- `evaluation/` - Evaluation modules
  - `ragas_evaluator.py` - Ragas metrics
  - `llm_judge.py` - LLM-as-a-Judge

- `observability/` - Monitoring
  - `cloudwatch_handler.py` - CloudWatch integration
  - `logger.py` - Logging
  - `metrics.py` - Metrics collection

### **Configuration**

- `config/config.yaml` - Main configuration
- `bedrock-agent-simple.json` - Bedrock agent config
- `Dockerfile.bedrock` - Container image
- `requirements.txt` - Dependencies

### **Deployment**

- `deploy_to_bedrock_agentcore.sh` - Deployment script
- `cloudformation/dashboard.yaml` - CloudFormation template

### **Documentation**

- `README.md` - Project overview
- `docs/architecture.md` - Architecture details
- `docs/*.drawio` - Architecture diagrams

---

## 🔗 Integration

### **External Agent Integration**

The `DevAgent` can connect to external agents:

```python
# DevAgent uses BillAgentInterface
agent = DevAgent(
    config=config,
    agentcore_base_url="http://external-agent-url",
    bill_agent_name="bill",
    timeout=60
)
```

This enables:
- HTTP-based communication
- Retry logic
- Error handling
- Session management

---

## 📊 Monitoring

### **CloudWatch**

- **Logs**: `/aws/bedrock/agents/rag-evaluation`
- **Metrics**: Custom evaluation metrics
- **Dashboard**: CloudFormation template included

### **Access**

- Agent Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/DBW5ST5EOA
- CloudWatch: https://console.aws.amazon.com/cloudwatch/
- ECR: `rag-evaluation-agent-core`
- S3: `rag-evaluation-documents-890742586186`

---

## 🎯 Key Features

- ✅ Multi-agent architecture with LangGraph
- ✅ S3 document retrieval
- ✅ External agent integration
- ✅ RAG evaluation (Ragas + LLM-as-a-Judge)
- ✅ AWS Bedrock deployment
- ✅ CloudWatch monitoring
- ✅ Docker containerization

---

## 📝 Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure AWS credentials: `aws configure`
4. Deploy: `./deploy_to_bedrock_agentcore.sh`
5. Test: Open AWS Console and use the Test alias

---

## 🔧 Development

### **Run Tests**

```bash
pytest tests/
```

### **Local Development**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/test_agents.py
```

---

## 📞 Support

- **Agent ID**: DBW5ST5EOA
- **Region**: us-east-1
- **Status**: PREPARED ✅

