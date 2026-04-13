"""Dev agent that integrates with external Bill AgentCore agent."""

import time
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from .base import BaseAgent, AgentState
from agents.external_agent_interface import BillAgentInterface, AgentCoreRequest, AgentCoreResponse


class DevAgent(BaseAgent):
    """Dev agent that uses external Bill AgentCore agent for RAG pipeline."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        agentcore_base_url: str,
        bill_agent_name: str = "bill",
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize Bill dev agent.
        
        Args:
            config: Agent configuration
            agentcore_base_url: Base URL for AgentCore service
            bill_agent_name: Name of the bill agent
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            **kwargs: Additional configuration
        """
        super().__init__(config, **kwargs)
        self.agentcore_base_url = agentcore_base_url
        self.bill_agent_name = bill_agent_name
        
        # Initialize Bill agent interface
        self.bill_interface = BillAgentInterface(
            base_url=agentcore_base_url,
            agent_name=bill_agent_name,
            timeout=timeout,
            max_retries=max_retries
        )
        self.bill_interface.set_logger(self.logger)
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute dev agent operation using Bill agent.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state with generated responses
        """
        start_time = time.time()
        session_id = state.session_id
        
        try:
            self.log_with_context(
                "info",
                "Starting Bill dev agent execution",
                session_id=session_id,
                agentcore_url=self.agentcore_base_url,
                bill_agent=self.bill_agent_name
            )
            
            # Get documents from state
            documents = state.data.get('documents', [])
            if not documents:
                raise ValueError("No documents found in state")
            
            # Get queries from state or use default
            queries = state.data.get('queries', self._get_default_queries())
            
            # Generate responses using Bill agent
            responses = []
            for query in queries:
                response = await self._generate_response_with_bill(
                    query, documents, session_id
                )
                responses.append({
                    'query': query,
                    'response': response['answer'],
                    'context_used': response['context'],
                    'metadata': response['metadata']
                })
            
            # Update state
            state.data['generated_responses'] = responses
            state.data['dev_metadata'] = {
                'agent_type': 'bill',
                'agentcore_url': self.agentcore_base_url,
                'bill_agent': self.bill_agent_name,
                'query_count': len(queries),
                'response_count': len(responses),
                'execution_time': time.time() - start_time
            }
            
            # Record metrics
            duration = time.time() - start_time
            self._record_execution_time("dev_bill", duration, session_id)
            self._record_success("dev_bill", session_id)
            self.record_agent_metric(
                metric_name="bill_responses_generated",
                value=len(responses),
                unit="Count",
                session_id=session_id
            )
            
            self.log_with_context(
                "info",
                f"Successfully generated {len(responses)} responses using Bill agent",
                session_id=session_id,
                duration=duration
            )
            
            return state
            
        except Exception as e:
            self.log_with_context(
                "error",
                f"Failed to execute Bill dev agent: {e}",
                session_id=session_id,
                error=str(e)
            )
            self._record_failure("dev_askbill", session_id, e)
            raise
    
    async def _generate_response_with_bill(
        self,
        query: str,
        documents: List[Document],
        session_id: str
    ) -> Dict[str, Any]:
        """Generate response using Bill agent.
        
        Args:
            query: Input query
            documents: Available documents
            session_id: Session ID for logging
            
        Returns:
            Response with answer, context, and metadata
        """
        response_start_time = time.time()
        
        try:
            # Prepare context from documents
            context = self._prepare_context_from_documents(documents)
            
            # Create request for Bill agent
            request = AgentCoreRequest(
                query=query,
                context=context,
                session_id=session_id,
                metadata={
                    "document_count": len(documents),
                    "context_length": len(context),
                    "query_type": "rag_evaluation"
                }
            )
            
            # Send request to Bill agent
            agent_response = await self.bill_interface.send_request(request)
            
            if agent_response.error:
                raise Exception(f"Bill agent error: {agent_response.error}")
            
            # Calculate metrics
            response_time = time.time() - response_start_time
            
            # Record metrics
            self.record_agent_metric(
                metric_name="bill_response_latency",
                value=response_time,
                unit="Seconds",
                session_id=session_id,
                agent_name=self.bill_agent_name
            )
            
            # Record token usage if available
            if agent_response.tokens_used:
                for token_type, count in agent_response.tokens_used.items():
                    self.record_agent_metric(
                        metric_name=f"bill_tokens_{token_type}",
                        value=count,
                        unit="Count",
                        session_id=session_id,
                        agent_name=self.bill_agent_name
                    )
            
            return {
                "answer": agent_response.answer,
                "context": context,
                "metadata": {
                    "response_time": response_time,
                    "confidence": agent_response.confidence,
                    "agent_response_time": agent_response.execution_time,
                    "tokens_used": agent_response.tokens_used,
                    "agent_name": self.bill_agent_name,
                    "agentcore_url": self.agentcore_base_url,
                    "agent_metadata": agent_response.metadata
                }
            }
            
        except Exception as e:
            self.log_with_context(
                "error",
                f"Failed to generate response with Bill agent for query: {query[:100]}...",
                session_id=session_id,
                query=query,
                error=str(e)
            )
            raise
    
    def _prepare_context_from_documents(self, documents: List[Document]) -> str:
        """Prepare context string from documents.
        
        Args:
            documents: List of LangChain documents
            
        Returns:
            Formatted context string
        """
        if not documents:
            return ""
        
        # Combine document contents
        context_parts = []
        for i, doc in enumerate(documents):
            context_parts.append(f"Document {i+1}:\n{doc.page_content}")
        
        return "\n\n".join(context_parts)
    
    def _get_default_queries(self) -> List[str]:
        """Get default queries for testing."""
        return [
            "What is the main topic of the document?",
            "Can you summarize the key points?",
            "What are the important details mentioned?",
            "How does this relate to the overall context?",
            "What conclusions can be drawn?"
        ]
    
    async def single_turn_conversation(
        self,
        query: str,
        documents: List[Document],
        session_id: str
    ) -> Dict[str, Any]:
        """Simulate a single-turn conversation using Bill agent.
        
        Args:
            query: User query
            documents: Available documents
            session_id: Session ID
            
        Returns:
            Conversation response
        """
        response = await self._generate_response_with_bill(query, documents, session_id)
        
        return {
            "type": "single_turn",
            "query": query,
            "response": response["answer"],
            "context": response["context"],
            "metadata": response["metadata"]
        }
    
    async def multi_turn_conversation(
        self,
        queries: List[str],
        documents: List[Document],
        session_id: str
    ) -> List[Dict[str, Any]]:
        """Simulate a multi-turn conversation using Bill agent.
        
        Args:
            queries: List of queries in conversation order
            documents: Available documents
            session_id: Session ID
            
        Returns:
            List of conversation responses
        """
        responses = []
        for i, query in enumerate(queries):
            response = await self._generate_response_with_bill(query, documents, session_id)
            responses.append({
                "type": "multi_turn",
                "turn": i + 1,
                "query": query,
                "response": response["answer"],
                "context": response["context"],
                "metadata": response["metadata"]
            })
        
        return responses
    
    async def health_check(self) -> bool:
        """Check if Bill agent is healthy.
        
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            return await self.bill_interface.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the Bill agent.
        
        Returns:
            Agent information dictionary
        """
        try:
            return await self.bill_interface.get_agent_info()
        except Exception as e:
            return {"error": str(e)}
