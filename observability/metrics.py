"""CloudWatch metrics collection for the RAG evaluation pipeline."""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import contextmanager

import boto3
from botocore.exceptions import ClientError


@dataclass
class MetricDimension:
    """CloudWatch metric dimension."""
    name: str
    value: str


@dataclass
class MetricData:
    """CloudWatch metric data point."""
    metric_name: str
    value: float
    unit: str
    timestamp: Optional[float] = None
    dimensions: Optional[List[MetricDimension]] = None


class MetricsCollector:
    """Collects and sends metrics to CloudWatch."""
    
    def __init__(
        self,
        namespace: str = "RAGEvaluation",
        region: str = "us-east-1",
        batch_size: int = 20
    ):
        """Initialize metrics collector.
        
        Args:
            namespace: CloudWatch namespace
            region: AWS region
            batch_size: Maximum number of metrics per batch
        """
        self.namespace = namespace
        self.region = region
        self.batch_size = batch_size
        self._cloudwatch = boto3.client('cloudwatch', region_name=region)
        self._metrics_buffer: List[MetricData] = []
    
    def add_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[float] = None
    ) -> None:
        """Add a metric to the buffer.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, etc.)
            dimensions: Metric dimensions
            timestamp: Metric timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        metric_dimensions = None
        if dimensions:
            metric_dimensions = [
                MetricDimension(name=k, value=v) for k, v in dimensions.items()
            ]
        
        metric_data = MetricData(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=timestamp,
            dimensions=metric_dimensions
        )
        
        self._metrics_buffer.append(metric_data)
        
        # Send metrics if buffer is full
        if len(self._metrics_buffer) >= self.batch_size:
            self.flush_metrics()
    
    def flush_metrics(self) -> None:
        """Send all buffered metrics to CloudWatch."""
        if not self._metrics_buffer:
            return
        
        try:
            # Convert to CloudWatch format
            cloudwatch_metrics = []
            for metric in self._metrics_buffer:
                cw_metric = {
                    'MetricName': metric.metric_name,
                    'Value': metric.value,
                    'Unit': metric.unit,
                    'Timestamp': metric.timestamp
                }
                
                if metric.dimensions:
                    cw_metric['Dimensions'] = [
                        {'Name': d.name, 'Value': d.value}
                        for d in metric.dimensions
                    ]
                
                cloudwatch_metrics.append(cw_metric)
            
            # Send metrics in batches
            for i in range(0, len(cloudwatch_metrics), self.batch_size):
                batch = cloudwatch_metrics[i:i + self.batch_size]
                self._cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            self._metrics_buffer.clear()
            
        except ClientError as e:
            # Log error but don't raise to avoid breaking the pipeline
            print(f"Failed to send metrics to CloudWatch: {e}")
    
    @contextmanager
    def timer(
        self,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """Context manager to time operations and record duration.
        
        Args:
            metric_name: Name of the timing metric
            dimensions: Metric dimensions
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.add_metric(
                metric_name=f"{metric_name}_duration",
                value=duration,
                unit="Seconds",
                dimensions=dimensions
            )
    
    def increment_counter(
        self,
        metric_name: str,
        value: float = 1.0,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric.
        
        Args:
            metric_name: Name of the counter metric
            value: Value to increment by (default: 1.0)
            dimensions: Metric dimensions
        """
        self.add_metric(
            metric_name=metric_name,
            value=value,
            unit="Count",
            dimensions=dimensions
        )
    
    def record_latency(
        self,
        operation: str,
        latency: float,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Record operation latency.
        
        Args:
            operation: Name of the operation
            latency: Latency in seconds
            dimensions: Metric dimensions
        """
        self.add_metric(
            metric_name=f"{operation}_latency",
            value=latency,
            unit="Seconds",
            dimensions=dimensions
        )
    
    def record_evaluation_score(
        self,
        metric_type: str,
        score: float,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Record evaluation score.
        
        Args:
            metric_type: Type of evaluation metric
            score: Evaluation score (0.0 to 1.0)
            dimensions: Metric dimensions
        """
        self.add_metric(
            metric_name=f"evaluation_{metric_type}",
            value=score,
            unit="None",
            dimensions=dimensions
        )
    
    def record_token_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Record token usage for a model.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            dimensions: Metric dimensions
        """
        base_dims = dimensions or {}
        
        # Input tokens
        self.add_metric(
            metric_name="token_usage_input",
            value=input_tokens,
            unit="Count",
            dimensions={**base_dims, "model": model, "token_type": "input"}
        )
        
        # Output tokens
        self.add_metric(
            metric_name="token_usage_output",
            value=output_tokens,
            unit="Count",
            dimensions={**base_dims, "model": model, "token_type": "output"}
        )
        
        # Total tokens
        self.add_metric(
            metric_name="token_usage_total",
            value=input_tokens + output_tokens,
            unit="Count",
            dimensions={**base_dims, "model": model, "token_type": "total"}
        )


class MetricsMixin:
    """Mixin class to add metrics collection to agents."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = MetricsCollector()
    
    def record_agent_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        session_id: Optional[str] = None,
        **dimensions
    ) -> None:
        """Record an agent-specific metric."""
        base_dims = {
            "agent": self.__class__.__name__,
            **dimensions
        }
        
        if session_id:
            base_dims["session_id"] = session_id
        
        self.metrics.add_metric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            dimensions=base_dims
        )
