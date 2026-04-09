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
        "X402_GATEWAY_URL": "https://api.serendb.com",
        "SEREN_API_KEY": "test-api-key",
        "RETRY_ATTEMPTS": "1",
    }


@pytest.mark.asyncio()
async def test_query_model_success(env_values, respx_mock):
    config_module, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    member = config_module.settings.get_council_members()[0]  # Claude

    route = respx_mock.post(
        "https://api.serendb.com/publishers/anthropic-claude-api/v1/messages"
    ).mock(
        return_value=Response(200, json={"content": [{"text": "Hello from Claude"}]})
    )

    result = await client.query_model(member, "Hello?")

    assert route.called
    assert result.success is True
    assert result.content == "Hello from Claude"

    request = route.calls[0].request
    assert request.headers["authorization"] == "Bearer test-api-key"
    assert "x-payment-delegation" not in request.headers


@pytest.mark.asyncio()
async def test_query_model_payment_error(env_values, respx_mock):
    _, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    member = client_module.CouncilMember(
        "test", "test-publisher", "test-model", "/v1/chat/completions", "openai"
    )

    respx_mock.post(
        "https://api.serendb.com/publishers/test-publisher/v1/chat/completions"
    ).mock(return_value=Response(402))

    with pytest.raises(client_module.PaymentRequiredError):
        await client.query_model(member, "Hello?")


@pytest.mark.asyncio()
async def test_query_models_parallel_collects_results(env_values, respx_mock):
    config_module, client_module = _load_modules(env_values)
    client = client_module.X402Client()
    members = config_module.settings.get_council_members()[:2]  # Claude and GPT5

    respx_mock.post(
        "https://api.serendb.com/publishers/anthropic-claude-api/v1/messages"
    ).mock(
        return_value=Response(200, json={"content": [{"text": "Reply from claude"}]})
    )
    respx_mock.post(
        "https://api.serendb.com/publishers/openai/v1/chat/completions"
    ).mock(
        return_value=Response(200, json={"choices": [{"message": {"content": "Reply from gpt5"}}]})
    )

    results = await client.query_models_parallel(members, "Discuss")

    assert len(results) == 2
    assert all(r.success for r in results)
    assert {r.model_name for r in results} == {m.name for m in members}
