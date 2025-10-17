"""Interface for external AgentCore agents."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class AgentCoreRequest:
    """Request structure for AgentCore agents."""
    query: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentCoreResponse:
    """Response structure from AgentCore agents."""
    answer: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    tokens_used: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class ExternalAgentInterface(ABC):
    """Abstract interface for external agent communication."""
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """Initialize external agent interface.
        
        Args:
            base_url: Base URL for the external agent service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = None
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
    
    @abstractmethod
    async def send_request(self, request: AgentCoreRequest) -> AgentCoreResponse:
        """Send request to external agent.
        
        Args:
            request: Request to send
            
        Returns:
            Response from external agent
        """
        pass
    
    def _log_request(self, request: AgentCoreRequest, response: AgentCoreResponse, duration: float):
        """Log request and response details."""
        if self.logger:
            self.logger.info(
                f"External agent request completed",
                extra={
                    "query": request.query[:100],
                    "session_id": request.session_id,
                    "duration": duration,
                    "success": response.error is None,
                    "error": response.error
                }
            )


class BillAgentInterface(ExternalAgentInterface):
    """Interface for the Bill AgentCore agent."""
    
    def __init__(
        self,
        base_url: str,
        agent_name: str = "bill",
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize Bill agent interface.
        
        Args:
            base_url: Base URL for AgentCore service
            agent_name: Name of the bill agent
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            **kwargs: Additional configuration
        """
        super().__init__(base_url, timeout, max_retries)
        self.agent_name = agent_name
        self.endpoint = f"{self.base_url}/agents/{self.agent_name}/invoke"
    
    async def send_request(self, request: AgentCoreRequest) -> AgentCoreResponse:
        """Send request to Bill agent.
        
        Args:
            request: Request to send
            
        Returns:
            Response from Bill agent
        """
        start_time = time.time()
        
        try:
            # Prepare request payload
            payload = {
                "query": request.query,
                "session_id": request.session_id,
                "metadata": request.metadata or {}
            }
            
            if request.context:
                payload["context"] = request.context
            
            # Make async request
            response = await self._make_async_request(payload)
            
            # Parse response
            if response.status_code == 200:
                response_data = response.json()
                
                agent_response = AgentCoreResponse(
                    answer=response_data.get("answer", ""),
                    confidence=response_data.get("confidence"),
                    metadata=response_data.get("metadata", {}),
                    execution_time=time.time() - start_time,
                    tokens_used=response_data.get("tokens_used"),
                )
            else:
                agent_response = AgentCoreResponse(
                    answer="",
                    error=f"HTTP {response.status_code}: {response.text}",
                    execution_time=time.time() - start_time
                )
            
            # Log the request
            self._log_request(request, agent_response, agent_response.execution_time)
            
            return agent_response
            
        except Exception as e:
            duration = time.time() - start_time
            error_response = AgentCoreResponse(
                answer="",
                error=str(e),
                execution_time=duration
            )
            
            self._log_request(request, error_response, duration)
            return error_response
    
    async def _make_async_request(self, payload: Dict[str, Any]) -> requests.Response:
        """Make asynchronous HTTP request."""
        loop = asyncio.get_event_loop()
        
        def make_request():
            return self.session.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
        
        return await loop.run_in_executor(None, make_request)
    
    async def health_check(self) -> bool:
        """Check if the Bill agent is healthy.
        
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            health_endpoint = f"{self.base_url}/agents/{self.agent_name}/health"
            response = await self._make_async_request({})
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the Bill agent.
        
        Returns:
            Agent information dictionary
        """
        try:
            info_endpoint = f"{self.base_url}/agents/{self.agent_name}/info"
            response = await self._make_async_request({})
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to get agent info: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}


class AgentCoreManager:
    """Manager for multiple AgentCore agents."""
    
    def __init__(self, base_url: str, **kwargs):
        """Initialize AgentCore manager.
        
        Args:
            base_url: Base URL for AgentCore service
            **kwargs: Additional configuration
        """
        self.base_url = base_url
        self.agents: Dict[str, ExternalAgentInterface] = {}
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
        for agent in self.agents.values():
            agent.set_logger(logger)
    
    def add_agent(self, name: str, agent_interface: ExternalAgentInterface):
        """Add an agent interface.
        
        Args:
            name: Agent name
            agent_interface: Agent interface instance
        """
        self.agents[name] = agent_interface
        if self.logger:
            agent_interface.set_logger(self.logger)
    
    def get_agent(self, name: str) -> Optional[ExternalAgentInterface]:
        """Get agent interface by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent interface or None if not found
        """
        return self.agents.get(name)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all registered agents.
        
        Returns:
            Dictionary mapping agent names to health status
        """
        health_status = {}
        
        for name, agent in self.agents.items():
            try:
                if hasattr(agent, 'health_check'):
                    health_status[name] = await agent.health_check()
                else:
                    health_status[name] = True  # Assume healthy if no health check
            except Exception:
                health_status[name] = False
        
        return health_status
    
    def list_agents(self) -> List[str]:
        """List all registered agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
