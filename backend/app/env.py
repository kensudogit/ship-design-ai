"""Load C:\\devlop\\ship-design-ai\\.env. Never log secret values."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DEFAULT_MODEL = "gpt-4o-mini"


def openai_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAO_API_KEY") or "").strip()


def openai_model() -> str:
    return (os.getenv("OPENAI_MODEL") or DEFAULT_MODEL).strip()


def openai_configured() -> bool:
    return bool(openai_api_key())
