"""ABOUTME: Async client for querying LLM publishers via x402.
ABOUTME: Handles retries, payment errors, and parallel fan-out."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.config import CouncilMember, settings


@dataclass
class LLMResponse:
    """Normalized response payload from a council member."""

    model_name: str
    content: str
    success: bool
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class X402ClientError(Exception):
    """Base exception for x402 client failures."""


class PaymentRequiredError(X402ClientError):
    """Raised when upstream gateway indicates insufficient funds."""


class X402Client:
    """Async helper that communicates with Seren's x402 gateway."""

    def __init__(self) -> None:
        self.gateway_url = settings.x402_gateway_url
        self.wallet = settings.council_wallet
        self.timeout = settings.request_timeout_seconds
        self.retry_attempts = settings.retry_attempts

    def _get_headers(self) -> dict[str, str]:
        return {
            "X-AGENT-WALLET": self.wallet,
            "X-Payment-Delegation": "true",
            "Content-Type": "application/json",
        }

    def _build_url(self, publisher_id: str) -> str:
        return f"{self.gateway_url}/api/proxy/{publisher_id}/v1/chat/completions"

    async def query_model(
        self,
        member: CouncilMember,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": member.model, "messages": messages}
        url = self._build_url(member.publisher_id)

        last_error: Optional[str] = None
        for attempt in range(self.retry_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=self._get_headers(), json=payload)

                if response.status_code == 402:
                    raise PaymentRequiredError(f"Insufficient balance for {member.name}")

                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return LLMResponse(
                    model_name=member.name,
                    content=content,
                    success=True,
                    raw_response=body,
                )
            except PaymentRequiredError:
                raise
            except Exception as exc:  # pragma: no cover - string conversion is trivial
                last_error = str(exc)
                if attempt < self.retry_attempts:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue

        return LLMResponse(
            model_name=member.name,
            content="",
            success=False,
            error=last_error,
        )

    async def query_models_parallel(
        self,
        members: list[CouncilMember],
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> list[LLMResponse]:
        tasks = [self.query_model(member, prompt, system_prompt) for member in members]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized: list[LLMResponse] = []
        for member, result in zip(members, results):
            if isinstance(result, PaymentRequiredError):
                raise result
            if isinstance(result, Exception):
                normalized.append(
                    LLMResponse(
                        model_name=member.name,
                        content="",
                        success=False,
                        error=str(result),
                    )
                )
            else:
                normalized.append(result)

        return normalized

