"""FastAPI backend for RAG Evaluation Chat UI - proxies to Agent Core or API Server."""

import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any, Dict

app = FastAPI(title="RAG Evaluation Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent HTTP URL (agentcore_entry /invocations or api_server)
AGENT_HTTP_URL = os.getenv("AGENT_HTTP_URL", "")
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://localhost:8080")


class InvokeRequest(BaseModel):
    """Request for chat evaluation."""
    agentArn: Optional[str] = None
    prompt: Optional[str] = None
    sessionId: Optional[str] = None
    humanInLoop: Optional[bool] = None
    resume: Optional[Any] = None
    humanDecision: Optional[Dict[str, Any]] = None


@app.get("/")
def root():
    return {"status": "ok", "service": "RAG Evaluation Chat API"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.post("/api/invoke")
async def invoke_agent(request: InvokeRequest):
    """
    Invoke evaluation - supports normal eval and resume for human-in-the-loop.
    Proxies to AGENT_HTTP_URL (agentcore) or API_SERVER_URL (api_server).
    """
    body = request.model_dump(exclude_none=True)
    session_id = body.get("sessionId") or body.get("session_id")

    # Use api_server (/evaluate, /evaluate/resume) if API_SERVER_URL is preferred
    if API_SERVER_URL and not AGENT_HTTP_URL:
        return await _proxy_to_api_server(body, session_id)

    # Use agent HTTP (agentcore_entry /invocations)
    if AGENT_HTTP_URL:
        return await _proxy_to_agent_http(body, session_id)

    raise HTTPException(
        status_code=500,
        detail="Configure AGENT_HTTP_URL or API_SERVER_URL for agent invocation"
    )


async def _proxy_to_agent_http(body: dict, session_id: Optional[str]) -> dict:
    """Proxy to agentcore_entry HTTP endpoint."""
    url = AGENT_HTTP_URL.rstrip("/")
    if not url.endswith("/invocations"):
        url = f"{url}/invocations"
    payload = {
        "prompt": body.get("prompt"),
        "sessionId": session_id,
        "session_id": session_id,
        "human_in_loop": body.get("humanInLoop"),
        "humanInLoop": body.get("humanInLoop"),
    }
    if body.get("resume") is not None:
        payload["resume"] = body["resume"]
    if body.get("humanDecision") is not None:
        payload["human_decision"] = body["humanDecision"]
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _proxy_to_api_server(body: dict, session_id: Optional[str]) -> dict:
    """Proxy to api_server /evaluate and /evaluate/resume."""
    base = API_SERVER_URL.rstrip("/")
    if body.get("resume") is not None or body.get("humanDecision") is not None:
        url = f"{base}/evaluate/resume"
        payload = {
            "session_id": session_id,
            "human_decision": body.get("resume") or body.get("humanDecision", {}),
        }
    else:
        url = f"{base}/evaluate"
        payload = {
            "queries": [body.get("prompt", "")],
            "session_id": session_id,
            "human_in_loop": body.get("humanInLoop"),
        }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") == "awaiting_human_review":
        return {
            "status": "awaiting_human_review",
            "session_id": data.get("session_id"),
            "interrupt": data.get("interrupt"),
            "output": data.get("message"),
            "resume_instruction": data.get("resume_instruction"),
        }
    if data.get("success"):
        return {
            "output": json.dumps(data.get("summary", data), indent=2),
            "session_id": data.get("session_id"),
            "evaluation_results": data.get("state", {}).get("evaluation_results"),
            "summary": data.get("summary"),
        }
    return data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
