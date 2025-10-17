"""Base classes for agents in the RAG evaluation pipeline."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
import uuid
import time

from observability import MetricsMixin, LoggerMixin


@dataclass
class AgentState:
    """State object passed between agents."""
    session_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: float


class BaseAgent(ABC, MetricsMixin, LoggerMixin):
    """Base class for all agents in the pipeline."""
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        """Initialize base agent.
        
        Args:
            config: Agent configuration
            **kwargs: Additional configuration
        """
        super().__init__()
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's main logic.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        pass
    
    def _create_session_id(self, prefix: str = "rag-eval") -> str:
        """Create a unique session ID."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
    
    def _validate_state(self, state: AgentState) -> bool:
        """Validate agent state."""
        if not isinstance(state, AgentState):
            return False
        if not state.session_id:
            return False
        return True
    
    def _record_execution_time(self, operation: str, duration: float, session_id: str) -> None:
        """Record execution time metric."""
        self.record_agent_metric(
            metric_name=f"{operation}_duration",
            value=duration,
            unit="Seconds",
            session_id=session_id
        )
    
    def _record_success(self, operation: str, session_id: str) -> None:
        """Record success metric."""
        self.record_agent_metric(
            metric_name=f"{operation}_success",
            value=1.0,
            unit="Count",
            session_id=session_id
        )
    
    def _record_failure(self, operation: str, session_id: str, error: str = None) -> None:
        """Record failure metric."""
        self.record_agent_metric(
            metric_name=f"{operation}_failure",
            value=1.0,
            unit="Count",
            session_id=session_id,
            error_type=type(error).__name__ if error else "Unknown"
        )


class RetrievalAgent(BaseAgent):
    """Abstract base for retrieval agents."""
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        """Initialize retrieval agent."""
        super().__init__(config, **kwargs)
        self.batch_size = config.get('batch_size', 10)


class DevAgent(BaseAgent):
    """Abstract base for development agents."""
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        """Initialize dev agent."""
        super().__init__(config, **kwargs)
        self.context_window = config.get('context_window', 8000)


class EvaluatorAgent(BaseAgent):
    """Abstract base for evaluation agents."""
    
    def __init__(self, config: Dict[str, Any], **kwargs):
        """Initialize evaluator agent."""
        super().__init__(config, **kwargs)
