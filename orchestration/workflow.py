"""LangGraph workflow definition for RAG evaluation pipeline."""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from .state import PipelineState


def _compute_overall_score(evaluation_results: list) -> float:
    """Compute overall score from evaluation results."""
    if not evaluation_results:
        return 0.0
    scores = []
    for result in evaluation_results:
        evaluations = result.get("evaluations", {})
        for method in ["ragas", "llm_judge"]:
            if method in evaluations:
                metrics = evaluations[method].get("metrics", {})
                method_scores = [
                    v for v in metrics.values()
                    if v is not None and isinstance(v, (int, float))
                ]
                if method_scores:
                    scores.append(sum(method_scores) / len(method_scores))
    return sum(scores) / len(scores) if scores else 0.0


async def human_review_node(state: PipelineState) -> PipelineState:
    """Human-in-the-loop review node. Pauses when scores are below threshold (if HITL enabled)."""
    hitl_config = state.config.get("human_in_loop", {})
    hitl_enabled = hitl_config.get("enabled", False) or state.metadata.get("human_in_loop", False)

    if not hitl_enabled:
        return state

    evaluation_results = state.get_data("evaluator", "evaluation_results")
    if not evaluation_results:
        return state

    overall_score = _compute_overall_score(evaluation_results)
    threshold = (
        hitl_config.get("review_threshold")
        or state.config.get("evaluation", {}).get("thresholds", {}).get("overall", 0.8)
    )

    if overall_score >= threshold:
        return state

    interrupt_payload = {
        "action": "human_review",
        "session_id": state.session_id,
        "overall_score": round(overall_score, 4),
        "threshold": threshold,
        "message": f"Scores below threshold ({overall_score:.2f} < {threshold}). Approve, reject, or override?",
        "evaluation_summary": {
            "total_evaluations": len(evaluation_results),
            "queries": state.metadata.get("queries", []),
        },
    }

    human_decision = interrupt(interrupt_payload)

    if isinstance(human_decision, dict):
        action = human_decision.get("action", "reject")
        if action == "approve":
            state.metadata["human_review"] = {"action": "approved", "comment": human_decision.get("comment", "")}
        elif action == "override" and "score" in human_decision:
            state.metadata["human_review"] = {
                "action": "override",
                "override_score": human_decision["score"],
                "comment": human_decision.get("comment", ""),
            }
        else:
            state.metadata["human_review"] = {"action": "rejected", "comment": human_decision.get("comment", "")}

    return state


