# Deploying to AWS Bedrock Agent Core Runtime

This guide explains how to deploy your LangGraph agents to **AWS Bedrock Agent Core Runtime** (not Bedrock Agents).

## 📋 What is Bedrock Agent Core?

Bedrock Agent Core Runtime allows you to deploy custom containers with your own code and invoke them via AWS Bedrock. It's different from Bedrock Agents which use foundation models.

## 🚀 Prerequisites

1. **Install Bedrock AgentCore Starter Toolkit**:
   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```

2. **AWS CLI** configured with credentials
3. **Docker** installed and running

## 📦 Step 1: Install the Toolkit

```bash
pip install bedrock-agentcore-starter-toolkit
```

## ⚙️ Step 2: Prepare Your Agent Entry Point

Bedrock Agent Core expects an agent entry point. Since you have a LangGraph pipeline, create an entry point file:

**Create `agentcore_entry.py`**:

```python
"""Entry point for Bedrock Agent Core Runtime."""

import asyncio
import json
import os
from typing import Dict, Any

from config.config_manager import ConfigManager
from orchestration.pipeline import RAGEvaluationPipeline
from observability import setup_logger


# Initialize pipeline (globally to reuse)
pipeline = None
logger = None


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
        logger.info("Initializing RAG Evaluation Pipeline...")
        
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        pipeline = RAGEvaluationPipeline(
            config=config,
            logger=logger
        )
        
        logger.info("Pipeline initialized")
    
    try:
        # Extract input from event
        # Agent Core sends different formats, handle both
        input_text = None
        if 'prompt' in event:
            input_text = event['prompt']
        elif 'input' in event:
            input_text = event['input']
        elif 'inputText' in event:
            input_text = event['inputText']
        elif isinstance(event, str):
            input_text = event
        
        if not input_text:
            return {
                "error": "No input provided. Expected 'prompt', 'input', or 'inputText' in event."
            }
        
        logger.info(f"Processing request: {input_text[:100]}...")
        
        # Run the pipeline
        state = await pipeline.run_single_turn_evaluation(
            query=input_text,
            session_id=event.get('sessionId', f"agentcore-{os.getpid()}")
        )
        
        # Get summary
        summary = pipeline.get_pipeline_summary(state)
        
        # Extract response from pipeline
        response_text = "Evaluation completed."
        if state.dev_result and state.dev_result.success:
            responses = state.get_data("dev", "generated_responses")
            if responses and len(responses) > 0:
                response_text = responses[0].get('response', response_text)
        
        # Format response for Agent Core
        return {
            "output": response_text,
            "session_id": state.session_id,
            "pipeline_id": state.pipeline_id,
            "success": state.is_complete(),
            "execution_time": state.get_total_execution_time(),
            "summary": {
                "evaluation_complete": state.is_complete(),
                "errors": state.errors if state.errors else []
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            "error": str(e),
            "output": f"Error: {str(e)}"
        }


# For synchronous invocation (if needed)
def handle(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous handler wrapper."""
    return asyncio.run(handler(event, context))
```

## 🔧 Step 3: Configure Agent Core Deployment

Run the configuration command:

```bash
agentcore configure -e agentcore_entry.py
```

This will prompt you for:
- **Execution role**: Press Enter to auto-create (or specify existing)
- **ECR repository**: Press Enter to auto-create
- **Requirements file**: Confirm `requirements.txt`
- **OAuth**: Type `no` (unless you need it)
- **Memory settings**: Enable if you need long-term memory

## 🚀 Step 4: Deploy to Agent Core Runtime

```bash
agentcore launch
```

This command will:
1. Build a Docker container with your agent
2. Push the container to Amazon ECR
3. Create an Agent Core Runtime environment
4. Deploy your agent to AWS

You'll receive an **Agent ARN** upon successful deployment.

## 🧪 Step 5: Test Your Agent

```bash
# Test with a simple prompt
agentcore invoke '{"prompt": "What is RAG?"}'

# Or test the evaluation pipeline
agentcore invoke '{"prompt": "Evaluate this RAG system"}'
```

## 📝 Alternative: Manual Deployment Script

If you prefer manual control, here's a script:

```bash
#!/bin/bash
# Manual deployment to Bedrock Agent Core Runtime

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="rag-evaluation-agentcore"

echo "🚀 Deploying to Bedrock Agent Core Runtime..."

# Build and push Docker image (same as before)
docker build -f Dockerfile.bedrock -t ${ECR_REPO}:latest .
docker tag ${ECR_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest

aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest

# Then use agentcore CLI to create runtime
# agentcore launch
```

## 📚 Agent Core Entry Point Requirements

Your entry point must:

1. **Handle the event format**:
   ```python
   event = {
       "prompt": "user input",
       "sessionId": "optional-session-id"
   }
   ```

2. **Return proper format**:
   ```python
   return {
       "output": "agent response",
       # optional additional fields
   }
   ```

3. **Be async or sync**:
   - Use `async def handler()` for async
   - Use `def handle()` for sync (can wrap async with `asyncio.run()`)

## 🔍 Verifying Deployment

```bash
# List your agents
agentcore list

# Get agent details
agentcore describe <agent-arn>

# View logs
agentcore logs <agent-arn>
```

## 🌐 Invoking via Python SDK

```python
import boto3
import json

# Get your agent ARN from `agentcore list`
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/your-agent-id"

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentArn=agent_arn,
    inputText="What is RAG?",
    sessionId="session-123"
)

for event in response.get('completion', []):
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode('utf-8'), end='')
```

## 🔗 Key Differences: Agent Core vs Agents

| Feature | Bedrock Agents | Agent Core Runtime |
|---------|---------------|-------------------|
| **Models** | Foundation models (Claude, etc.) | Your custom code |
| **Containers** | Optional | Required |
| **Entry Point** | Instructions/prompts | Code handler function |
| **API** | `bedrock-agent` | `bedrock-agent-runtime` |
| **Use Case** | Chat assistants | Custom logic/agents |

## 📖 Additional Resources

- [Bedrock Agent Core Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [Agent Core Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Runtime Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/)

