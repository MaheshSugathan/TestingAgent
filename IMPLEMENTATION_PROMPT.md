# Complete Implementation Prompt: Lambda + Human-in-the-Loop for RAG/Agent Evaluation Projects

**Copy the prompt below and paste it into VS Code / Cursor to implement Lambda and Human-in-the-Loop for a similar project.**

---

## PROMPT START

### Objective
Implement a secure **AWS Lambda** backend with **Cognito authentication** and **Human-in-the-Loop (HITL)** for an agent/AI evaluation pipeline. The system should support both fully automated runs and runs that pause for human review when evaluation scores fall below a configurable threshold.

### Architecture Requirements

1. **Lambda + API Gateway + Cognito**
   - API Gateway REST API with Cognito User Pool authorizer
   - Lambda function invoked by API Gateway
   - All API routes require valid JWT (id_token) from Cognito

2. **Human-in-the-Loop Flow**
   - Pipeline runs: Retrieval → Generation → Evaluation → Human Review (conditional)
   - When HITL is enabled AND evaluation score < threshold: **pause** and return `status: "awaiting_human_review"`
   - Human can: **Approve**, **Reject**, or **Override** (with new score)
   - **Resume** endpoint: accepts `session_id` + `human_decision`, continues pipeline

3. **Two Modes**
   - **Without HITL**: Pipeline runs end-to-end, no pause
   - **With HITL**: Pipeline pauses when scores < threshold, waits for human decision, then resumes

### Technical Implementation Requirements

#### 1. Pipeline / Workflow (LangGraph or similar)

- Use **LangGraph** with a **checkpointer** (e.g., `MemorySaver` for dev, persistent store for prod)
- Add a **human_review node** after the evaluator
- In the node:
  - If `human_in_loop` is disabled → return state (pass-through)
  - If score >= threshold → return state (pass-through)
  - If score < threshold → call `interrupt(payload)` where payload is JSON-serializable
- Use `thread_id` (e.g., session_id) in config for resume: `config={"configurable": {"thread_id": session_id}}`
- Resume with: `graph.ainvoke(Command(resume=human_decision), config=config)`

#### 2. LangGraph Interrupt Pattern

```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

# In human_review_node:
if hitl_enabled and overall_score < threshold:
    human_decision = interrupt({
        "action": "human_review",
        "session_id": state.session_id,
        "overall_score": overall_score,
        "threshold": threshold,
        "message": "Scores below threshold. Approve, reject, or override?"
    })
    # Apply human_decision to state
return state
```

#### 3. Lambda Handler

- Parse `event["body"]` (JSON string from API Gateway)
- Support both **evaluate** and **resume** in the same handler:
  - If `resume` or `human_decision` present → call pipeline `resume_pipeline(session_id, human_decision)`
  - Else → call pipeline `run_pipeline(..., human_in_loop=body.get("humanInLoop"))`
- If result has `interrupt` → return `status: "awaiting_human_review"`, `session_id`, `interrupt` payload
- Else → return normal result
- Use **AGENT_HTTP_URL** env var to invoke agent via HTTP (POST to agent endpoint)
- Or use **AGENT_ARN** with boto3 for Bedrock if applicable
- Include CORS headers in all responses: `Access-Control-Allow-Origin`, `Access-Control-Allow-Headers`, `Access-Control-Allow-Methods`

#### 4. API Contract

**Evaluate request:**
```json
{
  "prompt": "Evaluate: What is X?",
  "sessionId": "optional-session-id",
  "humanInLoop": true
}
```

**Resume request:**
```json
{
  "resume": { "action": "approve" },
  "sessionId": "session-from-interrupt"
}
```

**Human decision options:**
- `{"action": "approve"}`
- `{"action": "reject"}`
- `{"action": "override", "score": 0.85}`

**Response when interrupted:**
```json
{
  "status": "awaiting_human_review",
  "session_id": "rag-eval-xxx",
  "interrupt": { "message": "...", "overall_score": 0.65, "threshold": 0.8 },
  "resume_instruction": "Call with resume and sessionId"
}
```

#### 5. Terraform / IaC

