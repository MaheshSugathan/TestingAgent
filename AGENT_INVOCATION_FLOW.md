# Agent Invocation Flow

This document explains how agents are invoked in the Bedrock Agent Core deployment, from external requests to individual agent execution.

## 🔄 Invocation Flow Overview

```
External Request
    ↓
Bedrock Agent Core Runtime
    ↓
agentcore_entry.py handler()
    ↓
RAGEvaluationPipeline.run_pipeline()
    ↓
LangGraph Workflow.ainvoke()
    ↓
Individual Agent Nodes (retrieval → dev → evaluator)
    ↓
Agent.execute() methods
    ↓
Response flows back up
```

## 📥 1. External Invocation (How to Call Your Agent)

### Using Agent Core CLI

```bash
agentcore invoke '{"prompt": "What is RAG?"}'
```

### Using AWS SDK (Python)

```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent_runtime(
    agentArn='arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/rag_evaluation_agent-YOUR_RUNTIME_ID',
    inputText='What is RAG?',
    sessionId='session-123'
)

# Stream the response
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'))
```

### Using AWS SDK (CLI)

```bash
aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/rag_evaluation_agent-YOUR_RUNTIME_ID \
  --input-text "What is RAG?" \
  --session-id "session-123" \
  output.json
```

## 📨 2. Request Format

Bedrock Agent Core sends requests to your handler in this format:

```python
event = {
    "prompt": "What is RAG?",  # or "input", "inputText", "text"
    "sessionId": "session-123",  # optional
    # Additional metadata may be included
}
```

Your handler (`agentcore_entry.py`) accepts:
- `prompt` - Primary input text
- `input` - Alternative input field
- `inputText` - Alternative input field  
- `text` - Alternative input field
- `sessionId` - Session identifier (optional)

## 🔀 3. Handler Processing (agentcore_entry.py)

The handler function processes the request:

```python
async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # 1. Extract input text from event
    input_text = event.get('prompt') or event.get('input') or ...
    
    # 2. Get or create session ID
    session_id = event.get('sessionId') or generate_new()
    
    # 3. Invoke the pipeline
    state = await pipeline.run_single_turn_evaluation(
        query=input_text,
        session_id=session_id
    )
    
    # 4. Format and return response
    return {
        "output": response_text,
        "session_id": state.session_id,
        "success": state.is_complete(),
        ...
    }
```

## 🚀 4. Pipeline Invocation (orchestration/pipeline.py)

The pipeline orchestrates the multi-agent workflow:

```python
async def run_single_turn_evaluation(self, query: str, session_id: str):
    # 1. Create initial state
    state = PipelineState(
        session_id=session_id,
        config=self.config,
        metadata={"queries": [query]}
    )
    
    # 2. Invoke LangGraph workflow
    workflow_result = await self.workflow.ainvoke(state)
    
    # 3. Convert result back to PipelineState
    final_state = PipelineState.from_dict(workflow_result)
    
    return final_state
```

## 🔗 5. LangGraph Workflow Execution (orchestration/workflow.py)

LangGraph orchestrates the agent sequence:

```python
workflow = StateGraph(PipelineState)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("dev", dev_node)
workflow.add_node("evaluator", evaluator_node)

# Flow: retrieval → dev → evaluator
workflow.set_entry_point("retrieval")
workflow.add_conditional_edges("retrieval", ...)
workflow.add_conditional_edges("dev", ...)
workflow.add_conditional_edges("evaluator", ...)
```

### Execution Order:

1. **retrieval_node** executes first
2. **dev_node** executes if retrieval succeeds
3. **evaluator_node** executes if dev succeeds
4. **error_handler_node** executes on any failure

## 🤖 6. Individual Agent Invocation

Each node in the workflow invokes a specific agent:

### Retrieval Agent Node

```python
async def retrieval_node(state: PipelineState) -> PipelineState:
    # 1. Initialize agent
    agent = S3RetrievalAgent(
        config=state.config.get("retrieval", {}),
        bucket_name=state.config.get("s3", {}).get("bucket"),
        ...
    )
    
    # 2. Create agent state
    agent_state = AgentState(
        session_id=state.session_id,
        data=state.metadata.get("initial_data", {}),
        metadata=state.metadata
    )
    
    # 3. Execute agent
    result_state = await agent.execute(agent_state)
    
    # 4. Store result in pipeline state
    result = AgentResult(
        agent_name="retrieval",
        success=True,
        data=result_state.data,
        ...
    )
    state.add_agent_result(result)
    
    return state
```

### Dev Agent Node

```python
async def dev_node(state: PipelineState) -> PipelineState:
    # 1. Get documents from retrieval result
    documents = state.get_data("retrieval", "documents")
    
    # 2. Initialize Dev agent
    agent = DevAgent(
        config=state.config.get("agents", {}).get("dev", {}),
        agentcore_base_url=agentcore_config.get("base_url"),
        bill_agent_name=agentcore_config.get("bill", {}).get("agent_name"),
        ...
    )
    
    # 3. Create agent state with documents
    agent_state = AgentState(
        session_id=state.session_id,
        data={
            "documents": documents,
            "queries": state.metadata.get("queries", [])
        },
        ...
    )
    
    # 4. Execute agent
    result_state = await agent.execute(agent_state)
    
    # 5. Store result
    state.add_agent_result(result)
    
    return state
```

### Evaluator Agent Node

```python
async def evaluator_node(state: PipelineState) -> PipelineState:
    # 1. Get responses from dev result
    responses = state.get_data("dev", "generated_responses")
    
    # 2. Initialize evaluator
    agent = RAGEvaluatorAgent(
        config=state.config.get("evaluator", {}),
        ragas_config=state.config.get("evaluation", {}).get("ragas", {}),
        llm_judge_config=state.config.get("evaluation", {}).get("llm_judge", {})
    )
    
    # 3. Execute evaluation
    result_state = await agent.execute(agent_state)
    
    # 4. Store result
    state.add_agent_result(result)
    
    return state
```

