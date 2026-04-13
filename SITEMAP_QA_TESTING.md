# Sitemap-Based Help & Support Agent Testing

This flow tests a **help/support agent** that uses **Pinecone** (or similar) to retrieve answers built from reference website content (e.g. from a [sitemap](https://example.com/sitemap.xml)).

---

## Architecture diagram

High-level system architecture: components, external systems, and data flow.

```mermaid
flowchart TB
    subgraph User["User / CLI"]
        U[User or run_sitemap_qa_eval.py]
    end

    subgraph Orchestrator["Orchestrator (Sitemap QA Runner)"]
        RUN[run_sitemap_qa_test]
    end

    subgraph Agents["Testing pipeline agents"]
        SQA[Sitemap Q&A Agent]
        DEV[Dev Agent]
        FUP[Follow-up Question Agent]
    end

    subgraph External["External systems"]
        SITE[Reference website<br/>sitemap.xml + page HTML]
        LLM[LLM / Bedrock<br/>Q&A + follow-up generation]
        HELP[Help / Support Agent<br/>Pinecone-backed]
    end

    U -->|page_url, options| RUN
    RUN --> SQA
    SQA -->|HTTP GET| SITE
    SQA -->|page content| LLM
    LLM -->|Q&A pairs JSON| SQA
    SQA -->|queries, reference_answers| RUN
    RUN --> DEV
    DEV -->|query| HELP
    HELP -->|response| DEV
    DEV -->|generated_responses| RUN
    RUN --> FUP
    FUP -->|query + response| LLM
    LLM -->|follow-up questions JSON| FUP
    FUP -->|followup_queries| RUN
    RUN -->|trigger back| DEV
    DEV --> HELP
    RUN -->|first_round + followup_round| U
```

**Component view (layers):**

```mermaid
flowchart LR
    subgraph Layer1["Entry"]
        CLI[CLI / API]
    end

    subgraph Layer2["Orchestrator"]
        Runner[Sitemap QA Runner]
    end

    subgraph Layer3["Agents"]
        A1[Sitemap Q&A]
        A2[Dev Agent]
        A3[Follow-up Agent]
    end

    subgraph Layer4["External"]
        Web[Website<br/>sitemap + pages]
        Bedrock[Bedrock / LLM]
        HelpAgent[Help Agent<br/>Pinecone]
    end

    CLI --> Runner
    Runner --> A1
    Runner --> A2
    Runner --> A3
    A1 --> Web
    A1 --> Bedrock
    A2 --> HelpAgent
    A3 --> Bedrock
    A3 --> A2
```

**Data flow (artifacts):**

```mermaid
flowchart LR
    I((page_url)) --> Q1[queries]
    Q1 --> Q2[reference_answers]
    Q1 --> P[page_content]
    Q1 --> R1[first_round responses]
    R1 --> FQ[followup_queries]
    FQ --> R2[followup_round responses]
    R1 --> O((results))
    R2 --> O
```

**System context (what the pipeline uses):**

```mermaid
flowchart TB
    subgraph Pipeline["Sitemap QA Testing Pipeline"]
        direction TB
        Runner[Orchestrator]
        SQA[Sitemap Q&A Agent]
        Dev[Dev Agent]
        Fup[Follow-up Agent]
        Runner --> SQA
        Runner --> Dev
        Runner --> Fup
    end

    SITE[(Reference<br/>Website)]
    LLM[(Bedrock / LLM)]
    HELP[(Help & Support<br/>Agent + Pinecone)]

    Pipeline -->|fetch sitemap & page| SITE
    Pipeline -->|generate Q&A, follow-ups| LLM
    Pipeline -->|run queries| HELP
```

---

## Flow diagram (QA approach)

```mermaid
flowchart LR
    subgraph Input
        A[User: page URL or sitemap link]
    end

    subgraph "1. Sitemap Q&A Agent"
        B[Fetch sitemap XML]
        C[Fetch page HTML]
        D[Extract text content]
        E[LLM: generate Q&A pairs]
        B --> C --> D --> E
    end

    subgraph "2. First round"
        F[Dev Agent]
        G[Help/Support Agent<br/>Pinecone-backed]
        F --> G
    end

    subgraph "3. Follow-up Agent"
        H[LLM: generate follow-up<br/>questions from each response]
    end

    subgraph "4. Trigger back"
        I[Dev Agent again]
        J[Help/Support Agent]
        I --> J
    end

    A --> B
    E --> |queries + ref answers| F
    G --> |responses| H
    H --> |follow-up queries| I
```

**High-level sequence:**

```mermaid
sequenceDiagram
    participant User
    participant SitemapQA as Sitemap Q&A Agent
    participant Dev as Dev Agent
    participant Help as Help/Support (Pinecone)
    participant FollowUp as Follow-up Agent

    User->>SitemapQA: page_url (from sitemap)
    SitemapQA->>SitemapQA: fetch sitemap → fetch page → extract text
    SitemapQA->>SitemapQA: LLM: generate Q&A pairs
    SitemapQA->>Dev: queries + reference_answers

    loop For each query
        Dev->>Help: query
        Help->>Dev: response (from Pinecone KB)
    end

    Dev->>FollowUp: generated_responses
    FollowUp->>FollowUp: LLM: follow-up questions per (query, response)
    FollowUp->>Dev: followup_queries

    loop For each follow-up query
        Dev->>Help: follow-up query
        Help->>Dev: response
    end

    Dev->>User: first_round + followup_round results
```

**Simplified flow (boxes):**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Sitemap Q&A    │     │   Dev Agent     │     │ Follow-up       │     │   Dev Agent     │
│  Agent          │────▶│   (1st round)   │────▶│ Question Agent  │────▶│   (2nd round)   │
│                 │     │                 │     │                 │     │                 │
│ • Fetch sitemap │     │ • Run queries   │     │ • From each     │     │ • Run follow-up │
│ • Fetch page    │     │   vs Help agent │     │   (Q, response) │     │   queries       │
│ • Extract text  │     │   (Pinecone)    │     │   generate      │     │   vs Help agent  │
│ • LLM → Q&A     │     │ • Collect       │     │   follow-up Qs   │     │ • Collect       │
│   pairs         │     │   responses     │     │ • trigger_back  │     │   responses     │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
      ▲                                                                         │
      │ page_url                                                                 │
      └─────────────────────────────────────────────────────────────────────────┘
                                    final results (first_round + followup_round)
```

## Overview

1. **Sitemap Q&A Agent** – Reads a link (from the sitemap or your input), fetches the page, and generates possible questions and reference answers for that page.
2. **Dev Agent** – Runs each of those queries against your help/support agent (Pinecone-backed) and collects responses.
3. **Follow-up Question Agent** – Reads each response and generates follow-up questions a customer might ask next.
4. **Trigger back** – Runs those follow-up questions through the Dev Agent again.

## Agents

| Agent | Role |
|-------|------|
| `SitemapQAAgent` | Fetch sitemap → fetch page by URL → extract content → LLM generates Q&A pairs |
| `DevAgent` | Send queries to your help/support agent (AgentCore / Pinecone) |
| `FollowUpQuestionAgent` | From each (query, response) generate follow-up questions and output them for a second Dev round |

## Configuration

In `config/config.yaml`:

```yaml
sitemap_qa:
  sitemap_url: "https://example.com/sitemap.xml"
  max_qa_pairs: 15
  max_followups_per_turn: 3
```

Set `agentcore.base_url` (and optional `agentcore.bill.agent_name`) to point at your deployed help/support agent.

## Running

### CLI

```bash
# First page in sitemap
python run_sitemap_qa_eval.py

# Specific page
python run_sitemap_qa_eval.py --page-url "https://example.com/help/contact-us"

# Custom AgentCore URL
python run_sitemap_qa_eval.py --agentcore-url "http://localhost:8000" --page-url "https://example.com/help/contact-us"

# No follow-up round
python run_sitemap_qa_eval.py --no-followup

# Save result to file
python run_sitemap_qa_eval.py --page-url "..." --output result.json
```

### Programmatic

```python
from orchestration.sitemap_qa_runner import run_sitemap_qa_test

result = await run_sitemap_qa_test(
    page_url="https://example.com/help/contact-us",
    agentcore_base_url="http://localhost:8000",
    run_followup_round=True,
)
# result["sitemap_qa"], result["first_round"], result["followup_queries"], result["followup_round"]
```

## Output shape

- **sitemap_qa**: `page_url`, `queries`, `qa_pairs`, `reference_answers`
- **first_round**: list of `{query, response, context_used, metadata}` from Dev Agent
- **followup_queries**: list of follow-up question strings
- **followup_round**: (if run) list of Dev Agent responses for those follow-ups

## Dependencies

- `beautifulsoup4` for parsing HTML from sitemap pages
- `requests` for fetching sitemap and page content
- Bedrock (or configured LLM) for generating Q&As and follow-up questions

## Implementation prompt for your project

To replicate this flow in another codebase, use the full **implementation prompt** in **[SITEMAP_QA_IMPLEMENTATION_PROMPT.md](SITEMAP_QA_IMPLEMENTATION_PROMPT.md)**. It includes:

- Copy-paste prompt describing the flow, technical requirements, and the two LLM prompts (Q&A generation, follow-up generation)
- Mermaid flow diagram
- Suggested file layout and config
- Reference to this repo's implementation
