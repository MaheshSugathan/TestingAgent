"""Structured logging setup for the RAG evaluation pipeline."""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

import watchtower


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add trace ID if available
        if hasattr(record, 'trace_id'):
            log_entry["trace_id"] = record.trace_id
            
        # Add session ID if available
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
            
        # Add custom fields
        if hasattr(record, 'custom_fields'):
            log_entry.update(record.custom_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_logger(
    name: str = "rag_evaluation",
    level: str = "INFO",
    log_format: str = "json",
    cloudwatch_log_group: Optional[str] = None,
    aws_region: str = "us-east-1",
    include_trace_id: bool = True
) -> logging.Logger:
    """Set up structured logger with CloudWatch integration.
    
    Args:
        name: Logger name
        level: Logging level
        log_format: Log format ('json' or 'text')
        cloudwatch_log_group: CloudWatch log group name
        aws_region: AWS region
        include_trace_id: Whether to include trace ID in logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # CloudWatch handler if configured
    if cloudwatch_log_group:
        try:
            cw_handler = watchtower.CloudWatchLogsHandler(
                log_group=cloudwatch_log_group,
                stream_name=f"{name}-{uuid.uuid4().hex[:8]}",
                region_name=aws_region
            )
            cw_handler.setFormatter(formatter)
            logger.addHandler(cw_handler)
        except Exception as e:
            logger.warning(f"Failed to setup CloudWatch logging: {e}")
    
    return logger


def get_logger(name: str = "rag_evaluation") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)
        self._trace_id = str(uuid.uuid4())
    
    def log_with_context(
        self,
        level: str,
        message: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log message with additional context."""
        extra = {
            'trace_id': self._trace_id,
            'session_id': session_id,
            'custom_fields': kwargs
        }
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        session_id: Optional[str] = None,
        **dimensions
    ) -> None:
        """Log a metric with context."""
        self.log_with_context(
            "info",
            f"Metric: {metric_name} = {value} {unit}",
            session_id=session_id,
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **dimensions
        )
