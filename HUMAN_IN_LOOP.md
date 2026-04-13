# Human-in-the-Loop (HITL) Guide

The Testing Agent supports **two modes** of operation: fully automated and human-in-the-loop. You can run with or without HITL using configuration or per-request parameters.

## Modes

| Mode | Description |
|------|-------------|
| **Without HITL** | Pipeline runs end-to-end. No pauses. Returns final evaluation result. |
| **With HITL** | When evaluation scores fall below threshold, pipeline pauses for human review. Human approves, rejects, or overrides before finalizing. |

## Configuration

### Config file (`config/config.yaml`)

```yaml
human_in_loop:
  enabled: false   # Set true for default HITL mode
  review_threshold: 0.8   # Scores below this trigger review (default: 0.8)
```

### Per-request override

You can override the config per evaluation request.

## Usage

### 1. API (FastAPI / api_server.py)

**Evaluation without HITL (default):**
```bash
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{"queries": ["What is RAG?"]}'
```

**Evaluation with HITL:**
```bash
curl -X POST http://localhost:8080/evaluate \
  -H "Content-Type: application/json" \
  -d '{"queries": ["What is RAG?"], "human_in_loop": true}'
```

**When interrupted (scores below threshold), response:**
```json
{
  "success": false,
  "status": "awaiting_human_review",
  "session_id": "rag-eval-xxx",
  "interrupt": {
    "action": "human_review",
    "session_id": "rag-eval-xxx",
    "overall_score": 0.65,
    "threshold": 0.8,
    "message": "Scores below threshold (0.65 < 0.8). Approve, reject, or override?"
  },
  "resume_instruction": "POST to /evaluate/resume with session_id and human_decision"
}
```

**Resume after human review:**
```bash
curl -X POST http://localhost:8080/evaluate/resume \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "rag-eval-xxx",
    "human_decision": {"action": "approve", "comment": "Approved after manual review"}
  }'
```

**Human decision options:**
- `{"action": "approve"}` - Approve despite low score
- `{"action": "reject"}` - Reject the evaluation
- `{"action": "override", "score": 0.85}` - Override with a new score

### 2. Agent Core entry (agentcore_entry.py)

**Request format:**
```json
{
  "prompt": "What is RAG?",
  "sessionId": "optional-session-id",
  "human_in_loop": true
}
```

**Resume format:**
```json
{
  "resume": {"action": "approve"},
  "sessionId": "rag-eval-xxx"
}
```

Or:
```json
{
  "human_decision": {"action": "override", "score": 0.9},
  "session_id": "rag-eval-xxx"
}
```

### 3. Python pipeline

```python
from orchestration.pipeline import RAGEvaluationPipeline

# Without HITL
result = await pipeline.run_single_turn_evaluation(
    query="What is RAG?",
    human_in_loop=False
)

# With HITL
result = await pipeline.run_single_turn_evaluation(
    query="What is RAG?",
    session_id="my-session",
    human_in_loop=True
)

if "interrupt" in result:
    # Show review UI, get human decision
    human_decision = {"action": "approve"}
    result = await pipeline.resume_pipeline(
        session_id=result["state"].session_id,
        human_decision=human_decision
    )

state = result["state"]
```

## Flow

```
Retrieval → Dev → Evaluator → Human Review (if HITL & score < threshold)
                                    ↓
                            [INTERRUPT - wait for human]
                                    ↓
                            Resume with human_decision
                                    ↓
                                 END
```

When HITL is disabled or scores are above threshold, Human Review passes through without pausing.

## Checkpointer

HITL uses LangGraph's checkpointing to save state when paused. The default is `MemorySaver` (in-memory). For production with distributed deployments (e.g., multiple Lambda/container instances), use a persistent checkpointer (e.g., SQLite, Redis, or DynamoDB) so resume works across requests.

## Chat app integration

For a chat UI:

1. Send evaluation request with `human_in_loop: true`
2. If response has `status: "awaiting_human_review"`, show evaluation summary and Approve / Reject / Override buttons
3. On user action, call `/evaluate/resume` with `session_id` and `human_decision`
4. Display final result
