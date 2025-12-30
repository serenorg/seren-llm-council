"""ABOUTME: Tests for Pydantic API models.
ABOUTME: Ensures validation and serialization rules."""

import pytest
from pydantic import ValidationError

from backend import models


def test_council_query_strips_whitespace():
    payload = models.CouncilQuery(query="  hello world  ")
    assert payload.query == "hello world"


def test_council_query_requires_text():
    with pytest.raises(ValidationError):
        models.CouncilQuery(query="   ")


def test_council_response_accepts_nested_models():
    response = models.CouncilResponse(
        final_answer="Result",
        stage1_responses={
            "claude": models.Stage1ResponseModel(
                model="claude", content="Opinion", success=True
            )
        },
        stage2_critiques={
            "claude": models.Stage2CritiqueModel(
                model="claude", analysis="Looks good", rankings=["claude"], success=True
            )
        },
        metadata=models.CouncilMetadata(
            models_succeeded=["claude"],
            models_failed=[],
            chairman="claude-opus-4.5",
        ),
    )

    assert response.metadata.chairman == "claude-opus-4.5"
    assert response.stage1_responses["claude"].content == "Opinion"

