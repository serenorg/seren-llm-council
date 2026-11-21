"""ABOUTME: FastAPI entrypoint for Seren LLM Council service.
ABOUTME: Exposes health and council query endpoints."""

import hmac
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException

from backend.config import settings
from backend.council import CouncilService
from backend.models import CouncilQuery, CouncilResponse
from backend.x402_client import PaymentRequiredError

app = FastAPI(title="Seren LLM Council", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def require_origin_secret(
    x_council_origin_secret: Optional[str] = Header(None, alias="X-Council-Origin-Secret"),
) -> None:
    """Refuses a query that does not carry the secret the Seren publisher sends."""
    supplied = (x_council_origin_secret or "").encode()
    if not hmac.compare_digest(supplied, settings.council_origin_secret.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post(
    "/v1/council/query",
    response_model=CouncilResponse,
    dependencies=[Depends(require_origin_secret)],
)
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
