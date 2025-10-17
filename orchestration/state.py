"""State management for the RAG evaluation pipeline."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


@dataclass
class AgentResult:
    """Result from an agent execution."""
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PipelineState:
    """State object passed through the pipeline."""
    session_id: str
    pipeline_id: str
    start_time: datetime
    current_step: str = "initialized"
    
    # Agent results
    retrieval_result: Optional[AgentResult] = None
    dev_result: Optional[AgentResult] = None
    evaluator_result: Optional[AgentResult] = None
    
    # Pipeline metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = f"rag-eval-{uuid.uuid4().hex[:8]}"
        if not self.pipeline_id:
            self.pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
        if not self.start_time:
            self.start_time = datetime.utcnow()
    
    def add_agent_result(self, result: AgentResult) -> None:
        """Add agent result to state."""
        if result.agent_name == "retrieval":
            self.retrieval_result = result
        elif result.agent_name == "dev":
            self.dev_result = result
        elif result.agent_name == "evaluator":
            self.evaluator_result = result
        
        # Update current step
        if result.success:
            if result.agent_name == "retrieval":
                self.current_step = "retrieval_completed"
            elif result.agent_name == "dev":
                self.current_step = "dev_completed"
            elif result.agent_name == "evaluator":
                self.current_step = "evaluation_completed"
        else:
            self.current_step = f"{result.agent_name}_failed"
            self.errors.append(f"{result.agent_name}: {result.error}")
    
    def get_data(self, agent_name: str, key: str = None) -> Any:
        """Get data from agent result."""
        result = getattr(self, f"{agent_name}_result", None)
        if not result:
            return None
        
        if key is None:
            return result.data
        return result.data.get(key)
    
    def get_metadata(self, agent_name: str, key: str = None) -> Any:
        """Get metadata from agent result."""
        result = getattr(self, f"{agent_name}_result", None)
        if not result:
            return None
        
        if key is None:
            return result.metadata
        return result.metadata.get(key)
    
    def is_complete(self) -> bool:
        """Check if pipeline is complete."""
        return (
            self.retrieval_result is not None and
            self.dev_result is not None and
            self.evaluator_result is not None and
            all(result.success for result in [
                self.retrieval_result,
                self.dev_result,
                self.evaluator_result
            ])
        )
    
    def has_errors(self) -> bool:
        """Check if pipeline has errors."""
        return len(self.errors) > 0
    
    def get_total_execution_time(self) -> float:
        """Get total pipeline execution time."""
        if not self.start_time:
            return 0.0
        
        total_time = (datetime.utcnow() - self.start_time).total_seconds()
        return total_time
    
    def get_agent_execution_time(self, agent_name: str) -> float:
        """Get execution time for specific agent."""
        result = getattr(self, f"{agent_name}_result", None)
        return result.execution_time if result else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "session_id": self.session_id,
            "pipeline_id": self.pipeline_id,
            "start_time": self.start_time.isoformat(),
            "current_step": self.current_step,
            "retrieval_result": self.retrieval_result.__dict__ if self.retrieval_result else None,
            "dev_result": self.dev_result.__dict__ if self.dev_result else None,
            "evaluator_result": self.evaluator_result.__dict__ if self.evaluator_result else None,
            "metadata": self.metadata,
            "errors": self.errors,
            "config": self.config,
            "is_complete": self.is_complete(),
            "has_errors": self.has_errors(),
            "total_execution_time": self.get_total_execution_time()
        }
