#!/usr/bin/env python3
"""
AgentCore-compliant Retrieval Agent for RAG evaluation pipeline
This agent can be deployed to AgentCore and handles document retrieval from S3
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

# Mock boto3 for AgentCore deployment (replace with actual boto3 in production)
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    # Mock boto3 for testing
    class MockS3Client:
        def get_object(self, Bucket, Key):
            return {'Body': MockBody()}
    
    class MockBody:
        def read(self):
            return b"Mock document content for testing"
    
    boto3 = type('MockBoto3', (), {'client': lambda x: MockS3Client()})()
    ClientError = Exception

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RetrievalRequest:
    """Request structure for retrieval agent."""
    query: str
    session_id: Optional[str] = None
    bucket_name: Optional[str] = None
    max_documents: int = 5
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class RetrievalResponse:
    """Response structure for retrieval agent."""
    documents: List[Dict[str, Any]]
    query: str
    session_id: Optional[str] = None
    retrieval_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RetrievalAgent:
    """AgentCore-compliant Retrieval Agent."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize retrieval agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config or {}
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.default_bucket = os.getenv('S3_BUCKET_NAME', 'rag-evaluation-documents')
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            logger.info(f"Initialized S3 client for region: {self.aws_region}")
        except Exception as e:
            logger.warning(f"Could not initialize S3 client: {e}")
            self.s3_client = None
    
    async def invoke(self, request: RetrievalRequest) -> RetrievalResponse:
        """Invoke the retrieval agent.
        
        Args:
            request: Retrieval request
            
        Returns:
            RetrievalResponse: Retrieved documents and metadata
        """
        start_time = time.time()
        session_id = request.session_id or f"retrieval-{int(time.time())}"
        
        try:
            logger.info(f"Starting retrieval for query: {request.query[:50]}...")
            
            # Retrieve documents
            documents = await self._retrieve_documents(
                query=request.query,
                bucket_name=request.bucket_name or self.default_bucket,
                max_documents=request.max_documents
            )
            
            retrieval_time = time.time() - start_time
            
            response = RetrievalResponse(
                documents=documents,
                query=request.query,
                session_id=session_id,
                retrieval_time=retrieval_time,
                metadata={
                    "agent_type": "retrieval",
                    "bucket_name": request.bucket_name or self.default_bucket,
                    "documents_retrieved": len(documents),
                    "query_length": len(request.query),
                    "timestamp": time.time()
                }
            )
            
            logger.info(f"Retrieved {len(documents)} documents in {retrieval_time:.3f}s")
            return response
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return RetrievalResponse(
                documents=[],
                query=request.query,
                session_id=session_id,
                retrieval_time=time.time() - start_time,
                error=str(e)
            )
    
    async def _retrieve_documents(
        self, 
        query: str, 
        bucket_name: str, 
        max_documents: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve documents from S3 bucket.
        
        Args:
            query: Search query
            bucket_name: S3 bucket name
            max_documents: Maximum number of documents to retrieve
            
        Returns:
            List of document dictionaries
        """
        documents = []
        
        if not self.s3_client:
            # Return mock documents for testing
            return self._get_mock_documents(query, max_documents)
        
        try:
            # List objects in bucket (simplified - in production, use proper search)
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=max_documents)
            
            for obj in response.get('Contents', [])[:max_documents]:
                try:
                    # Get object content
                    obj_response = self.s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                    content = obj_response['Body'].read().decode('utf-8')
                    
                    document = {
                        "content": content,
                        "metadata": {
                            "source": obj['Key'],
                            "bucket": bucket_name,
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat(),
                            "query_relevance": self._calculate_relevance(query, content)
                        }
                    }
                    documents.append(document)
                    
                except Exception as e:
                    logger.warning(f"Failed to retrieve document {obj['Key']}: {e}")
                    continue
                    
        except ClientError as e:
            logger.error(f"S3 error: {e}")
            # Fallback to mock documents
            documents = self._get_mock_documents(query, max_documents)
        
        return documents
    
    def _get_mock_documents(self, query: str, max_documents: int) -> List[Dict[str, Any]]:
        """Get mock documents for testing.
        
        Args:
            query: Search query
            max_documents: Maximum number of documents
            
        Returns:
            List of mock document dictionaries
        """
        mock_documents = [
            {
                "content": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It focuses on algorithms that can access data and use it to learn patterns.",
                "metadata": {
                    "source": "mock_doc_1.txt",
                    "bucket": "mock-bucket",
                    "size": 250,
                    "last_modified": "2024-01-01T00:00:00Z",
                    "query_relevance": 0.9
                }
            },
            {
                "content": "Deep learning is a subset of machine learning that uses neural networks with multiple layers (deep neural networks) to model and understand complex patterns in data. It's inspired by the structure and function of the brain.",
                "metadata": {
                    "source": "mock_doc_2.txt",
                    "bucket": "mock-bucket",
                    "size": 280,
                    "last_modified": "2024-01-02T00:00:00Z",
                    "query_relevance": 0.85
                }
            },
            {
                "content": "Natural Language Processing (NLP) is a field of artificial intelligence that focuses on the interaction between computers and humans through natural language. It combines computational linguistics with machine learning and deep learning.",
                "metadata": {
                    "source": "mock_doc_3.txt",
                    "bucket": "mock-bucket",
                    "size": 300,
                    "last_modified": "2024-01-03T00:00:00Z",
                    "query_relevance": 0.8
                }
            }
        ]
        
        # Filter based on query relevance
        query_lower = query.lower()
        relevant_docs = []
        
        for doc in mock_documents:
            content_lower = doc["content"].lower()
            if any(keyword in content_lower for keyword in query_lower.split()):
                relevant_docs.append(doc)
        
        return relevant_docs[:max_documents] if relevant_docs else mock_documents[:max_documents]
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content.
        
        Args:
            query: Search query
            content: Document content
            
        Returns:
            Relevance score between 0 and 1
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the agent.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "agent_type": "retrieval",
            "s3_available": self.s3_client is not None,
            "aws_region": self.aws_region,
            "default_bucket": self.default_bucket
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information.
        
        Returns:
            Agent information dictionary
        """
        return {
            "name": "retrieval-agent",
            "version": "1.0.0",
            "description": "Retrieval agent for RAG evaluation pipeline",
            "capabilities": ["document_retrieval", "s3_integration", "query_processing"],
            "status": "active",
            "config": self.config
        }

# AgentCore entry point
async def main():
    """Main entry point for AgentCore deployment."""
    agent = RetrievalAgent()
    
    # Example usage
    request = RetrievalRequest(
        query="What is machine learning?",
        session_id="test-session",
        max_documents=3
    )
    
    response = await agent.invoke(request)
    print(f"Retrieved {len(response.documents)} documents")
    print(f"Retrieval time: {response.retrieval_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(main())
