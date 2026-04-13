# RAGLens — Solution Overview

## Executive Summary

RAGLens is a production-ready, multi-agent RAG (Retrieval-Augmented Generation) evaluation platform that automates the testing and evaluation of AI-powered applications. Built on AWS Bedrock Agent Core Runtime, this solution orchestrates three specialized agents using LangGraph to retrieve documents, generate responses, and comprehensively evaluate response quality using multiple evaluation methodologies.

The platform enables organizations to systematically test, benchmark, and improve their RAG systems with automated evaluation pipelines that combine both quantitative metrics (via Ragas) and qualitative assessment (via LLM-as-a-Judge).

---

## Problem Statement

As organizations increasingly deploy RAG-based applications, they face significant challenges in:

1. **Quality Assurance**: Ensuring generated responses are accurate, relevant, and faithful to source documents
2. **Systematic Testing**: Lack of automated, repeatable evaluation processes for RAG systems
3. **Performance Benchmarking**: Need for standardized metrics to compare and improve system performance over time
4. **Scalability**: Manual evaluation processes don't scale with increasing volumes of test cases
5. **Integration Complexity**: Coordinating multiple evaluation methods and external systems

RAGLens addresses these challenges by providing an automated, scalable, and comprehensive evaluation framework.

---

## Solution Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           AWS Bedrock Agent Core Runtime                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Entry Point (agentcore_entry.py)         │ │
│  │  - Receives evaluation requests                      │ │
│  │  - Extracts queries and parameters                   │ │
│  │  - Manages session lifecycle                         │ │
│  └───────────────────────┬────────────────────────────────┘ │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         LangGraph Workflow (Orchestration)            │ │
│  │                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  │  Retrieval   │→ │    Dev       │→ │  Evaluator   │ │
│  │  │    Agent     │  │    Agent     │  │    Agent     │ │
│  │  │              │  │              │  │              │ │
│  │  │ • S3 Fetch   │  │ • HTTP Call  │  │ • Ragas      │ │
│  │  │ • Parse Docs │  │ • Generate   │  │   Metrics    │ │
│  │  │ • Format     │  │   Response   │  │ • LLM Judge  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │
│  │                                                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Observability Layer                       │ │
│  │  - CloudWatch Logs                                    │ │
│  │  - CloudWatch Metrics                                 │ │
│  │  - Structured JSON logging                            │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS Services                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │    S3    │  │ Bedrock  │  │CloudWatch│  │    ECR   │   │
│  │          │  │          │  │          │  │          │   │
│  │Documents │  │LLM Models│  │Logs/Metrics│ │Container│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Principles

- **Multi-Agent Orchestration**: Specialized agents work in sequence, each handling a specific responsibility
- **State-Based Execution**: Pipeline state flows through the workflow, maintaining context and results
- **Error Resilience**: Graceful error handling with retry mechanisms at multiple levels
- **Observability First**: Comprehensive logging and metrics for monitoring and debugging
- **Cloud-Native**: Built on AWS managed services for scalability and reliability

---

## Key Components

### 1. Entry Point Layer

**Component**: `agentcore_entry.py`

**Purpose**: Interface between AWS Bedrock Agent Core Runtime and the evaluation pipeline.

**Key Responsibilities**:
- Receive and parse invocation events from Agent Core Runtime
- Extract evaluation queries and parameters from various event formats
- Initialize and manage pipeline instances (singleton pattern for efficiency)
- Format and return evaluation results to the runtime

### 2. Orchestration Layer

**Components**: 
- `orchestration/pipeline.py` - Pipeline coordinator
- `orchestration/workflow.py` - LangGraph workflow definition
- `orchestration/state.py` - State management

**Purpose**: Coordinate the multi-agent workflow execution.

**Key Features**:
- **RAGEvaluationPipeline**: Manages pipeline lifecycle, state transitions, and metrics collection
- **LangGraph Workflow**: Defines agent execution sequence with conditional flow logic
- **PipelineState**: Maintains data and metadata throughout the evaluation process

### 3. Agent Layer

#### 3.1 Retrieval Agent (`S3RetrievalAgent`)

**Purpose**: Retrieve and prepare source documents from S3 for evaluation.

