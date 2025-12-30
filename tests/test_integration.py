"""ABOUTME: Integration-style tests for FastAPI + council service.
ABOUTME: Ensures dependency graph works end-to-end with fake client."""

import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("X402_GATEWAY_URL", "https://x402.serendb.com")
os.environ.setdefault("CLAUDE_PUBLISHER_ID", "claude-id")
os.environ.setdefault("OPENAI_PUBLISHER_ID", "openai-id")
os.environ.setdefault("MOONSHOT_PUBLISHER_ID", "moonshot-id")
os.environ.setdefault("GEMINI_PUBLISHER_ID", "gemini-id")
os.environ.setdefault("PERPLEXITY_PUBLISHER_ID", "perplexity-id")

from backend.main import app
from backend.x402_client import LLMResponse


class FakeX402Client:
    def __init__(self, caller_wallet: str):
        self.caller_wallet = caller_wallet
        self.stage1_counter = 0

    async def query_models_parallel(self, members, prompt, system_prompt=None):
        self.stage1_counter += 1
        return [
            LLMResponse(model_name=member.name, content=f"Opinion {member.name}", success=True)
            for member in members
        ]

    async def query_model(self, member, prompt, system_prompt=None):
        if member.name == "chairman":
            content = f"{member.name} finalizes"
        elif "Return ONLY valid JSON" in prompt:
            content = json.dumps({"analysis": f"{member.name} critique", "rankings": ["R1", "R2"]})
        else:
            content = f"Critique {member.name}"
        return LLMResponse(model_name=member.name, content=content, success=True)


def test_full_stack_query_flow():
    client = TestClient(app)

    with patch("backend.council.X402Client", FakeX402Client):
        response = client.post(
            "/v1/council/query",
            json={"query": "Explain AI"},
            headers={"X-AGENT-WALLET": "0xtest"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["final_answer"] == "chairman finalizes"
    assert len(payload["stage1_responses"]) == 5
    assert payload["metadata"]["duration_ms"] >= 0
