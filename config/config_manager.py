"""Configuration manager for loading and merging configurations."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from .settings import (
    Settings, AWSConfig, BedrockConfig, AgentCoreConfig, S3Config, 
    EvaluationConfig, AgentConfig, PipelineConfig, LoggingConfig
)


class ConfigManager:
    """Manages configuration loading from YAML and environment variables."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file.
                        Defaults to config/config.yaml
        """
        self.config_path = config_path or self._get_default_config_path()
        self._yaml_config: Dict[str, Any] = {}
        self._env_settings = Settings()
        
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        current_dir = Path(__file__).parent
        return str(current_dir / "config.yaml")
    
    def load_config(self) -> Dict[str, Any]:
        """Load and merge configuration from YAML and environment variables.
        
        Returns:
            Merged configuration dictionary
        """
        # Load YAML configuration
        self._yaml_config = self._load_yaml_config()
        
        # Merge with environment variables
        merged_config = self._merge_configs()
        
        return merged_config
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)
    
    def _merge_configs(self) -> Dict[str, Any]:
        """Merge YAML configuration with environment variables."""
        config = self._yaml_config.copy()
        
        # Override with environment variables where available
        if self._env_settings.s3_bucket:
            config.setdefault('s3', {})['bucket'] = self._env_settings.s3_bucket
        
        if self._env_settings.s3_key_prefix:
            config.setdefault('s3', {})['key_prefix'] = self._env_settings.s3_key_prefix
            
        if self._env_settings.aws_default_region:
            config.setdefault('aws', {})['region'] = self._env_settings.aws_default_region
            
        if self._env_settings.cloudwatch_namespace:
            config.setdefault('aws', {}).setdefault('cloudwatch', {})['namespace'] = self._env_settings.cloudwatch_namespace
            
        if self._env_settings.cloudwatch_log_group:
            config.setdefault('aws', {}).setdefault('cloudwatch', {})['log_group'] = self._env_settings.cloudwatch_log_group
        
        # Bedrock configuration
        if self._env_settings.bedrock_region:
            config.setdefault('bedrock', {})['region'] = self._env_settings.bedrock_region
            
        if self._env_settings.bedrock_embedding_model:
            config.setdefault('bedrock', {}).setdefault('models', {})['embedding'] = self._env_settings.bedrock_embedding_model
            
        if self._env_settings.bedrock_generation_model:
            config.setdefault('bedrock', {}).setdefault('models', {})['generation'] = self._env_settings.bedrock_generation_model
            
        if self._env_settings.bedrock_judge_model:
            config.setdefault('bedrock', {}).setdefault('models', {})['judge'] = self._env_settings.bedrock_judge_model
        
        # Pipeline configuration
        if self._env_settings.pipeline_session_id_prefix:
            config.setdefault('pipeline', {})['session_id_prefix'] = self._env_settings.pipeline_session_id_prefix
            
        if not self._env_settings.pipeline_enable_retries:
            config.setdefault('pipeline', {})['enable_retries'] = False
            
        if self._env_settings.pipeline_max_retries:
            config.setdefault('pipeline', {})['max_pipeline_retries'] = self._env_settings.pipeline_max_retries
        
        # Logging configuration
        if self._env_settings.log_level:
            config.setdefault('logging', {})['level'] = self._env_settings.log_level
            
        if self._env_settings.log_format:
            config.setdefault('logging', {})['format'] = self._env_settings.log_format
        
        return config
    
    def get_aws_config(self) -> AWSConfig:
        """Get AWS configuration."""
        aws_config = self._yaml_config.get('aws', {})
        return AWSConfig(**aws_config)
    
    def get_bedrock_config(self) -> BedrockConfig:
        """Get Bedrock configuration."""
        bedrock_config = self._yaml_config.get('bedrock', {})
        return BedrockConfig(**bedrock_config)
    
    def get_agentcore_config(self) -> AgentCoreConfig:
        """Get AgentCore configuration."""
        agentcore_config = self._yaml_config.get('agentcore', {})
        # Override with environment variables if available
        if self._env_settings.agentcore_enabled is not None:
            agentcore_config['enabled'] = self._env_settings.agentcore_enabled
        if self._env_settings.agentcore_base_url:
            agentcore_config['base_url'] = self._env_settings.agentcore_base_url
        
        # Update bill config
        bill_config = agentcore_config.get('bill', {})
        if self._env_settings.agentcore_bill_agent_name:
            bill_config['agent_name'] = self._env_settings.agentcore_bill_agent_name
        if self._env_settings.agentcore_bill_timeout:
            bill_config['timeout'] = self._env_settings.agentcore_bill_timeout
        if self._env_settings.agentcore_bill_max_retries:
            bill_config['max_retries'] = self._env_settings.agentcore_bill_max_retries
        
        agentcore_config['bill'] = bill_config
        return AgentCoreConfig(**agentcore_config)
    
    def get_s3_config(self) -> S3Config:
        """Get S3 configuration."""
        s3_config = self._yaml_config.get('s3', {})
        # Override with environment variables if available
        if self._env_settings.s3_bucket:
            s3_config['bucket'] = self._env_settings.s3_bucket
        if self._env_settings.s3_key_prefix:
            s3_config['key_prefix'] = self._env_settings.s3_key_prefix
        return S3Config(**s3_config)
    
    def get_evaluation_config(self) -> EvaluationConfig:
        """Get evaluation configuration."""
        eval_config = self._yaml_config.get('evaluation', {})
        return EvaluationConfig(**eval_config)
    
    def get_agent_config(self) -> AgentConfig:
        """Get agent configuration."""
        agent_config = self._yaml_config.get('agents', {})
        return AgentConfig(**agent_config)
    
    def get_pipeline_config(self) -> PipelineConfig:
        """Get pipeline configuration."""
        pipeline_config = self._yaml_config.get('pipeline', {})
        return PipelineConfig(**pipeline_config)
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        logging_config = self._yaml_config.get('logging', {})
        return LoggingConfig(**logging_config)
