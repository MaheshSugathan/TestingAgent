# Deployment Guide — RAGLens

Complete step-by-step guide for deploying RAGLens to AWS Bedrock Agent Core Runtime.

## 📋 Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Docker**: 20.10+ (for building images)
- **AWS CLI**: 2.0+ (configured with credentials)
- **bedrock-agentcore-starter-toolkit**: Latest version

### Required AWS Permissions

Your AWS user/role needs:
- `bedrock-agentcore:*` (full Agent Core access)
- `ecr:*` (ECR repository management)
- `iam:*` (role creation and management)
- `logs:*` (CloudWatch Logs access)
- `s3:*` (S3 bucket access for datasets)

### AWS Account Setup

1. **Enable Bedrock Agent Core** in your AWS account
2. **Configure AWS CLI**:
   ```bash
   aws configure
   ```
3. **Verify access**:
   ```bash
   aws sts get-caller-identity
   ```

## 🚀 Deployment Steps

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Bedrock Agent Core toolkit
pip install bedrock-agentcore-starter-toolkit
```

### Step 2: Configure Agent Core

```bash
# Configure Agent Core (use your agent name)
agentcore configure \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --disable-memory
```

This will:
- Create Agent Core configuration
- Set up IAM roles (if needed)
- Configure ECR repository
- Set region

### Step 3: Verify Configuration

```bash
# Check configuration
cat .bedrock_agentcore.yaml

# Should show:
# - agent_name: rag_evaluation_agent
# - region: us-east-1
# - execution_role_arn: arn:aws:iam::...
# - ecr_repository: bedrock-agentcore-rag_evaluation_agent
```

### Step 4: Build and Deploy

#### Option A: Using Agent Core CLI (Recommended)

```bash
# Deploy using toolkit (handles everything)
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --local-build
```

The `--local-build` flag:
- Builds Docker image locally
- Pushes to ECR
- Deploys to Agent Core Runtime
- Handles Docker Hub rate limits

#### Option B: Manual Deployment

```bash
# 1. Build Docker image locally
docker build -f Dockerfile.bedrock -t rag-evaluation-agent:latest .

# 2. Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# 3. Tag and push
ECR_REPO=$(aws ecr describe-repositories \
  --repository-names bedrock-agentcore-rag_evaluation_agent \
  --query 'repositories[0].repositoryUri' --output text)

docker tag rag-evaluation-agent:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest

# 4. Launch agent
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1
```

### Step 5: Verify Deployment

```bash
# Check agent status
agentcore status

# Should show:
# - Status: READY
# - Agent ARN: arn:aws:bedrock-agentcore:...
# - Endpoint: DEFAULT (READY)
```

### Step 6: Test Deployment

```bash
# Test invocation
agentcore invoke '{"prompt": "What is RAG?"}'

# Or using AWS CLI
AGENT_ARN=$(agentcore status | grep "Agent ARN" | tail -1 | awk '{print $NF}')
aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn "${AGENT_ARN}" \
  --input-text "What is RAG?" \
  --session-id "test-session-$(date +%s)" \
  --region us-east-1 \
  output.json

cat output.json
```

## 📁 Project Structure for Deployment

```
TestingAgent/
├── agentcore_entry.py          # Entry point for Agent Core Runtime
├── Dockerfile.bedrock          # Docker image for Agent Core
├── requirements.txt            # Python dependencies
├── config/
│   ├── config.yaml            # Configuration file
│   └── config_manager.py      # Config loader
├── agents/                     # Agent implementations
│   ├── base.py
│   ├── retrieval_agent.py
│   ├── dev_agent.py
│   └── evaluator_agent.py
├── orchestration/              # LangGraph workflow
│   ├── pipeline.py
│   ├── workflow.py
│   └── state.py
├── evaluation/                 # Evaluation modules
│   ├── ragas_evaluator.py
│   └── llm_judge.py
└── observability/              # Logging and metrics
    ├── logger.py
    └── metrics.py
```

## 🔧 Configuration

### Environment Variables

Create `.env` file (optional, can use config.yaml):

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# S3 Configuration
S3_BUCKET=rag-evaluation-datasets
S3_KEY_PREFIX=test-data/

# Bedrock Configuration
BEDROCK_REGION=us-east-1
BEDROCK_JUDGE_MODEL=anthropic.claude-3-sonnet-20240229-v1:0

# CloudWatch Configuration
CLOUDWATCH_NAMESPACE=RAGEvaluation
```

### Configuration File

Edit `config/config.yaml`:

```yaml
aws:
  region: "us-east-1"
  cloudwatch:
    namespace: "RAGEvaluation"
    log_group: "/aws/rag-evaluation"

s3:
  bucket: "rag-evaluation-datasets"
  key_prefix: "test-data/"

bedrock:
  region: "us-east-1"
  models:
    judge: "anthropic.claude-3-sonnet-20240229-v1:0"

agentcore:
  enabled: true
  base_url: "http://localhost:8000"  # External agent URL
  bill:
    agent_name: "bill"
    timeout: 60
    max_retries: 3
```

