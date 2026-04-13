# Case Study: RAGLens — Automated RAG Evaluation at Scale

## Global Insurance Co.: From Manual QA to Automated RAG Testing

*This case study illustrates how an organization adopted **RAGLens** to automate evaluation of its RAG-based internal knowledge assistant. Names and figures are representative; the scenario reflects typical enterprise challenges and outcomes.*

---

## 1. Executive Summary

**Global Insurance Co.** (GIC) deployed a RAG-powered internal assistant to help underwriters and claims staff find answers from policy documents, guidelines, and historical cases. After an initial pilot, the team struggled to validate quality consistently before each release. Manual review of sample queries was slow, subjective, and did not scale. By adopting **RAGLens**—multi-agent RAG evaluation on AWS Bedrock Agent Core—GIC automated end-to-end evaluation, cut pre-release validation from days to hours, and established reproducible quality benchmarks. The solution also improved confidence in model and retrieval changes and provided audit-ready evaluation reports for compliance.

---

## 2. Company and Context

### 2.1 About Global Insurance Co.

- **Industry**: Property and casualty insurance  
- **Size**: ~15,000 employees; operations in North America, Europe, and Asia  
- **AI use case**: Internal RAG assistant (“Guide”) used by underwriters and claims analysts to query policy docs, guidelines, and FAQs  

### 2.2 The RAG System (“Guide”)

- **Purpose**: Answer questions from internal knowledge bases (S3-backed document stores)  
- **Users**: Underwriters, claims staff, and support teams  
- **Deployment**: API backend; web and mobile clients  
- **Data**: Thousands of PDFs, Word docs, and structured JSON (policies, guidelines, FAQs)  

Guide was built with a custom retrieval layer (vector search over chunked documents) and an LLM for answer generation. A separate “Bill”-style agent service was used for some specialized flows.

---

## 3. The Challenge

### 3.1 Quality Assurance at Scale

After the pilot, GIC’s ML and QA teams faced several issues:

1. **Manual evaluation bottleneck**  
   Before each release, QA manually ran 50–100 sample queries, compared answers to references, and logged issues. This took **3–5 days** and did not cover edge cases or regressions in retrieval.

2. **Inconsistent judgment**  
   Different reviewers applied different standards. There was no shared definition of “good” vs “bad” for faithfulness, relevance, or completeness.

3. **Slow feedback on changes**  
   Model upgrades, prompt tweaks, or retrieval/config changes required another round of manual checks. Experimentation was slow.

4. **Audit and compliance**  
   Risk and compliance wanted **documented evidence** of how Guide’s outputs were validated before production. Spreadsheets and ad-hoc notes were insufficient.

5. **Limited scalability**  
   The knowledge base and query volume grew. Manual QA could not scale to hundreds or thousands of test queries.

### 3.2 Goals

GIC set clear objectives:

- **Automate** end-to-end RAG evaluation (retrieve → generate → evaluate) with minimal manual steps.  
- **Standardize** metrics (e.g., faithfulness, relevance, correctness) and qualitative assessment.  
- **Shorten** pre-release validation from days to hours.  
- **Support** experimentation (model/prompt/retrieval changes) with quick, comparable results.  
- **Produce** evaluation reports suitable for internal audit and compliance.

---

## 4. The Solution: RAGLens

### 4.1 Why RAGLens?

GIC evaluated build-vs-buy options:

- **In-house scripts**: Flexible but required significant engineering to support Ragas, LLM-as-a-Judge, orchestration, and AWS integration.  
- **Generic LLM evaluation tools**: Often single-model or single-metric; not purpose-built for full RAG pipelines.  
- **RAGLens**: Multi-agent RAG evaluation on Bedrock Agent Core, with Ragas + LLM-as-a-Judge, S3 ingestion, and pluggable external RAG (e.g., Guide/Bill). It matched GIC’s need for automation, standardization, and AWS-native deployment.

### 4.2 Implementation Overview

**Architecture**

- **Retrieval Agent**: Fetches and parses test documents from S3 (same bucket structure used for Guide’s knowledge base).  
- **Dev Agent**: Calls GIC’s existing Guide/Bill APIs to generate answers. No change to production services.  
- **Evaluator Agent**: Runs Ragas metrics (faithfulness, relevance, correctness, context precision) and LLM-as-a-Judge (Claude on Bedrock).  
- **Orchestration**: LangGraph workflow on Bedrock Agent Core Runtime; state passed through retrieval → dev → evaluator.  
- **Observability**: Structured logs and CloudWatch metrics for debugging and monitoring.

**Deployment**

- RAGLens deployed as a container on **AWS Bedrock Agent Core Runtime** in the same AWS account and region as Guide.  
- Test datasets (curated queries + reference docs) stored in **S3**.  
- Evaluation invoked via **CLI**, **AWS SDK**, and later **Lambda + API Gateway + Cognito** for secure, API-based access from internal tools.

**Integration with Guide**

- Dev Agent configured to call Guide’s (and optionally Bill’s) HTTP APIs.  
- Queries and context (from Retrieval Agent) were sent to these services; generated answers were fed into the Evaluator Agent.  
- No code changes in Guide; only configuration of RAGLens’s external agent endpoint.

