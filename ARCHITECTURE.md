# RAG Evaluation Platform - Architecture

## 📐 System Architecture Overview

The RAG Evaluation Platform is a multi-agent system that orchestrates document retrieval, response generation, and evaluation using AWS Bedrock Agent Core Runtime.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Bedrock Agent Core Runtime                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Container                                │  │
│  │                                                                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │              Entry Point: agentcore_entry.py                  │ │  │
│  │  │  - Receives requests from Agent Core Runtime                  │ │  │
│  │  │  - Extracts prompt/input from event                           │ │  │
│  │  │  - Initializes and invokes pipeline                            │ │  │
│  │  │  - Returns formatted response                                 │ │  │
│  │  └───────────────────────┬──────────────────────────────────────┘ │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │        RAGEvaluationPipeline (orchestration/pipeline.py)    │ │  │
│  │  │  - Manages pipeline execution                               │ │  │
│  │  │  - Handles state management                                  │ │  │
│  │  │  - Coordinates LangGraph workflow                            │ │  │
│  │  │  - Collects metrics and logs                                │ │  │
│  │  └───────────────────────┬──────────────────────────────────────┘ │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │           LangGraph Workflow (orchestration/workflow.py)    │ │  │
│  │  │                                                              │ │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │ │  │
│  │  │  │  Retrieval   │→ │    Dev       │→ │  Evaluator   │      │ │  │
│  │  │  │    Agent     │  │    Agent     │  │    Agent     │      │ │  │
│  │  │  │              │  │              │  │              │      │ │  │
│  │  │  │ • S3 Fetch   │  │ • HTTP Call  │  │ • Ragas      │      │ │  │
│  │  │  │ • Parse Docs │  │ • Bill Agent│  │ • LLM Judge │      │ │  │
│  │  │  │ • Document   │  │ • Generate  │  │ • Metrics   │      │ │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘      │ │  │
│  │  │                                                              │ │  │
│  │  │  Error Handler ←───┘                                         │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                          │                                         │  │
│  │                          ▼                                         │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │              Observability Layer                              │ │  │
│  │  │  - CloudWatch Logs (observability/logger.py)                │ │  │
│  │  │  - CloudWatch Metrics (observability/metrics.py)             │ │  │
│  │  │  - Structured logging with JSON format                       │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           AWS Services                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │      S3       │  │   Bedrock    │  │ CloudWatch  │  │      ECR    │ │
│  │               │  │              │  │             │  │             │ │
│  │ • Datasets    │  │ • LLM Models │  │ • Logs      │  │ • Container │ │
│  │ • Documents    │  │ • Invoke API │  │ • Metrics   │  │   Images    │ │
│  │ • Results     │  │              │  │ • Dashboard │  │             │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐                                    │
│  │ Agent Core    │  │   IAM        │                                    │
│  │ Runtime       │  │              │                                    │
│  │               │  │ • Roles      │                                    │
│  │ • Runtime     │  │ • Policies   │                                    │
│  │ • Endpoints   │  │              │                                    │
│  └──────────────┘  └──────────────┘                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

## 🧩 Component Architecture

### 1. Entry Point Layer

**File**: `agentcore_entry.py`

**Purpose**: Interface between AWS Bedrock Agent Core Runtime and the application.

**Responsibilities**:
- Receives invocation events from Agent Core Runtime
- Extracts input text from various event formats (`prompt`, `input`, `inputText`, `text`)
- Initializes the pipeline (singleton pattern for efficiency)
- Invokes the pipeline with user query
- Formats and returns response to Agent Core Runtime

**Key Functions**:
```python
async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handler function for Agent Core Runtime."""
    # Extract input, initialize pipeline, execute, return response
```

### 2. Orchestration Layer

**Files**: 
- `orchestration/pipeline.py` - Pipeline coordinator
- `orchestration/workflow.py` - LangGraph workflow definition
- `orchestration/state.py` - State management

**Purpose**: Coordinates the multi-agent workflow.

**RAGEvaluationPipeline**:
- Manages pipeline lifecycle
- Handles state transitions
- Collects metrics and logs
- Provides pipeline summary

