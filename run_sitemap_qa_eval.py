#!/usr/bin/env python3
"""
Run sitemap-based help & support agent evaluation.

Usage:
  # Use first page from sitemap
  python run_sitemap_qa_eval.py

  # Use a specific page URL from the sitemap
  python run_sitemap_qa_eval.py --page-url "https://example.com/help/contact-us"

  # Point to your AgentCore / help agent
  python run_sitemap_qa_eval.py --agentcore-url "http://localhost:8000" --page-url "https://example.com/help/contact-us"

  # Skip follow-up round
  python run_sitemap_qa_eval.py --no-followup
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestration.sitemap_qa_runner import run_sitemap_qa_test


def main():
    parser = argparse.ArgumentParser(description="Sitemap-based help/support agent evaluation (sitemap → Q&As → Dev Agent → follow-ups → Dev Agent)")
    parser.add_argument("--page-url", type=str, default=None, help="Page URL from sitemap to generate Q&As from (default: first in sitemap)")
    parser.add_argument("--sitemap-url", type=str, default="https://example.com/sitemap.xml", help="Sitemap URL")
    parser.add_argument("--agentcore-url", type=str, default="http://localhost:8000", help="AgentCore / help agent base URL")
    parser.add_argument("--bill-agent", type=str, default="bill", help="Agent name for invocation")
    parser.add_argument("--no-followup", action="store_true", help="Do not run follow-up question round")
    parser.add_argument("--session-id", type=str, default=None, help="Optional session ID")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML (default: config/config.yaml)")
    parser.add_argument("--output", type=str, default=None, help="Write JSON result to file")
    args = parser.parse_args()

    try:
        from config.config_manager import ConfigManager
        config = ConfigManager().load_config()
    except Exception:
        config = {}

    async def _run():
        return await run_sitemap_qa_test(
            page_url=args.page_url,
            sitemap_url=args.sitemap_url,
            config=config,
            agentcore_base_url=args.agentcore_url,
            bill_agent_name=args.bill_agent,
            run_followup_round=not args.no_followup,
            session_id=args.session_id,
        )

    result = asyncio.run(_run())

    # Serialize for JSON (e.g. first_round may contain non-serializable objects)
    def _serialize(obj):
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_serialize(v) for v in obj]
        if hasattr(obj, "__dict__"):
            return _serialize(obj.__dict__)
        return obj

    out = _serialize(result)
    print(json.dumps(out, indent=2, default=str))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"Result written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
