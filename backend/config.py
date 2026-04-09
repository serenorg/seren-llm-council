"""ABOUTME: Configuration helpers for Seren LLM Council backend.
ABOUTME: Loads council roster and runtime settings from environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class CouncilMember:
    """Represents a single council model configuration."""

    def __init__(
        self,
        name: str,
        slug: str,
        model: str,
        endpoint_path: str = "/chat/completions",
        api_format: str = "openai",
    ):
        self.name = name
        self.slug = slug
        self.model = model
        self.endpoint_path = endpoint_path
        self.api_format = api_format  # "openai" or "anthropic"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    x402_gateway_url: str = Field(..., description="Seren gateway base URL")
    seren_api_key: str = Field(..., description="API key for Seren gateway")

    default_chairman: str = "claude-opus-4-5"
    min_responses_required: int = 3
    retry_attempts: int = 1
    request_timeout_seconds: int = 120
    flat_fee_usd: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def get_council_members(self) -> list[CouncilMember]:
        members = [
            CouncilMember(
                "claude",
                "anthropic-claude-api",
                "claude-sonnet-4-5",
                endpoint_path="/messages",
                api_format="anthropic",
            ),
            CouncilMember("gpt5", "openai", "gpt-5.2"),
            CouncilMember("kimi", "moonshot-ai", "kimi-k2-0711-preview"),
            CouncilMember("gemini", "google-gemini-3", "google/gemini-3-pro-preview"),
            CouncilMember("sonar", "perplexity", "sonar"),
        ]
        self._validate_member_models(members)
        return members

    def _validate_member_models(self, members: list[CouncilMember]) -> None:
        expected_models = {
            "claude": "claude-sonnet-4-5",
            "gpt5": "gpt-5.2",
            "kimi": "kimi-k2-0711-preview",
            "gemini": "google/gemini-3-pro-preview",
            "sonar": "sonar",
        }
        for member in members:
            expected = expected_models.get(member.name)
            if expected and member.model != expected:
                raise ValueError(
                    f"Model mismatch for {member.name}: expected {expected}, got {member.model}"
                )

    def get_chairman_config(self, chairman_override: Optional[str] = None) -> CouncilMember:
        model_name = chairman_override or self.default_chairman

        if model_name.startswith("claude"):
            return CouncilMember(
                "chairman",
                "anthropic-claude-api",
                model_name,
                endpoint_path="/messages",
                api_format="anthropic",
            )
        elif model_name.startswith("gpt"):
            return CouncilMember(
                "chairman",
                "openai",
                model_name,
                endpoint_path="/chat/completions",
            )
        else:
            return CouncilMember(
                "chairman",
                "anthropic-claude-api",
                model_name,
                endpoint_path="/messages",
                api_format="anthropic",
            )


settings = Settings()
