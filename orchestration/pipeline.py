"""Main pipeline orchestrator for RAG evaluation."""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from .state import PipelineState
from .workflow import create_evaluation_workflow
from observability import setup_logger, MetricsCollector


class RAGEvaluationPipeline:
    """Main pipeline orchestrator for RAG evaluation."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        logger=None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize RAG evaluation pipeline.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
            metrics_collector: Metrics collector instance
        """
        self.config = config
        self.logger = logger or setup_logger("RAGEvaluationPipeline")
        self.metrics = metrics_collector or MetricsCollector(
            namespace=config.get("aws", {}).get("cloudwatch", {}).get("namespace", "RAGEvaluation")
        )

        # Checkpointer for human-in-the-loop (required for interrupt/resume)
        self.checkpointer = MemorySaver()
        self.workflow = create_evaluation_workflow(checkpointer=self.checkpointer)

        self.max_retries = config.get("pipeline", {}).get("max_pipeline_retries", 2)
        self.enable_retries = config.get("pipeline", {}).get("enable_retries", True)
    
    async def run_pipeline(
        self,
        queries: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        human_in_loop: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run the complete RAG evaluation pipeline.

        Args:
            queries: List of queries to evaluate (optional)
            session_id: Session ID for tracking (used as thread_id for HITL resume)
            human_in_loop: Override config to enable/disable HITL for this run
            **kwargs: Additional parameters

        Returns:
            Dict with keys:
            - "state": Final PipelineState
            - "interrupt": Optional interrupt payload if awaiting human review
        """
        session_id = session_id or f"rag-eval-{int(time.time())}"

        merged_config = dict(self.config)
        if human_in_loop is not None:
            merged_config.setdefault("human_in_loop", {})["enabled"] = human_in_loop
        if "human_in_loop" not in merged_config:
            merged_config["human_in_loop"] = {"enabled": False}

        state = PipelineState(
            session_id=session_id,
            config=merged_config,
            metadata={
                "queries": queries or [],
                "pipeline_start_time": datetime.utcnow().isoformat(),
                "human_in_loop": merged_config["human_in_loop"].get("enabled", False),
                **kwargs
            }
        )

        self.logger.info("Starting RAG evaluation pipeline", extra={
            "session_id": state.session_id,
            "pipeline_id": state.pipeline_id,
            "human_in_loop": state.metadata.get("human_in_loop", False)
        })

        try:
            config = {"configurable": {"thread_id": session_id}}
            workflow_result = await self.workflow.ainvoke(state, config=config)

            interrupt_data = None
            if isinstance(workflow_result, dict):
                interrupt_data = workflow_result.pop("__interrupt__", None)
                final_state = PipelineState.from_dict(workflow_result)
            else:
                final_state = workflow_result

            self._record_pipeline_metrics(final_state)

            if final_state.is_complete():
                self.logger.info(
                    "Pipeline completed successfully",
                    extra={"session_id": final_state.session_id, "execution_time": final_state.get_total_execution_time()}
                )
            else:
                self.logger.error(
                    "Pipeline completed with errors",
                    extra={"session_id": final_state.session_id, "errors": final_state.errors}
                )

            result = {"state": final_state}
            if interrupt_data is not None:
                result["interrupt"] = [v.value if hasattr(v, "value") else v for v in interrupt_data]
            return result

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}", extra={"session_id": state.session_id, "error": str(e)})
            self.metrics.add_metric(metric_name="pipeline_failure", value=1.0, unit="Count", dimensions={"session_id": state.session_id})
            raise

    async def resume_pipeline(
        self,
        session_id: str,
        human_decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resume pipeline after human-in-the-loop interrupt.

        Args:
            session_id: Same session_id from the interrupted run (thread_id)
            human_decision: Human's decision, e.g. {"action": "approve"} or {"action": "override", "score": 0.85}

        Returns:
            Same structure as run_pipeline: {"state": ..., "interrupt": ...}
        """
        config = {"configurable": {"thread_id": session_id}}
        workflow_result = await self.workflow.ainvoke(Command(resume=human_decision), config=config)

        interrupt_data = workflow_result.pop("__interrupt__", None)

        if isinstance(workflow_result, dict):
            final_state = PipelineState.from_dict(workflow_result)
        else:
            final_state = workflow_result

        self._record_pipeline_metrics(final_state)

        result = {"state": final_state}
        if interrupt_data is not None:
            result["interrupt"] = [v.value if hasattr(v, "value") else v for v in interrupt_data]
        return result
    
    async def run_single_turn_evaluation(
        self,
        query: str,
        session_id: Optional[str] = None,
        human_in_loop: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Run single-turn evaluation pipeline.

        Returns:
            Dict with "state" (PipelineState) and optionally "interrupt" (if awaiting human review)
        """
        return await self.run_pipeline(
            queries=[query],
            session_id=session_id,
            human_in_loop=human_in_loop,
            evaluation_type="single_turn"
        )

    async def run_multi_turn_evaluation(
        self,
        queries: List[str],
        session_id: Optional[str] = None,
        human_in_loop: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Run multi-turn evaluation pipeline.

        Returns:
            Dict with "state" (PipelineState) and optionally "interrupt" (if awaiting human review)
        """
        return await self.run_pipeline(
            queries=queries,
            session_id=session_id,
            human_in_loop=human_in_loop,
            evaluation_type="multi_turn"
        )
    
    def _record_pipeline_metrics(self, state: PipelineState) -> None:
        """Record pipeline metrics to CloudWatch."""
        try:
            # Pipeline-level metrics
            self.metrics.add_metric(
                metric_name="pipeline_duration",
                value=state.get_total_execution_time(),
                unit="Seconds",
                dimensions={"session_id": state.session_id}
            )
            
            if state.is_complete():
                self.metrics.add_metric(
                    metric_name="pipeline_success",
                    value=1.0,
                    unit="Count",
                    dimensions={"session_id": state.session_id}
                )
            else:
                self.metrics.add_metric(
                    metric_name="pipeline_failure",
                    value=1.0,
                    unit="Count",
                    dimensions={"session_id": state.session_id}
                )
            
            # Agent-level metrics
            for agent_name in ["retrieval", "dev", "evaluator"]:
                execution_time = state.get_agent_execution_time(agent_name)
                if execution_time > 0:
                    self.metrics.add_metric(
                        metric_name=f"{agent_name}_duration",
                        value=execution_time,
                        unit="Seconds",
                        dimensions={"session_id": state.session_id}
                    )
            
            # Evaluation metrics
            if state.evaluator_result and state.evaluator_result.success:
                evaluation_results = state.get_data("evaluator", "evaluation_results")
                if evaluation_results:
                    self._record_evaluation_metrics(evaluation_results, state.session_id)
            
        except Exception as e:
            self.logger.error(f"Failed to record pipeline metrics: {e}")
    
    def _record_evaluation_metrics(
        self,
        evaluation_results: List[Dict[str, Any]],
        session_id: str
    ) -> None:
        """Record evaluation metrics."""
        for result in evaluation_results:
            evaluations = result.get("evaluations", {})
            
            # Record Ragas metrics
            if "ragas" in evaluations and "metrics" in evaluations["ragas"]:
                ragas_metrics = evaluations["ragas"]["metrics"]
                for metric, score in ragas_metrics.items():
                    if score is not None:
                        self.metrics.add_metric(
                            metric_name=f"evaluation_ragas_{metric}",
                            value=score,
                            unit="None",
                            dimensions={"session_id": session_id}
                        )
            
            # Record LLM-as-a-Judge metrics
            if "llm_judge" in evaluations and "metrics" in evaluations["llm_judge"]:
                llm_metrics = evaluations["llm_judge"]["metrics"]
                for metric, score in llm_metrics.items():
                    if score is not None:
                        self.metrics.add_metric(
                            metric_name=f"evaluation_llm_{metric}",
                            value=score,
                            unit="None",
                            dimensions={"session_id": session_id}
                        )
    
    def get_pipeline_summary(self, state: PipelineState) -> Dict[str, Any]:
        """Get summary of pipeline execution.
        
        Args:
            state: Final pipeline state
            
        Returns:
            Pipeline summary
        """
        summary = {
            "session_id": state.session_id,
            "pipeline_id": state.pipeline_id,
            "execution_time": state.get_total_execution_time(),
            "success": state.is_complete(),
            "errors": state.errors,
            "agent_results": {}
        }
        
        # Add agent results
        for agent_name in ["retrieval", "dev", "evaluator"]:
            result = getattr(state, f"{agent_name}_result", None)
            if result:
                summary["agent_results"][agent_name] = {
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
        
        # Add evaluation summary if available
        if state.evaluator_result and state.evaluator_result.success:
            evaluation_results = state.get_data("evaluator", "evaluation_results")
            if evaluation_results:
                summary["evaluation_summary"] = self._get_evaluation_summary(evaluation_results)
        
        return summary
    
    def _get_evaluation_summary(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get evaluation summary from results."""
        summary = {
            "total_evaluations": len(evaluation_results),
            "average_scores": {},
            "passing_rates": {}
        }
        
        # Calculate average scores and passing rates for each method
        methods = ["ragas", "llm_judge"]
        
        for method in methods:
            scores = {}
            passing_counts = {}
            
            for result in evaluation_results:
                evaluations = result.get("evaluations", {})
                if method in evaluations and "metrics" in evaluations[method]:
                    metrics = evaluations[method]["metrics"]
                    
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
            
            # Calculate averages and passing rates
            method_scores = {}
            method_passing_rates = {}
            
            for metric, score_list in scores.items():
                if score_list:
                    method_scores[metric] = sum(score_list) / len(score_list)
                    method_passing_rates[metric] = passing_counts.get(metric, 0) / len(score_list)
            
            summary["average_scores"][method] = method_scores
            summary["passing_rates"][method] = method_passing_rates
        
        return summary
