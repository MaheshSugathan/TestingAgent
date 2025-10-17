#!/usr/bin/env python3
"""
AgentCore-compliant Dev Agent for RAG evaluation pipeline
This agent integrates with external Bill agent and can be deployed to AgentCore
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DevRequest:
    """Request structure for dev agent."""
    query: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    bill_agent_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class DevResponse:
    """Response structure for dev agent."""
    query: str
    response: str
    confidence: Optional[float] = None
    session_id: Optional[str] = None
    execution_time: float = 0.0
    bill_agent_metadata: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DevAgent:
    """AgentCore-compliant Dev Agent with Bill integration."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize dev agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config or {}
        self.bill_agent_url = self.config.get('bill_agent_url', 'http://localhost:8001')
        self.timeout = self.config.get('timeout', 60)
        self.max_retries = self.config.get('max_retries', 3)
    
    async def invoke(self, request: DevRequest) -> DevResponse:
        """Invoke the dev agent.
        
        Args:
            request: Dev agent request
            
        Returns:
            DevResponse: Generated response with metadata
        """
        start_time = time.time()
        session_id = request.session_id or f"dev-{int(time.time())}"
        
        try:
            logger.info(f"Starting dev agent execution for query: {request.query[:50]}...")
            
            # Generate response using Bill agent
            response = await self._generate_response_with_bill(
                query=request.query,
                context=request.context or "",
                session_id=session_id,
                bill_agent_url=request.bill_agent_url or self.bill_agent_url
            )
            
            execution_time = time.time() - start_time
            
            dev_response = DevResponse(
                query=request.query,
                response=response.get("answer", ""),
                confidence=response.get("confidence"),
                session_id=session_id,
                execution_time=execution_time,
                bill_agent_metadata=response.get("metadata", {}),
                metadata={
                    "agent_type": "dev",
                    "bill_agent_url": request.bill_agent_url or self.bill_agent_url,
                    "context_used": bool(request.context),
                    "context_length": len(request.context) if request.context else 0,
                    "query_length": len(request.query),
                    "timestamp": time.time()
                }
            )
            
            logger.info(f"Dev agent execution completed in {execution_time:.3f}s")
            return dev_response
            
        except Exception as e:
            logger.error(f"Dev agent execution failed: {e}")
            return DevResponse(
                query=request.query,
                response="",
                session_id=session_id,
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _generate_response_with_bill(
        self, 
        query: str, 
        context: str, 
        session_id: str,
        bill_agent_url: str
    ) -> Dict[str, Any]:
        """Generate response using Bill agent.
        
        Args:
            query: User query
            context: Retrieved context
            session_id: Session identifier
            bill_agent_url: Bill agent URL
            
        Returns:
            Response dictionary from Bill agent
        """
        payload = {
            "query": query,
            "context": context,
            "session_id": session_id,
            "metadata": {
                "source": "dev_agent",
                "timestamp": time.time()
            }
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling Bill agent (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    f"{bill_agent_url}/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Bill agent response received successfully")
                    return result
                else:
                    logger.warning(f"Bill agent returned status {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Bill agent request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise e
                await asyncio.sleep(1)  # Wait before retry
        
        # If all retries failed, return a fallback response
        return {
            "answer": "I apologize, but I'm unable to process your request at the moment. Please try again later.",
            "confidence": 0.0,
            "metadata": {
                "error": "Bill agent unavailable",
                "attempts": self.max_retries
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the agent.
        
        Returns:
            Health status dictionary
        """
        # Check Bill agent connectivity
        bill_healthy = False
        try:
            response = requests.get(f"{self.bill_agent_url}/health", timeout=5)
            bill_healthy = response.status_code == 200
        except Exception:
            pass
        
        return {
            "status": "healthy" if bill_healthy else "degraded",
            "agent_type": "dev",
            "bill_agent_url": self.bill_agent_url,
            "bill_agent_healthy": bill_healthy,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information.
        
        Returns:
            Agent information dictionary
        """
        return {
            "name": "dev-agent",
            "version": "1.0.0",
            "description": "Dev agent for RAG evaluation pipeline with Bill integration",
            "capabilities": ["response_generation", "bill_integration", "context_processing"],
            "status": "active",
            "config": self.config
        }

# AgentCore entry point
async def main():
    """Main entry point for AgentCore deployment."""
    agent = DevAgent()
    
    # Example usage
    request = DevRequest(
        query="What is machine learning?",
        context="Machine learning is a subset of artificial intelligence...",
        session_id="test-session"
    )
    
    response = await agent.invoke(request)
    print(f"Response: {response.response}")
    print(f"Confidence: {response.confidence}")
    print(f"Execution time: {response.execution_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
