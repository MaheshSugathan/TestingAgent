"""
Lambda function to securely invoke Bedrock Agent Core Runtime.
Supports human-in-the-loop (HITL) and resume.
"""

import json
import os
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_ARN = os.getenv("AGENT_ARN", "")
AGENT_HTTP_URL = os.getenv("AGENT_HTTP_URL", "").rstrip("/")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not AGENT_ARN and not AGENT_HTTP_URL:
    raise ValueError("Set AGENT_ARN or AGENT_HTTP_URL")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        user_info = extract_user_info(event)
        logger.info("Request from user: %s", user_info.get("username", "unknown"))

        body = parse_request_body(event)

        if AGENT_HTTP_URL:
            return invoke_via_http(body, context)
        return invoke_via_bedrock(body, context, user_info)
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        return create_error_response(500, f"Internal server error: {str(e)}")


def invoke_via_http(body: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Invoke agent via HTTP (Agent Core /invocations endpoint)."""
    session_id = body.get("sessionId") or body.get("session_id") or f"lambda-{context.aws_request_id}"
    payload = {
        "prompt": body.get("prompt") or body.get("inputText") or body.get("input"),
        "sessionId": session_id,
        "session_id": session_id,
        "human_in_loop": body.get("humanInLoop") or body.get("human_in_loop"),
    }
    if body.get("resume") is not None:
        payload["resume"] = body["resume"]
    if body.get("humanDecision") is not None:
        payload["human_decision"] = body["humanDecision"]

    url = f"{AGENT_HTTP_URL}/invocations" if not AGENT_HTTP_URL.endswith("/invocations") else AGENT_HTTP_URL
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return create_success_response(data)


def invoke_via_bedrock(body: Dict[str, Any], context: Any, user_info: Dict[str, str]) -> Dict[str, Any]:
    """Invoke via Bedrock Agent Runtime (fallback)."""
    import boto3
    from botocore.exceptions import ClientError

    if not AGENT_ARN:
        return create_error_response(500, "AGENT_ARN not set; use AGENT_HTTP_URL for Agent Core")

    input_text = body.get("prompt") or body.get("inputText") or body.get("input")
    if not input_text and body.get("resume") is None:
        return create_error_response(400, "Missing prompt or inputText")

    session_id = body.get("sessionId") or body.get("session_id") or f"lambda-{context.aws_request_id}"

    payload = {
        "prompt": input_text,
        "sessionId": session_id,
        "human_in_loop": body.get("humanInLoop"),
    }
    if body.get("resume") is not None:
        payload["resume"] = body["resume"]
    if body.get("humanDecision") is not None:
        payload["human_decision"] = body["humanDecision"]

    client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
    try:
        resp = client.invoke_agent(
            agentId=AGENT_ARN.split("/")[-1] if "/" in AGENT_ARN else AGENT_ARN,
            agentAliasId="TSTALIASID",
            sessionId=session_id,
            inputText=input_text or "",
        )
    except ClientError as e:
        logger.error("Bedrock error: %s", str(e))
        return create_error_response(500, str(e))

    output_parts = []
    for event_stream in resp.get("completion", []):
        if "chunk" in event_stream:
            chunk = event_stream["chunk"]
            if "bytes" in chunk:
                output_parts.append(chunk["bytes"].decode("utf-8"))
            elif "text" in chunk:
                output_parts.append(chunk["text"])

    output_text = "".join(output_parts)
    try:
        data = json.loads(output_text) if output_text.strip().startswith("{") else {"output": output_text}
    except json.JSONDecodeError:
        data = {"output": output_text}

    return create_success_response({
        **data,
        "sessionId": session_id,
        "user": user_info.get("username", "unknown"),
    })


def extract_user_info(event: Dict[str, Any]) -> Dict[str, str]:
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        return {
            "user_id": claims.get("sub", "unknown"),
            "username": claims.get("cognito:username") or claims.get("username", "unknown"),
            "email": claims.get("email", "unknown"),
        }
    except Exception as e:
        logger.warning("Could not extract user info: %s", e)
        return {"user_id": "unknown", "username": "unknown", "email": "unknown"}


def parse_request_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"inputText": body}
    return body if isinstance(body, dict) else {}


def create_success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": cors_headers(),
        "body": json.dumps(data),
    }


def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": cors_headers(),
        "body": json.dumps({"error": message, "statusCode": status_code}),
    }


def cors_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }
