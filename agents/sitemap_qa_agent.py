"""
Sitemap Q&A Generator Agent.

Reads a link from a sitemap, fetches the page content,
and generates possible questions and answers for testing the help/support agent (Pinecone-backed).
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import boto3
from botocore.exceptions import ClientError
import requests
from bs4 import BeautifulSoup

from .base import BaseAgent, AgentState


# Default sitemap URL (override via config or input)
DEFAULT_SITEMAP_URL = "https://example.com/sitemap.xml"


class SitemapQAAgent(BaseAgent):
    """
    Agent that:
    1. Reads sitemap (or uses user-provided link)
    2. Fetches the page at that link
    3. Extracts text content
    4. Uses LLM to generate Q&A pairs for testing the help/support agent
    """

    def __init__(
        self,
        config: Dict[str, Any],
        sitemap_url: str = DEFAULT_SITEMAP_URL,
        bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        aws_region: str = "us-east-1",
        max_qa_pairs: int = 15,
        **kwargs
    ):
        super().__init__(config, **kwargs)
        self.sitemap_url = sitemap_url
        self.bedrock_model_id = bedrock_model_id
        self.aws_region = aws_region
        self.max_qa_pairs = max_qa_pairs
        self._bedrock = None

    @property
    def bedrock(self):
        if self._bedrock is None:
            self._bedrock = boto3.client("bedrock-runtime", region_name=self.aws_region)
        return self._bedrock

    async def execute(self, state: AgentState) -> AgentState:
        """
        Input from state:
          - page_url: optional specific page URL (from sitemap). If not set, use first from sitemap or fail.
          - sitemap_url: optional override sitemap URL
        Output in state:
          - sitemap_urls: list of URLs from sitemap
          - page_url: URL that was processed
          - page_content: extracted text (truncated)
          - qa_pairs: list of {question, answer}
          - queries: list of question strings (for Dev Agent)
          - reference_answers: list of answers (for evaluation)
        """
        start_time = time.time()
        session_id = state.session_id

        try:
            page_url = state.data.get("page_url") or state.metadata.get("page_url")
            sitemap_url = state.data.get("sitemap_url") or state.metadata.get("sitemap_url") or self.sitemap_url

            self.log_with_context("info", "Fetching sitemap", session_id=session_id, sitemap_url=sitemap_url)
            urls = await self._fetch_sitemap_urls(sitemap_url)

            if not urls:
                raise ValueError("No URLs found in sitemap")

            if not page_url:
                page_url = urls[0]
                self.log_with_context("info", f"No page_url provided, using first from sitemap: {page_url}", session_id=session_id)

            if page_url not in urls and not any(page_url.startswith(u) or u.startswith(page_url) for u in urls):
                self.log_with_context("info", f"page_url not in sitemap list, will fetch anyway: {page_url}", session_id=session_id)

            self.log_with_context("info", f"Fetching page content: {page_url}", session_id=session_id)
            content = await self._fetch_page_content(page_url)

            if not content or len(content.strip()) < 50:
                raise ValueError(f"Insufficient content extracted from {page_url}")

            self.log_with_context("info", "Generating Q&A pairs via LLM", session_id=session_id)
            self._last_session_id = session_id
            qa_pairs = await self._generate_qa_pairs(content, page_url, session_id)

            queries = [p["question"] for p in qa_pairs]
            reference_answers = [p.get("answer", "") for p in qa_pairs]

            state.data["sitemap_urls"] = urls[:100]
            state.data["page_url"] = page_url
            state.data["page_content"] = content[:15000]
            state.data["qa_pairs"] = qa_pairs
            state.data["queries"] = queries
            state.data["reference_answers"] = reference_answers
            state.data["sitemap_qa_metadata"] = {
                "sitemap_url": sitemap_url,
                "page_url": page_url,
                "num_qa_pairs": len(qa_pairs),
                "execution_time": time.time() - start_time,
            }

            self._record_execution_time("sitemap_qa", time.time() - start_time, session_id)
            self._record_success("sitemap_qa", session_id)
            return state

        except Exception as e:
            self.log_with_context("error", f"Sitemap QA agent failed: {e}", session_id=session_id, error=str(e))
            self._record_failure("sitemap_qa", session_id, e)
            raise

    async def _fetch_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Fetch sitemap XML and return list of <loc> URLs."""
        resp = requests.get(sitemap_url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (compatible; RAG-Test/1.0)"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = root.findall(".//sm:loc", ns) or root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if not locs:
            locs = root.findall(".//loc")
        return [el.text.strip() for el in locs if el.text and el.text.strip().startswith("http")]

    async def _fetch_page_content(self, page_url: str) -> str:
        """Fetch HTML and extract main text content."""
        resp = requests.get(
            page_url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RAG-Test/1.0)"},
            allow_redirects=True,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:50000]

    async def _generate_qa_pairs(self, content: str, page_url: str, session_id: Optional[str] = None) -> List[Dict[str, str]]:
        """Use Bedrock to generate question-answer pairs from page content."""
        content_slice = content[:12000]

        prompt = f"""You are creating test questions and answers for a help/support chatbot that answers from a knowledge base built from reference websites.

Page URL: {page_url}

Page content (excerpt):
---
{content_slice}
---

Generate {self.max_qa_pairs} realistic customer questions that someone might ask after reading this page, and provide the expected/reference answer based only on the content above. Focus on: contact info, how-to steps, eligibility, pricing, FAQs, and key facts.

Return a JSON array of objects, each with "question" and "answer" keys. No other text.
Example format:
[{{"question": "How do I contact support?", "answer": "You can contact via..."}}, ...]
"""

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = self.bedrock.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(body),
            contentType="application/json",
        )
        response_body = json.loads(response["body"].read())
        content_out = response_body["content"][0]["text"]

        try:
            content_out = content_out.strip()
            if "```json" in content_out:
                content_out = content_out.split("```json")[1].split("```")[0].strip()
            elif "```" in content_out:
                content_out = content_out.split("```")[1].split("```")[0].strip()
            qa_pairs = json.loads(content_out)
            if not isinstance(qa_pairs, list):
                qa_pairs = [qa_pairs]
            return qa_pairs[: self.max_qa_pairs]
        except json.JSONDecodeError:
            self.log_with_context("warning", "LLM did not return valid JSON, using fallback", session_id=getattr(self, "_last_session_id", "sitemap-qa"))
            return [{"question": "What is this page about?", "answer": "This page is from the reference website."}]
