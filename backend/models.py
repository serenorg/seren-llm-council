"""ABOUTME: Pydantic models for council API contracts.
ABOUTME: Provides request, response, and metadata schemas."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class CouncilQuery(BaseModel):
    """Incoming payload for council queries."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="User query for the council")
    chairman: Optional[str] = Field(default=None, description="Optional chairman override")

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Query must not be empty")
        return stripped


class Stage1ResponseModel(BaseModel):
    """Normalized stage 1 response."""

    model_config = ConfigDict(extra="forbid")

    model: str
    content: str
    success: bool = True
    error: Optional[str] = None


class Stage2CritiqueModel(BaseModel):
    """Stage 2 critique payload per model."""

    model_config = ConfigDict(extra="forbid")

    model: str
    analysis: str
    rankings: List[str] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class CouncilMetadata(BaseModel):
    """Metadata about the council run."""

    model_config = ConfigDict(extra="forbid")

    models_succeeded: List[str]
    models_failed: List[str]
    chairman: str
    cost_usd: float
    duration_ms: int


class CouncilResponse(BaseModel):
    """Response object returned to callers."""

    model_config = ConfigDict(extra="forbid")

    final_answer: str
    stage1_responses: Dict[str, Stage1ResponseModel]
    stage2_critiques: Dict[str, Stage2CritiqueModel]
    metadata: CouncilMetadata