**Capabilities**:
- Connect to configured S3 buckets
- List and fetch documents based on query parameters
- Parse multiple formats (JSON, TXT)
- Convert to standardized LangChain Document objects
- Handle errors gracefully with retry logic

**Input**: Query/metadata
**Output**: List of formatted documents ready for RAG processing

#### 3.2 Dev Agent (`DevAgent`)

**Purpose**: Generate responses using external agent integration.

**Capabilities**:
- Receive documents from retrieval agent
- Invoke external agent services (e.g., Bill agent) via HTTP
- Generate context-aware responses
- Handle retries, timeouts, and connection errors
- Track token usage and performance metrics

**Input**: Documents + Query
**Output**: Generated responses with metadata

#### 3.3 Evaluator Agent (`RAGEvaluatorAgent`)

**Purpose**: Evaluate generated responses for quality using multiple methods.

**Capabilities**:
- Execute Ragas evaluation metrics (faithfulness, relevance, correctness, context precision)
- Run LLM-as-a-Judge evaluation using AWS Bedrock models
- Calculate composite scores and thresholds
- Generate comprehensive evaluation reports
- Handle evaluation failures gracefully

**Input**: Documents + Query + Generated Response
**Output**: Evaluation scores, metrics, and detailed reports

### 4. Evaluation Layer

**Components**:
- `evaluation/ragas_evaluator.py` - Ragas metrics evaluation
- `evaluation/llm_judge.py` - LLM-as-a-Judge evaluation
- `evaluation/evaluation_metrics.py` - Metrics definitions

**Evaluation Methods**:

**Ragas Metrics**:
- **Faithfulness**: Measures how grounded the response is in the provided context
- **Relevance**: Assesses the relevance of retrieved context to the query
- **Correctness**: Evaluates factual accuracy of the response
- **Context Precision**: Measures the precision of retrieved context

**LLM-as-a-Judge**:
- Uses AWS Bedrock Claude models for qualitative assessment
- Provides structured JSON evaluation with reasoning
- Offers nuanced scoring and detailed feedback

### 5. Observability Layer

**Components**:
- `observability/logger.py` - Structured logging
- `observability/metrics.py` - CloudWatch metrics
- `observability/cloudwatch_handler.py` - CloudWatch integration

**Features**:
- JSON-structured logs for easy parsing and analysis
- CloudWatch Logs integration for centralized log management
- Custom metrics collection (execution time, success rates, scores)
- Error tracking and performance monitoring
- OpenTelemetry support for distributed tracing

### 6. Configuration Layer

**Components**:
- `config/config.yaml` - YAML configuration
- `config/config_manager.py` - Configuration loader
- `config/settings.py` - Pydantic settings

**Configuration Sources**:
1. YAML configuration file
2. Environment variables
3. Runtime overrides
4. AWS Parameter Store (future support)

---

## Workflow & Data Flow

### Evaluation Request Flow

```
1. User submits evaluation request
   ↓
2. AWS Bedrock Agent Core Runtime receives request
   ↓
3. Entry point extracts query and initializes pipeline
   ↓
4. Pipeline creates initial state with session ID
   ↓
5. LangGraph workflow orchestrates agent execution:
   
   a. Retrieval Agent
      - Fetches documents from S3
      - Parses and formats documents
      - Stores results in pipeline state
      ↓
   b. Dev Agent
      - Retrieves documents from state
      - Calls external agent service
      - Generates responses
      - Stores results in pipeline state
      ↓
   c. Evaluator Agent
      - Retrieves documents, query, and responses
      - Runs Ragas evaluation
      - Runs LLM-as-a-Judge evaluation
      - Calculates composite scores
      - Stores evaluation results in pipeline state
      ↓
6. Pipeline compiles final results
   ↓
7. Entry point formats response
   ↓
8. Results returned to user
```

### State Management

The `PipelineState` object carries data through the entire evaluation process:

- **Session Management**: Unique session IDs for tracking
- **Configuration**: Runtime configuration parameters
- **Metadata**: Query information, timestamps, and execution context
- **Agent Results**: Results from each agent (retrieval, dev, evaluator)
- **Metrics**: Execution times, success indicators, error information
- **Evaluation Output**: Final scores, reports, and recommendations

---

## Key Features

### 1. Multi-Agent Orchestration