## 🔧 7. Agent.execute() Method

Each agent implements the `execute()` method:

```python
class BaseAgent(ABC):
    async def execute(self, state: AgentState) -> AgentState:
        """Execute agent operation."""
        # 1. Agent-specific logic
        # 2. Update state.data with results
        # 3. Update state.metadata
        # 4. Return updated state
        return state
```

### Example: DevAgent.execute()

```python
async def execute(self, state: AgentState) -> AgentState:
    # 1. Get documents and queries
    documents = state.data.get('documents', [])
    queries = state.data.get('queries', [])
    
    # 2. Generate responses using external agent
    for query in queries:
        response = await self._generate_response_with_bill(
            query, documents, state.session_id
        )
        responses.append(response)
    
    # 3. Update state
    state.data['generated_responses'] = responses
    state.data['dev_metadata'] = {...}
    
    return state
```

## 🔄 8. State Flow Through Pipeline

```
Initial State
  session_id: "session-123"
  metadata: {"queries": ["What is RAG?"]}
  config: {...}
    ↓
[retrieval_node]
  retrieval_result: AgentResult(
    agent_name="retrieval",
    data={"documents": [...]}
  )
    ↓
[dev_node]
  dev_result: AgentResult(
    agent_name="dev",
    data={"generated_responses": [...]}
  )
    ↓
[evaluator_node]
  evaluator_result: AgentResult(
    agent_name="evaluator",
    data={"evaluation_results": [...]}
  )
    ↓
Final State (returned to handler)
```

## 📤 9. Response Format

The handler returns this format to Bedrock Agent Core:

```python
{
    "output": "RAG evaluation pipeline completed.",
    "session_id": "session-123",
    "pipeline_id": "pipeline-abc123",
    "success": true,
    "execution_time": 1.24,
    "evaluation_results": [...],  # if available
    "summary": {
        "evaluation_complete": true,
        "errors": [],
        "agent_results": {
            "retrieval": true,
            "dev": true,
            "evaluator": true
        }
    }
}
```

## 🧪 10. Testing Invocation

### Test Locally

```python
# Test handler directly
from agentcore_entry import handler

event = {
    "prompt": "What is RAG?",
    "sessionId": "test-session"
}

result = await handler(event, None)
print(result)
```

### Test via CLI

```bash
# Using agentcore CLI
agentcore invoke '{"prompt": "What is RAG?"}'

# Using AWS CLI
aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn <your-arn> \
  --input-text "What is RAG?"
```

## 🔍 11. Debugging Invocation

### View Logs

```bash
# Runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR_AGENT_LOG_GROUP_SUFFIX-DEFAULT \
  --log-stream-name-prefix "2025/11/03/[runtime-logs]" --follow

# OpenTelemetry logs
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR_AGENT_LOG_GROUP_SUFFIX-DEFAULT \
  --log-stream-names "otel-rt-logs" --follow
```

### Check Agent Status

```bash
agentcore status
```

## 📊 12. Invocation Sequence Diagram

```
Client/User
    |
    | POST request with prompt
    ↓
Bedrock Agent Core Runtime
    |
    | invokes handler()
    ↓
agentcore_entry.py::handler()
    |
    | extracts input_text
    | creates session_id
    ↓
RAGEvaluationPipeline::run_single_turn_evaluation()
    |
    | creates PipelineState
    | calls workflow.ainvoke(state)
    ↓
LangGraph Workflow
    |
    | executes nodes in sequence
    ↓
┌─────────────────────┐
│ retrieval_node()    │
│  - Creates agent    │
│  - agent.execute()  │
│  - Updates state    │
└──────────┬──────────┘
           |
           ↓ (if success)
┌─────────────────────┐
│ dev_node()          │
│  - Gets documents   │
│  - Creates agent    │
│  - agent.execute()  │
│  - Updates state    │
└──────────┬──────────┘
           |
           ↓ (if success)
┌─────────────────────┐
│ evaluator_node()    │
│  - Gets responses   │
│  - Creates agent    │
│  - agent.execute()  │
│  - Updates state    │
└──────────┬──────────┘
           |
           ↓
    Final State
           |
           ↓
    handler() returns response
           |
           ↓
Bedrock Agent Core Runtime
           |
           ↓
    Client receives response
```

## 🔑 Key Points

1. **Asynchronous**: All invocations are async (`async/await`)
2. **State-based**: PipelineState flows through the workflow
3. **Error handling**: Each node can fail gracefully
4. **Conditional flow**: Success/failure determines next node
5. **Reusable pipeline**: Pipeline is initialized once and reused
6. **Session management**: Session IDs track conversations

## 📝 Example: Complete Invocation

```python
# 1. External client calls
response = client.invoke_agent_runtime(
    agentArn='arn:aws:bedrock-agentcore:...',
    inputText='What is RAG?',
    sessionId='session-123'
)

# 2. Bedrock Agent Core calls
handler({
    "prompt": "What is RAG?",
    "sessionId": "session-123"
}, context)

# 3. Handler calls pipeline
state = await pipeline.run_single_turn_evaluation(
    query="What is RAG?",
    session_id="session-123"
)

# 4. Pipeline calls workflow
final_state = await workflow.ainvoke(state)

# 5. Workflow calls nodes in sequence:
#    - retrieval_node() → agent.execute()
#    - dev_node() → agent.execute()
#    - evaluator_node() → agent.execute()

# 6. Response flows back up the chain
```