**LangGraph Workflow**:
- Defines agent execution sequence
- Manages conditional flow (success/failure paths)
- Handles error recovery
- Maintains state across agents

**PipelineState**:
- Carries data through the pipeline
- Stores agent results
- Tracks execution metadata
- Provides state reconstruction from dict

### 3. Agent Layer

**Files**:
- `agents/base.py` - Base agent class and interfaces
- `agents/retrieval_agent.py` - Document retrieval from S3
- `agents/dev_agent.py` - Response generation with external agent
- `agents/evaluator_agent.py` - Response evaluation
- `agents/external_agent_interface.py` - External agent communication

#### 3.1 Retrieval Agent (`S3RetrievalAgent`)

**Purpose**: Retrieve documents from S3 for RAG evaluation.

**Responsibilities**:
- Connect to S3 bucket
- List and fetch documents
- Parse JSON and TXT formats
- Convert to LangChain Document objects
- Handle errors gracefully

**Input**: Query/metadata
**Output**: List of LangChain Documents

#### 3.2 Dev Agent (`DevAgent`)

**Purpose**: Generate responses using external agent integration.

**Responsibilities**:
- Receive documents from retrieval agent
- Call external Bill agent via HTTP
- Generate responses with context
- Handle retries and timeouts
- Track token usage

**Input**: Documents + Query
**Output**: Generated responses with metadata

#### 3.3 Evaluator Agent (`RAGEvaluatorAgent`)

**Purpose**: Evaluate generated responses for quality.

**Responsibilities**:
- Run Ragas evaluation metrics
- Execute LLM-as-a-Judge evaluation
- Calculate composite scores
- Generate evaluation reports
- Handle evaluation failures

**Input**: Documents + Query + Generated Response
**Output**: Evaluation scores and metrics

### 4. Evaluation Layer

**Files**:
- `evaluation/ragas_evaluator.py` - Ragas metrics evaluation
- `evaluation/llm_judge.py` - LLM-as-a-Judge evaluation
- `evaluation/evaluation_metrics.py` - Metrics definitions

**Purpose**: Provide multiple evaluation methods.

**Ragas Evaluator**:
- Faithfulness metric
- Relevance metric
- Correctness metric
- Context precision metric

**LLM Judge**:
- Uses Bedrock Claude models
- Structured JSON evaluation
- Reasoning and scoring

### 5. Observability Layer

**Files**:
- `observability/logger.py` - Structured logging
- `observability/metrics.py` - CloudWatch metrics
- `observability/cloudwatch_handler.py` - CloudWatch integration

**Purpose**: Monitoring, logging, and observability.

**Features**:
- JSON-structured logs
- CloudWatch Logs integration
- Custom metrics collection
- Error tracking
- Performance monitoring

### 6. Configuration Layer

**Files**:
- `config/config.yaml` - YAML configuration
- `config/config_manager.py` - Configuration loader
- `config/settings.py` - Pydantic settings

**Purpose**: Centralized configuration management.

**Configuration Sources**:
1. YAML file (`config/config.yaml`)
2. Environment variables
3. Runtime overrides
4. AWS Parameter Store (future)

## 🔄 Data Flow

### Request Flow

```
1. User Request
   ↓
2. AWS Bedrock Agent Core Runtime
   ↓
3. agentcore_entry.py::handler()
   - Extracts: {"prompt": "What is RAG?"}
   - Creates session_id
   ↓
4. RAGEvaluationPipeline::run_single_turn_evaluation()
   - Creates PipelineState
   - Sets metadata
   ↓
5. LangGraph Workflow::ainvoke()
   ↓
6. retrieval_node()
   - Fetches documents from S3
   - Parses to LangChain Documents
   - Stores in state.retrieval_result
   ↓
7. dev_node()
   - Gets documents from state
   - Calls external Bill agent
   - Generates responses
   - Stores in state.dev_result
   ↓
8. evaluator_node()
   - Gets responses from state
   - Runs Ragas evaluation
   - Runs LLM-as-a-Judge
   - Stores in state.evaluator_result
   ↓
9. Final State
   - All agent results populated
   - Metrics collected
   ↓
10. handler() returns formatted response
    {
      "output": "...",
      "session_id": "...",
      "success": true,
      "evaluation_results": [...]
    }
```

