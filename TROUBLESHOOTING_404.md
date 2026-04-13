# Troubleshooting 404 Errors in Bedrock Agent Core

This guide helps resolve 404 errors when invoking Bedrock Agent Core agents, based on our working setup.

## 🔍 Common Causes of 404 Errors

### 1. Wrong Agent ARN Format

**Error**: `ResourceNotFoundException` or 404

**Solution**: Verify the Agent ARN format

```bash
# Get the correct ARN
agentcore status

# Should be in format:
# arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/AGENT-NAME-ID
```

**Correct ARN format**:
```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/rag_evaluation_agent-YOUR_RUNTIME_ID
```

**Wrong ARN formats** (will cause 404):
- `arn:aws:bedrock:us-east-1:123456789012:agent/...` ❌ (Bedrock Agents, not Agent Core)
- `arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/...` ❌ (missing `/runtime/`)

### 2. Using Wrong API Client

**Error**: `UnknownOperationException` or 404

**Problem**: Using `bedrock-agent` API instead of `bedrock-agent-runtime`

**Solution**: Use the correct API client

```python
# ❌ WRONG - This is for Bedrock Agents (not Agent Core)
client = boto3.client('bedrock-agent', region_name='us-east-1')
response = client.invoke_agent(...)  # This won't work for Agent Core

# ✅ CORRECT - Use bedrock-agent-runtime for Agent Core
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent_runtime(
    agentArn='arn:aws:bedrock-agentcore:...',
    inputText='What is RAG?'
)
```

**CLI**:
```bash
# ❌ WRONG
aws bedrock-agent invoke-agent ...

# ✅ CORRECT
aws bedrock-agent-runtime invoke-agent-runtime ...
```

### 3. Handler Function Not Exported

**Error**: Container starts but returns 404

**Problem**: The handler function is not accessible to Agent Core

**Solution**: Ensure handler is at module level

**Our working setup** (`agentcore_entry.py`):

```python
# ✅ Handler function at module level (not inside a class)
async def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handler function for Agent Core Runtime."""
    # ... implementation
    return result

# ✅ Also provide synchronous wrapper
def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous handler wrapper."""
    return asyncio.run(handler(event, context))
```

**Dockerfile CMD** (how we configured it):

```dockerfile
# ✅ Using module path
CMD ["opentelemetry-instrument", "python", "-m", "agentcore_entry"]
```

**Key Points**:
- Handler must be named `handler` (async) or `handle` (sync)
- Must be at module level (not in a class)
- Module must be importable

### 4. Wrong Entry Point Configuration

**Error**: Agent deployed but invocation fails with 404

**Solution**: Check entry point in Agent Core configuration

```bash
# Check your configuration
cat .bedrock_agentcore.yaml

# Verify entrypoint points to correct file
# Should be: agentcore_entry.py (or your handler file)
```

**Our configuration**:
```bash
agentcore configure -e agentcore_entry.py
```

### 5. Container Not Running

**Error**: Runtime can't start the container

**Solution**: Check agent status and logs

```bash
# Check agent status
agentcore status

# Check if container is running
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR-AGENT-ID-DEFAULT \
  --log-stream-name-prefix "2025/11/03/[runtime-logs]" \
  --since 10m

# Look for errors like:
# - "Failed to start container"
# - "Health check failed"
# - "Import error"
```

### 6. Wrong Region

**Error**: Resource not found in region

**Solution**: Ensure region matches

```python
# Check your agent's region
agentcore status  # Shows region

# Use same region in API calls
client = boto3.client(
    'bedrock-agent-runtime', 
    region_name='us-east-1'  # Must match agent region
)
```

### 7. Missing IAM Permissions

**Error**: Access denied or 404 (due to permissions)

**Solution**: Check IAM permissions

**Required permissions**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agent-runtime:InvokeAgentRuntime"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:*:*:runtime/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetRuntime",
                "bedrock-agentcore:ListRuntimes"
            ],
            "Resource": "*"
        }
    ]
}
```

## ✅ Working Invocation Example

Based on our working setup:

### Python SDK

```python
import boto3

# Get agent ARN from: agentcore status
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/rag_evaluation_agent-YOUR_RUNTIME_ID"

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

try:
    response = client.invoke_agent_runtime(
        agentArn=agent_arn,
        inputText="What is RAG?",
        sessionId="session-123"
    )
    
    # Stream response
    for event in response.get('completion', []):
        if 'chunk' in event:
            if 'bytes' in event['chunk']:
                print(event['chunk']['bytes'].decode('utf-8'), end='')
            elif 'text' in event['chunk']:
                print(event['chunk']['text'], end='')
                
