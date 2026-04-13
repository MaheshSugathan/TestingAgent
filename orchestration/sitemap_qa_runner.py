"""
Sitemap-based help & support testing workflow.

Orchestrates:
1. SitemapQAAgent: read link from sitemap, fetch page, generate Q&A pairs
2. DevAgent: run each query against the help/support agent (Pinecone-backed)
3. FollowUpQuestionAgent: generate follow-up questions from responses
4. Trigger back: run follow-up queries through DevAgent again
"""

import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from agents import SitemapQAAgent, DevAgent, FollowUpQuestionAgent
from agents.base import AgentState
from observability import setup_logger


async def run_sitemap_qa_test(
    page_url: Optional[str] = None,
    sitemap_url: str = "https://example.com/sitemap.xml",
    config: Optional[Dict[str, Any]] = None,
    agentcore_base_url: str = "http://localhost:8000",
    bill_agent_name: str = "bill",
    run_followup_round: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full sitemap QA test: sitemap page → Q&As → Dev Agent → follow-ups → Dev Agent again.

    Args:
        page_url: Specific page URL from sitemap to generate Q&As from. If None, uses first URL in sitemap.
        sitemap_url: Sitemap URL.
        config: Pipeline/config dict. If None, minimal config is used.
        agentcore_base_url: Base URL for the help/support agent (AgentCore).
        bill_agent_name: Agent name for invocation.
        run_followup_round: If True, run follow-up questions through Dev Agent after first round.
        session_id: Optional session ID for tracing.

    Returns:
        Dict with:
          - sitemap_qa: output from SitemapQAAgent (queries, qa_pairs, page_url, etc.)
          - first_round: Dev Agent responses for initial queries
          - followup_queries: list of follow-up questions generated
          - followup_round: (if run_followup_round) Dev Agent responses for follow-up queries
          - session_id
    """
    import uuid
    log = setup_logger("SitemapQARunner")
    session_id = session_id or f"sitemap-qa-{uuid.uuid4().hex[:8]}"
    config = config or {}

    result = {
        "session_id": session_id,
        "page_url": page_url,
        "sitemap_qa": None,
        "first_round": None,
        "followup_queries": [],
        "followup_round": None,
    }

    # --- 1. Sitemap Q&A Agent ---
    sqa_config = config.get("sitemap_qa", {})
    sitemap_url = sqa_config.get("sitemap_url", sitemap_url)
    log.info("Running Sitemap Q&A agent", extra={"session_id": session_id, "page_url": page_url})
    sitemap_agent = SitemapQAAgent(
        config=config,
        sitemap_url=sitemap_url,
        max_qa_pairs=sqa_config.get("max_qa_pairs", 15),
    )
    agent_state = AgentState(
        session_id=session_id,
        data={"page_url": page_url, "sitemap_url": sitemap_url},
        metadata={"page_url": page_url},
    )
    agent_state = await sitemap_agent.execute(agent_state)
    queries = agent_state.data.get("queries", [])
    reference_answers = agent_state.data.get("reference_answers", [])
    page_content = agent_state.data.get("page_content", "")
    result["sitemap_qa"] = {
        "page_url": agent_state.data.get("page_url"),
        "queries": queries,
        "qa_pairs": agent_state.data.get("qa_pairs", []),
        "reference_answers": reference_answers,
    }

    if not queries:
        log.warning("No queries generated from sitemap QA agent", extra={"session_id": session_id})
        return result

    # Build one document from page content so Dev Agent has context (help/support agent may use Pinecone only)
    documents = [Document(page_content=page_content[:50000], metadata={"source": result["sitemap_qa"]["page_url"] or "sitemap"})]

    # --- 2. Dev Agent (first round) ---
    log.info("Running Dev Agent (first round)", extra={"session_id": session_id, "query_count": len(queries)})
    dev_agent = DevAgent(
        config=config.get("agents", {}).get("dev", {}),
        agentcore_base_url=agentcore_base_url,
        bill_agent_name=bill_agent_name,
        timeout=config.get("agentcore", {}).get("bill", {}).get("timeout", 60),
        max_retries=config.get("agentcore", {}).get("bill", {}).get("max_retries", 3),
    )
    dev_state = AgentState(
        session_id=session_id,
        data={"documents": documents, "queries": queries},
        metadata={"queries": queries},
    )
    dev_state = await dev_agent.execute(dev_state)
    first_round_responses = dev_state.data.get("generated_responses", [])
    result["first_round"] = first_round_responses

    # --- 3. Follow-up Question Agent ---
    log.info("Running Follow-up Question agent", extra={"session_id": session_id})
    followup_agent = FollowUpQuestionAgent(
        config=config,
        max_followups_per_turn=sqa_config.get("max_followups_per_turn", 3),
    )
    followup_state = AgentState(
        session_id=session_id,
        data={"generated_responses": first_round_responses},
        metadata={},
    )
    followup_state = await followup_agent.execute(followup_state)
    followup_queries = followup_state.data.get("followup_queries", [])
    result["followup_queries"] = followup_queries
    result["followup_context"] = followup_state.data.get("followup_context", [])

    # --- 4. Trigger back: Dev Agent with follow-up queries ---
    if run_followup_round and followup_queries:
        log.info("Running Dev Agent (follow-up round)", extra={"session_id": session_id, "query_count": len(followup_queries)})
        dev_state_2 = AgentState(
            session_id=session_id,
            data={"documents": documents, "queries": followup_queries},
            metadata={"queries": followup_queries, "round": "followup"},
        )
        dev_state_2 = await dev_agent.execute(dev_state_2)
        result["followup_round"] = dev_state_2.data.get("generated_responses", [])

    return result
