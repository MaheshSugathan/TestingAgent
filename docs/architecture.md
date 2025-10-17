# RAG Evaluation Pipeline Architecture

## System Overview

The RAG Evaluation Pipeline is a multi-agent system that orchestrates document retrieval, response generation, and evaluation using AWS services and modern AI frameworks.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Evaluation Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Retrieval   │    │   Dev       │    │ Evaluator   │         │
│  │   Agent     │───▶│   Agent     │───▶│   Agent     │         │
│  │             │    │             │    │             │         │
│  │ • S3 Fetch  │    │ • Bedrock   │    │ • Ragas     │         │
│  │ • Doc Parse │    │ • RAG Chain │    │ • LLM Judge │         │
│  │ • CloudWatch│    │ • Metrics   │    │ • Metrics   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                LangGraph Orchestration                      │ │
│  │                                                             │ │
│  │ • State Management                                          │ │
│  │ • Error Handling                                            │ │
│  │ • Retry Logic                                               │ │
│  │ • Workflow Control                                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      AWS Services                               │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │     S3      │  │ AgentCore   │  │ CloudWatch  │            │
│  │             │  │             │  │             │            │
│  │ • Datasets  │  │ • Bill   │  │ • Metrics   │            │
│  │ • Documents │  │ • Agent     │  │ • Logs      │            │
│  │ • Results   │  │ • HTTP API  │  │ • Dashboard │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. RetrievalAgent
- **Purpose**: Load test datasets from S3 and convert to LangChain documents
- **Key Features**:
  - S3 integration with boto3
  - Support for JSON and TXT formats
  - Batch processing capabilities
  - CloudWatch logging and metrics

### 2. DevAgent
- **Purpose**: Simulate conversations using external Bill agent via AgentCore
- **Key Features**:
  - AgentCore integration
  - HTTP-based communication with retry logic
  - Health check capabilities
  - Token usage tracking
  - Response latency monitoring

### 3. EvaluatorAgent
- **Purpose**: Evaluate DevAgent responses using multiple methods
- **Key Features**:
  - Ragas metrics (faithfulness, relevance, correctness)
  - LLM-as-a-Judge evaluation
  - Structured JSON output
  - Comprehensive scoring

### 4. Orchestration Layer
- **Purpose**: Manage agent workflow and state
- **Key Features**:
  - LangGraph workflow management
  - State persistence
  - Error handling and retries
  - Session tracking

## Data Flow

1. **Initialization**: Pipeline loads configuration and initializes agents
2. **Retrieval**: RetrievalAgent fetches documents from S3
3. **Generation**: DevAgent processes documents and generates responses
4. **Evaluation**: EvaluatorAgent assesses response quality
5. **Reporting**: Results are logged and metrics are sent to CloudWatch

## Configuration Management

The system supports multiple configuration sources:
- YAML configuration files
- Environment variables
- Runtime parameter overrides
- AWS Systems Manager Parameter Store (future enhancement)

## Monitoring and Observability

### Metrics
- Pipeline execution time
- Agent success/failure rates
- Evaluation scores
- Token usage and costs
- Document retrieval performance

### Logging
- Structured JSON logging
- Session-based traceability
- Error context and stack traces
- Performance timing data

### Dashboards
- CloudWatch dashboard for real-time monitoring
- Custom widgets for each agent
- Historical trend analysis
- Alert configuration

## Security Considerations

- AWS IAM role-based access control
- Least-privilege permissions
- Encryption at rest and in transit
- VPC isolation options
- Audit logging

## Scalability

- Horizontal scaling through multiple pipeline instances
- Batch processing for large datasets
- Configurable resource limits
- Parallel evaluation support
- Efficient memory management

## Error Handling

- Graceful degradation on component failures
- Configurable retry policies
- Circuit breaker patterns
- Comprehensive error reporting
- State recovery mechanisms

## Future Enhancements

- Multi-region deployment support
- Advanced caching strategies
- Custom evaluation metrics
- Integration with other LLM providers
- Real-time streaming evaluation