def create_evaluation_workflow(checkpointer=None):
    """Create LangGraph workflow for RAG evaluation pipeline.

    Args:
        checkpointer: Optional checkpointer for human-in-the-loop (required for HITL resume).
                     Use MemorySaver() for dev; use persistent store for production.

    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(PipelineState)

    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("dev", dev_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("error_handler", error_handler_node)

    workflow.set_entry_point("retrieval")

    workflow.add_conditional_edges(
        "retrieval",
        retrieval_condition,
        {"success": "dev", "failure": "error_handler"}
    )

    workflow.add_conditional_edges(
        "dev",
        dev_condition,
        {"success": "evaluator", "failure": "error_handler"}
    )

    workflow.add_conditional_edges(
        "evaluator",
        evaluator_condition,
        {"success": "human_review", "failure": "error_handler"}
    )

    workflow.add_edge("human_review", END)
    workflow.add_edge("error_handler", END)

    compile_kwargs = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return workflow.compile(**compile_kwargs)


async def retrieval_node(state: PipelineState) -> PipelineState:
    """Retrieval agent node."""
    try:
        # Initialize retrieval agent
        from agents import S3RetrievalAgent
        agent = S3RetrievalAgent(
            config=state.config.get("retrieval", {}),
            bucket_name=state.config.get("s3", {}).get("bucket", "rag-evaluation-datasets"),
            key_prefix=state.config.get("s3", {}).get("key_prefix", "test-data/"),
            aws_region=state.config.get("aws", {}).get("region", "us-east-1")
        )

        # Create agent state
        from agents.base import AgentState
        agent_state = AgentState(
            session_id=state.session_id,
            data=state.metadata.get("initial_data", {}),
            metadata=state.metadata
        )

        # Execute retrieval
        result_state = await agent.execute(agent_state)

        # Create result
        from .state import AgentResult
        result = AgentResult(
            agent_name="retrieval",
            success=True,
            data=result_state.data,
            metadata=result_state.metadata,
            execution_time=result_state.data.get("retrieval_metadata", {}).get("retrieval_time", 0.0)
        )

        state.add_agent_result(result)

    except Exception as e:
        # Create error result
        from .state import AgentResult
        result = AgentResult(
            agent_name="retrieval",
            success=False,
            error=str(e)
        )
        state.add_agent_result(result)

    return state


async def dev_node(state: PipelineState) -> PipelineState:
    """Dev agent node."""
    try:
        # Get documents from retrieval result
        documents = state.get_data("retrieval", "documents")
        if not documents:
            raise ValueError("No documents found from retrieval agent")

        # Initialize Dev agent with Bill integration
        from agents import DevAgent
        agentcore_config = state.config.get("agentcore", {})

        agent = DevAgent(
            config=state.config.get("agents", {}).get("dev", {}),
            agentcore_base_url=agentcore_config.get("base_url", "http://localhost:8000"),
            bill_agent_name=agentcore_config.get("bill", {}).get("agent_name", "bill"),
            timeout=agentcore_config.get("bill", {}).get("timeout", 60),
            max_retries=agentcore_config.get("bill", {}).get("max_retries", 3)
        )

        # Create agent state
        from agents.base import AgentState
        agent_state = AgentState(
            session_id=state.session_id,
            data={
                "documents": documents,
                "queries": state.metadata.get("queries", [])
            },
            metadata=state.metadata
        )

        # Execute dev agent
        result_state = await agent.execute(agent_state)

        # Create result
        from .state import AgentResult
        result = AgentResult(
            agent_name="dev",
            success=True,
            data=result_state.data,
            metadata=result_state.metadata,
            execution_time=result_state.data.get("dev_metadata", {}).get("execution_time", 0.0)
        )

        state.add_agent_result(result)

    except Exception as e:
        # Create error result
        from .state import AgentResult
        result = AgentResult(
            agent_name="dev",
            success=False,
            error=str(e)
        )
        state.add_agent_result(result)

    return state


async def evaluator_node(state: PipelineState) -> PipelineState:
    """Evaluator agent node."""
    try:
        # Get responses from dev result
        responses = state.get_data("dev", "generated_responses")
        if not responses:
            raise ValueError("No responses found from dev agent")

        # Initialize evaluator agent
        from agents import RAGEvaluatorAgent
        agent = RAGEvaluatorAgent(
            config=state.config.get("evaluator", {}),
            ragas_config=state.config.get("evaluation", {}).get("ragas", {}),
            llm_judge_config=state.config.get("evaluation", {}).get("llm_judge", {})
        )

        # Create agent state
        from agents.base import AgentState
        agent_state = AgentState(
            session_id=state.session_id,
            data={
                "generated_responses": responses
            },
            metadata=state.metadata
        )

        # Execute evaluator agent
        result_state = await agent.execute(agent_state)

        # Create result
        from .state import AgentResult
        result = AgentResult(
            agent_name="evaluator",
            success=True,
            data=result_state.data,
            metadata=result_state.metadata,
            execution_time=result_state.data.get("evaluation_metadata", {}).get("execution_time", 0.0)
        )

        state.add_agent_result(result)

    except Exception as e:
        # Create error result
        from .state import AgentResult
        result = AgentResult(
            agent_name="evaluator",
            success=False,
            error=str(e)
        )
        state.add_agent_result(result)

    return state


async def error_handler_node(state: PipelineState) -> PipelineState:
    """Error handling node."""
    # Log errors and update state
    state.current_step = "error_handling"
    return state


def retrieval_condition(state: PipelineState) -> str:
    """Condition for retrieval node."""
    if state.retrieval_result and state.retrieval_result.success:
        return "success"
    return "failure"


def dev_condition(state: PipelineState) -> str:
    """Condition for dev node."""
    if state.dev_result and state.dev_result.success:
        return "success"
    return "failure"


def evaluator_condition(state: PipelineState) -> str:
    """Condition for evaluator node."""
    if state.evaluator_result and state.evaluator_result.success:
        return "success"
    return "failure"
