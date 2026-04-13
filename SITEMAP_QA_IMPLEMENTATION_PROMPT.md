# Implementation Prompt: Sitemap-Based QA + Follow-up Testing for Help/Support Agents

Use this prompt in your actual project (e.g. with Cursor, Copilot, or another AI assistant) to implement the same flow: **sitemap/page → Q&A generation → run queries against your help agent → generate follow-up questions → trigger back (run follow-ups against the agent again)**.

---

## Copy-paste prompt (for your project)

```
Implement a sitemap-based QA testing flow for our help/support agent (which uses a vector DB like Pinecone for retrieval). Follow this design:

## 1. Flow (high level)

1. **Sitemap / Page Q&A Agent**
   - Input: a page URL (e.g. from a sitemap like https://example.com/sitemap.xml) or the sitemap URL.
   - Fetch the sitemap XML, parse <loc> URLs. If user provided a specific page_url, use it; else use the first URL from the sitemap.
   - Fetch the page HTML at that URL, strip scripts/nav/footer, extract main text (e.g. with BeautifulSoup).
   - Call an LLM (e.g. Bedrock Claude or OpenAI) with the page content and ask it to generate N realistic customer Q&A pairs (question + reference answer) that someone might ask after reading that page. Focus on: contact info, how-to steps, eligibility, pricing, FAQs, key facts.
   - Output: list of queries, list of reference_answers, and the page content (to use as context for the dev agent if needed).

2. **Dev / Invoker Agent**
   - Input: list of queries (and optional context document from the page).
   - For each query, call our help/support agent API (the one that uses Pinecone/vector retrieval) and collect the response.
   - Output: list of { query, response, context_used, metadata }.

3. **Follow-up Question Agent**
   - Input: the list of { query, response } from step 2.
   - For each pair, call the LLM to generate 1–3 short, natural follow-up questions a customer might ask next (e.g. "What are the opening hours?", "How do I do that online?").
   - Output: list of follow-up question strings and optional context (parent_query, parent_response, followup_question).

4. **Trigger back**
   - Run the Dev/Invoker Agent again with the follow-up questions as the new query list (same or minimal context).
   - Collect responses and return first_round + followup_round results.

## 2. Technical requirements

- **Sitemap Q&A agent**: Fetch sitemap (HTTP GET), parse XML (e.g. xml.etree or BeautifulSoup), fetch page HTML, extract text (BeautifulSoup), call LLM with a structured prompt that returns a JSON array of { "question", "answer" }. Limit content sent to LLM (e.g. first 10–15k chars) and cap Q&A pairs (e.g. 15).
- **Dev agent**: Reuse existing integration with our help/support agent (HTTP or SDK). Accept queries and optional documents; for each query invoke the agent and collect response.
- **Follow-up agent**: Input list of { query, response }; call LLM with a prompt that returns a JSON array of follow-up question strings. Parse JSON (handle ```json blocks) and dedupe/limit (e.g. 1–3 per source response).
- **Orchestrator/runner**: One async function that: (1) runs Sitemap Q&A agent with page_url, (2) runs Dev agent with the generated queries (and page content as one document if your dev agent needs context), (3) runs Follow-up agent on the responses, (4) if follow-up round is enabled, runs Dev agent again with followup_queries. Return a single result object with sitemap_qa, first_round, followup_queries, followup_round.

## 3. Prompts to implement

### Prompt A – Generate Q&A pairs from page content (Sitemap Q&A Agent)

Use this exact structure; replace [N] and [DOMAIN] with your values (e.g. 15, your brand name):

```
You are creating test questions and answers for a help/support chatbot that answers from a knowledge base built from [DOMAIN] reference websites.

Page URL: {page_url}

Page content (excerpt):
---
{content_slice}
---

Generate {N} realistic customer questions that someone might ask after reading this page, and provide the expected/reference answer based only on the content above. Focus on: contact info, how-to steps, eligibility, pricing, FAQs, and key facts.

Return a JSON array of objects, each with "question" and "answer" keys. No other text.
Example format:
[{"question": "How do I contact support?", "answer": "You can contact via..."}, ...]
```

