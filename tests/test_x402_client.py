"""ABOUTME: Tests for x402 HTTP client behaviors.
ABOUTME: Covers success, payment errors, and parallel queries."""

from importlib import reload
from types import ModuleType
from unittest.mock import patch
import os
import pytest
from httpx import Response


def _load_modules(env: dict) -> tuple[ModuleType, ModuleType]:
    with patch.dict(os.environ, env, clear=True):
        import backend.config as config_module
        reload(config_module)

        import backend.x402_client as client_module
        reload(client_module)

        return config_module, client_module


@pytest.fixture()
def env_values() -> dict:
    return {
        "COUNCIL_WALLET": "0xtest",
        "X402_GATEWAY_URL": "https://x402.serendb.com",
        "CLAUDE_PUBLISHER_ID": "claude-id",
        "OPENAI_PUBLISHER_ID": "openai-id",
        "MOONSHOT_PUBLISHER_ID": "moonshot-id",
        "GEMINI_PUBLISHER_ID": "gemini-id",
        "PERPLEXITY_PUBLISHER_ID": "perplexity-id",
        "RETRY_ATTEMPTS": "1",
    }


@pytest.mark.asyncio()
async def test_query_model_success(env_values, respx_mock):
    config_module, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    member = config_module.settings.get_council_members()[0]

    route = respx_mock.post(
        "https://x402.serendb.com/api/proxy/claude-id/v1/chat/completions"
    ).mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": "Hello from Claude"}}]
        })
    )

    result = await client.query_model(member, "Hello?")

    assert route.called
    assert result.success is True
    assert result.content == "Hello from Claude"


@pytest.mark.asyncio()
async def test_query_model_payment_error(env_values, respx_mock):
    _, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    member = client_module.CouncilMember("test", "claude-id", "claude")

    respx_mock.post(
        "https://x402.serendb.com/api/proxy/claude-id/v1/chat/completions"
    ).mock(return_value=Response(402))

    with pytest.raises(client_module.PaymentRequiredError):
        await client.query_model(member, "Hello?")


@pytest.mark.asyncio()
async def test_query_models_parallel_collects_results(env_values, respx_mock):
    config_module, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    members = config_module.settings.get_council_members()[:2]

    for member in members:
        respx_mock.post(
            f"https://x402.serendb.com/api/proxy/{member.publisher_id}/v1/chat/completions"
        ).mock(
            return_value=Response(200, json={
                "choices": [{"message": {"content": f"Reply from {member.name}"}}]
            })
        )

    results = await client.query_models_parallel(members, "Discuss")

    assert len(results) == 2
    assert all(r.success for r in results)
    assert {r.model_name for r in results} == {m.name for m in members}
