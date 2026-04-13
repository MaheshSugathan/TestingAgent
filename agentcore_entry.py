"""Entry point for Bedrock Agent Core Runtime."""

import asyncio
import json
import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn

from config.config_manager import ConfigManager
from orchestration.pipeline import RAGEvaluationPipeline
from observability import setup_logger, MetricsCollector


# Initialize pipeline (globally to reuse)
pipeline = None
logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize pipeline on startup."""
    global pipeline, logger
    
    # Startup: Initialize pipeline
    logger = setup_logger("AgentCoreEntry")
    logger.info("Initializing RAGLens pipeline for Agent Core...")
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        metrics_collector = MetricsCollector(
            namespace=config.get("aws", {}).get("cloudwatch", {}).get("namespace", "RAGEvaluation")
        )
        
        pipeline = RAGEvaluationPipeline(
            config=config,
            logger=logger,
            metrics_collector=metrics_collector
        )
        
        logger.info("Pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Core entry point...")


# Create FastAPI app for Agent Core HTTP interface
app = FastAPI(title="Bedrock Agent Core Entry Point", lifespan=lifespan)


async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handler function for Agent Core Runtime.
    
    Args:
        event: Event from Agent Core (contains 'prompt' or 'input')
        context: Runtime context
        
    Returns:
        Response dictionary with 'output' or 'response'
    """
    global pipeline, logger
    
    # Initialize pipeline if not already done
    if pipeline is None:
        logger = setup_logger("AgentCoreEntry")
        logger.info("Initializing RAGLens pipeline...")
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Initialize metrics collector
            metrics_collector = MetricsCollector(
                namespace=config.get("aws", {}).get("cloudwatch", {}).get("namespace", "RAGEvaluation")
            )
            
            pipeline = RAGEvaluationPipeline(
                config=config,
                logger=logger,
                metrics_collector=metrics_collector
            )
            
            logger.info("Pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}", exc_info=True)
            return {
                "error": f"Pipeline initialization failed: {str(e)}",
                "output": f"Error: Failed to initialize pipeline. {str(e)}"
            }
    
    try:
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                event = {"prompt": event}
        elif not isinstance(event, dict):
            event = {}

        session_id = event.get("sessionId") or event.get("session_id") or f"agentcore-{os.getpid()}-{asyncio.get_event_loop().time()}"
        human_in_loop = event.get("human_in_loop", event.get("humanInLoop"))

        # Resume flow: human provided decision after interrupt
        if event.get("resume") is not None or event.get("human_decision") is not None:
            human_decision = event.get("resume") or event.get("human_decision")
            resume_session_id = event.get("sessionId") or event.get("session_id")
            if not resume_session_id:
                return {"error": "session_id required for resume", "output": "Error: session_id required to resume."}
            logger.info(f"Resuming pipeline for session {resume_session_id}")
            run_result = await pipeline.resume_pipeline(session_id=resume_session_id, human_decision=human_decision)
        else:
            # Normal evaluation flow
            input_text = event.get("prompt") or event.get("input") or event.get("inputText") or event.get("text")
            if not input_text:
                return {
                    "error": "No input provided. Expected 'prompt', 'input', 'inputText', or 'text'.",
                    "output": "Error: No input text provided."
                }
            logger.info(f"Processing request: {input_text[:100]}...")

            run_result = await pipeline.run_single_turn_evaluation(
                query=input_text,
                session_id=session_id,
                human_in_loop=human_in_loop
            )

        state = run_result["state"]
        interrupt_payloads = run_result.get("interrupt")

        # Awaiting human review
        if interrupt_payloads:
            payload = interrupt_payloads[0] if interrupt_payloads else {}
            return {
                "status": "awaiting_human_review",
                "output": payload.get("message", "Evaluation requires human review."),
                "session_id": state.session_id,
                "interrupt": payload,
                "resume_instruction": "Call with resume=true, session_id, and human_decision (e.g. {\"action\": \"approve\"} or {\"action\": \"override\", \"score\": 0.85})"
            }

        # Normal completion
        summary = pipeline.get_pipeline_summary(state)
        response_text = "RAG evaluation pipeline completed."
        if state.dev_result and state.dev_result.success:
            responses = state.get_data("dev", "generated_responses")
            if responses:
                response_text = responses[0].get("response", response_text)

        result = {
            "output": response_text,
            "session_id": state.session_id,
            "pipeline_id": state.pipeline_id,
            "success": state.is_complete(),
            "execution_time": state.get_total_execution_time()
        }
        if state.evaluator_result and state.evaluator_result.success:
            evaluation_results = state.get_data("evaluator", "evaluation_results")
            if evaluation_results:
                result["evaluation_results"] = evaluation_results[:3]
        result["summary"] = {
            "evaluation_complete": state.is_complete(),
            "errors": state.errors if state.errors else [],
            "agent_results": {
                "retrieval": state.retrieval_result.success if state.retrieval_result else False,
                "dev": state.dev_result.success if state.dev_result else False,
                "evaluator": state.evaluator_result.success if state.evaluator_result else False
            }
        }
        logger.info(f"Request completed successfully: {state.session_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            "error": str(e),
            "output": f"Error processing request: {str(e)}"
        }


# For synchronous invocation (if needed)
def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous handler wrapper."""
    global logger
    try:
        return asyncio.run(handler(event, context))
    except Exception as e:
        if logger is None:
            logger = setup_logger("AgentCoreEntry")
        logger.error(f"Handler error: {e}", exc_info=True)
        return {
            "error": str(e),
            "output": f"Handler error: {str(e)}"
        }


# HTTP endpoints for Agent Core
@app.get("/")
async def root():
    """Root endpoint - also used for health checks."""
    return {"status": "ok", "service": "rag_evaluation_agent"}

@app.get("/ping")
async def ping():
    """Health check endpoint for Agent Core."""
    return {"status": "ok"}


@app.post("/invocations")
async def invocations(request: Request):
    """Invocation endpoint for Agent Core."""
    global logger
    
    # Ensure logger is initialized
    if logger is None:
        logger = setup_logger("AgentCoreEntry")
    
    try:
        # Parse request body
        body = await request.json()
        
        # Handle different request formats
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {"prompt": body}
        
        # Call handler
        result = await handler(body, None)
        return JSONResponse(content=result)
    except Exception as e:
        if logger:
            logger.error(f"Invocation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# For direct testing or when run as module
if __name__ == "__main__":
    # Run as HTTP server for Agent Core
    # Pipeline will be initialized via lifespan event
    # Agent Core expects an HTTP server on port 9000
    uvicorn.run(app, host="0.0.0.0", port=9000)

