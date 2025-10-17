# Multi-Agent RAG Evaluation Pipeline

A comprehensive, modular Python project that implements a multi-agent RAG (Retrieval-Augmented Generation) evaluation pipeline using LangChain, LangGraph, AWS Bedrock, and Ragas.

## 🏗️ Architecture Overview

The pipeline consists of three main agents orchestrated by LangGraph:

1. **📥 RetrievalAgent**: Loads test datasets from S3 and converts them to LangChain documents
2. **🤖 DevAgent**: Simulates conversations using external Bill agent via AgentCore integration
3. **🧠 EvaluatorAgent**: Evaluates responses using Ragas metrics and LLM-as-a-Judge

## 🚀 Features

- **Modular Design**: Clean separation of concerns with dedicated modules for each component
- **Multi-Agent Orchestration**: Uses LangGraph for robust agent workflow management
- **Dual Evaluation**: Supports both Ragas metrics and LLM-as-a-Judge evaluation
- **External Agent Integration**: Seamless integration with Bill agent via AgentCore
- **Cloud Integration**: Full AWS integration with Bedrock, S3, and CloudWatch
- **Comprehensive Observability**: Detailed logging and metrics collection
- **Flexible Configuration**: YAML and environment variable support
- **CLI Interface**: Easy-to-use command-line interface
- **Testing Suite**: Comprehensive unit tests with sample data

## 📁 Project Structure

```
├── agents/                    # Agent implementations
│   ├── __init__.py
│   ├── base.py               # Base agent classes
│   ├── retrieval_agent.py    # S3 retrieval agent
│   ├── dev_agent.py          # Bill AgentCore agent
│   ├── external_agent_interface.py # AgentCore integration
│   └── evaluator_agent.py    # Evaluation agent
├── config/                   # Configuration management
│   ├── __init__.py
│   ├── config.yaml          # Default configuration
│   ├── config_manager.py    # Configuration loader
│   └── settings.py          # Pydantic settings
├── evaluation/               # Evaluation frameworks
│   ├── __init__.py
│   ├── evaluation_metrics.py # Metric definitions
│   ├── ragas_evaluator.py   # Ragas implementation
│   └── llm_judge.py         # LLM-as-a-Judge
├── orchestration/            # Workflow orchestration
│   ├── __init__.py
│   ├── pipeline.py          # Main pipeline orchestrator
│   ├── state.py             # State management
│   └── workflow.py          # LangGraph workflow
├── observability/            # Logging and metrics
│   ├── __init__.py
│   ├── cloudwatch_handler.py # CloudWatch integration
│   ├── logger.py            # Structured logging
│   └── metrics.py           # Metrics collection
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── data/                # Sample test data
│   ├── test_agents.py       # Agent tests
│   └── test_pipeline.py     # Pipeline tests
├── cli.py                   # Command-line interface
├── requirements.txt         # Python dependencies
├── env.example             # Environment variables template
└── README.md               # This file
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd TestingAgents
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your AWS credentials and configuration
   ```

4. **Configure AWS credentials**:
   ```bash
   aws configure
   # Or set environment variables in .env
   ```

## ⚙️ Configuration

The pipeline supports both YAML configuration files and environment variables:

### YAML Configuration (`config/config.yaml`)

```yaml
# AWS Configuration
aws:
  region: "us-east-1"
  cloudwatch:
    namespace: "RAGEvaluation"
    log_group: "/aws/rag-evaluation"

# AgentCore Configuration
agentcore:
  enabled: true
  base_url: "http://localhost:8000"
  askbill:
    agent_name: "askbill"
    timeout: 60
    max_retries: 3

# Bedrock Configuration (for LLM-as-a-Judge evaluation only)
bedrock:
  region: "us-east-1"
  models:
    judge: "anthropic.claude-3-sonnet-20240229-v1:0"

# S3 Configuration
s3:
  bucket: "rag-evaluation-datasets"
  key_prefix: "test-data/"
  supported_formats: ["json", "txt"]

# Agent Configuration
agents:
  dev:
    timeout: 60
    max_retries: 3
    context_window: 8000

# Evaluation Configuration
evaluation:
  ragas:
    enabled: true
    metrics: ["faithfulness", "relevance", "correctness"]
  llm_judge:
    enabled: true
    model: "anthropic.claude-3-sonnet-20240229-v1:0"
```

### Environment Variables

Key environment variables (see `env.example` for complete list):

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=rag-evaluation-datasets
BEDROCK_GENERATION_MODEL=anthropic.claude-3-sonnet-20240229-v1:0

# AgentCore Configuration
AGENTCORE_ENABLED=true
AGENTCORE_BASE_URL=http://localhost:8000
AGENTCORE_ASKBILL_AGENT_NAME=askbill

# Bedrock Configuration (for LLM-as-a-Judge evaluation only)
BEDROCK_REGION=us-east-1
BEDROCK_JUDGE_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

## 🎯 Usage

### Command Line Interface

The pipeline provides a comprehensive CLI for different evaluation scenarios:

#### Basic Single-Turn Evaluation

```bash
python cli.py evaluate --single-turn --query "What is machine learning?"
```

#### Multi-Turn Evaluation

