# Changelog

All notable changes to the RAG Evaluation Pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of RAG Evaluation Pipeline
- Multi-agent architecture with LangGraph orchestration
- RetrievalAgent for S3 document loading
- DevAgent for Bill AgentCore integration
- EvaluatorAgent with Ragas and LLM-as-a-Judge support
- Comprehensive CLI interface
- CloudWatch metrics and logging
- Unit test suite with sample data
- CloudFormation templates for dashboard setup
- Comprehensive documentation and README

### Changed
- Simplified architecture to use single DevAgent with Bill integration
- Removed BedrockDevAgent to focus on AgentCore integration
- Updated configuration to prioritize AgentCore over Bedrock
- Streamlined CLI options by removing agent-type selection

### Features
- **RetrievalAgent**: Load test datasets from S3 bucket with JSON/TXT support
- **DevAgent**: Simulate conversations using external Bill agent via AgentCore
- **EvaluatorAgent**: Evaluate responses using Ragas metrics and LLM-as-a-Judge
- **Orchestration**: LangGraph workflow with error handling and retries
- **Observability**: CloudWatch metrics, structured logging, and dashboard creation
- **Configuration**: YAML and environment variable support
- **CLI Interface**: Command-line tool with multiple evaluation modes
- **Testing**: Comprehensive unit tests with mocking and sample data

### CLI Commands
- `python cli.py evaluate` - Run evaluation pipeline
- `python cli.py dashboard` - Create CloudWatch dashboard
- `python cli.py test` - Run connectivity tests

### CLI Options
- `--single-turn` / `--multi-turn` - Evaluation modes
- `--judge ragas|llm|both` - Evaluation methods
- `--agent-type askbill|bedrock` - Dev agent selection
- `--agentcore-url` - Custom AgentCore service URL
- `--askbill-agent` - Custom Bill agent name
- `--query` / `--queries-file` - Input queries
- `--output` - Save results to file

### Configuration
- **AWS**: Region, CloudWatch namespace and log group
- **Bedrock**: Model IDs, temperature, max tokens
- **AgentCore**: Base URL, Bill agent configuration
- **S3**: Bucket name, key prefix, supported formats
- **Evaluation**: Ragas metrics, LLM-as-a-Judge settings
- **Agents**: Timeout, retries, batch size settings
- **Pipeline**: Session management, retry logic

### Metrics
- Retrieval time and success/failure rates
- Dev agent latency and token usage
- Evaluation scores (faithfulness, relevance, correctness)
- Pipeline execution time and success rates

### Architecture
- Modular design with clean separation of concerns
- LangGraph workflow orchestration
- External agent integration via HTTP API
- Comprehensive error handling and retry logic
- Session-based traceability
- CloudWatch integration for monitoring

## [1.0.0] - 2024-01-XX

### Added
- Initial release of the RAG Evaluation Pipeline
- Complete multi-agent system implementation
- AgentCore integration for external agent support
- Comprehensive testing and documentation

### Security
- Environment variable support for sensitive configuration
- AWS IAM integration with least-privilege principles
- Input validation and sanitization

### Performance
- Parallel evaluation support
- Efficient batch processing
- Configurable timeouts and resource limits
- Memory-optimized document processing

---

## Release Notes Template

### Breaking Changes
- None in initial release

### Migration Guide
- No migration needed for initial release

### Known Issues
- None currently known

### Deprecations
- None in initial release
