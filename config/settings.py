"""Pydantic settings for the RAG evaluation pipeline."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AWSConfig(BaseModel):
    """AWS configuration."""
    region: str = Field(default="us-east-1", description="AWS region")
    cloudwatch: Dict[str, str] = Field(
        default={
            "namespace": "RAGEvaluation",
            "log_group": "/aws/rag-evaluation"
        }
    )


class BedrockConfig(BaseModel):
    """Bedrock configuration."""
    region: str = Field(default="us-east-1", description="Bedrock region")
    models: Dict[str, str] = Field(
        default={
            "embedding": "amazon.titan-embed-text-v1",
            "generation": "anthropic.claude-3-sonnet-20240229-v1:0",
            "judge": "anthropic.claude-3-sonnet-20240229-v1:0"
        }
    )
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    temperature: float = Field(default=0.1, description="Temperature")


class AgentCoreConfig(BaseModel):
    """AgentCore configuration."""
    enabled: bool = Field(default=True, description="Enable AgentCore integration")
    base_url: str = Field(default="http://localhost:8000", description="AgentCore service URL")
    bill: Dict[str, Any] = Field(
        default={
            "agent_name": "bill",
            "timeout": 60,
            "max_retries": 3,
            "health_check_interval": 30
        }
    )


class S3Config(BaseModel):
    """S3 configuration."""
    bucket: str = Field(description="S3 bucket name")
    key_prefix: str = Field(default="test-data/", description="Key prefix")
    supported_formats: List[str] = Field(
        default=["json", "txt"], 
        description="Supported file formats"
    )


class EvaluationConfig(BaseModel):
    """Evaluation configuration."""
    ragas: Dict[str, any] = Field(
        default={
            "enabled": True,
            "metrics": ["faithfulness", "relevance", "correctness", "context_precision"]
        }
    )
    llm_judge: Dict[str, any] = Field(
        default={
            "enabled": True,
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "temperature": 0.0,
            "max_tokens": 1024
        }
    )
    thresholds: Dict[str, float] = Field(
        default={
            "faithfulness": 0.8,
            "relevance": 0.8,
            "correctness": 0.8,
            "overall": 0.8
        }
    )


class AgentConfig(BaseModel):
    """Agent configuration."""
    retrieval: Dict[str, int] = Field(
        default={"timeout": 30, "max_retries": 3, "batch_size": 10}
    )
    dev: Dict[str, int] = Field(
        default={"timeout": 60, "max_retries": 3, "context_window": 8000}
    )
    evaluator: Dict[str, int] = Field(
        default={"timeout": 45, "max_retries": 2}
    )


class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    session_id_prefix: str = Field(default="rag-eval")
    enable_retries: bool = Field(default=True)
    max_pipeline_retries: int = Field(default=2)
    parallel_evaluation: bool = Field(default=True)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    include_trace_id: bool = Field(default=True)


class Settings(BaseSettings):
    """Main settings class."""
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "us-east-1"
    
    # Bedrock Configuration
    bedrock_region: str = "us-east-1"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v1"
    bedrock_generation_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_judge_model: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # AgentCore Configuration
    agentcore_enabled: bool = True
    agentcore_base_url: str = "http://localhost:8000"
    agentcore_bill_agent_name: str = "bill"
    agentcore_bill_timeout: int = 60
    agentcore_bill_max_retries: int = 3
    
    # S3 Configuration
    s3_bucket: str = "rag-evaluation-datasets"
    s3_key_prefix: str = "test-data/"
    
    # CloudWatch Configuration
    cloudwatch_namespace: str = "RAGEvaluation"
    cloudwatch_log_group: str = "/aws/rag-evaluation"
    
    # Evaluation Configuration
    evaluation_threshold_faithfulness: float = 0.8
    evaluation_threshold_relevance: float = 0.8
    evaluation_threshold_correctness: float = 0.8
    
    # Pipeline Configuration
    pipeline_session_id_prefix: str = "rag-eval"
    pipeline_enable_retries: bool = True
    pipeline_max_retries: int = 2
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