- **Cognito User Pool** + User Pool Client
- **Lambda** with IAM role, env vars: `AGENT_HTTP_URL`, `AGENT_ARN`, `AWS_REGION`
- **API Gateway** REST API with Cognito authorizer on `/invoke`
- **OPTIONS** method for CORS preflight
- Lambda integration (AWS_PROXY)

#### 6. Frontend / Chat UI (if applicable)

- Toggle: "Human-in-the-loop" on/off
- When response has `status: "awaiting_human_review"`: show Approve / Reject / Override buttons
- On button click: call API with `resume` and `sessionId`
- Settings: API URL, Cognito Hosted UI URL, Bearer token (id_token)
- Store token and API URL in localStorage

### Key Files to Create/Modify

| File | Purpose |
|------|---------|
| `orchestration/workflow.py` | Add `human_review_node`, `interrupt()`, checkpointer |
| `orchestration/pipeline.py` | `run_pipeline()` with `human_in_loop`, `resume_pipeline()`, thread_id config |
| `orchestration/state.py` | Add `human_review` to metadata if needed |
| `lambda/agentcore_invoker.py` | Parse evaluate vs resume, invoke via HTTP or boto3, return interrupt response |
| `config/config.yaml` | `human_in_loop.enabled`, `human_in_loop.review_threshold` |
| `terraform/cognito_lambda.tf` | Cognito, Lambda, API Gateway, CORS |
| `api_server.py` or entry | Handle `/evaluate`, `/evaluate/resume`, pass `human_in_loop` |
| Frontend `App.jsx` | Chat UI with HITL toggle, review buttons, resume call |

### Checklist

- [ ] Pipeline has checkpointer (MemorySaver minimum)
- [ ] `human_review_node` conditionally calls `interrupt()`
- [ ] Pipeline returns `{"state": ..., "interrupt": ...}` structure
- [ ] `resume_pipeline(session_id, human_decision)` exists
- [ ] Lambda handles both evaluate and resume
- [ ] Lambda supports AGENT_HTTP_URL for HTTP invoke
- [ ] API Gateway has Cognito authorizer
- [ ] CORS headers on all Lambda responses
- [ ] Config supports `human_in_loop.enabled` and per-request override
- [ ] Frontend shows review UI when `awaiting_human_review`

### Reference Implementation

For a complete working example, refer to this project's:
- `orchestration/workflow.py` (human_review_node)
- `orchestration/pipeline.py` (run_pipeline, resume_pipeline)
- `lambda/agentcore_invoker.py` (evaluate + resume, HTTP invoke)
- `agentcore_entry.py` (handler with interrupt/resume)
- `api_server.py` (POST /evaluate, POST /evaluate/resume)
- `web_ui/src/App.jsx` (chat UI with HITL)
- `terraform/chat_app.tf`, `cognito_lambda.tf`
- `HUMAN_IN_LOOP.md`, `CHAT_APP_DEPLOYMENT.md`

---

## PROMPT END

---

## How to Use

1. Open VS Code / Cursor in your project
2. Copy everything between **PROMPT START** and **PROMPT END** above
3. Paste into the AI chat
4. Add any project-specific details (e.g., "My pipeline uses X instead of Y")
5. Ask the AI to implement step by step

---

## Quick Copy (Compact Version)

For a shorter prompt, use this:

```
Implement Lambda + Human-in-the-Loop for my agent evaluation pipeline.

Requirements:
1. Lambda + API Gateway + Cognito auth
2. LangGraph pipeline with human_review node using interrupt() when score < threshold
3. Two modes: with HITL (pause for review) and without (fully automated)
4. Resume endpoint: session_id + human_decision (approve/reject/override)
5. Lambda: parse body for evaluate vs resume; return status "awaiting_human_review" when interrupted
6. Use AGENT_HTTP_URL or AGENT_ARN; CORS headers on all responses
7. Config: human_in_loop.enabled, review_threshold
8. Chat UI: HITL toggle, Approve/Reject/Override buttons when interrupted

LangGraph: use interrupt() from langgraph.types, MemorySaver checkpointer, thread_id in config, Command(resume=...) for resume.
```
