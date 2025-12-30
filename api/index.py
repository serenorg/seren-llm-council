"""ABOUTME: Vercel serverless entrypoint for Seren LLM Council.
ABOUTME: Wraps FastAPI app for Vercel Python runtime."""

import sys
from pathlib import Path

# Add project root to path so backend module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.main import app  # noqa: E402, F401
