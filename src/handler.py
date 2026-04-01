"""
Example Lambda Handler for CI/CD Pipeline Template

This is a sample handler that demonstrates a typical pattern for the pipeline:
- Receives an HTTP request from API Gateway
- Processes the request (can integrate with Claude, databases, etc.)
- Returns a structured response
- All infrastructure deployed via Terraform with staging and prod environments

In production, customize this handler to implement your specific business logic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

import anthropic

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ProcessRequest:
    """Validated inbound request."""
    task_type: str
    payload: dict[str, Any]


@dataclass
class ProcessResponse:
    """Structured outbound response."""
    success: bool
    result: str | dict[str, Any]
    environment: str
    model: str | None
    latency_ms: int
    usage: dict[str, int] | None = None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def validate_request(body: dict[str, Any]) -> ProcessRequest:
    """Parse and validate the incoming request body."""
    task_type = body.get("task_type", "").strip().lower()
    if not task_type:
        raise ValueError("'task_type' is required and cannot be empty")

    payload = body.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("'payload' must be a JSON object")

    return ProcessRequest(task_type=task_type, payload=payload)


def process_with_claude(request: ProcessRequest) -> tuple[str, dict[str, int], str]:
    """
    Example: Call Claude for inference.
    Customize this based on your business logic.
    """
    client = anthropic.Anthropic()

    system_prompt = "You are a helpful assistant processing structured data."
    user_message = json.dumps(request.payload, indent=2)

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    result_text = response.content[0].text
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    return result_text, usage, response.model


def process_request(request: ProcessRequest) -> ProcessResponse:
    """
    Route the request to the appropriate handler.
    Expand this with domain-specific logic.
    """
    start = time.monotonic()

    try:
        if request.task_type == "echo":
            # Simple echo handler — no Claude call
            result = {"echoed_payload": request.payload, "environment": ENVIRONMENT}
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProcessResponse(
                success=True,
                result=result,
                environment=ENVIRONMENT,
                model=None,
                latency_ms=latency_ms,
                usage=None,
            )

        elif request.task_type == "analyze":
            # Example: Use Claude for analysis
            result_text, usage, model = process_with_claude(request)
            latency_ms = int((time.monotonic() - start) * 1000)
            return ProcessResponse(
                success=True,
                result=result_text,
                environment=ENVIRONMENT,
                model=model,
                latency_ms=latency_ms,
                usage=usage,
            )

        else:
            raise ValueError(
                f"Unknown task_type '{request.task_type}'. "
                "Supported: echo, analyze"
            )

    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error("Processing failed", extra={"error": str(exc)})
        return ProcessResponse(
            success=False,
            result=f"Processing error: {str(exc)}",
            environment=ENVIRONMENT,
            model=None,
            latency_ms=latency_ms,
            usage=None,
        )


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context: Any) -> dict:
    """
    AWS Lambda handler for API Gateway HTTP API.

    Expects a JSON body with:
      - task_type: str — the type of task to perform
      - payload:   dict — the request data

    Returns:
      - 200 with ProcessResponse JSON on success
      - 400 on validation errors
      - 500 on unexpected failures
    """
    logger.info(
        "Received event",
        extra={
            "path": event.get("path"),
            "method": event.get("httpMethod"),
            "environment": ENVIRONMENT,
        },
    )

    try:
        # Parse body — API Gateway may pass string or dict
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        request = validate_request(body)
        result = process_request(request)

        status_code = 200 if result.success else 400

        logger.info(
            "Task completed",
            extra={
                "success": result.success,
                "environment": ENVIRONMENT,
                "latency_ms": result.latency_ms,
            },
        )

        response_dict = asdict(result)
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response_dict),
        }

    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Validation error", extra={"error": str(exc)})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }

    except Exception:
        logger.exception("Unexpected error")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"}),
        }
