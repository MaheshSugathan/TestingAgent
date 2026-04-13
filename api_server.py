"""FastAPI server for local RAGLens pipeline."""

import asyncio
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from config.config_manager import ConfigManager
from orchestration.pipeline import RAGEvaluationPipeline
from observability import setup_logger, MetricsCollector


# Request models
class EvaluationRequest(BaseModel):
    """Request model for evaluation."""
    queries: List[str] = Field(..., description="List of queries to evaluate")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")
    evaluation_type: Optional[str] = Field("single_turn", description="Type of evaluation: single_turn or multi_turn")
    human_in_loop: Optional[bool] = Field(None, description="Enable human-in-the-loop (pause for review when scores below threshold)")


class ResumeRequest(BaseModel):
    """Request model for resuming after human review."""
    session_id: str = Field(..., description="Session ID from the interrupted evaluation")
    human_decision: Dict[str, Any] = Field(
        ...,
        description="Human decision, e.g. {\"action\": \"approve\"} or {\"action\": \"override\", \"score\": 0.85}"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str


# Global variables for pipeline
pipeline: Optional[RAGEvaluationPipeline] = None
logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup/shutdown."""
    global pipeline, logger

    # Startup
    logger = setup_logger("RAGEvaluationAPI")
    logger.info("Starting RAGLens API Server...")

    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # Initialize metrics collector
        metrics_collector = MetricsCollector(
            namespace=config.get("aws", {}).get("cloudwatch", {}).get("namespace", "RAGEvaluation")
        )

        # Initialize pipeline
        pipeline = RAGEvaluationPipeline(
            config=config,
            logger=logger,
            metrics_collector=metrics_collector
        )

        logger.info("RAGLens pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down RAGLens API Server...")


# Create FastAPI app
app = FastAPI(
    title="RAGLens API",
    description="API for running the RAGLens pipeline locally",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return HealthResponse(status="ok", message="RAGLens API is running")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    return HealthResponse(
        status="healthy",
        message="Pipeline is ready to process requests"
    )


@app.post("/evaluate")
async def evaluate(request: EvaluationRequest):
    """Run RAG evaluation pipeline.

    Returns:
        Evaluation results, or awaiting_human_review when HITL is enabled and scores are below threshold
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        if request.evaluation_type == "single_turn" and len(request.queries) == 1:
            run_result = await pipeline.run_single_turn_evaluation(
                query=request.queries[0],
                session_id=request.session_id,
                human_in_loop=request.human_in_loop
            )
        else:
            run_result = await pipeline.run_multi_turn_evaluation(
                queries=request.queries,
                session_id=request.session_id,
                human_in_loop=request.human_in_loop
            )

        state = run_result["state"]
        interrupt_payloads = run_result.get("interrupt")

        if interrupt_payloads:
            payload = interrupt_payloads[0] if interrupt_payloads else {}
            return {
                "success": False,
                "status": "awaiting_human_review",
                "session_id": state.session_id,
                "interrupt": payload,
                "message": payload.get("message", "Evaluation requires human review."),
                "resume_instruction": "POST to /evaluate/resume with session_id and human_decision"
            }

        summary = pipeline.get_pipeline_summary(state)
        return {
            "success": True,
            "session_id": state.session_id,
            "summary": summary,
            "state": {
                "session_id": state.session_id,
                "pipeline_id": state.pipeline_id,
                "is_complete": state.is_complete(),
                "execution_time": state.get_total_execution_time(),
                "errors": state.errors
            }
        }
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/evaluate/resume")
async def evaluate_resume(request: ResumeRequest):
    """Resume evaluation after human-in-the-loop review."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    try:
        run_result = await pipeline.resume_pipeline(
            session_id=request.session_id,
            human_decision=request.human_decision
        )
        state = run_result["state"]
        interrupt_payloads = run_result.get("interrupt")

        if interrupt_payloads:
            payload = interrupt_payloads[0] if interrupt_payloads else {}
            return {
                "success": False,
                "status": "awaiting_human_review",
                "session_id": state.session_id,
                "interrupt": payload,
                "message": payload.get("message", "Still awaiting human review.")
            }

        summary = pipeline.get_pipeline_summary(state)
        return {
            "success": True,
            "session_id": state.session_id,
            "summary": summary,
            "state": {
                "session_id": state.session_id,
                "pipeline_id": state.pipeline_id,
                "is_complete": state.is_complete(),
                "execution_time": state.get_total_execution_time(),
                "errors": state.errors
            }
        }
    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")


@app.post("/evaluate/async")
async def evaluate_async(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """Run RAG evaluation pipeline asynchronously.

    Args:
        request: Evaluation request with queries
        background_tasks: FastAPI background tasks

    Returns:
        Task ID for tracking
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    # Generate task ID
    import time
    task_id = f"task-{int(time.time())}-{request.session_id or 'default'}"

    async def run_evaluation():
        """Background task to run evaluation."""
        try:
            if request.evaluation_type == "single_turn" and len(request.queries) == 1:
                run_result = await pipeline.run_single_turn_evaluation(
                    query=request.queries[0],
                    session_id=request.session_id,
                    human_in_loop=request.human_in_loop
                )
            else:
                run_result = await pipeline.run_multi_turn_evaluation(
                    queries=request.queries,
                    session_id=request.session_id,
                    human_in_loop=request.human_in_loop
                )
            logger.info(f"Background evaluation completed: {task_id}")
        except Exception as e:
            logger.error(f"Background evaluation failed {task_id}: {e}", exc_info=True)

    background_tasks.add_task(run_evaluation)

    return {
        "success": True,
        "task_id": task_id,
        "message": "Evaluation started in background",
        "session_id": request.session_id
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