- Three specialized agents working in coordination
- LangGraph-based workflow management
- Conditional flow logic based on success/failure
- State persistence throughout execution

### 2. Comprehensive Evaluation

- **Quantitative Metrics**: Ragas-based evaluation with multiple dimensions
- **Qualitative Assessment**: LLM-as-a-Judge for nuanced evaluation
- **Composite Scoring**: Combined metrics for overall quality assessment
- **Configurable Thresholds**: Customizable quality thresholds

### 3. Scalability & Performance

- Horizontal scaling via AWS Bedrock Agent Core Runtime
- Async/await throughout for concurrent processing
- Connection pooling for external services
- Pipeline singleton pattern for efficient resource usage

### 4. Reliability & Resilience

- Retry logic with exponential backoff
- Graceful error handling at each layer
- Error recovery mechanisms
- Detailed error reporting and logging

### 5. Observability

- Comprehensive CloudWatch integration
- Structured JSON logging
- Custom metrics collection
- Performance monitoring
- Distributed tracing support

### 6. Flexible Configuration

- YAML-based configuration
- Environment variable overrides
- Runtime parameter customization
- Multi-format document support

### 7. Multiple Deployment Options

- AWS Bedrock Agent Core Runtime (production)
- Local Docker deployment
- FastAPI server for local testing
- Docker Compose for development

---

## Technology Stack

### Core Technologies

- **Python 3.11+**: Primary programming language
- **LangGraph**: Workflow orchestration
- **LangChain**: Document processing and RAG utilities
- **FastAPI**: API server (for local deployment)

### AWS Services

- **AWS Bedrock Agent Core Runtime**: Container hosting and management
- **Amazon Bedrock**: LLM inference for evaluation
- **Amazon S3**: Document storage
- **Amazon CloudWatch**: Logging and metrics
- **Amazon ECR**: Container image registry
- **AWS IAM**: Authentication and authorization

### Evaluation Libraries

- **Ragas**: RAG evaluation metrics library
- **LLM-as-a-Judge**: Qualitative evaluation using LLMs

### Infrastructure

- **Docker**: Containerization
- **OpenTelemetry**: Observability instrumentation
- **Pydantic**: Data validation and settings management

---

## Deployment Model

### Production Deployment (AWS Bedrock Agent Core Runtime)

1. **Container Build**: Docker image with all dependencies
2. **ECR Push**: Image pushed to Amazon ECR
3. **Agent Core Configuration**: Runtime configuration via CLI
4. **Deployment**: Agent deployed to Bedrock Agent Core Runtime
5. **Scaling**: Automatic scaling managed by AWS

### Local Deployment Options

- **Docker Compose**: Full stack local deployment
- **FastAPI Server**: API-based local testing
- **Direct Python**: Development and testing

### Infrastructure as Code

- **Terraform**: Infrastructure provisioning (optional)
- **CloudFormation**: AWS resource management (optional)

---

## Integration Points

### 1. AWS Bedrock Agent Core Runtime

- **Protocol**: HTTP/JSON events
- **Interface**: Handler function in `agentcore_entry.py`
- **Purpose**: Host and manage the agent container

### 2. External Agent Services

- **Protocol**: HTTP/REST
- **Interface**: `agents/external_agent_interface.py`
- **Purpose**: Generate responses using external agent (e.g., Bill agent)
- **Features**: Retry logic, timeout handling, health checks

### 3. AWS Bedrock (LLM Models)

- **Service**: Amazon Bedrock
- **Models**: Claude 3 Sonnet (for LLM-as-a-Judge)
- **Interface**: boto3 `bedrock` client
- **Purpose**: LLM inference for qualitative evaluation

### 4. Amazon S3

- **Purpose**: Document storage for RAG evaluation
- **Interface**: boto3 `s3` client
- **Formats**: JSON, TXT files
- **Features**: List, fetch, parse documents

### 5. CloudWatch

- **Logs**: Structured JSON logs
- **Metrics**: Custom evaluation metrics
- **Dashboard**: Monitoring and alerting

---

## Use Cases

### 1. RAG System Quality Assurance

Evaluate the quality of RAG-based applications before production deployment, ensuring responses meet accuracy and relevance standards.

### 2. Continuous Performance Monitoring

