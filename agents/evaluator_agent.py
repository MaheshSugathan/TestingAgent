"""Evaluator agent for assessing RAG responses using Ragas and LLM-as-a-Judge."""

import time
from typing import List, Dict, Any, Optional

from .base import EvaluatorAgent, AgentState
from evaluation import RagasEvaluator, LLMJudgeEvaluator, EvaluationResult


class RAGEvaluatorAgent(EvaluatorAgent):
    """Evaluator agent using both Ragas and LLM-as-a-Judge."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        ragas_config: Optional[Dict[str, Any]] = None,
        llm_judge_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize RAG evaluator agent.
        
        Args:
            config: Agent configuration
            ragas_config: Ragas evaluator configuration
            llm_judge_config: LLM-as-a-Judge configuration
            **kwargs: Additional configuration
        """
        super().__init__(config, **kwargs)
        
        # Initialize evaluators
        self.ragas_evaluator = None
        self.llm_judge_evaluator = None
        
        # Configure evaluators
        if ragas_config and ragas_config.get('enabled', True):
            self.ragas_evaluator = RagasEvaluator(**ragas_config)
            self.ragas_evaluator.set_logger(self.logger)
        
        if llm_judge_config and llm_judge_config.get('enabled', True):
            self.llm_judge_evaluator = LLMJudgeEvaluator(**llm_judge_config)
            self.llm_judge_evaluator.set_logger(self.logger)
        
        # Evaluation configuration
        self.evaluation_methods = []
        if self.ragas_evaluator:
            self.evaluation_methods.append("ragas")
        if self.llm_judge_evaluator:
            self.evaluation_methods.append("llm_judge")
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute evaluation operation.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state with evaluation results
        """
        start_time = time.time()
        session_id = state.session_id
        
        try:
            self.log_with_context(
                "info",
                "Starting evaluation execution",
                session_id=session_id,
                methods=self.evaluation_methods
            )
            
            # Get generated responses from state
            responses = state.data.get('generated_responses', [])
            if not responses:
                raise ValueError("No generated responses found in state")
            
            # Perform evaluations
            evaluation_results = []
            
            for response in responses:
                result = await self._evaluate_response(
                    response, session_id
                )
                evaluation_results.append(result)
            
            # Update state
            state.data['evaluation_results'] = evaluation_results
            state.data['evaluation_metadata'] = {
                'methods_used': self.evaluation_methods,
                'total_evaluations': len(evaluation_results),
                'execution_time': time.time() - start_time
            }
            
            # Record metrics
            duration = time.time() - start_time
            self._record_execution_time("evaluation", duration, session_id)
            self._record_success("evaluation", session_id)
            
            # Record individual evaluation scores
            await self._record_evaluation_metrics(evaluation_results, session_id)
            
            self.log_with_context(
                "info",
                f"Successfully completed {len(evaluation_results)} evaluations",
                session_id=session_id,
                duration=duration
            )
            
            return state
            
        except Exception as e:
            self.log_with_context(
                "error",
                f"Failed to execute evaluation: {e}",
                session_id=session_id,
                error=str(e)
            )
            self._record_failure("evaluation", session_id, e)
            raise
    
    async def _evaluate_response(
        self,
        response: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Evaluate a single response using available methods.
        
        Args:
            response: Response to evaluate
            session_id: Session ID for logging
            
        Returns:
            Evaluation results
        """
        query = response['query']
        answer = response['response']
        context = response.get('context_used', '')
        
        evaluation_results = {
            'query': query,
            'answer': answer,
            'context': context,
            'evaluations': {},
            'metadata': response.get('metadata', {})
        }
        
        # Run Ragas evaluation if available
        if self.ragas_evaluator:
            try:
                ragas_result = self.ragas_evaluator.evaluate_single(
                    query=query,
                    answer=answer,
                    context=context,
                    session_id=session_id
                )
                evaluation_results['evaluations']['ragas'] = ragas_result.to_dict()
                
                self.log_with_context(
                    "debug",
                    "Ragas evaluation completed",
                    session_id=session_id,
                    query=query[:100],
                    scores=ragas_result.metrics.to_dict()
                )
                
            except Exception as e:
                self.log_with_context(
                    "error",
                    f"Ragas evaluation failed: {e}",
                    session_id=session_id,
                    query=query[:100],
                    error=str(e)
                )
                evaluation_results['evaluations']['ragas'] = {
                    'error': str(e),
                    'metrics': {}
                }
        
        # Run LLM-as-a-Judge evaluation if available
        if self.llm_judge_evaluator:
            try:
                llm_result = self.llm_judge_evaluator.evaluate_single(
                    query=query,
                    answer=answer,
                    context=context,
                    session_id=session_id
                )
                evaluation_results['evaluations']['llm_judge'] = llm_result.to_dict()
                
                self.log_with_context(
                    "debug",
                    "LLM-as-a-Judge evaluation completed",
                    session_id=session_id,
                    query=query[:100],
                    scores=llm_result.metrics.to_dict()
                )
                
            except Exception as e:
                self.log_with_context(
                    "error",
                    f"LLM-as-a-Judge evaluation failed: {e}",
                    session_id=session_id,
                    query=query[:100],
                    error=str(e)
                )
                evaluation_results['evaluations']['llm_judge'] = {
                    'error': str(e),
                    'metrics': {}
                }
        
        return evaluation_results
    
    async def _record_evaluation_metrics(
        self,
        evaluation_results: List[Dict[str, Any]],
        session_id: str
    ) -> None:
        """Record evaluation metrics to CloudWatch.
        
        Args:
            evaluation_results: List of evaluation results
            session_id: Session ID for logging
        """
        for result in evaluation_results:
            evaluations = result.get('evaluations', {})
            
            # Record Ragas metrics
            if 'ragas' in evaluations and 'metrics' in evaluations['ragas']:
                ragas_metrics = evaluations['ragas']['metrics']
                for metric, score in ragas_metrics.items():
                    if score is not None:
                        self.record_agent_metric(
                            metric_name=f"evaluation_ragas_{metric}",
                            value=score,
                            unit="None",
                            session_id=session_id
                        )
            
            # Record LLM-as-a-Judge metrics
            if 'llm_judge' in evaluations and 'metrics' in evaluations['llm_judge']:
                llm_metrics = evaluations['llm_judge']['metrics']
                for metric, score in llm_metrics.items():
                    if score is not None:
                        self.record_agent_metric(
                            metric_name=f"evaluation_llm_{metric}",
                            value=score,
                            unit="None",
                            session_id=session_id
                        )
    
    async def evaluate_single_response(
        self,
        query: str,
        answer: str,
        context: str,
        ground_truth: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate a single response directly.
        
        Args:
            query: Input query
            answer: Generated answer
            context: Retrieved context
            ground_truth: Ground truth answer (optional)
            session_id: Session ID
            
        Returns:
            Evaluation results
        """
        response = {
            'query': query,
            'response': answer,
            'context_used': context,
            'metadata': {}
        }
        
        return await self._evaluate_response(response, session_id)
    
    async def evaluate_batch_responses(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[str],
        ground_truths: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate multiple responses in batch.
        
        Args:
            queries: List of queries
            answers: List of answers
            contexts: List of contexts
            ground_truths: List of ground truth answers (optional)
            session_id: Session ID
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, (query, answer, context) in enumerate(zip(queries, answers, contexts)):
            ground_truth = ground_truths[i] if ground_truths else None
            
            result = await self.evaluate_single_response(
                query=query,
                answer=answer,
                context=context,
                ground_truth=ground_truth,
                session_id=session_id
            )
            
            results.append(result)
        
        return results
    
    def get_evaluation_summary(
        self,
        evaluation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get summary statistics from evaluation results.
        
        Args:
            evaluation_results: List of evaluation results
            
        Returns:
            Summary statistics
        """
        summary = {
            'total_evaluations': len(evaluation_results),
            'methods_used': self.evaluation_methods,
            'average_scores': {},
            'passing_rates': {}
        }
        
        # Calculate average scores for each method
        for method in self.evaluation_methods:
            scores = {}
            passing_counts = {}
            total_count = 0
            
            for result in evaluation_results:
                evaluations = result.get('evaluations', {})
                if method in evaluations and 'metrics' in evaluations[method]:
                    metrics = evaluations[method]['metrics']
                    total_count += 1
                    
                    for metric, score in metrics.items():
                        if score is not None:
                            if metric not in scores:
                                scores[metric] = []
                            scores[metric].append(score)
                            
                            # Count passing scores (>= 0.8)
                            if metric not in passing_counts:
                                passing_counts[metric] = 0
                            if score >= 0.8:
                                passing_counts[metric] += 1
            
            # Calculate averages
            method_scores = {}
            method_passing_rates = {}
            
            for metric, score_list in scores.items():
                if score_list:
                    method_scores[metric] = sum(score_list) / len(score_list)
                    method_passing_rates[metric] = passing_counts.get(metric, 0) / len(score_list)
            
            summary['average_scores'][method] = method_scores
            summary['passing_rates'][method] = method_passing_rates
        
        return summary