## 🐳 Docker Configuration

### Dockerfile.bedrock

The Dockerfile used for Agent Core deployment:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN uv pip install -r requirements.txt
RUN uv pip install aws-opentelemetry-distro>=0.10.1

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# Expose ports
EXPOSE 9000 8000 8080

# Entry point
CMD ["opentelemetry-instrument", "python", "-m", "agentcore_entry"]
```

### Build Requirements

- Base image: Python 3.12
- Working directory: `/app`
- User: Non-root (`bedrock_agentcore`)
- Entry point: `agentcore_entry` module

## 🔍 Verification & Troubleshooting

### Check Agent Status

```bash
# Get status
agentcore status

# Expected output:
# ✅ Status: READY
# ✅ Agent ARN: arn:aws:bedrock-agentcore:...
# ✅ Endpoint: DEFAULT (READY)
```

### Check Logs

```bash
# Get log group name from agent status
LOG_GROUP="/aws/bedrock-agentcore/runtimes/rag_evaluation_agent-*-DEFAULT"

# View recent logs
aws logs tail "${LOG_GROUP}" \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --since 10m \
  --region us-east-1

# Follow logs
aws logs tail "${LOG_GROUP}" \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --follow \
  --region us-east-1
```

### Common Issues

#### 1. Container Not Starting

**Symptoms**: Agent status shows "FAILED" or "ERROR"

**Check**:
```bash
# Check CloudWatch logs
aws logs tail "${LOG_GROUP}" --since 30m

# Look for:
# - Import errors
# - Handler function not found
# - Permission errors
```

**Fix**:
- Verify `agentcore_entry.py` exists
- Check handler function is named `handler` or `handle`
- Verify all dependencies in requirements.txt

#### 2. Handler Not Found

**Symptoms**: 404 errors on invocation

**Fix**:
- Ensure `CMD` in Dockerfile: `["python", "-m", "agentcore_entry"]`
- Verify handler function is at module level (not in class)
- Check entry point in `.bedrock_agentcore.yaml`

#### 3. Import Errors

**Symptoms**: ModuleNotFoundError in logs

**Fix**:
- Verify all dependencies in `requirements.txt`
- Check `PYTHONPATH` is set correctly
- Ensure relative imports are correct

#### 4. Permission Errors

**Symptoms**: AccessDenied errors

**Fix**:
- Check IAM execution role permissions
- Verify ECR repository access
- Check S3 bucket permissions

## 🔄 Updating Deployment

### Update Code

```bash
# 1. Make code changes
# ... edit files ...

# 2. Rebuild and redeploy
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --local-build

# Or if using existing image
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1
```

### Update Configuration

```bash
# 1. Edit config/config.yaml
# ... make changes ...

# 2. Rebuild image (config is baked into image)
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --local-build
```

### Rollback

```bash
# List versions
aws ecr describe-images \
  --repository-name bedrock-agentcore-rag_evaluation_agent \
  --region us-east-1

# Redeploy specific version
agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --image-tag <previous-tag>
```

## 📊 Post-Deployment

### Monitor Metrics

```bash
# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace RAGEvaluation \
  --metric-name PipelineExecutionTime \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

### View Dashboard

- **CloudWatch Dashboard**: https://console.aws.amazon.com/cloudwatch/
- **Agent Core Console**: https://console.aws.amazon.com/bedrock-agentcore/
- **GenAI Dashboard**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core

## 🧹 Cleanup

### Remove Agent

```bash
# Delete agent
agentcore delete \
  --agent-name rag_evaluation_agent \
  --region us-east-1
```

### Clean Up Resources

```bash
# Delete ECR repository
aws ecr delete-repository \
  --repository-name bedrock-agentcore-rag_evaluation_agent \
  --force \
  --region us-east-1

# Delete IAM roles (if created manually)
aws iam delete-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-* \
  --policy-name BedrockAgentCoreRuntimeExecutionPolicy-*

aws iam delete-role \
  --role-name AmazonBedrockAgentCoreSDKRuntime-*
```

## 📝 Summary

Deployment checklist:

- [ ] Prerequisites installed (Python, Docker, AWS CLI)
- [ ] AWS credentials configured
- [ ] Agent Core configured (`agentcore configure`)
- [ ] Docker image built and pushed
- [ ] Agent deployed (`agentcore launch`)
- [ ] Status verified (`agentcore status`)
- [ ] Test invocation successful
- [ ] Logs accessible
- [ ] Metrics visible

For detailed architecture, see `ARCHITECTURE.md`.

