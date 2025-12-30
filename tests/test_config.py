"""ABOUTME: Tests for backend configuration settings.
ABOUTME: Validates council roster helpers and overrides."""

from importlib import reload
from types import ModuleType
from unittest.mock import patch
import os
import pytest


@pytest.fixture()
def base_env() -> dict:
    return {
        "COUNCIL_WALLET": "0xtest",
        "X402_GATEWAY_URL": "https://test.example.com",
        "CLAUDE_PUBLISHER_ID": "claude-id",
        "OPENAI_PUBLISHER_ID": "openai-id",
        "MOONSHOT_PUBLISHER_ID": "moonshot-id",
        "GEMINI_PUBLISHER_ID": "gemini-id",
        "PERPLEXITY_PUBLISHER_ID": "perplexity-id",
    }


def _load_config(env: dict) -> ModuleType:
    with patch.dict(os.environ, env, clear=True):
        import backend.config as config_module

        reload(config_module)
        return config_module


def test_settings_load_required_fields(base_env):
    config_module = _load_config(base_env)

    assert config_module.settings.council_wallet == "0xtest"
    assert config_module.settings.x402_gateway_url == "https://test.example.com"


def test_get_council_members_returns_five(base_env):
    config_module = _load_config(base_env)

    members = config_module.settings.get_council_members()
    assert len(members) == 5
    assert members[0].name == "claude"
    assert members[-1].name == "sonar"


def test_get_chairman_respects_override(base_env):
    config_module = _load_config(base_env)

    chairman = config_module.settings.get_chairman_config("gpt-5")
    assert chairman.model == "gpt-5"
    assert chairman.name == "chairman"
