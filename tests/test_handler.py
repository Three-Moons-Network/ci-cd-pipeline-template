"""
Tests for the Lambda handler.

Uses mocking to avoid real Anthropic API calls during CI.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.handler import (
    ProcessRequest,
    lambda_handler,
    process_request,
    validate_request,
)


# ---------------------------------------------------------------------------
# validate_request
# ---------------------------------------------------------------------------


class TestValidateRequest:
    def test_valid_echo_task(self):
        req = validate_request(
            {
                "task_type": "echo",
                "payload": {"message": "hello"},
            }
        )
        assert req.task_type == "echo"
        assert req.payload == {"message": "hello"}

    def test_valid_analyze_task(self):
        req = validate_request(
            {
                "task_type": "analyze",
                "payload": {"data": [1, 2, 3]},
            }
        )
        assert req.task_type == "analyze"

    def test_missing_task_type_raises(self):
        with pytest.raises(ValueError, match="task_type"):
            validate_request({"task_type": "", "payload": {}})

    def test_missing_payload_defaults_to_empty_dict(self):
        req = validate_request({"task_type": "echo"})
        assert req.payload == {}

    def test_invalid_payload_type_raises(self):
        with pytest.raises(ValueError, match="payload"):
            validate_request({"task_type": "echo", "payload": "not a dict"})

    def test_task_type_is_lowercased(self):
        req = validate_request(
            {
                "task_type": "ECHO",
                "payload": {},
            }
        )
        assert req.task_type == "echo"


# ---------------------------------------------------------------------------
# process_request
# ---------------------------------------------------------------------------


class TestProcessRequest:
    def test_echo_task_returns_success(self):
        req = ProcessRequest(
            task_type="echo",
            payload={"test": "data"},
        )
        result = process_request(req)

        assert result.success is True
        assert result.environment in ("dev", "staging", "prod")
        assert result.latency_ms > 0
        assert result.model is None
        assert result.usage is None

    def test_echo_task_echoes_payload(self):
        req = ProcessRequest(
            task_type="echo",
            payload={"key": "value"},
        )
        result = process_request(req)

        assert result.success is True
        assert isinstance(result.result, dict)
        assert result.result["echoed_payload"]["key"] == "value"

    @patch("src.handler.anthropic.Anthropic")
    def test_analyze_task_calls_claude(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Analysis result")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        req = ProcessRequest(
            task_type="analyze",
            payload={"text": "analyze me"},
        )
        result = process_request(req)

        assert result.success is True
        assert result.result == "Analysis result"
        assert result.model == "claude-sonnet-4-20250514"
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50

    def test_unknown_task_type_returns_failure(self):
        req = ProcessRequest(
            task_type="unknown",
            payload={},
        )
        result = process_request(req)

        assert result.success is False
        assert "Unknown task_type" in result.result


# ---------------------------------------------------------------------------
# lambda_handler
# ---------------------------------------------------------------------------


class TestLambdaHandler:
    def test_valid_echo_request_returns_200(self):
        event = {
            "body": json.dumps(
                {
                    "task_type": "echo",
                    "payload": {"msg": "test"},
                }
            ),
            "path": "/process",
            "httpMethod": "POST",
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "application/json"

        body = json.loads(result["body"])
        assert body["success"] is True

    def test_invalid_json_returns_400(self):
        event = {"body": "not json {{{"}
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    def test_missing_task_type_returns_400(self):
        event = {
            "body": json.dumps(
                {
                    "task_type": "",
                    "payload": {},
                }
            ),
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_cors_headers_present_in_response(self):
        event = {
            "body": json.dumps(
                {
                    "task_type": "echo",
                    "payload": {},
                }
            ),
        }

        result = lambda_handler(event, None)
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"

    @patch("src.handler.anthropic.Anthropic")
    def test_successful_analyze_request(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Analyzed")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        event = {
            "body": json.dumps(
                {
                    "task_type": "analyze",
                    "payload": {"data": "test"},
                }
            ),
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200

        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["result"] == "Analyzed"

    def test_body_as_dict_is_handled(self):
        """API Gateway v2 may pass body as already-parsed dict."""
        event = {
            "body": {
                "task_type": "echo",
                "payload": {"x": 1},
            },
        }

        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["success"] is True

    def test_missing_body_defaults_to_empty_json(self):
        event = {"path": "/process"}

        result = lambda_handler(event, None)
        assert result["statusCode"] == 400