except client.exceptions.ResourceNotFoundException as e:
    print(f"404 Error: Agent not found. Check ARN: {agent_arn}")
except Exception as e:
    print(f"Error: {e}")
```

### AWS CLI

```bash
# Get agent ARN first
AGENT_ARN=$(agentcore status | grep "Agent ARN" | awk '{print $NF}')

# Invoke with correct API
aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn "${AGENT_ARN}" \
  --input-text "What is RAG?" \
  --session-id "session-$(date +%s)" \
  --region us-east-1 \
  output.json

# Check response
cat output.json
```

### Agent Core CLI

```bash
# This automatically uses correct ARN and API
agentcore invoke '{"prompt": "What is RAG?"}'
```

## 🔧 Diagnostic Steps

### Step 1: Verify Agent Exists

```bash
# Check agent status
agentcore status

# Should show:
# - Agent ARN
# - Status: READY
# - Endpoint: DEFAULT (READY)
```

### Step 2: Check Agent ARN Format

```bash
AGENT_ARN=$(agentcore status | grep "Agent ARN" | tail -1 | awk '{print $NF}')

# Verify format
echo $AGENT_ARN
# Should contain: bedrock-agentcore:REGION:ACCOUNT:runtime/AGENT-NAME-ID
```

### Step 3: Test with Agent Core CLI

```bash
# If this works, the issue is with your SDK/CLI call
agentcore invoke '{"prompt": "test"}'
```

### Step 4: Check Container Logs

```bash
# Get logs to see if handler is being called
aws logs tail /aws/bedrock-agentcore/runtimes/YOUR-AGENT-ID-DEFAULT \
  --log-stream-name-prefix "2025/11/03/[runtime-logs]" \
  --follow
```

### Step 5: Verify Handler Function

```python
# Test handler locally
python -c "
from agentcore_entry import handler
import asyncio
result = asyncio.run(handler({'prompt': 'test'}, None))
print(result)
"
```

### Step 6: Check Dockerfile

```dockerfile
# ✅ Correct - runs module as entry point
CMD ["opentelemetry-instrument", "python", "-m", "agentcore_entry"]

# ❌ Wrong - this won't work
# CMD ["python", "agentcore_entry.py"]
# CMD ["python", "-c", "from agentcore_entry import handler"]
```

## 📋 Quick Checklist

- [ ] Using `bedrock-agent-runtime` API (not `bedrock-agent`)
- [ ] Agent ARN contains `/runtime/` in path
- [ ] Handler function is named `handler` or `handle`
- [ ] Handler is at module level (not in a class)
- [ ] Entry point file is configured correctly
- [ ] Region matches in all API calls
- [ ] IAM permissions include `bedrock-agent-runtime:InvokeAgentRuntime`
- [ ] Agent status is READY (check with `agentcore status`)
- [ ] Container is running (check CloudWatch logs)

## 🐛 Common Mistakes

### Mistake 1: Wrong API
```python
# ❌ Wrong
client = boto3.client('bedrock-agent', ...)
client.invoke_agent(...)

# ✅ Correct
client = boto3.client('bedrock-agent-runtime', ...)
client.invoke_agent_runtime(...)
```

### Mistake 2: Wrong ARN Format
```python
# ❌ Wrong - Bedrock Agents format
agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/AGENT-ID"

# ✅ Correct - Agent Core format
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/AGENT-NAME-ID"
```

### Mistake 3: Handler Inside Class
```python
# ❌ Wrong
class AgentHandler:
    async def handler(self, event, context):
        return {"output": "..."}

# ✅ Correct
async def handler(event, context):
    return {"output": "..."}
```

### Mistake 4: Wrong Module Path
```dockerfile
# ❌ Wrong
CMD ["python", "agentcore_entry.py"]

# ✅ Correct
CMD ["python", "-m", "agentcore_entry"]
```

## 📞 Getting Help

If still getting 404 after checking all above:

1. **Check CloudWatch Logs**:
   ```bash
   aws logs tail /aws/bedrock-agentcore/runtimes/YOUR-AGENT-ID-DEFAULT --follow
   ```

2. **Verify Agent ARN**:
   ```bash
   agentcore status
   ```

3. **Test with Agent Core CLI**:
   ```bash
   agentcore invoke '{"prompt": "test"}'
   ```

4. **Check IAM Permissions**:
   ```bash
   aws iam get-user-policy --user-name YOUR-USER --policy-name YOUR-POLICY
   ```

