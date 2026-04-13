"""
Follow-up Question Agent.

Reads the response from the Dev Agent (help/support agent) and generates
follow-up questions based on the response, then triggers back (returns them
so they can be run through the Dev Agent again).
"""

import json
import time
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

from .base import BaseAgent, AgentState


class FollowUpQuestionAgent(BaseAgent):
    """
    Agent that:
    1. Reads query + response from Dev Agent
    2. Generates follow-up questions based on the response
    3. Outputs follow-up queries so the pipeline can trigger back to Dev Agent
    """

    def __init__(
        self,
        config: Dict[str, Any],
        bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        aws_region: str = "us-east-1",
        max_followups_per_turn: int = 3,
        **kwargs
    ):
        super().__init__(config, **kwargs)
        self.bedrock_model_id = bedrock_model_id
        self.aws_region = aws_region
        self.max_followups_per_turn = max_followups_per_turn
        self._bedrock = None

    @property
    def bedrock(self):
        if self._bedrock is None:
            self._bedrock = boto3.client("bedrock-runtime", region_name=self.aws_region)
        return self._bedrock

    async def execute(self, state: AgentState) -> AgentState:
        """
        Input from state:
          - generated_responses: list of {query, response, ...} from Dev Agent
        Output in state:
          - followup_queries: list of follow-up question strings
          - followup_context: list of {parent_query, parent_response, followup_question}
          - trigger_back: True (indicates pipeline should run followup_queries through Dev Agent again)
        """
        start_time = time.time()
        session_id = state.session_id

        try:
            responses = state.data.get("generated_responses", [])
            if not responses:
                state.data["followup_queries"] = []
                state.data["followup_context"] = []
                state.data["trigger_back"] = False
                state.data["followup_metadata"] = {"execution_time": time.time() - start_time, "count": 0}
                return state

            followup_queries = []
            followup_context = []

            for item in responses:
                query = item.get("query", "")
                response_text = item.get("response", "")
                if not query or not response_text:
                    continue
                followups = await self._generate_followups(query, response_text, session_id)
                for fq in followups[: self.max_followups_per_turn]:
                    followup_queries.append(fq)
                    followup_context.append({
                        "parent_query": query,
                        "parent_response": response_text[:500],
                        "followup_question": fq,
                    })

            state.data["followup_queries"] = followup_queries
            state.data["followup_context"] = followup_context
            state.data["trigger_back"] = len(followup_queries) > 0
            state.data["followup_metadata"] = {
                "execution_time": time.time() - start_time,
                "count": len(followup_queries),
                "source_responses": len(responses),
            }

            self._record_execution_time("followup_agent", time.time() - start_time, session_id)
            self._record_success("followup_agent", session_id)
            return state

        except Exception as e:
            self.log_with_context("error", f"Follow-up agent failed: {e}", session_id=session_id, error=str(e))
            self._record_failure("followup_agent", session_id, e)
            raise

    async def _generate_followups(self, query: str, response: str, session_id: str) -> List[str]:
        """Use Bedrock to generate follow-up questions from the user query and agent response."""
        prompt = f"""You are generating follow-up questions that a customer might ask after receiving this answer from a help/support chatbot.

Original question: {query}

Agent's response: {response}

Generate 1 to {self.max_followups_per_turn} short, natural follow-up questions that a user might ask next (e.g. "What are the opening hours?", "How do I do that online?", "Is there a phone number?"). Return ONLY a JSON array of strings, e.g. ["question1?", "question2?"]. No other text.
"""

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            response_out = self.bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(body),
                contentType="application/json",
            )
            response_body = json.loads(response_out["body"].read())
            content_out = response_body["content"][0]["text"].strip()
            if "```json" in content_out:
                content_out = content_out.split("```json")[1].split("```")[0].strip()
            elif "```" in content_out:
                content_out = content_out.split("```")[1].split("```")[0].strip()
            followups = json.loads(content_out)
            if isinstance(followups, list):
                return [str(q).strip() for q in followups if q]
            return []
        except (ClientError, json.JSONDecodeError, KeyError) as e:
            self.log_with_context("warning", f"Follow-up generation failed: {e}, returning empty", session_id=session_id)
            return []