Parse the LLM response as JSON array; if parsing fails, return a single fallback Q&A. Cap the list at N items.

### Prompt B – Generate follow-up questions (Follow-up Agent)

Use this structure; replace [N] with max follow-ups per turn (e.g. 3):

```
You are generating follow-up questions that a customer might ask after receiving this answer from a help/support chatbot.

Original question: {query}

Agent's response: {response}

Generate 1 to [N] short, natural follow-up questions that a user might ask next (e.g. "What are the opening hours?", "How do I do that online?", "Is there a phone number?"). Return ONLY a JSON array of strings, e.g. ["question1?", "question2?"]. No other text.
```

Parse the LLM response as JSON array of strings; on failure return empty list.

## 4. Config

Support at least:

- sitemap_url (default: your main sitemap)
- max_qa_pairs (e.g. 15)
- max_followups_per_turn (e.g. 3)
- help_agent_base_url or equivalent for the Dev/Invoker agent

## 5. CLI (optional)

Provide a script that accepts:
- --page-url (optional; if missing, use first URL from sitemap)
- --sitemap-url
- --agent-url (help/support agent base URL)
- --no-followup (skip second Dev round)
- --output (write JSON result to file)

Invoke the orchestrator and print or save the result (first_round, followup_queries, followup_round).

## 6. Dependencies

- HTTP client (requests or httpx) for sitemap and page fetch
- HTML parsing (e.g. BeautifulSoup) for page text extraction
- LLM client (Bedrock, OpenAI, etc.) for both prompts
- Existing help/support agent client for Dev agent

Implement the two agents (Sitemap Q&A, Follow-up), the Dev/Invoker integration, and the orchestrator that wires them in order and supports "trigger back" for the follow-up round.
```

---

## Quick reference: flow diagram (Mermaid)

```mermaid
flowchart LR
    A[page_url] --> B[Sitemap Q&A Agent]
    B --> C[queries + ref answers]
    C --> D[Dev Agent 1st]
    D --> E[Help Agent]
    E --> F[responses]
    F --> G[Follow-up Agent]
    G --> H[followup_queries]
    H --> I[Dev Agent 2nd]
    I --> J[Help Agent]
    J --> K[followup_round]
```

---

## Files to create (suggested)

| File | Purpose |
|------|--------|
| `agents/sitemap_qa_agent.py` | Fetch sitemap + page, extract text, LLM → Q&A pairs |
| `agents/followup_agent.py` | From (query, response) list → LLM → follow-up question list |
| `orchestration/sitemap_qa_runner.py` | Orchestrator: Sitemap QA → Dev → Follow-up → Dev (trigger back) |
| `run_sitemap_qa_eval.py` | CLI with --page-url, --agent-url, --no-followup, --output |
| Config section | e.g. `sitemap_qa.sitemap_url`, `max_qa_pairs`, `max_followups_per_turn` |

---

## Reference implementation

In this repo (RAGLens / `raglens`), the flow is implemented as:

- **Flow diagram & QA approach**: see `SITEMAP_QA_TESTING.md` (flow diagram, sequence diagram, simplified boxes).
- **Sitemap Q&A Agent**: `agents/sitemap_qa_agent.py` (sitemap fetch, page fetch, BeautifulSoup, Bedrock prompt for Q&A).
- **Follow-up Agent**: `agents/followup_agent.py` (Bedrock prompt for follow-up questions, JSON array of strings).
- **Runner**: `orchestration/sitemap_qa_runner.py` (async `run_sitemap_qa_test()`).
- **CLI**: `run_sitemap_qa_eval.py` (argparse, ConfigManager, output JSON).
- **Prompts**: embedded in the two agents (see Prompt A and Prompt B above for the exact text).

Use this prompt in your actual project and adjust [DOMAIN], [N], agent URLs, and file names to match your product and codebase.
