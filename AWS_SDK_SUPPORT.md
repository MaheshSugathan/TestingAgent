# AWS SDK Support for Bedrock Agent Core

## 📦 Version Requirements

### Python & boto3 Versions

**Current Project Configuration:**
- **Python**: 3.11 (in Dockerfile) / 3.13.4 (local)
- **boto3**: >= 1.34.0 (requirements.txt)
- **botocore**: >= 1.34.0 (requirements.txt)

**Minimum Requirements for Bedrock Agent Core:**
- **boto3**: >= 1.39.8 (for bedrock-agentcore support)
- **botocore**: >= 1.33.8
- **Python**: 3.8+ (boto3 supports 3.6+, but we use 3.11+)

### Update boto3 for Agent Core Support

```bash
# Update to latest versions
pip install --upgrade boto3 botocore

# Or install specific version
pip install boto3>=1.39.8 botocore>=1.33.8
```

## 🔧 Correct API Client & Methods

### Issue: Method Not Found

If you get `'bedrock-agent-runtime' object has no attribute 'invoke_agent_runtime'`, it's likely:

1. **Wrong service client name**
2. **Outdated boto3 version**
3. **Wrong method name**

### Solution 1: Use Correct Client Service

Bedrock Agent Core uses **different service names** depending on the API:

```python
# ❌ WRONG - This is for Bedrock Agents (not Agent Core)
client = boto3.client('bedrock-agent-runtime', ...)
client.invoke_agent(...)  # This is for Bedrock Agents

# ✅ CORRECT - For Bedrock Agent Core Runtime
client = boto3.client('bedrock-agentcore', region_name='us-east-1')
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:...',
    runtimeSessionId='session-123',
    payload=json.dumps({"prompt": "What is RAG?"}).encode()
)
```

### Solution 2: Check Available Methods

```python
import boto3

# Create client
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# List all methods
methods = [m for m in dir(client) if not m.startswith('_')]
print("Available methods:")
for m in sorted(methods):
    if 'invoke' in m.lower() or 'agent' in m.lower():
        print(f"  ✓ {m}")

# Check service model
print("\nService operations:")
for op in client._service_model.operation_names:
    if 'invoke' in op.lower() or 'agent' in op.lower():
        print(f"  ✓ {op}")
```

## 📚 Correct Invocation Patterns

### Pattern 1: Using bedrock-agentcore Client

```python
import boto3
import json

# Client for Bedrock Agent Core
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Prepare payload
payload = json.dumps({"prompt": "What is RAG?"}).encode()

# Invoke agent runtime
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/agent-name-id',
    runtimeSessionId='session-123',
    payload=payload
)

# Process streaming response
for line in response['response'].iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### Pattern 2: Using bedrock-agent-runtime Client (Alternative)

Some regions/services might use `bedrock-agent-runtime`:

```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

# Note: Method name might be different
# Check available methods first
print(dir(client))

# Possible methods:
# - invoke_agent_runtime
# - invoke_agent
# - invoke_agent_for_user
```

### Pattern 3: Direct HTTP Call (if SDK doesn't support)

```python
import boto3
import requests
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Get credentials
session = boto3.Session()
credentials = session.get_credentials()

# Prepare request
url = 'https://bedrock-agentcore-runtime.us-east-1.amazonaws.com/runtime/agents/your-agent-arn/invoke'
headers = {
    'Content-Type': 'application/json'
}
payload = {
    "prompt": "What is RAG?",
    "sessionId": "session-123"
}

# Sign request
request = AWSRequest(method='POST', url=url, data=json.dumps(payload), headers=headers)
SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)

# Make request
response = requests.post(url, data=request.data, headers=request.headers)
print(response.json())
```

## 🔍 Verify Your Setup

### Check boto3 Version

```python
import boto3
print(f"boto3 version: {boto3.__version__}")
print(f"botocore version: {boto3.Session().get_config_variable('botocore')}")

# Check if bedrock-agentcore client is available
try:
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    print("✅ bedrock-agentcore client available")
    print(f"Available methods: {[m for m in dir(client) if 'invoke' in m.lower()]}")
except Exception as e:
    print(f"❌ Error: {e}")
```

### Check Service Availability

```python
import boto3

services_to_check = [
    'bedrock-agentcore',
    'bedrock-agent-runtime',
    'bedrock-agent'
]

for service in services_to_check:
    try:
        client = boto3.client(service, region_name='us-east-1')
        methods = [m for m in dir(client) if 'invoke' in m.lower()]
        print(f"✅ {service}: {methods}")
    except Exception as e:
        print(f"❌ {service}: {e}")
```

## 📋 Working Example from Our Project

Based on our working deployment:

```python
import boto3

# Get agent ARN from: agentcore status
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/rag_evaluation_agent-YOUR_RUNTIME_ID"

# Try bedrock-agentcore client first
try:
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Prepare payload
    import json
    payload = json.dumps({"prompt": "What is RAG?"}).encode()
    
    # Invoke
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId='session-123',
        payload=payload
    )
    
    # Process response
    for line in response['response'].iter_lines():
        if line:
            print(line.decode('utf-8'))
            
except AttributeError as e:
    print(f"Method not found: {e}")
    print("Try updating boto3: pip install --upgrade boto3 botocore")
except Exception as e:
    print(f"Error: {e}")
```

## 🚀 Recommended: Use Agent Core CLI

The easiest way is to use the `agentcore` CLI tool:

```bash
# Install
pip install bedrock-agentcore-starter-toolkit

# Invoke
agentcore invoke '{"prompt": "What is RAG?"}'
```

This handles all the SDK complexities automatically.

## 🔄 Alternative: Update requirements.txt

To ensure everyone has the right versions:

```txt
# Update requirements.txt
boto3>=1.39.8
botocore>=1.33.8
```

Then:
```bash
pip install --upgrade -r requirements.txt
```

## 📝 Summary

| Component | Version | Notes |
|-----------|---------|-------|
| **Python** | 3.11+ | Used in Docker containers |
| **boto3** | >= 1.39.8 | Required for bedrock-agentcore support |
| **botocore** | >= 1.33.8 | Required for bedrock-agentcore support |
| **Client** | `bedrock-agentcore` | Service name for Agent Core |
| **Method** | `invoke_agent_runtime` | API method name |

**If method not found:**
1. Update boto3: `pip install --upgrade boto3 botocore`
2. Verify client: `boto3.client('bedrock-agentcore')`
3. Check methods: `dir(client)`
4. Use Agent Core CLI: `agentcore invoke`

