"""Ragas-based evaluation for RAG responses."""

import time
from typing import List, Dict, Any, Optional
import pandas as pd

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from .evaluation_metrics import EvaluationResult, EvaluationMetrics, BatchEvaluationResult


class RagasEvaluator:
    """Evaluator using Ragas metrics."""
    
    def __init__(
        self,
        metrics: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize Ragas evaluator.
        
        Args:
            metrics: List of metrics to compute
            **kwargs: Additional configuration
        """
        self.metrics = metrics or [
            "faithfulness",
            "answer_relevancy", 
            "context_precision",
            "context_recall"
        ]
        
        # Map metric names to Ragas metrics
        self.metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }
        
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
    
    def evaluate_single(
        self,
        query: str,
        answer: str,
        context: str,
        ground_truth: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate a single query-answer pair.
        
        Args:
            query: Input query
            answer: Generated answer
            context: Retrieved context
            ground_truth: Ground truth answer (optional)
            session_id: Session ID for logging
            
        Returns:
            Evaluation result
        """
        try:
            # Prepare data for Ragas
            data = {
                "question": [query],
                "answer": [answer],
                "contexts": [[context]],
            }
            
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            df = pd.DataFrame(data)
            
            # Select metrics to evaluate
            selected_metrics = [
                self.metric_map[metric] for metric in self.metrics
                if metric in self.metric_map
            ]
            
            # Run evaluation
            result = evaluate(
                df,
                metrics=selected_metrics
            )
            
            # Extract scores
            scores = result.to_pandas().iloc[0].to_dict()
            
            # Create evaluation metrics
            metrics = EvaluationMetrics(
                faithfulness=scores.get("faithfulness"),
                answer_relevancy=scores.get("answer_relevancy"),
                context_precision=scores.get("context_precision"),
                context_recall=scores.get("context_recall"),
            )
            
            return EvaluationResult(
                query=query,
                answer=answer,
                context=context,
                metrics=metrics,
                evaluation_method="ragas",
                session_id=session_id
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ragas evaluation failed: {e}")
            
            # Return default result with zero scores
            return EvaluationResult(
                query=query,
                answer=answer,
                context=context,
                metrics=EvaluationMetrics(),
                evaluation_method="ragas",
                session_id=session_id,
                comments=f"Evaluation failed: {str(e)}"
            )
    
    def evaluate_batch(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[str],
        ground_truths: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> BatchEvaluationResult:
        """Evaluate multiple query-answer pairs.
        
        Args:
            queries: List of queries
            answers: List of answers
            contexts: List of contexts
            ground_truths: List of ground truth answers (optional)
            session_id: Session ID for logging
            
        Returns:
            Batch evaluation result
        """
        try:
            # Prepare data for Ragas
            data = {
                "question": queries,
                "answer": answers,
                "contexts": [[ctx] for ctx in contexts],
            }
            
            if ground_truths:
                data["ground_truth"] = ground_truths
            
            df = pd.DataFrame(data)
            
            # Select metrics to evaluate
            selected_metrics = [
                self.metric_map[metric] for metric in self.metrics
                if metric in self.metric_map
            ]
            
            # Run evaluation
            result = evaluate(
                df,
                metrics=selected_metrics
            )
            
            # Convert to individual results
            results = []
            scores_df = result.to_pandas()
            
            for idx, row in scores_df.iterrows():
                metrics = EvaluationMetrics(
                    faithfulness=row.get("faithfulness"),
                    answer_relevancy=row.get("answer_relevancy"),
                    context_precision=row.get("context_precision"),
                    context_recall=row.get("context_recall"),
                )
                
                results.append(EvaluationResult(
                    query=queries[idx],
                    answer=answers[idx],
                    context=contexts[idx],
                    metrics=metrics,
                    evaluation_method="ragas",
                    session_id=session_id
                ))
            
            return BatchEvaluationResult(
                results=results,
                session_id=session_id
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ragas batch evaluation failed: {e}")
            
            # Return empty batch result
            return BatchEvaluationResult(
                results=[],
                session_id=session_id
            )
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics."""
        return list(self.metric_map.keys())
    
    def is_metric_available(self, metric_name: str) -> bool:
        """Check if a metric is available."""
        return metric_name in self.metric_map
