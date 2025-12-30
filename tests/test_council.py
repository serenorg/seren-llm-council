"""ABOUTME: Tests for council orchestration routines.
ABOUTME: Covers stage fan-out and degradation rules."""

from importlib import reload
from types import ModuleType
from unittest.mock import patch
import os
import pytest


def _load_council_modules(env: dict) -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    with patch.dict(os.environ, env, clear=True):
        import backend.config as config_module
        reload(config_module)

        import backend.models as models_module
        reload(models_module)

        import backend.x402_client as client_module
        reload(client_module)

        import backend.council as council_module
        reload(council_module)

        return config_module, models_module, client_module, council_module


class FakeClient:
    def __init__(self, llm_response_cls, failing_members: set[str] | None = None):
        self.llm_response_cls = llm_response_cls
        self.failing_members = failing_members or set()

    async def query_models_parallel(self, members, prompt, system_prompt=None):
        responses = []
        for member in members:
            if member.name in self.failing_members:
                responses.append(
                    self.llm_response_cls(
                        model_name=member.name,
                        content="",
                        success=False,
                        error="upstream error",
                    )
                )
            else:
                responses.append(
                    self.llm_response_cls(
                        model_name=member.name,
                        content=f"Opinion from {member.name}",
                        success=True,
                    )
                )
        return responses

    async def query_model(self, member, prompt, system_prompt=None):
        if member.name in self.failing_members:
            return self.llm_response_cls(
                model_name=member.name,
                content="",
                success=False,
                error="model offline",
            )
        return self.llm_response_cls(
            model_name=member.name,
            content=f"{member.name} sees: {prompt[:20]}",
            success=True,
        )


@pytest.fixture()
def env_values() -> dict:
    return {
        "COUNCIL_WALLET": "0xtest",
        "X402_GATEWAY_URL": "https://x402.test",
        "CLAUDE_PUBLISHER_ID": "claude-id",
        "OPENAI_PUBLISHER_ID": "openai-id",
        "MOONSHOT_PUBLISHER_ID": "moonshot-id",
        "GEMINI_PUBLISHER_ID": "gemini-id",
        "PERPLEXITY_PUBLISHER_ID": "perplexity-id",
        "MIN_RESPONSES_REQUIRED": "3",
    }


@pytest.mark.asyncio()
async def test_stage1_opinions_returns_five(env_values):
    config_module, _, client_module, council_module = _load_council_modules(env_values)
    service = council_module.CouncilService(client=FakeClient(client_module.LLMResponse))

    results = await service.stage1_opinions("Explain AI")

    assert len(results) == 5
    assert sum(1 for r in results if r.success) == 5


@pytest.mark.asyncio()
async def test_run_council_builds_response(env_values):
    config_module, models_module, client_module, council_module = _load_council_modules(env_values)
    service = council_module.CouncilService(client=FakeClient(client_module.LLMResponse))

    response = await service.run_council("What is AGI?", chairman="custom-chair")

    assert isinstance(response, models_module.CouncilResponse)
    assert response.final_answer
    assert set(response.stage1_responses.keys()) == {
        member.name for member in config_module.settings.get_council_members()
    }
    assert response.metadata.chairman == "custom-chair"
    assert len(response.metadata.models_succeeded) == 5


@pytest.mark.asyncio()
async def test_run_council_fails_when_not_enough_responses(env_values):
    _, _, client_module, council_module = _load_council_modules(env_values)
    failing = {"claude", "gpt5", "kimi"}
    service = council_module.CouncilService(
        client=FakeClient(client_module.LLMResponse, failing_members=failing)
    )

    with pytest.raises(RuntimeError):
        await service.run_council("Need advice")