Run automated evaluation pipelines as part of CI/CD workflows to monitor system performance over time and detect regressions.

### 3. Model Comparison

Compare different RAG implementations, models, or configurations by running standardized evaluations and comparing metrics.

### 4. Dataset Validation

Validate the quality of training or test datasets by evaluating how well the system performs on them.

### 5. A/B Testing

Compare different RAG configurations or models by running parallel evaluations and comparing results.

### 6. Research & Development

Support R&D efforts by providing comprehensive evaluation frameworks for experimenting with new approaches.

---

## Benefits

### 1. Automation

- Eliminates manual evaluation processes
- Reduces time-to-evaluation from hours to minutes
- Enables continuous testing and validation

### 2. Comprehensiveness

- Multiple evaluation methods provide holistic assessment
- Quantitative and qualitative metrics offer complete picture
- Standardized evaluation ensures consistency

### 3. Scalability

- Handles large volumes of test cases
- Automatic scaling via AWS managed services
- Efficient resource utilization

### 4. Reliability

- Production-ready with error handling and retries
- AWS managed infrastructure for high availability
- Comprehensive monitoring and alerting

### 5. Flexibility

- Configurable evaluation methods and thresholds
- Support for multiple document formats
- Extensible architecture for custom agents

### 6. Observability

- Complete visibility into evaluation process
- Detailed logs and metrics for debugging
- Performance monitoring and optimization

### 7. Cost Efficiency

- Pay-per-use pricing with AWS services
- Efficient resource utilization
- Container reuse reduces overhead

---

## Monitoring & Observability

### Logging

- **Format**: JSON-structured logs
- **Destination**: CloudWatch Logs
- **Levels**: DEBUG, INFO, WARNING, ERROR
- **Content**: Execution traces, agent results, errors, performance metrics

### Metrics

- **Namespace**: RAGEvaluation (configurable)
- **Key Metrics**:
  - Pipeline execution time
  - Agent success rates
  - Evaluation scores (by metric)
  - Error counts and types
  - Document retrieval statistics
  - Response generation latency

### CloudWatch Dashboard

- Real-time monitoring of evaluation pipelines
- Agent performance visualization
- Score trends over time
- Error rate tracking
- Resource utilization

### Alerting

- Configurable CloudWatch alarms
- Error rate thresholds
- Performance degradation detection
- Score threshold alerts

---

## Security

### Authentication & Authorization

- IAM role-based authentication
- No hardcoded credentials
- Principle of least privilege

### Data Security

- Encrypted data in transit (HTTPS/TLS)
- Encrypted data at rest (S3, CloudWatch)
- VPC isolation support

### Container Security

- Non-root user in containers
- Minimal base images
- Regular security scanning (ECR)

### Compliance

- CloudWatch encryption
- Audit logging
- Access control via IAM

---

## Future Enhancements

### Planned Features

1. **Additional Evaluation Metrics**: Support for more Ragas metrics and custom metrics
2. **Batch Processing**: Enhanced support for large-scale batch evaluations
3. **Caching**: Response caching for improved performance
4. **Multi-Model Support**: Support for additional LLM providers and models
5. **Dashboard UI**: Web-based dashboard for visualization and management
6. **Report Generation**: Automated report generation in various formats
7. **Parameter Store Integration**: AWS Systems Manager Parameter Store for configuration
8. **VPC Support**: Enhanced VPC configuration and networking

### Extension Points

- Custom agent development
- New evaluation method integration
- Additional external service integrations
- Custom metrics development

---

## Conclusion

RAGLens provides a comprehensive, scalable, and production-ready solution for evaluating RAG-based applications. By combining multiple evaluation methodologies with robust orchestration and observability, it enables organizations to systematically test, benchmark, and improve their AI systems.

With its cloud-native architecture, flexible configuration, and comprehensive monitoring, the platform supports both development and production use cases, making it an essential tool for teams deploying RAG applications.

---

## Related Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Detailed system architecture
- **[README.md](README.md)**: Getting started guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Deployment instructions
- **[AGENT_INVOCATION_FLOW.md](AGENT_INVOCATION_FLOW.md)**: How agents are invoked
- **[TROUBLESHOOTING_404.md](TROUBLESHOOTING_404.md)**: Common issues and solutions
