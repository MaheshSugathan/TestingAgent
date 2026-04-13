"""Unit tests for the RAG evaluation pipeline."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

from orchestration import RAGEvaluationPipeline
from orchestration.state import PipelineState, AgentResult
from config import ConfigManager


class TestPipelineState:
    """Test cases for PipelineState."""
    
    def test_pipeline_state_creation(self):
        """Test PipelineState creation."""
        state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow(),
            config={"test": "config"}
        )
        
        assert state.session_id == "test-session"
        assert state.pipeline_id == "test-pipeline"
        assert state.current_step == "initialized"
        assert not state.is_complete()
        assert not state.has_errors()
    
    def test_add_agent_result(self):
        """Test adding agent results."""
        state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow()
        )
        
        # Add successful retrieval result
        retrieval_result = AgentResult(
            agent_name="retrieval",
            success=True,
            data={"documents": ["doc1", "doc2"]},
            metadata={"count": 2}
        )
        
        state.add_agent_result(retrieval_result)
        
        assert state.retrieval_result == retrieval_result
        assert state.current_step == "retrieval_completed"
        
        # Add failed dev result
        dev_result = AgentResult(
            agent_name="dev",
            success=False,
            error="Test error"
        )
        
        state.add_agent_result(dev_result)
        
        assert state.dev_result == dev_result
        assert state.current_step == "dev_failed"
        assert len(state.errors) == 1
        assert "dev: Test error" in state.errors
    
    def test_get_data(self):
        """Test getting data from agent results."""
        state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow()
        )
        
        # Add result with data
        result = AgentResult(
            agent_name="retrieval",
            success=True,
            data={"documents": ["doc1"], "count": 1},
            metadata={"timestamp": "2024-01-01"}
        )
        
        state.add_agent_result(result)
        
        # Test getting all data
        all_data = state.get_data("retrieval")
        assert all_data["documents"] == ["doc1"]
        assert all_data["count"] == 1
        
        # Test getting specific key
        documents = state.get_data("retrieval", "documents")
        assert documents == ["doc1"]
        
        # Test getting from non-existent agent
        assert state.get_data("dev") is None
    
    def test_is_complete(self):
        """Test pipeline completion check."""
        state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow()
        )
        
        # Initially not complete
        assert not state.is_complete()
        
        # Add all successful results
        agents = ["retrieval", "dev", "evaluator"]
        for agent_name in agents:
            result = AgentResult(
                agent_name=agent_name,
                success=True,
                data={}
            )
            state.add_agent_result(result)
        
        assert state.is_complete()
        
        # Add failed result
        failed_result = AgentResult(
            agent_name="dev",
            success=False,
            error="Test error"
        )
        state.add_agent_result(failed_result)
        
        assert not state.is_complete()


class TestRAGEvaluationPipeline:
    """Test cases for RAGEvaluationPipeline."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        return {
            "aws": {
                "region": "us-east-1",
                "cloudwatch": {
                    "namespace": "TestNamespace",
                    "log_group": "/test/log-group"
                }
            },
            "s3": {
                "bucket": "test-bucket",
                "key_prefix": "test-data/"
            },
            "bedrock": {
                "region": "us-east-1",
                "models": {
                    "embedding": "amazon.titan-embed-text-v1",
                    "generation": "anthropic.claude-3-sonnet-20240229-v1:0"
                }
            },
            "evaluation": {
                "ragas": {"enabled": True},
                "llm_judge": {"enabled": True}
            },
            "pipeline": {
                "max_pipeline_retries": 2,
                "enable_retries": True
            }
        }
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger."""
        return Mock()
    
    @pytest.fixture
    def pipeline(self, mock_config, mock_logger):
        """Create pipeline instance."""
        with patch('orchestration.pipeline.create_evaluation_workflow'), \
             patch('observability.MetricsCollector'):
            
            return RAGEvaluationPipeline(
                config=mock_config,
                logger=mock_logger
            )
    
    @pytest.mark.asyncio
    async def test_run_single_turn_evaluation(self, pipeline):
        """Test single-turn evaluation."""
        # Mock the workflow
        mock_workflow = Mock()
        mock_state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow(),
            config=pipeline.config
        )
        
        # Mock successful completion
        mock_state.add_agent_result(AgentResult(
            agent_name="retrieval",
            success=True,
            data={"documents": ["doc1"]}
        ))
        mock_state.add_agent_result(AgentResult(
            agent_name="dev",
            success=True,
            data={"responses": ["response1"]}
        ))
        mock_state.add_agent_result(AgentResult(
            agent_name="evaluator",
            success=True,
            data={"evaluations": ["eval1"]}
        ))
        
        mock_workflow.ainvoke = AsyncMock(return_value=mock_state)
        pipeline.workflow = mock_workflow

        result = await pipeline.run_single_turn_evaluation(
            query="What is machine learning?",
            session_id="test-session"
        )

        assert "state" in result
        assert result["state"].session_id == "test-session"
        assert result["state"].is_complete()
        assert "interrupt" not in result or result.get("interrupt") is None

        mock_workflow.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_multi_turn_evaluation(self, pipeline):
        """Test multi-turn evaluation."""
        # Mock the workflow
        mock_workflow = Mock()
        mock_state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow(),
            config=pipeline.config
        )
        
        # Mock successful completion
        mock_state.add_agent_result(AgentResult(
            agent_name="retrieval",
            success=True,
            data={"documents": ["doc1"]}
        ))
        mock_state.add_agent_result(AgentResult(
            agent_name="dev",
            success=True,
            data={"responses": ["response1", "response2"]}
        ))
        mock_state.add_agent_result(AgentResult(
            agent_name="evaluator",
            success=True,
            data={"evaluations": ["eval1", "eval2"]}
        ))
        
        mock_workflow.ainvoke = AsyncMock(return_value=mock_state)
        pipeline.workflow = mock_workflow

        queries = ["What is ML?", "How does it work?"]
        result = await pipeline.run_multi_turn_evaluation(
            queries=queries,
            session_id="test-session"
        )

        assert "state" in result
        assert result["state"].session_id == "test-session"
        assert result["state"].is_complete()

        call_args = mock_workflow.ainvoke.call_args[0][0]
        assert call_args.metadata["queries"] == queries
    
    def test_get_pipeline_summary(self, pipeline):
        """Test pipeline summary generation."""
        # Create a mock state with results
        state = PipelineState(
            session_id="test-session",
            pipeline_id="test-pipeline",
            start_time=datetime.utcnow(),
            config=pipeline.config
        )
        
        # Add agent results
        state.add_agent_result(AgentResult(
            agent_name="retrieval",
            success=True,
            data={"documents": ["doc1"]},
            execution_time=1.5
        ))
        state.add_agent_result(AgentResult(
            agent_name="dev",
            success=True,
            data={"responses": ["response1"]},
            execution_time=2.0
        ))
        state.add_agent_result(AgentResult(
            agent_name="evaluator",
            success=True,
            data={"evaluation_results": [{"evaluations": {"ragas": {"metrics": {"faithfulness": 0.8}}}}]},
            execution_time=1.0
        ))
        
        summary = pipeline.get_pipeline_summary(state)
        
        assert summary["session_id"] == "test-session"
        assert summary["success"] is True
        assert summary["execution_time"] > 0
        assert len(summary["agent_results"]) == 3
        assert "evaluation_summary" in summary
    
    def test_get_evaluation_summary(self, pipeline):
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
        
        summary = pipeline._get_evaluation_summary(evaluation_results)
        
        assert summary["total_evaluations"] == 2
        assert "average_scores" in summary
        assert "passing_rates" in summary
        
        # Check Ragas averages
        ragas_scores = summary["average_scores"]["ragas"]
        assert ragas_scores["faithfulness"] == 0.75  # (0.8 + 0.7) / 2
        assert ragas_scores["relevance"] == 0.85  # (0.9 + 0.8) / 2
        
        # Check LLM judge averages
        llm_scores = summary["average_scores"]["llm_judge"]
        assert llm_scores["overall_score"] == 0.8  # (0.85 + 0.75) / 2
        assert llm_scores["coherence"] == 0.75  # (0.8 + 0.7) / 2


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        # This would require a mock config file or testing with actual files
        # For now, we'll test the basic structure
        config_manager = ConfigManager()
        
        # Test that config manager can be instantiated
        assert config_manager is not None
        assert hasattr(config_manager, 'load_config')
        assert hasattr(config_manager, 'get_aws_config')
        assert hasattr(config_manager, 'get_bedrock_config')


@pytest.mark.asyncio
async def test_async_pipeline_execution():
    """Test that async pipeline operations work correctly."""
    async def dummy_pipeline():
        return "pipeline_result"
    
    result = await dummy_pipeline()
    assert result == "pipeline_result"


if __name__ == "__main__":
    pytest.main([__file__])
