"""ABOUTME: FastAPI route tests for council service.
ABOUTME: Validates success and error responses."""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("COUNCIL_WALLET", "0xtest")
os.environ.setdefault("X402_GATEWAY_URL", "https://x402.serendb.com")
os.environ.setdefault("CLAUDE_PUBLISHER_ID", "claude-id")
os.environ.setdefault("OPENAI_PUBLISHER_ID", "openai-id")
os.environ.setdefault("MOONSHOT_PUBLISHER_ID", "moonshot-id")
os.environ.setdefault("GEMINI_PUBLISHER_ID", "gemini-id")
os.environ.setdefault("PERPLEXITY_PUBLISHER_ID", "perplexity-id")

from backend import models
from backend.main import app, get_council_service
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


class DummyService:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result or _sample_response()
        self.error = error

    async def run_council(self, query: str, chairman: str | None = None):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def reset_dependencies():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_query_endpoint_returns_response():
    app.dependency_overrides[get_council_service] = lambda: DummyService()
    client = TestClient(app)

    response = client.post("/v1/council/query", json={"query": "Help"})

    assert response.status_code == 200
    assert response.json()["final_answer"] == "Final"


def test_query_endpoint_handles_payment_error():
    app.dependency_overrides[get_council_service] = lambda: DummyService(
        error=PaymentRequiredError("Insufficient balance")
    )
    client = TestClient(app)

    response = client.post("/v1/council/query", json={"query": "Help"})

    assert response.status_code == 402
    assert response.json()["detail"] == "Insufficient balance"


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
