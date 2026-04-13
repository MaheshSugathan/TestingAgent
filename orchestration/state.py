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
    session_id: str = field(default_factory=lambda: f"rag-eval-{uuid.uuid4().hex[:8]}")
    pipeline_id: str = field(default_factory=lambda: f"pipeline-{uuid.uuid4().hex[:8]}")
    start_time: datetime = field(default_factory=datetime.utcnow)
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
        # These now have defaults in field definitions, but keep for backwards compatibility
        pass
    
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PipelineState':
        """Create PipelineState from dictionary (for LangGraph state reconstruction)."""
        # Handle start_time conversion
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        elif not isinstance(start_time, datetime):
            start_time = datetime.utcnow()
        
        # Reconstruct AgentResult objects
        def reconstruct_agent_result(result_data: Any) -> Optional[AgentResult]:
            if result_data is None:
                return None
            if isinstance(result_data, AgentResult):
                return result_data
            if isinstance(result_data, dict):
                # Handle timestamp conversion
                timestamp = result_data.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                elif not isinstance(timestamp, datetime):
                    timestamp = datetime.utcnow()
                else:
                    timestamp = timestamp
                
                return AgentResult(
                    agent_name=result_data.get('agent_name', ''),
                    success=result_data.get('success', False),
                    data=result_data.get('data', {}),
                    metadata=result_data.get('metadata', {}),
                    error=result_data.get('error'),
                    execution_time=result_data.get('execution_time', 0.0),
                    timestamp=timestamp
                )
            return None
        
        return cls(
            session_id=data.get('session_id', ''),
            pipeline_id=data.get('pipeline_id', ''),
            start_time=start_time,
            current_step=data.get('current_step', 'initialized'),
            retrieval_result=reconstruct_agent_result(data.get('retrieval_result')),
            dev_result=reconstruct_agent_result(data.get('dev_result')),
            evaluator_result=reconstruct_agent_result(data.get('evaluator_result')),
            metadata=data.get('metadata', {}),
            errors=data.get('errors', []),
            config=data.get('config', {})
        )
    
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
