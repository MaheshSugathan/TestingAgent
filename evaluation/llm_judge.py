"""LLM-as-a-Judge evaluation for RAG responses."""

import json
import time
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from .evaluation_metrics import EvaluationResult, EvaluationMetrics, BatchEvaluationResult


class LLMJudgeEvaluator:
    """Evaluator using LLM-as-a-Judge approach with Bedrock."""
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        aws_region: str = "us-east-1",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs
    ):
        """Initialize LLM-as-a-Judge evaluator.
        
        Args:
            model_id: Bedrock model ID for judging
            aws_region: AWS region
            temperature: Model temperature
            max_tokens: Maximum tokens for response
            **kwargs: Additional configuration
        """
        self.model_id = model_id
        self.aws_region = aws_region
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Bedrock client
        try:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=aws_region
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Bedrock client: {e}")
        
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger instance."""
        self.logger = logger
    
    def evaluate_single(
        self,
        query: str,
        answer: str,
        context: str,
        ground_truth: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate a single query-answer pair.
        
        Args:
            query: Input query
            answer: Generated answer
            context: Retrieved context
            ground_truth: Ground truth answer (optional)
            session_id: Session ID for logging
            
        Returns:
            Evaluation result
        """
        try:
            # Create evaluation prompt
            prompt = self._create_evaluation_prompt(
                query, answer, context, ground_truth
            )
            
            # Get LLM judgment
            judgment = self._get_llm_judgment(prompt)
            
            # Parse judgment
            metrics = self._parse_judgment(judgment)
            
            return EvaluationResult(
                query=query,
                answer=answer,
                context=context,
                metrics=metrics,
                evaluation_method="llm_judge",
                session_id=session_id,
                comments=judgment.get("reasoning", "")
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"LLM-as-a-Judge evaluation failed: {e}")
            
            # Return default result with zero scores
            return EvaluationResult(
                query=query,
                answer=answer,
                context=context,
                metrics=EvaluationMetrics(),
                evaluation_method="llm_judge",
                session_id=session_id,
                comments=f"Evaluation failed: {str(e)}"
            )
    
    def evaluate_batch(
        self,
        queries: List[str],
        answers: List[str],
        contexts: List[str],
        ground_truths: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> BatchEvaluationResult:
        """Evaluate multiple query-answer pairs.
        
        Args:
            queries: List of queries
            answers: List of answers
            contexts: List of contexts
            ground_truths: List of ground truth answers (optional)
            session_id: Session ID for logging
            
        Returns:
            Batch evaluation result
        """
        results = []
        
        for i, (query, answer, context) in enumerate(zip(queries, answers, contexts)):
            ground_truth = ground_truths[i] if ground_truths else None
            
            result = self.evaluate_single(
                query=query,
                answer=answer,
                context=context,
                ground_truth=ground_truth,
                session_id=session_id
            )
            
            results.append(result)
        
        return BatchEvaluationResult(
            results=results,
            session_id=session_id
        )
    
    def _create_evaluation_prompt(
        self,
        query: str,
        answer: str,
        context: str,
        ground_truth: Optional[str] = None
    ) -> str:
        """Create evaluation prompt for LLM judge."""
        
        prompt = f"""You are an expert evaluator for RAG (Retrieval-Augmented Generation) systems. Your task is to evaluate the quality of a generated answer based on the provided context and query.

Query: {query}

Context: {context}

Generated Answer: {answer}"""

        if ground_truth:
            prompt += f"\n\nGround Truth: {ground_truth}"

        prompt += """

Please evaluate the generated answer on the following criteria (score from 0.0 to 1.0):

1. **Faithfulness**: How well does the answer stay true to the provided context? Does it avoid hallucination?
2. **Relevance**: How relevant is the answer to the query? Does it address what was asked?
3. **Correctness**: How accurate is the answer based on the context and ground truth (if provided)?
4. **Coherence**: How well-structured and coherent is the answer?
5. **Completeness**: How complete is the answer in addressing the query?
6. **Overall**: Overall quality score considering all factors.

Please respond with a JSON object in the following format:
{
    "faithfulness": 0.0-1.0,
    "relevance": 0.0-1.0,
    "correctness": 0.0-1.0,
    "coherence": 0.0-1.0,
    "completeness": 0.0-1.0,
    "overall": 0.0-1.0,
    "reasoning": "Brief explanation of the scores"
}

Focus on being objective and consistent in your evaluation."""

        return prompt
    
    def _get_llm_judgment(self, prompt: str) -> Dict[str, Any]:
        """Get judgment from LLM."""
        try:
            # Prepare request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Invoke model
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Try to parse JSON from response
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, return default structure
                return {
                    "faithfulness": 0.5,
                    "relevance": 0.5,
                    "correctness": 0.5,
                    "coherence": 0.5,
                    "completeness": 0.5,
                    "overall": 0.5,
                    "reasoning": "Failed to parse LLM response"
                }
            
        except ClientError as e:
            if self.logger:
                self.logger.error(f"Bedrock invocation failed: {e}")
            raise
        except Exception as e:
            if self.logger:
                self.logger.error(f"LLM judgment failed: {e}")
            raise
    
    def _parse_judgment(self, judgment: Dict[str, Any]) -> EvaluationMetrics:
        """Parse LLM judgment into evaluation metrics."""
        return EvaluationMetrics(
            faithfulness=judgment.get("faithfulness"),
            relevance=judgment.get("relevance"),
            correctness=judgment.get("correctness"),
            coherence_score=judgment.get("coherence"),
            completeness_score=judgment.get("completeness"),
            overall_score=judgment.get("overall"),
        )
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics."""
        return [
            "faithfulness",
            "relevance", 
            "correctness",
            "coherence",
            "completeness",
            "overall"
        ]
