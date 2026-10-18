"""LLM は仕様抽出と説明のみ。幾何評価・制約は engine が行う。船級判定ではない。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.env import openai_api_key, openai_model

EXTRACT_FIELDS = (
    "length_pp",
    "beam",
    "draft",
    "depth",
    "block_coefficient",
    "speed_kn",
)

SYSTEM_EXTRACT = """You extract preliminary Handymax bulk-carrier design parameters.
Return JSON only with keys: length_pp, beam, draft, depth, block_coefficient, speed_kn, notes.
Units: meters and knots. Use null when the text does not specify a value. Do not invent.
This is educational. Not for class approval, resistance, or IMO stability."""

SYSTEM_EXPLAIN = """You are a teaching assistant for preliminary ship design (geom-v3).
Explain the given evaluation JSON in Japanese for a designer.
Rules:
- Displacement volume is always Lpp × B × T × Cb. Density is 1.025 t/m³.
- Rt/Pe/Pd come from a Holtrop-1982 subset + ITTC-57. Call them 初期推定, never 試運転, CFD, or 実船馬力.
- DWT, cargo DWT, fuel, Fn, GM indicator are OPEN educational estimates.
- Never claim IMO intact stability or class approval.
- Do not say the hull is optimal or uniquely best.
- Numbers must come from the JSON. List constraint violations and unassessed items.
- End with: 設計者と船級の確認が必要です。"""


class LlmConfigError(RuntimeError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def normalize_extract(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in EXTRACT_FIELDS:
        val = payload.get(key)
        if val is None or val == "":
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if key == "block_coefficient" and not (0 < num <= 1):
            continue
        if num <= 0:
            continue
        out[key] = num
    notes = payload.get("notes")
    if isinstance(notes, str) and notes.strip():
        out["notes"] = notes.strip()
    return out


def _client():
    key = openai_api_key()
    if not key:
        raise LlmConfigError("OPENAI_API_KEY が .env にありません")
    from openai import OpenAI

    return OpenAI(api_key=key, timeout=40.0)


def extract_spec(text: str) -> dict[str, Any]:
    prompt = (text or "").strip()
    if len(prompt) < 4:
        raise ValueError("仕様文が短すぎます")
    resp = _client().chat.completions.create(
        model=openai_model(),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_EXTRACT},
            {"role": "user", "content": prompt[:4000]},
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    data = normalize_extract(parse_json_object(content))
    data["model"] = openai_model()
    data["role"] = "extract"
    return data


def explain_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    compact = {k: v for k, v in evaluation.items() if k not in {"mesh", "surface", "open"}}
    resp = _client().chat.completions.create(
        model=openai_model(),
        temperature=0.2,
        max_tokens=700,
        messages=[
            {"role": "system", "content": SYSTEM_EXPLAIN},
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)[:8000]},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    return {
        "text": text,
        "model": openai_model(),
        "role": "explain",
        "disclaimer": "LLM の説明は教育用。数値は geom-v2。船級・抵抗の判定ではない。",
    }
