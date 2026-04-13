# RAGLens

*Bring RAG quality into focus — retrieve, generate, judge, repeat.*

**Measure what matters.** A production-style, multi-agent pipeline that **retrieves**, **generates**, and **scores** RAG answers—with **Ragas**, **LLM-as-a-Judge**, and **AWS Bedrock Agent Core** baked in.

Stop guessing if your retrieval is helping. Run a structured eval loop, ship metrics to CloudWatch, and iterate with confidence.

## Built on AWS — and wired for eval

**Same cloud as your models:** the pipeline is meant to run **on AWS**, with **Bedrock** for generation *and* judging, **S3** for documents, **CloudWatch** for signals, and **Agent Core** as the runtime that holds the LangGraph workflow together.

| Area | What we use |
|------|-------------|
| **Runtime & agents** | [AWS Bedrock Agent Core](https://aws.amazon.com/bedrock/agentcore/) — containerized LangGraph entrypoint (`agentcore_entry.py`) |
| **Models** | [Amazon Bedrock](https://aws.amazon.com/bedrock/) — LLM-as-a-Judge & foundation models (e.g. Claude) |
| **Data plane** | [Amazon S3](https://aws.amazon.com/s3/) — retrieval corpus & eval inputs |
| **Observability** | [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) — logs & metrics namespace |
| **Security** | [AWS IAM](https://aws.amazon.com/iam/) — roles & least-privilege patterns in docs/Terraform |
| **Shipping the app** | [Amazon ECR](https://aws.amazon.com/ecr/) — images for Agent Core; **Docker** locally |
| **Optional production paths** | [AWS Lambda](https://aws.amazon.com/lambda/) + [Amazon Cognito](https://aws.amazon.com/cognito/) + API Gateway — chat UI & secure invoke patterns (`lambda/`, `terraform/`) |
| **Application stack** | Python 3.11+ · **LangGraph** · **FastAPI** · **Ragas** |

<p align="left">
  <a href="https://aws.amazon.com/bedrock/"><img src="https://img.shields.io/badge/Amazon_Bedrock-232F3E?style=flat-square&logo=amazonaws&logoColor=white" alt="Amazon Bedrock" /></a>
  <a href="https://aws.amazon.com/bedrock/agentcore/"><img src="https://img.shields.io/badge/Bedrock_Agent_Core-232F3E?style=flat-square&logo=amazonaws&logoColor=white" alt="Bedrock Agent Core" /></a>
  <img src="https://img.shields.io/badge/Amazon_S3-569A31?style=flat-square&logo=amazons3&logoColor=white" alt="Amazon S3" />
  <img src="https://img.shields.io/badge/Amazon_CloudWatch-FF4F8B?style=flat-square&logo=amazonaws&logoColor=white" alt="Amazon CloudWatch" />
  <img src="https://img.shields.io/badge/AWS_Lambda-FF9900?style=flat-square&logo=awslambda&logoColor=white" alt="AWS Lambda" />
  <img src="https://img.shields.io/badge/Amazon_Cognito-DD344C?style=flat-square&logo=amazonaws&logoColor=white" alt="Amazon Cognito" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/LangGraph-111111?style=flat-square" alt="LangGraph" />
</p>

*Tip: badges are for scanning; the table above is the source of truth for how each AWS piece maps to the repo.*

---

## Why this repo

| You want to… | This gives you… |
|--------------|-----------------|
| Compare models or prompts fairly | Repeatable metrics (faithfulness, relevance, correctness) |
| See retrieval + generation end-to-end | LangGraph workflow: Retrieval → Dev → Evaluator |
| Run on AWS without reinventing ops | **Bedrock Agent Core** entrypoint, Docker, observability hooks |
| Keep humans in the loop when scores dip | Optional **HITL** pause in the pipeline |

---

## Highlights

- **Multi-agent orchestration** — LangGraph ties retrieval, response generation, and evaluation into one flow.
- **Dual evaluation** — Classical Ragas metrics plus LLM-as-a-Judge on Amazon Bedrock.
- **Observable by default** — Structured logging and CloudWatch-friendly metrics.
- **Agent Core ready** — `agentcore_entry.py` and `Dockerfile.bedrock` for deployment to **AWS Bedrock Agent Core Runtime**.
- **Extras in-repo** — Web UI (`web_ui/`), Lambda/Cognito patterns, Terraform samples, sitemap QA tooling—pick what you need.

---

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────────┐
│           AWS Bedrock Agent Core Runtime                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              Entry Point (agentcore_entry.py)          │ │
│  └───────────────────────┬────────────────────────────────┘ │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         LangGraph Workflow (orchestration/)            │ │
│  │                                                       │ │
│  │  Retrieval → Dev → Evaluator                         │ │
│  │     ↓         ↓         ↓                             │ │
│  │   S3      External   Ragas + LLM Judge                │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Deep dive:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Quick start

**Prerequisites:** Python 3.11+, Docker 20.10+, AWS CLI, Bedrock / Agent Core access.

```bash
git clone https://github.com/MaheshSugathan/TestingAgent.git
cd TestingAgent

pip install -r requirements.txt
pip install bedrock-agentcore-starter-toolkit
```

**Deploy to Agent Core (example):**

```bash
agentcore configure \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --disable-memory

agentcore launch \
  --agent-name rag_evaluation_agent \
  --region us-east-1 \
  --local-build

agentcore status
agentcore invoke '{"prompt": "What is RAG?"}'
```

**Full deployment:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

## Invoke your agent

**CLI**

```bash
agentcore invoke '{"prompt": "What is RAG?"}'
```

**Python (SDK)**

```python
import boto3
import json

client = boto3.client("bedrock-agentcore", region_name="us-east-1")

# ARN from: agentcore status
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:...",
    runtimeSessionId="session-123",
    payload=json.dumps({"prompt": "What is RAG?"}).encode(),
)

for line in response["response"].iter_lines():
    if line:
        print(line.decode("utf-8"))
```

**AWS CLI**

```bash
AGENT_ARN=$(agentcore status | grep "Agent ARN" | tail -1 | awk '{print $NF}')

aws bedrock-agent-runtime invoke-agent-runtime \
  --agent-arn "${AGENT_ARN}" \
  --input-text "What is RAG?" \
  --session-id "session-$(date +%s)" \
  --region us-east-1 \
  output.json
```

---

## Project layout

```
TestingAgent/
├── agentcore_entry.py          # Bedrock Agent Core entrypoint
├── Dockerfile.bedrock          # Container image for Agent Core
├── api_server.py               # Optional local FastAPI server
├── requirements.txt
│
├── agents/                     # Retrieval, dev, evaluator, sitemap QA, …
├── orchestration/              # LangGraph pipeline & workflow
├── evaluation/                 # Ragas + LLM judge
├── observability/              # Logging & metrics
├── config/                     # config.yaml & loader
├── web_ui/                     # Chat-style UI for invoking agents
├── lambda/                     # Example Lambda + Agent Core invocation
└── terraform/                  # Sample AWS infra (see terraform/README.md)
```

---

## Configuration

Optional `.env`:

```bash
AWS_REGION=us-east-1
S3_BUCKET=rag-evaluation-datasets
BEDROCK_REGION=us-east-1
```

Edit `config/config.yaml` for regions, S3 prefixes, Bedrock judge model, thresholds, and AgentCore URLs. See file for full options.

---

## Monitoring

```bash
LOG_GROUP="/aws/bedrock-agentcore/runtimes/rag_evaluation_agent-*-DEFAULT"

aws logs tail "${LOG_GROUP}" \
  --log-stream-name-prefix "$(date +%Y/%m/%d)/[runtime-logs]" \
  --follow \
  --region us-east-1
```

- [GenAI observability (CloudWatch)](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core)
- [Bedrock Agent Core console](https://console.aws.amazon.com/bedrock-agentcore/)

---

## Troubleshooting

| Issue | Doc |
|-------|-----|
| 404 / wrong ARN or client | [TROUBLESHOOTING_404.md](TROUBLESHOOTING_404.md) |
| boto3 / SDK quirks | [AWS_SDK_SUPPORT.md](AWS_SDK_SUPPORT.md) |
| End-to-end invocation | [AGENT_INVOCATION_FLOW.md](AGENT_INVOCATION_FLOW.md) |

---

## Documentation

- [BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md) — Scenario and value
- [CASE_STUDY.md](CASE_STUDY.md) — Evaluation at scale
- [HUMAN_IN_LOOP.md](HUMAN_IN_LOOP.md) — Human-in-the-loop
- [SITEMAP_QA_TESTING.md](SITEMAP_QA_TESTING.md) — Sitemap Q&A and follow-ups
- [SITEMAP_QA_IMPLEMENTATION_PROMPT.md](SITEMAP_QA_IMPLEMENTATION_PROMPT.md) — Port the flow elsewhere
- [SOLUTION_OVERVIEW.md](SOLUTION_OVERVIEW.md) — Technical overview
- [DEPLOYMENT.md](DEPLOYMENT.md) — Deploy guide
- [DOCKER_LOCAL_SETUP.md](DOCKER_LOCAL_SETUP.md) — Local Docker
- [web_ui/README.md](web_ui/README.md) — Web UI

---

## Security

- IAM-first auth on AWS  
- Non-root container user in images  
- CloudWatch logs; VPC-ready patterns in docs  
- Keep secrets out of git—use env vars, IAM roles, and ignored local config (see `.gitignore`)

---

## License

MIT

---

## Status

Ready for **Bedrock Agent Core** workflows: agents wired, metrics path in place, and docs for deploy and troubleshooting.
