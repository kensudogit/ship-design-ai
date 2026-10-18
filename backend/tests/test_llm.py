import json
import os

os.environ["SKIP_DB_INIT"] = "1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.llm import normalize_extract, parse_json_object


def _client():
    from fastapi.testclient import TestClient
    from app.main import app

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override():
        db = Testing()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_parse_fenced_json():
    raw = '```json\n{"length_pp": 180, "beam": 30}\n```'
    assert parse_json_object(raw)["length_pp"] == 180


def test_normalize_drops_invalid():
    out = normalize_extract(
        {
            "length_pp": 180,
            "beam": -3,
            "block_coefficient": 1.4,
            "draft": "10",
            "notes": "Handymax",
        }
    )
    assert out["length_pp"] == 180
    assert out["draft"] == 10
    assert "beam" not in out
    assert "block_coefficient" not in out
    assert out["notes"] == "Handymax"


def test_extract_endpoint_mocked(monkeypatch):
    def fake_extract(text: str):
        assert "180" in text
        return {
            "length_pp": 180.0,
            "beam": 30.0,
            "draft": 10.0,
            "depth": 16.0,
            "block_coefficient": 0.75,
            "speed_kn": 14.0,
            "model": "mock",
            "role": "extract",
        }

    monkeypatch.setattr("app.main.extract_spec", fake_extract)
    client = _client()
    r = client.post("/api/design/extract", json={"text": "Lpp 180 m, B 30 m の Handymax"})
    assert r.status_code == 200
    body = r.json()
    assert body["evaluation"]["volume_m3"] == 40500.0
    assert body["hull"]["length_pp"] == 180
    assert "sk-" not in json.dumps(body)


def test_explain_endpoint_mocked(monkeypatch):
    def fake_explain(evaluation: dict):
        assert evaluation["volume_m3"] == 40500.0
        return {
            "text": "排水容積は Lpp×B×T×Cb の教育用概算です。設計者と船級の確認が必要です。",
            "model": "mock",
            "role": "explain",
            "disclaimer": "x",
        }

    monkeypatch.setattr("app.main.explain_evaluation", fake_explain)
    client = _client()
    r = client.post(
        "/api/design/explain",
        json={"length_pp": 180, "beam": 30, "draft": 10, "block_coefficient": 0.75, "depth": 16},
    )
    assert r.status_code == 200
    assert "教育用" in r.json()["text"]


def test_health_does_not_leak_key():
    body = _client().get("/health").json()
    dumped = json.dumps(body)
    assert "openai" in body
    assert "sk-" not in dumped
    assert "OPENAI_API_KEY" not in dumped
