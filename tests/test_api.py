"""ABOUTME: FastAPI route tests for council service.
ABOUTME: Validates success and error responses."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("X402_GATEWAY_URL", "https://x402.serendb.com")
os.environ.setdefault("CLAUDE_PUBLISHER_ID", "claude-id")
os.environ.setdefault("OPENAI_PUBLISHER_ID", "openai-id")
os.environ.setdefault("MOONSHOT_PUBLISHER_ID", "moonshot-id")
os.environ.setdefault("GEMINI_PUBLISHER_ID", "gemini-id")
os.environ.setdefault("PERPLEXITY_PUBLISHER_ID", "perplexity-id")

from backend import models
from backend.main import app
from backend.x402_client import PaymentRequiredError


def _sample_response() -> models.CouncilResponse:
    return models.CouncilResponse(
        final_answer="Final",
        stage1_responses={
            "claude": models.Stage1ResponseModel(
                model="claude", content="Opinion", success=True
            )
        },
        stage2_critiques={
            "claude": models.Stage2CritiqueModel(
                model="claude", analysis="Critique", rankings=["claude"], success=True
            )
        },
        metadata=models.CouncilMetadata(
            models_succeeded=["claude"],
            models_failed=[],
            chairman="claude-opus-4.5",
            cost_usd=15.0,
            duration_ms=42,
        ),
    )


def test_query_endpoint_returns_response():
    client = TestClient(app)
    mock_response = _sample_response()

    with patch("backend.main.CouncilService") as mock_cls:
        mock_service = AsyncMock()
        mock_service.run_council.return_value = mock_response
        mock_cls.return_value = mock_service

        response = client.post(
            "/v1/council/query",
            json={"query": "Help"},
            headers={"X-AGENT-WALLET": "0xtest"},
        )

    assert response.status_code == 200
    assert response.json()["final_answer"] == "Final"
    mock_cls.assert_called_once_with(caller_wallet="0xtest")


def test_query_endpoint_handles_payment_error():
    client = TestClient(app)

    with patch("backend.main.CouncilService") as mock_cls:
        mock_service = AsyncMock()
        mock_service.run_council.side_effect = PaymentRequiredError("Insufficient balance")
        mock_cls.return_value = mock_service

        response = client.post(
            "/v1/council/query",
            json={"query": "Help"},
            headers={"X-AGENT-WALLET": "0xtest"},
        )

    assert response.status_code == 402
    assert response.json()["detail"] == "Insufficient balance"


def test_query_endpoint_requires_wallet_header():
    client = TestClient(app)

    response = client.post("/v1/council/query", json={"query": "Help"})

    assert response.status_code == 422
    assert "x-agent-wallet" in response.text.lower()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
