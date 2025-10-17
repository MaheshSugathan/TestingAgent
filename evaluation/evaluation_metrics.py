"""Evaluation metrics and result classes."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    faithfulness: Optional[float] = None
    relevance: Optional[float] = None
    correctness: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_relevancy: Optional[float] = None
    
    # LLM-as-a-Judge metrics
    overall_score: Optional[float] = None
    coherence_score: Optional[float] = None
    completeness_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "faithfulness": self.faithfulness,
            "relevance": self.relevance,
            "correctness": self.correctness,
            "context_precision": self.context_precision,
            "context_recall": self.context_recall,
            "answer_relevancy": self.answer_relevancy,
            "overall_score": self.overall_score,
            "coherence_score": self.coherence_score,
            "completeness_score": self.completeness_score,
        }
    
    def get_overall_score(self) -> float:
        """Calculate overall score from available metrics."""
        scores = [
            self.faithfulness,
            self.relevance,
            self.correctness,
            self.context_precision,
            self.answer_relevancy,
            self.overall_score
        ]
        
        valid_scores = [s for s in scores if s is not None]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0


@dataclass
class EvaluationResult:
    """Container for evaluation result."""
    query: str
    answer: str
    context: str
    metrics: EvaluationMetrics
    comments: Optional[str] = None
    evaluation_method: str = "unknown"
    timestamp: datetime = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "answer": self.answer,
            "context": self.context,
            "metrics": self.metrics.to_dict(),
            "comments": self.comments,
            "evaluation_method": self.evaluation_method,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "overall_score": self.metrics.get_overall_score()
        }
    
    def meets_threshold(self, threshold: float = 0.8) -> bool:
        """Check if overall score meets threshold."""
        return self.metrics.get_overall_score() >= threshold


@dataclass
class BatchEvaluationResult:
    """Container for batch evaluation results."""
    results: List[EvaluationResult]
    session_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def get_average_scores(self) -> Dict[str, float]:
        """Calculate average scores across all results."""
        if not self.results:
            return {}
        
        metrics_sum = {}
        count = len(self.results)
        
        for result in self.results:
            metrics_dict = result.metrics.to_dict()
            for key, value in metrics_dict.items():
                if value is not None:
                    metrics_sum[key] = metrics_sum.get(key, 0) + value
        
        return {key: value / count for key, value in metrics_sum.items()}
    
    def get_passing_rate(self, threshold: float = 0.8) -> float:
        """Calculate percentage of results meeting threshold."""
        if not self.results:
            return 0.0
        
        passing_count = sum(1 for result in self.results if result.meets_threshold(threshold))
        return passing_count / len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [result.to_dict() for result in self.results],
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "average_scores": self.get_average_scores(),
            "passing_rate": self.get_passing_rate(),
            "total_evaluations": len(self.results)
        }