### 4.3 Evaluation Design

- **Test set**: 200+ queries covering common topics, edge cases, and known failure modes.  
- **Metrics**:  
  - Ragas: faithfulness, relevance, correctness, context precision.  
  - LLM-as-a-Judge: overall score, coherence, completeness, plus free-form reasoning.  
- **Thresholds**: 0.8 for key metrics and overall score; configurable per environment.  
- **Reports**: JSON evaluation results, aggregate scores, pass rates, and per-query details, stored in S3 and used for release sign-off and audit.

---

## 5. Results and Benefits

### 5.1 Validation Time

| Metric | Before (manual) | After (RAGLens) |
|--------|------------------|------------------------|
| Pre-release validation | 3–5 days | **~4–6 hours** (automated run + review) |
| Test query coverage | 50–100 | **200+** (expandable) |
| Run frequency | Per release | **Per release + on-demand** for experiments |

### 5.2 Quality and Consistency

- **Standardized metrics**: Same Ragas and LLM-as-a-Judge criteria across all runs.  
- **Regression detection**: Regressions (e.g., from model or retrieval changes) identified before production.  
- **Clear pass/fail**: Configurable thresholds and overall scores made release decisions explicit.

### 5.3 Experimentation and Iteration

- **Faster A/B tests**: Model or prompt changes evaluated on the same test set in hours.  
- **Comparison across configs**: Side-by-side metrics for different retrievers or model versions.  
- **Reduced risk**: Fewer “hope it works” releases; more data-driven decisions.

### 5.4 Compliance and Audit

- **Traceable evaluation**: Logs, metrics, and evaluation reports document how Guide was tested.  
- **Reproducibility**: Same test set and config produce comparable results over time.  
- **Audit-ready outputs**: Stored evaluation results used in compliance reviews.

### 5.5 Operational Impact

- **Less manual QA**: QA team shifted from repetitive sample checking to designing test cases and analyzing results.  
- **Better collaboration**: Shared metrics and reports improved alignment between ML, product, and risk teams.  
- **Scalability**: Adding more queries or running more frequently did not require proportional headcount.

---

## 6. Challenges and Mitigations

### 6.1 Initial Setup and Calibration

- **Challenge**: Deciding thresholds and aligning Ragas + LLM-as-a-Judge with “good enough” for Guide.  
- **Mitigation**: Ran evaluations on a curated subset, compared scores to expert judgments, and tuned thresholds. Iterated over 2–3 sprints.

### 6.2 Integration with Internal APIs

- **Challenge**: Guide and Bill use different request/response shapes.  
- **Mitigation**: Used the Dev Agent’s configurable HTTP client; added thin adapter logic where needed. Kept production services unchanged.

### 6.3 Cost and Performance

- **Challenge**: Large test sets and LLM-as-a-Judge increased Bedrock usage and runtime.  
- **Mitigation**: Sampled subsets for quick checks; full runs for release. Used async execution and pipeline optimizations. Monitored costs via CloudWatch and budgets.

---

## 7. Lessons Learned

1. **Invest in test data**: High-quality, diverse queries and reference docs are as important as the evaluation platform.  
2. **Start with a subset**: Calibrate metrics and thresholds on a smaller set before scaling.  
3. **Treat evaluation as a product**: Clear ownership (e.g., ML or QA), runbooks, and onboarding for new team members.  
4. **Use observability**: Logs and metrics were critical for debugging pipeline or integration issues.  
5. **Align with compliance early**: Involving risk/compliance during design simplified audit use of evaluation reports.

---

## 8. Future Plans

- **Expand test set**: Add more languages, product lines, and edge cases.  
- **CI/CD integration**: Trigger automated evaluation on specific branches or before production deploys.  
- **Dashboard**: Web UI for viewing trends, comparing runs, and drilling into failures.  
- **Additional metrics**: Custom dimensions (e.g., compliance-specific checks) alongside Ragas and LLM-as-a-Judge.

---

## 9. Conclusion

Global Insurance Co. reduced pre-release validation from **3–5 days to roughly half a day**, standardized RAG quality assessment, and gained **audit-ready evaluation**. RAGLens’s **multi-agent orchestration**, **Ragas + LLM-as-a-Judge** blend, and **AWS-native deployment** allowed GIC to automate evaluation without replacing Guide. The same platform now supports faster experimentation and more confident releases as Guide’s scope and usage grow.

---

## Appendix A: Glossary

- **RAG**: Retrieval-Augmented Generation  
- **Ragas**: Open-source framework for RAG evaluation metrics  
- **LLM-as-a-Judge**: Using an LLM to score or critique another model’s outputs  
- **Bedrock Agent Core Runtime**: AWS managed runtime for agent-based workloads  
- **LangGraph**: Library for orchestrating multi-step, stateful agent workflows  

---

## Appendix B: Related Documentation

- [BUSINESS_AND_SOLUTION.md](BUSINESS_AND_SOLUTION.md) — Business scenario, solution, uniqueness, benefits  
- [SOLUTION_OVERVIEW.md](SOLUTION_OVERVIEW.md) — Technical solution overview  
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture  