### State Flow

```
PipelineState
├── session_id: "session-123"
├── pipeline_id: "pipeline-abc"
├── config: {...}
├── metadata: {
│     "queries": ["What is RAG?"],
│     "initial_data": {}
│   }
├── retrieval_result: AgentResult
│   ├── success: true
│   ├── data: {
│   │     "documents": [Document(...)],
│   │     "retrieval_metadata": {...}
│   │   }
│   └── execution_time: 0.5
├── dev_result: AgentResult
│   ├── success: true
│   ├── data: {
│   │     "generated_responses": [...],
│   │     "dev_metadata": {...}
│   │   }
│   └── execution_time: 2.3
└── evaluator_result: AgentResult
    ├── success: true
    ├── data: {
    │     "evaluation_results": [...],
    │     "evaluator_metadata": {...}
    │   }
    └── execution_time: 1.8
```

## 🔌 External Integrations

### AWS Bedrock Agent Core Runtime

- **Service**: AWS Bedrock Agent Core Runtime
- **Purpose**: Hosts and manages the agent container
- **Integration**: Via `agentcore_entry.py` handler function
- **Protocol**: HTTP/JSON events

### AWS Bedrock (LLM Models)

- **Service**: AWS Bedrock
- **Purpose**: LLM inference for LLM-as-a-Judge
- **Models**: Claude 3 Sonnet
- **Integration**: Via boto3 `bedrock` client

### AWS S3

- **Service**: Amazon S3
- **Purpose**: Document storage for RAG evaluation
- **Integration**: Via boto3 `s3` client
- **Format**: JSON and TXT files

### External Agent (Bill)

- **Service**: External HTTP service
- **Purpose**: Response generation
- **Protocol**: HTTP/REST
- **Integration**: Via `agents/external_agent_interface.py`

## 🔐 Security & Permissions

### IAM Roles

1. **Execution Role** (`AmazonBedrockAgentCoreSDKRuntime-*`)
   - Used by container runtime
   - Permissions: ECR, CloudWatch, Bedrock, S3

2. **CodeBuild Role** (`AmazonBedrockAgentCoreSDKCodeBuild-*`)
   - Used for building Docker images
   - Permissions: ECR push, S3 source, CloudWatch logs

### Security Features

- Non-root user in container
- IAM role-based authentication
- VPC isolation (if configured)
- CloudWatch encryption
- ECR image scanning

## 📊 Monitoring & Observability

### CloudWatch Logs

- **Log Group**: `/aws/bedrock-agentcore/runtimes/{agent-name}-DEFAULT`
- **Format**: JSON structured logs
- **Levels**: INFO, ERROR, DEBUG

### CloudWatch Metrics

- **Namespace**: `RAGEvaluation` (configurable)
- **Metrics**: 
  - Pipeline execution time
  - Agent success rates
  - Evaluation scores
  - Error counts

### OpenTelemetry

- Automatic instrumentation via `opentelemetry-instrument`
- Distributed tracing
- Metrics collection

## 🚀 Deployment Architecture

See `DEPLOYMENT.md` for detailed deployment steps.

### Deployment Components

1. **Docker Image** - Application container
2. **ECR Repository** - Image storage
3. **Agent Core Runtime** - Runtime environment
4. **IAM Roles** - Execution permissions
5. **CloudWatch** - Logs and metrics

## 📈 Scalability

### Horizontal Scaling

- Agent Core Runtime handles scaling automatically
- Multiple concurrent invocations supported
- Container reuse for efficiency

### Performance Optimization

- Pipeline singleton pattern (reuse initialization)
- Async/await throughout
- Efficient state management
- Connection pooling for external services

## 🔄 Error Handling

### Error Recovery

- Each agent handles errors independently
- LangGraph conditional edges for error paths
- Retry logic with exponential backoff
- Graceful degradation

### Error Reporting

- Errors logged to CloudWatch
- Error metrics tracked
- State includes error information
- Response includes error details

