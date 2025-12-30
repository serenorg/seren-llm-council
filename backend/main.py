"""ABOUTME: FastAPI entrypoint for Seren LLM Council service.
ABOUTME: Exposes health and council query endpoints."""

from fastapi import FastAPI, Header, HTTPException

from backend.council import CouncilService
from backend.models import CouncilQuery, CouncilResponse
from backend.x402_client import PaymentRequiredError

app = FastAPI(title="Seren LLM Council", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/council/query", response_model=CouncilResponse)
async def query_council(
    payload: CouncilQuery,
    x_agent_wallet: str = Header(..., alias="X-AGENT-WALLET"),
) -> CouncilResponse:
    service = CouncilService(caller_wallet=x_agent_wallet)
    try:
        return await service.run_council(payload.query, chairman=payload.chairman)
    except PaymentRequiredError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