```bash
python cli.py evaluate --multi-turn --queries-file tests/data/sample_queries.txt
```

#### Choose Evaluation Method

```bash
# Use only Ragas
python cli.py evaluate --judge ragas --query "What is RAG?"

# Use only LLM-as-a-Judge
python cli.py evaluate --judge llm --query "What is RAG?"

# Use both (default)
python cli.py evaluate --judge both --query "What is RAG?"
```

#### Configure Bill Agent

```bash
# Use default Bill agent
python cli.py evaluate --query "What is machine learning?"

# Specify custom AgentCore URL
python cli.py evaluate --agentcore-url http://your-agentcore-server:8000 --query "Test query"

# Specify custom Bill agent name
python cli.py evaluate --askbill-agent my-custom-askbill --query "Test query"
```

#### Save Results

```bash
python cli.py evaluate --query "What is machine learning?" --output results.json
```

#### Create CloudWatch Dashboard

```bash
python cli.py dashboard
```

#### Test Connectivity

```bash
python cli.py test
```

### Programmatic Usage

```python
import asyncio
from config import ConfigManager
from orchestration import RAGEvaluationPipeline

# Load configuration
config_manager = ConfigManager()
config = config_manager.load_config()

# Initialize pipeline
pipeline = RAGEvaluationPipeline(config)

# Run single-turn evaluation
async def main():
    result = await pipeline.run_single_turn_evaluation(
        query="What is machine learning?",
        session_id="my-session"
    )
    
    # Get summary
    summary = pipeline.get_pipeline_summary(result)
    print(f"Pipeline completed: {summary['success']}")
    print(f"Execution time: {summary['execution_time']:.2f}s")

asyncio.run(main())
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_agents.py
pytest tests/test_pipeline.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pytest --cov=. tests/
```

### Sample Data

The `tests/data/` directory contains sample documents and queries for testing:

- `sample_documents.json`: Sample documents in JSON format
- `sample_queries.txt`: Sample queries for evaluation

## 📊 Monitoring and Observability

### CloudWatch Metrics

The pipeline automatically sends metrics to CloudWatch:

- **Retrieval Metrics**: Document retrieval time, success/failure rates
- **Dev Agent Metrics**: Response latency, token usage, success rates
- **Evaluation Metrics**: Faithfulness, relevance, correctness scores
- **Pipeline Metrics**: Overall execution time, success/failure rates

### Logging

Structured JSON logging with:

- **Session Tracking**: Unique session IDs for traceability
- **Agent Context**: Detailed logging for each agent
- **Error Handling**: Comprehensive error logging with context
- **CloudWatch Integration**: Automatic log forwarding to CloudWatch

### Dashboard

Create a CloudWatch dashboard:

```bash
python cli.py dashboard
```

This creates a dashboard with widgets for:
- Retrieval agent performance
- Dev agent latency and token usage
- Evaluation scores over time
- Pipeline success rates

## 🔧 Development

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the `execute` method
3. Add the agent to the workflow in `orchestration/workflow.py`
4. Update tests in `tests/test_agents.py`

### Adding New Evaluation Metrics

1. Extend `EvaluationMetrics` in `evaluation/evaluation_metrics.py`
2. Implement the metric in either `RagasEvaluator` or `LLMJudgeEvaluator`
3. Update configuration schema
4. Add tests

### Custom Configuration

1. Add new fields to `config/settings.py`
2. Update `config/config.yaml` with defaults
3. Modify `ConfigManager` to handle the new configuration

## 🚨 Error Handling

The pipeline includes comprehensive error handling:

- **Retry Logic**: Configurable retries for transient failures
- **Graceful Degradation**: Continue execution even if some components fail
- **Error Tracking**: Detailed error logging and metrics
- **State Management**: Maintains pipeline state across failures

## 🔒 Security Considerations

- **AWS IAM**: Use least-privilege IAM policies
- **Environment Variables**: Store sensitive data in environment variables
- **VPC**: Consider running in a VPC for additional security
- **Encryption**: Enable encryption for S3 buckets and CloudWatch logs

## 📈 Performance Optimization

- **Parallel Processing**: Supports parallel evaluation when configured
- **Batch Operations**: Efficient batch processing for multiple queries
- **Caching**: Vector store caching for repeated evaluations
- **Resource Management**: Configurable timeouts and resource limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section below
2. Review the test suite for usage examples
3. Open an issue on GitHub
4. Check AWS CloudWatch logs for detailed error information

## 🔍 Troubleshooting

### Common Issues

1. **AWS Credentials**: Ensure AWS credentials are properly configured
2. **Bedrock Access**: Verify Bedrock access in your AWS region
3. **S3 Permissions**: Check S3 bucket permissions and access
4. **Memory Issues**: Adjust batch sizes for large datasets

### Debug Mode

Enable verbose logging:

```bash
python cli.py --verbose evaluate --query "test query"
```

### Health Checks

Run connectivity tests:

```bash
python cli.py test
```

This will verify:
- AWS credentials
- Bedrock access
- S3 bucket access
- Configuration validity

---

**Built with ❤️ using LangChain, LangGraph, AWS Bedrock, and Ragas**
