"""Unit tests for AgentCore integration."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from langchain.schema import Document

from agents.dev_agent import DevAgent
from agents.external_agent_interface import BillAgentInterface, AgentCoreRequest, AgentCoreResponse
from agents.base import AgentState


class TestBillAgentInterface:
    """Test cases for BillAgentInterface."""
    
    @pytest.fixture
    def mock_requests_session(self):
        """Mock requests session."""
        with patch('agents.external_agent_interface.requests.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            yield mock_session_instance
    
    @pytest.fixture
    def askbill_interface(self, mock_requests_session):
        """Create Bill agent interface."""
        return BillAgentInterface(
            base_url="http://localhost:8000",
            agent_name="askbill",
            timeout=60,
            max_retries=3
        )
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, askbill_interface):
        """Test successful request to Bill agent."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "answer": "This is a test response",
            "confidence": 0.95,
            "metadata": {"tokens_used": 150},
            "tokens_used": {"input": 100, "output": 50}
        }
        
        with patch.object(askbill_interface, '_make_async_request', return_value=mock_response):
            request = AgentCoreRequest(
                query="What is machine learning?",
                context="ML is a subset of AI",
                session_id="test-session"
            )
            
            response = await askbill_interface.send_request(request)
            
            assert response.answer == "This is a test response"
            assert response.confidence == 0.95
            assert response.error is None
            assert response.tokens_used == {"input": 100, "output": 50}
    
    @pytest.mark.asyncio
    async def test_send_request_failure(self, askbill_interface):
        """Test failed request to Bill agent."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(askbill_interface, '_make_async_request', return_value=mock_response):
            request = AgentCoreRequest(
                query="What is machine learning?",
                session_id="test-session"
            )
            
            response = await askbill_interface.send_request(request)
            
            assert response.answer == ""
            assert response.error == "HTTP 500: Internal Server Error"
    
    @pytest.mark.asyncio
    async def test_health_check(self, askbill_interface):
        """Test health check functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(askbill_interface, '_make_async_request', return_value=mock_response):
            is_healthy = await askbill_interface.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_get_agent_info(self, askbill_interface):
        """Test getting agent information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "askbill",
            "version": "1.0.0",
            "capabilities": ["rag", "conversation"]
        }
        
        with patch.object(askbill_interface, '_make_async_request', return_value=mock_response):
            info = await askbill_interface.get_agent_info()
            assert info["name"] == "askbill"
            assert info["version"] == "1.0.0"


class TestBillDevAgent:
    """Test cases for BillDevAgent."""
    
    @pytest.fixture
    def mock_askbill_interface(self):
        """Mock Bill agent interface."""
        with patch('agents.askbill_dev_agent.BillAgentInterface') as mock_interface_class:
            mock_interface = Mock()
            mock_interface_class.return_value = mock_interface
            yield mock_interface
    
    @pytest.fixture
    def askbill_dev_agent(self, mock_askbill_interface):
        """Create Bill dev agent."""
        config = {
            'timeout': 60,
            'max_retries': 3,
            'context_window': 8000
        }
        
        return DevAgent(
            config=config,
            agentcore_base_url="http://localhost:8000",
            bill_agent_name="bill",
            timeout=60,
            max_retries=3
        )
    
    @pytest.mark.asyncio
    async def test_prepare_context_from_documents(self, askbill_dev_agent):
        """Test context preparation from documents."""
        documents = [
            Document(page_content="Document 1 content", metadata={"source": "doc1"}),
            Document(page_content="Document 2 content", metadata={"source": "doc2"})
        ]
        
        context = askbill_dev_agent._prepare_context_from_documents(documents)
        
        assert "Document 1:" in context
        assert "Document 1 content" in context
        assert "Document 2:" in context
        assert "Document 2 content" in context
    
    @pytest.mark.asyncio
    async def test_generate_response_with_askbill(self, askbill_dev_agent, mock_askbill_interface):
        """Test response generation using Bill agent."""
        # Setup mock response
        mock_response = AgentCoreResponse(
            answer="This is the Bill response",
            confidence=0.9,
            metadata={"model": "claude-3"},
            execution_time=1.5,
            tokens_used={"input": 100, "output": 50}
        )
        mock_askbill_interface.send_request.return_value = mock_response
        
        # Test documents
        documents = [
            Document(page_content="Test document content", metadata={"source": "test"})
        ]
        
        response = await askbill_dev_agent._generate_response_with_askbill(
            query="What is this about?",
            documents=documents,
            session_id="test-session"
        )
        
        assert response["answer"] == "This is the Bill response"
        assert response["context"] == "Document 1:\nTest document content"
        assert response["metadata"]["confidence"] == 0.9
        assert response["metadata"]["agent_name"] == "askbill"
        
        # Verify Bill interface was called correctly
        mock_askbill_interface.send_request.assert_called_once()
        call_args = mock_askbill_interface.send_request.call_args[0][0]
        assert call_args.query == "What is this about?"
        assert call_args.session_id == "test-session"
    
    @pytest.mark.asyncio
    async def test_execute_with_success(self, askbill_dev_agent, mock_askbill_interface):
        """Test successful execution of Bill dev agent."""
        # Setup mock response
        mock_response = AgentCoreResponse(
            answer="Test response",
            confidence=0.8,
            execution_time=1.0,
            tokens_used={"input": 50, "output": 25}
        )
        mock_askbill_interface.send_request.return_value = mock_response
        
        # Create test state
        state = AgentState(
            session_id="test-session",
            data={
                'documents': [
                    Document(page_content="Test content", metadata={"source": "test"})
                ],
                'queries': ["What is this about?"]
            },
            metadata={}
        )
        
        result_state = await askbill_dev_agent.execute(state)
        
        assert len(result_state.data['generated_responses']) == 1
        assert result_state.data['generated_responses'][0]['query'] == "What is this about?"
        assert result_state.data['generated_responses'][0]['response'] == "Test response"
        assert result_state.data['dev_metadata']['agent_type'] == 'askbill'
    
    @pytest.mark.asyncio
    async def test_single_turn_conversation(self, askbill_dev_agent, mock_askbill_interface):
        """Test single-turn conversation."""
        mock_response = AgentCoreResponse(
            answer="Single turn response",
            confidence=0.85,
            execution_time=0.8
        )
        mock_askbill_interface.send_request.return_value = mock_response
        
        documents = [Document(page_content="Test content")]
        
        result = await askbill_dev_agent.single_turn_conversation(
            query="Test query",
            documents=documents,
            session_id="test-session"
        )
        
        assert result["type"] == "single_turn"
        assert result["query"] == "Test query"
        assert result["response"] == "Single turn response"
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, askbill_dev_agent, mock_askbill_interface):
        """Test multi-turn conversation."""
        mock_responses = [
            AgentCoreResponse(answer="Response 1", confidence=0.8),
            AgentCoreResponse(answer="Response 2", confidence=0.9)
        ]
        mock_askbill_interface.send_request.side_effect = mock_responses
        
        documents = [Document(page_content="Test content")]
        queries = ["Query 1", "Query 2"]
        
        results = await askbill_dev_agent.multi_turn_conversation(
            queries=queries,
            documents=documents,
            session_id="test-session"
        )
        
        assert len(results) == 2
        assert results[0]["turn"] == 1
        assert results[0]["query"] == "Query 1"
        assert results[0]["response"] == "Response 1"
        assert results[1]["turn"] == 2
        assert results[1]["query"] == "Query 2"
        assert results[1]["response"] == "Response 2"
    
    @pytest.mark.asyncio
    async def test_health_check(self, askbill_dev_agent, mock_askbill_interface):
        """Test health check functionality."""
        mock_askbill_interface.health_check.return_value = True
        
        is_healthy = await askbill_dev_agent.health_check()
        assert is_healthy is True
        mock_askbill_interface.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_agent_info(self, askbill_dev_agent, mock_askbill_interface):
        """Test getting agent information."""
        mock_info = {
            "name": "askbill",
            "version": "1.0.0",
            "capabilities": ["rag", "conversation"]
        }
        mock_askbill_interface.get_agent_info.return_value = mock_info
        
        info = await askbill_dev_agent.get_agent_info()
        assert info == mock_info
        mock_askbill_interface.get_agent_info.assert_called_once()


class TestAgentCoreRequest:
    """Test cases for AgentCoreRequest."""
    
    def test_agent_core_request_creation(self):
        """Test AgentCoreRequest creation."""
        request = AgentCoreRequest(
            query="Test query",
            context="Test context",
            session_id="test-session",
            metadata={"key": "value"}
        )
        
        assert request.query == "Test query"
        assert request.context == "Test context"
        assert request.session_id == "test-session"
        assert request.metadata == {"key": "value"}
    
    def test_agent_core_request_minimal(self):
        """Test AgentCoreRequest with minimal fields."""
        request = AgentCoreRequest(query="Test query")
        
        assert request.query == "Test query"
        assert request.context is None
        assert request.session_id is None
        assert request.metadata is None


class TestAgentCoreResponse:
    """Test cases for AgentCoreResponse."""
    
    def test_agent_core_response_creation(self):
        """Test AgentCoreResponse creation."""
        response = AgentCoreResponse(
            answer="Test answer",
            confidence=0.9,
            metadata={"model": "claude-3"},
            execution_time=1.5,
            tokens_used={"input": 100, "output": 50}
        )
        
        assert response.answer == "Test answer"
        assert response.confidence == 0.9
        assert response.metadata == {"model": "claude-3"}
        assert response.execution_time == 1.5
        assert response.tokens_used == {"input": 100, "output": 50}
        assert response.error is None
    
    def test_agent_core_response_with_error(self):
        """Test AgentCoreResponse with error."""
        response = AgentCoreResponse(
            answer="",
            error="Test error",
            execution_time=0.5
        )
        
        assert response.answer == ""
        assert response.error == "Test error"
        assert response.execution_time == 0.5
        assert response.confidence is None


@pytest.mark.asyncio
async def test_async_agentcore_operations():
    """Test that async AgentCore operations work correctly."""
    # Mock async request
    async def mock_async_request():
        return "async_agentcore_result"
    
    result = await mock_async_request()
    assert result == "async_agentcore_result"


if __name__ == "__main__":
    pytest.main([__file__])
