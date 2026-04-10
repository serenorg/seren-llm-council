"""ABOUTME: FastAPI entrypoint for Seren LLM Council service.
ABOUTME: Exposes health and council query endpoints."""

import traceback

from fastapi import FastAPI, Header, HTTPException

from backend.council import CouncilService
from backend.models import CouncilQuery, CouncilResponse
from backend.x402_client import PaymentRequiredError, X402Client

app = FastAPI(title="Seren LLM Council", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/probe")
async def debug_probe() -> dict:
    """Temporary diagnostic: test one model call and report raw results."""
    from backend.config import settings

    info: dict = {
        "gateway_url": settings.x402_gateway_url,
        "api_key_set": bool(settings.seren_api_key),
        "api_key_prefix": settings.seren_api_key[:12] + "..." if settings.seren_api_key else None,
    }

    members = settings.get_council_members()
    info["members"] = [
        {"name": m.name, "slug": m.slug, "model": m.model, "path": m.endpoint_path}
        for m in members
    ]

    client = X402Client()
    try:
        result = await client.query_model(members[0], "Say hi")
        info["test_call"] = {
            "model": members[0].name,
            "success": result.success,
            "content": result.content[:100] if result.content else "",
            "error": result.error,
        }
    except Exception as exc:
        info["test_call"] = {
            "model": members[0].name,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        await client.aclose()

    return info


@app.post("/v1/council/query", response_model=CouncilResponse)
async def query_council(
    payload: CouncilQuery,
    x_agent_wallet: str = Header(..., alias="X-AGENT-WALLET"),
) -> CouncilResponse:
    service = CouncilService()
    try:
        return await service.run_council(payload.query, chairman=payload.chairman)
    except PaymentRequiredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
