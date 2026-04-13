"""Unit tests for agents."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document

from agents.retrieval_agent import S3RetrievalAgent
from agents.dev_agent import DevAgent
from agents.evaluator_agent import RAGEvaluatorAgent
from agents.base import AgentState


class TestS3RetrievalAgent:
    """Test cases for S3RetrievalAgent."""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        with patch('boto3.client') as mock_client:
            mock_s3 = Mock()
            mock_client.return_value = mock_s3
            yield mock_s3
    
    @pytest.fixture
    def retrieval_agent(self, mock_s3_client):
        """Create retrieval agent instance."""
        config = {
            'timeout': 30,
            'max_retries': 3,
            'batch_size': 10
        }
        return S3RetrievalAgent(
            config=config,
            bucket_name="test-bucket",
            key_prefix="test-data/",
            aws_region="us-east-1"
        )
    
    @pytest.mark.asyncio
    async def test_parse_json_content(self, retrieval_agent):
        """Test JSON content parsing."""
        json_content = '''
        {
            "title": "Test Document",
            "content": "This is test content",
            "metadata": {"source": "test"}
        }
        '''
        
        doc = await retrieval_agent._parse_json_content(json_content, "test.json")
        
        assert doc is not None
        assert isinstance(doc, Document)
        assert "Test Document" in doc.page_content
        assert doc.metadata["source"] == "test.json"
    
    @pytest.mark.asyncio
    async def test_parse_text_content(self, retrieval_agent):
        """Test text content parsing."""
        text_content = "This is a simple text document for testing."
        
        doc = await retrieval_agent._parse_text_content(text_content, "test.txt")
        
        assert doc is not None
        assert isinstance(doc, Document)
        assert doc.page_content == text_content
        assert doc.metadata["source"] == "test.txt"
    
    @pytest.mark.asyncio
    async def test_list_s3_objects(self, retrieval_agent, mock_s3_client):
        """Test S3 object listing."""
        # Mock paginator response
        mock_paginator = Mock()
        mock_s3_client.get_paginator.return_value = mock_paginator
        
        mock_page = {
            'Contents': [
                {'Key': 'test-data/document1.json', 'Size': 1024},
                {'Key': 'test-data/document2.txt', 'Size': 512},
                {'Key': 'test-data/image.jpg', 'Size': 2048}  # Should be filtered out
            ]
        }
        mock_paginator.paginate.return_value = [mock_page]
        
        objects = await retrieval_agent._list_s3_objects()
        
        # Should filter out unsupported formats
        assert len(objects) == 2
        assert any(obj['Key'].endswith('.json') for obj in objects)
        assert any(obj['Key'].endswith('.txt') for obj in objects)


class TestDevAgent:
    """Test cases for DevAgent (Bill integration)."""
    
    @pytest.fixture
    def mock_bill_interface(self):
        """Mock Bill agent interface."""
        with patch('agents.dev_agent.BillAgentInterface') as mock_interface_class:
            mock_interface = Mock()
            mock_interface_class.return_value = mock_interface
            yield mock_interface
    
    @pytest.fixture
    def dev_agent(self, mock_bill_interface):
        """Create dev agent instance."""
        config = {
            'timeout': 60,
            'max_retries': 3,
            'context_window': 8000
        }
        
        return DevAgent(
            config=config,
            agentcore_base_url="http://localhost:8000",
            askbill_agent_name="askbill",
            timeout=60,
            max_retries=3
        )
    
    @pytest.mark.asyncio
    async def test_prepare_context_from_documents(self, dev_agent):
        """Test context preparation from documents."""
        documents = [
            Document(page_content="Document 1 content", metadata={"source": "doc1"}),
            Document(page_content="Document 2 content", metadata={"source": "doc2"})
        ]
        
        context = dev_agent._prepare_context_from_documents(documents)
        
        assert "Document 1:" in context
        assert "Document 1 content" in context
        assert "Document 2:" in context
        assert "Document 2 content" in context
    
    def test_get_default_queries(self, dev_agent):
        """Test default queries generation."""
        queries = dev_agent._get_default_queries()
        
        assert len(queries) == 5
        assert all(isinstance(q, str) for q in queries)
        assert "main topic" in queries[0].lower()


class TestRAGEvaluatorAgent:
    """Test cases for RAGEvaluatorAgent."""
    
    @pytest.fixture
    def evaluator_agent(self):
        """Create evaluator agent instance."""
        config = {
            'timeout': 45,
            'max_retries': 2
        }
        
        ragas_config = {
            'enabled': True,
            'metrics': ['faithfulness', 'relevance']
        }
        
        llm_judge_config = {
            'enabled': True,
            'model_id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'aws_region': 'us-east-1'
        }
        
        with patch('agents.evaluator_agent.RagasEvaluator'), \
             patch('agents.evaluator_agent.LLMJudgeEvaluator'):
            
            return RAGEvaluatorAgent(
                config=config,
                ragas_config=ragas_config,
                llm_judge_config=llm_judge_config
            )
    
    @pytest.mark.asyncio
    async def test_evaluate_single_response(self, evaluator_agent):
        """Test single response evaluation."""
        # Mock evaluators
        evaluator_agent.ragas_evaluator = Mock()
        evaluator_agent.ragas_evaluator.evaluate_single.return_value = Mock(
            to_dict=lambda: {
                'query': 'test query',
                'answer': 'test answer',
                'metrics': {'faithfulness': 0.8, 'relevance': 0.9}
            }
        )
        
        evaluator_agent.llm_judge_evaluator = Mock()
        evaluator_agent.llm_judge_evaluator.evaluate_single.return_value = Mock(
            to_dict=lambda: {
                'query': 'test query',
                'answer': 'test answer',
                'metrics': {'overall_score': 0.85, 'coherence': 0.8}
            }
        )
        
        result = await evaluator_agent.evaluate_single_response(
            query="What is machine learning?",
            answer="Machine learning is a subset of AI.",
            context="ML is a subset of artificial intelligence.",
            session_id="test-session"
        )
        
        assert "evaluations" in result
        assert "ragas" in result["evaluations"]
        assert "llm_judge" in result["evaluations"]
    
    def test_get_evaluation_summary(self, evaluator_agent):
        """Test evaluation summary generation."""
        evaluation_results = [
            {
                "evaluations": {
                    "ragas": {
                        "metrics": {
                            "faithfulness": 0.8,
                            "relevance": 0.9
                        }
                    },
                    "llm_judge": {
                        "metrics": {
                            "overall_score": 0.85,
                            "coherence": 0.8
                        }
                    }
                }
            },
            {
                "evaluations": {
                    "ragas": {
                        "metrics": {
                            "faithfulness": 0.7,
                            "relevance": 0.8
                        }
                    },
                    "llm_judge": {
                        "metrics": {
                            "overall_score": 0.75,
                            "coherence": 0.7
                        }
                    }
                }
            }
        ]
        
        summary = evaluator_agent.get_evaluation_summary(evaluation_results)
        
        assert summary["total_evaluations"] == 2
        assert "average_scores" in summary
        assert "passing_rates" in summary
        
        # Check average calculation
        ragas_scores = summary["average_scores"]["ragas"]
        assert ragas_scores["faithfulness"] == 0.75  # (0.8 + 0.7) / 2
        assert ragas_scores["relevance"] == 0.85  # (0.9 + 0.8) / 2


class TestAgentState:
    """Test cases for AgentState."""
    
    def test_agent_state_creation(self):
        """Test AgentState creation."""
        state = AgentState(
            session_id="test-session",
            data={"test": "data"},
            metadata={"test": "metadata"}
        )
        
        assert state.session_id == "test-session"
        assert state.data["test"] == "data"
        assert state.metadata["test"] == "metadata"
    
    def test_agent_state_validation(self):
        """Test AgentState validation."""
        # Valid state
        valid_state = AgentState(
            session_id="test-session",
            data={},
            metadata={}
        )
        
        # Invalid state (missing session_id)
        invalid_state = AgentState(
            session_id="",
            data={},
            metadata={}
        )
        
        from agents.base import BaseAgent
        base_agent = BaseAgent({})
        
        assert base_agent._validate_state(valid_state) is True
        assert base_agent._validate_state(invalid_state) is False


@pytest.mark.asyncio
async def test_async_operations():
    """Test that async operations work correctly."""
    # This is a basic test to ensure asyncio compatibility
    async def dummy_async_function():
        return "async_result"
    
    result = await dummy_async_function()
    assert result == "async_result"


if __name__ == "__main__":
    pytest.main([__file__])
