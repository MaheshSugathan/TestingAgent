#!/usr/bin/env python3
"""
Simple Bill Agent for testing RAG evaluation pipeline
This is a standalone implementation that doesn't require Docker
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Request/Response Models
class AgentRequest(BaseModel):
    query: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    tokens_used: Optional[Dict[str, int]] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    agent_name: str
    version: str

# Initialize FastAPI app
app = FastAPI(
    title="Bill Agent",
    description="Bill agent for RAG evaluation pipeline",
    version="1.0.0"
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        agent_name="bill",
        version="1.0.0"
    )

@app.get("/info")
async def get_agent_info():
    """Get agent information."""
    return {
        "name": "bill",
        "version": "1.0.0",
        "description": "Bill agent for RAG evaluation pipeline",
        "capabilities": ["text_generation", "rag", "conversation"],
        "status": "active"
    }

@app.post("/invoke", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """Invoke the Bill agent with a query."""
    start_time = time.time()
    
    try:
        # Mock response generation
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Generate a mock response based on the query
        mock_response = generate_mock_response(request.query, request.context)
        
        execution_time = time.time() - start_time
        
        return AgentResponse(
            answer=mock_response["answer"],
            confidence=mock_response["confidence"],
            metadata={
                "model": "mock-bill-agent",
                "processing_time": execution_time,
                "context_length": len(request.context) if request.context else 0,
                "query_length": len(request.query),
                "session_id": request.session_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            execution_time=execution_time,
            tokens_used={
                "input": len(request.query.split()) + (len(request.context.split()) if request.context else 0),
                "output": len(mock_response["answer"].split())
            }
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        return AgentResponse(
            answer="",
            confidence=0.0,
            metadata={
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            },
            execution_time=execution_time,
            error=str(e)
        )

def generate_mock_response(query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Generate a mock response for demonstration purposes."""
    
    # Simple mock responses based on query keywords
    query_lower = query.lower()
    
    if "summary" in query_lower or "summarize" in query_lower:
        answer = "Based on the provided context, here's a comprehensive summary of the key points and main findings."
        confidence = 0.85
    elif "explain" in query_lower:
        answer = "I'll explain this concept in detail, covering the main aspects and providing relevant examples."
        confidence = 0.90
    elif "compare" in query_lower:
        answer = "Let me compare these concepts, highlighting the similarities and differences between them."
        confidence = 0.80
    elif "what is" in query_lower:
        answer = "This refers to a specific concept or entity. Let me provide a detailed explanation of its characteristics and significance."
        confidence = 0.88
    elif "how" in query_lower:
        answer = "Here's a step-by-step explanation of how this process works, including the key steps and considerations."
        confidence = 0.82
    else:
        answer = f"I understand you're asking about: '{query}'. Based on the context provided, here's my response addressing your question with relevant details and insights."
        confidence = 0.75
    
    # Add context reference if provided
    if context:
        answer += f"\n\nNote: This response is based on the provided context which contains {len(context)} characters of relevant information."
    
    return {
        "answer": answer,
        "confidence": confidence
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Bill Agent is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "invoke": "/invoke"
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Bill Agent on http://localhost:8001")
    print("📋 Available endpoints:")
    print("  • Health: http://localhost:8001/health")
    print("  • Info: http://localhost:8001/info")
    print("  • Invoke: http://localhost:8001/invoke")
    print("  • Root: http://localhost:8001/")
    print("\n🧪 Test with:")
    print('curl -X POST "http://localhost:8001/invoke" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"query": "What is machine learning?"}\'')
    
    uvicorn.run(
        "test_bill_agent:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
