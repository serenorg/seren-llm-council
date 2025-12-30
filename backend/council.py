"""ABOUTME: Council orchestration logic across three stages.
ABOUTME: Coordinates x402 requests and aggregates deliberation results."""

from __future__ import annotations

import asyncio
from typing import List, Optional

from backend.config import CouncilMember, settings
from backend.models import (
    CouncilMetadata,
    CouncilResponse,
    Stage1ResponseModel,
    Stage2CritiqueModel,
)
from backend.x402_client import LLMResponse, PaymentRequiredError, X402Client

STAGE1_SYSTEM_PROMPT = (
    "You are a council member. Provide your best independent answer to the question."
)
STAGE2_PROMPT_TEMPLATE = (
    "You are critiquing peer responses to the question: {query}.\n\n"
    "Here are the anonymous responses:\n{responses}\n\n"
    "Provide a ranked list of the top responses and point out mistakes."
)
STAGE3_PROMPT_TEMPLATE = (
    "You are the chairman synthesizing all insights.\nQuestion: {query}\n\n"
    "Stage 1 responses:\n{responses}\n\nStage 2 critiques:\n{critiques}\n\n"
    "Write a final, well-structured answer referencing the best ideas."
)


def _summarize_stage1(responses: List[LLMResponse]) -> str:
    lines = []
    for idx, response in enumerate(responses, start=1):
        status = response.content if response.success else f"ERROR: {response.error or 'unknown'}"
        lines.append(f"Response {idx} ({response.model_name}): {status}")
    return "\n".join(lines)


def _summarize_stage2(responses: List[LLMResponse]) -> str:
    lines = []
    for idx, response in enumerate(responses, start=1):
        status = response.content if response.success else f"ERROR: {response.error or 'unknown'}"
        lines.append(f"Critique {idx} ({response.model_name}): {status}")
    return "\n".join(lines)


class CouncilService:
    """Coordinates the three-stage council deliberation."""

    def __init__(self, client: Optional[X402Client] = None) -> None:
        self.client = client or X402Client()
        self.settings = settings

    async def stage1_opinions(self, query: str) -> List[LLMResponse]:
        members = self.settings.get_council_members()
        return await self.client.query_models_parallel(
            members,
            prompt=query,
            system_prompt=STAGE1_SYSTEM_PROMPT,
        )

    async def stage2_critiques(
        self,
        query: str,
        stage1_responses: List[LLMResponse],
    ) -> List[LLMResponse]:
        members = self.settings.get_council_members()
        stage1_summary = _summarize_stage1(stage1_responses)

        async def _critique(member: CouncilMember) -> LLMResponse:
            prompt = STAGE2_PROMPT_TEMPLATE.format(query=query, responses=stage1_summary)
            return await self.client.query_model(member, prompt)

        tasks = [_critique(member) for member in members]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized: List[LLMResponse] = []
        for member, result in zip(members, raw_results):
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

    async def stage3_synthesis(
        self,
        query: str,
        stage1_responses: List[LLMResponse],
        stage2_responses: List[LLMResponse],
        chairman: Optional[CouncilMember] = None,
    ) -> LLMResponse:
        chair = chairman or self.settings.get_chairman_config()
        prompt = STAGE3_PROMPT_TEMPLATE.format(
            query=query,
            responses=_summarize_stage1(stage1_responses),
            critiques=_summarize_stage2(stage2_responses),
        )
        result = await self.client.query_model(chair, prompt)
        if not result.success:
            raise RuntimeError("Chairman failed to synthesize response")
        return result

    async def run_council(self, query: str, chairman: Optional[str] = None) -> CouncilResponse:
        stage1 = await self.stage1_opinions(query)
        success_count = sum(1 for response in stage1 if response.success)
        if success_count < self.settings.min_responses_required:
            raise RuntimeError("Insufficient successful council responses")

        stage2 = await self.stage2_critiques(query, stage1)
        chairman_member = self.settings.get_chairman_config(chairman)
        final = await self.stage3_synthesis(query, stage1, stage2, chairman_member)

        stage1_payload = {
            response.model_name: Stage1ResponseModel(
                model=response.model_name,
                content=response.content,
                success=response.success,
                error=response.error,
            )
            for response in stage1
        }
        stage2_payload = {
            response.model_name: Stage2CritiqueModel(
                model=response.model_name,
                analysis=response.content,
                rankings=[],
                success=response.success,
                error=response.error,
            )
            for response in stage2
        }
        metadata = CouncilMetadata(
            models_succeeded=[response.model_name for response in stage1 if response.success],
            models_failed=[response.model_name for response in stage1 if not response.success],
            chairman=chairman_member.model,
        )

        return CouncilResponse(
            final_answer=final.content,
            stage1_responses=stage1_payload,
            stage2_critiques=stage2_payload,
            metadata=metadata,
        )


async def run_council(query: str, chairman: Optional[str] = None) -> CouncilResponse:
    service = CouncilService()
    return await service.run_council(query, chairman=chairman)

