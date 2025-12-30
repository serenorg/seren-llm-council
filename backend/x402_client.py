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
    rankings: Optional[list[str]] = None


class X402ClientError(Exception):
    """Base exception for x402 client failures."""


class PaymentRequiredError(X402ClientError):
    """Raised when upstream gateway indicates insufficient funds."""


class X402Client:
    """Async helper that communicates with Seren's x402 gateway."""

    def __init__(self, caller_wallet: str) -> None:
        self.gateway_url = settings.x402_gateway_url
        self.caller_wallet = caller_wallet
        self.timeout = settings.request_timeout_seconds
        self.retry_attempts = settings.retry_attempts
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Payment-Delegation": "true",
        }

    def _get_proxy_url(self) -> str:
        return f"{self.gateway_url}/api/proxy"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_payload(
        self,
        member: CouncilMember,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict:
        if member.api_format == "anthropic":
            messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
            payload: dict = {
                "model": member.model,
                "messages": messages,
                "max_tokens": 4096,
            }
            if system_prompt:
                payload["system"] = system_prompt
            return payload
        else:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            return {"model": member.model, "messages": messages}

    def _parse_response(self, member: CouncilMember, body: dict) -> str:
        if member.api_format == "anthropic":
            return body["content"][0]["text"]
        else:
            return body["choices"][0]["message"]["content"]

    def _build_gateway_request(
        self,
        member: CouncilMember,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Build the x402 gateway proxy request envelope."""
        llm_payload = self._build_payload(member, prompt, system_prompt)
        return {
            "publisherId": member.publisher_id,
            "agentWallet": self.caller_wallet,
            "request": {
                "method": "POST",
                "path": member.endpoint_path,
                "body": llm_payload,
            },
        }

    async def query_model(
        self,
        member: CouncilMember,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        gateway_request = self._build_gateway_request(member, prompt, system_prompt)
        url = self._get_proxy_url()

        last_error: Optional[str] = None
        for attempt in range(self.retry_attempts + 1):
            try:
                client = await self._get_client()
                response = await client.post(url, headers=self._get_headers(), json=gateway_request)

                if response.status_code == 402:
                    raise PaymentRequiredError(f"Insufficient balance for {member.name}")

                response.raise_for_status()
                body = response.json()
                content = self._parse_response(member, body)
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
