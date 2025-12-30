"""ABOUTME: Integration-style tests for FastAPI + council service.
ABOUTME: Ensures dependency graph works end-to-end with fake client."""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("COUNCIL_WALLET", "0xtest")
os.environ.setdefault("X402_GATEWAY_URL", "https://x402.test")
os.environ.setdefault("CLAUDE_PUBLISHER_ID", "claude-id")
os.environ.setdefault("OPENAI_PUBLISHER_ID", "openai-id")
os.environ.setdefault("MOONSHOT_PUBLISHER_ID", "moonshot-id")
os.environ.setdefault("GEMINI_PUBLISHER_ID", "gemini-id")
os.environ.setdefault("PERPLEXITY_PUBLISHER_ID", "perplexity-id")

from backend.council import CouncilService
from backend.main import app, get_council_service
from backend.x402_client import LLMResponse


class FakeX402Client:
    def __init__(self):
        self.stage1_counter = 0

    async def query_models_parallel(self, members, prompt, system_prompt=None):
        self.stage1_counter += 1
        return [
            LLMResponse(model_name=member.name, content=f"Opinion {member.name}", success=True)
            for member in members
        ]

    async def query_model(self, member, prompt, system_prompt=None):
        content = f"{member.name} finalizes" if member.name == "chairman" else f"Critique {member.name}"
        return LLMResponse(model_name=member.name, content=content, success=True)


@pytest.fixture(autouse=True)
def clean_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_full_stack_query_flow():
    service = CouncilService(client=FakeX402Client())
    app.dependency_overrides[get_council_service] = lambda: service
    client = TestClient(app)

    response = client.post("/v1/council/query", json={"query": "Explain AI"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["final_answer"] == "chairman finalizes"
    assert len(payload["stage1_responses"]) == 5

