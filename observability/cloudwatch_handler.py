"""CloudWatch handler for custom metrics and dashboards."""

import json
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError


class CloudWatchHandler:
    """Handles CloudWatch operations for dashboards and alarms."""
    
    def __init__(self, region: str = "us-east-1"):
        """Initialize CloudWatch handler.
        
        Args:
            region: AWS region
        """
        self.region = region
        self._cloudwatch = boto3.client('cloudwatch', region_name=region)
    
    def create_dashboard(
        self,
        dashboard_name: str,
        metrics_config: Dict[str, Any]
    ) -> bool:
        """Create a CloudWatch dashboard.
        
        Args:
            dashboard_name: Name of the dashboard
            metrics_config: Configuration for dashboard metrics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            dashboard_body = self._generate_dashboard_body(metrics_config)
            
            self._cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            return True
            
        except ClientError as e:
            print(f"Failed to create dashboard: {e}")
            return False
    
    def _generate_dashboard_body(self, metrics_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate CloudWatch dashboard body from configuration.
        
        Args:
            metrics_config: Metrics configuration
            
        Returns:
            Dashboard body dictionary
        """
        widgets = []
        
        # Retrieval metrics widget
        widgets.append({
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["RAGEvaluation", "retrieval_duration", {"stat": "Average"}],
                    ["RAGEvaluation", "retrieval_success", {"stat": "Sum"}],
                    ["RAGEvaluation", "retrieval_failure", {"stat": "Sum"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Retrieval Agent Metrics",
                "period": 300
            }
        })
        
        # Dev agent metrics widget
        widgets.append({
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["RAGEvaluation", "dev_latency", {"stat": "Average"}],
                    ["RAGEvaluation", "token_usage_total", {"stat": "Sum"}],
                    ["RAGEvaluation", "dev_success", {"stat": "Sum"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Dev Agent Metrics",
                "period": 300
            }
        })
        
        # Evaluation metrics widget
        widgets.append({
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 24,
            "height": 6,
            "properties": {
                "metrics": [
                    ["RAGEvaluation", "evaluation_faithfulness", {"stat": "Average"}],
                    ["RAGEvaluation", "evaluation_relevance", {"stat": "Average"}],
                    ["RAGEvaluation", "evaluation_correctness", {"stat": "Average"}],
                    ["RAGEvaluation", "evaluation_context_precision", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Evaluation Metrics",
                "period": 300,
                "yAxis": {
                    "left": {
                        "min": 0,
                        "max": 1
                    }
                }
            }
        })
        
        # Pipeline overview widget
        widgets.append({
            "type": "metric",
            "x": 0,
            "y": 12,
            "width": 24,
            "height": 6,
            "properties": {
                "metrics": [
                    ["RAGEvaluation", "pipeline_success", {"stat": "Sum"}],
                    ["RAGEvaluation", "pipeline_failure", {"stat": "Sum"}],
                    ["RAGEvaluation", "pipeline_duration", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Pipeline Overview",
                "period": 300
            }
        })
        
        return {
            "widgets": widgets
        }
    
    def create_alarm(
        self,
        alarm_name: str,
        metric_name: str,
        namespace: str,
        threshold: float,
        comparison_operator: str = "LessThanThreshold",
        evaluation_periods: int = 2,
        period: int = 300
    ) -> bool:
        """Create a CloudWatch alarm.
        
        Args:
            alarm_name: Name of the alarm
            metric_name: Name of the metric
            namespace: CloudWatch namespace
            threshold: Alarm threshold
            comparison_operator: Comparison operator
            evaluation_periods: Number of periods to evaluate
            period: Evaluation period in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._cloudwatch.put_metric_alarm(
                AlarmName=alarm_name,
                ComparisonOperator=comparison_operator,
                EvaluationPeriods=evaluation_periods,
                MetricName=metric_name,
                Namespace=namespace,
                Period=period,
                Statistic="Average",
                Threshold=threshold,
                ActionsEnabled=True,
                AlarmDescription=f"Alarm for {metric_name}"
            )
            
            return True
            
        except ClientError as e:
            print(f"Failed to create alarm: {e}")
            return False
    
    def list_metrics(self, namespace: str = "RAGEvaluation") -> List[Dict[str, Any]]:
        """List metrics in a namespace.
        
        Args:
            namespace: CloudWatch namespace
            
        Returns:
            List of metric information
        """
        try:
            response = self._cloudwatch.list_metrics(
                Namespace=namespace
            )
            return response.get('Metrics', [])
            
        except ClientError as e:
            print(f"Failed to list metrics: {e}")
            return []
    
    def get_metric_statistics(
        self,
        metric_name: str,
        namespace: str = "RAGEvaluation",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        period: int = 3600,
        statistics: List[str] = None
    ) -> Dict[str, Any]:
        """Get metric statistics.
        
        Args:
            metric_name: Name of the metric
            namespace: CloudWatch namespace
            start_time: Start time for statistics
            end_time: End time for statistics
            period: Period in seconds
            statistics: List of statistics to retrieve
            
        Returns:
            Metric statistics
        """
        if statistics is None:
            statistics = ["Average", "Sum", "Maximum", "Minimum"]
        
        try:
            response = self._cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=statistics
            )
            return response
            
        except ClientError as e:
            print(f"Failed to get metric statistics: {e}")
            return {}
