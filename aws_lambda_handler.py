"""
AWS Lambda handler for RAG Evaluation Platform
This handler is used for serverless deployment on AWS Lambda
"""

import json
import logging
from typing import Dict, Any

from orchestration.pipeline import RAGEvaluationPipeline
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for RAG evaluation pipeline
    
    Args:
        event: Lambda event dictionary containing:
            - queries: List of queries to evaluate
            - session_id: Optional session identifier
            - multi_turn: Boolean flag for multi-turn conversations
            - evaluation_method: Evaluation method ('ragas' or 'llm_judge')
        context: Lambda context object
        
    Returns:
        Dictionary containing evaluation results
    """
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Parse event
        queries = event.get('queries', [])
        session_id = event.get('session_id', context.aws_request_id)
        multi_turn = event.get('multi_turn', False)
        evaluation_method = event.get('evaluation_method', 'llm_judge')
        
        logger.info(f"Processing evaluation request: {len(queries)} queries, session_id={session_id}")
        
        # Initialize pipeline
        pipeline = RAGEvaluationPipeline(config=config)
        
        # Run evaluation
        if multi_turn:
            results = pipeline.run_multi_turn_evaluation(
                queries=queries,
                session_id=session_id
            )
        else:
            results = pipeline.run_evaluation(
                queries=queries,
                session_id=session_id
            )
        
        # Format response
        response = {
            'statusCode': 200,
            'body': {
                'session_id': session_id,
                'results': results,
                'queries_count': len(queries),
                'evaluation_method': evaluation_method,
                'multi_turn': multi_turn
            }
        }
        
        logger.info(f"Evaluation completed successfully: session_id={session_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing evaluation: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'message': 'Failed to process evaluation request'
            }
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Alias for lambda_handler"""
    return lambda_handler(event, context)


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'queries': ['What is machine learning?', 'How does RAG work?'],
        'session_id': 'test-session-123',
        'multi_turn': False,
        'evaluation_method': 'llm_judge'
    }
    
    class MockContext:
        aws_request_id = 'test-request-id'
    
    context = MockContext()
    
    result = lambda_handler(test_event, context)
    print(json.dumps(result, indent=2))

