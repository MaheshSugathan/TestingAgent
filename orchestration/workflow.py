"""LangGraph workflow definition for RAG evaluation pipeline."""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .state import PipelineState


def create_evaluation_workflow() -> StateGraph:
    """Create LangGraph workflow for RAG evaluation pipeline.
    
    Returns:
        Configured StateGraph instance
    """
    
    # Define the workflow
    workflow = StateGraph(PipelineState)
    
    # Add nodes for each agent
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("dev", dev_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("error_handler", error_handler_node)
    
    # Define the flow
    workflow.set_entry_point("retrieval")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "retrieval",
        retrieval_condition,
        {
            "success": "dev",
            "failure": "error_handler"
        }
    )
    
    workflow.add_conditional_edges(
        "dev",
        dev_condition,
        {
            "success": "evaluator",
            "failure": "error_handler"
        }
    )
    
    workflow.add_conditional_edges(
        "evaluator",
        evaluator_condition,
        {
            "success": END,
            "failure": "error_handler"
        }
    )
    
    workflow.add_edge("error_handler", END)
    
    return workflow.compile()


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
        from ..agents.base import AgentState
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
            askbill_agent_name=agentcore_config.get("askbill", {}).get("agent_name", "askbill"),
            timeout=agentcore_config.get("askbill", {}).get("timeout", 60),
            max_retries=agentcore_config.get("askbill", {}).get("max_retries", 3)
        )
        
        # Create agent state
        from ..agents.base import AgentState
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
        from ..agents.base import AgentState
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
