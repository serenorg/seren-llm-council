"""ABOUTME: Configuration helpers for Seren LLM Council backend.
ABOUTME: Loads council roster and runtime settings from environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class CouncilMember:
    """Represents a single council model configuration."""

    def __init__(self, name: str, publisher_id: str, model: str):
        self.name = name
        self.publisher_id = publisher_id
        self.model = model


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    council_wallet: str = Field(..., description="Council service wallet address")
    x402_gateway_url: str = Field(..., description="x402 gateway base URL")

    claude_publisher_id: str
    openai_publisher_id: str
    moonshot_publisher_id: str
    gemini_publisher_id: str
    perplexity_publisher_id: str

    default_chairman: str = "claude-opus-4.5"
    min_responses_required: int = 3
    retry_attempts: int = 1
    request_timeout_seconds: int = 120
    flat_fee_usd: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    def get_council_members(self) -> list[CouncilMember]:
        members = [
            CouncilMember("claude", self.claude_publisher_id, "claude-sonnet-4-5-20241022"),
            CouncilMember("gpt5", self.openai_publisher_id, "gpt-5"),
            CouncilMember("kimi", self.moonshot_publisher_id, "kimi-k2"),
            CouncilMember("gemini", self.gemini_publisher_id, "gemini-2.5-pro"),
            CouncilMember("sonar", self.perplexity_publisher_id, "sonar"),
        ]
        self._validate_member_models(members)
        return members

    def _validate_member_models(self, members: list[CouncilMember]) -> None:
        expected_models = {
            "claude": "claude-sonnet-4-5-20241022",
            "gpt5": "gpt-5",
            "kimi": "kimi-k2",
            "gemini": "gemini-2.5-pro",
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
        return CouncilMember("chairman", self.claude_publisher_id, model_name)


settings = Settings()
