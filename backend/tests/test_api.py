import os

os.environ["SKIP_DB_INIT"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
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
client = TestClient(app)


def test_evaluate_ok():
    r = client.post(
        "/api/design/evaluate",
        json={"length_pp": 180, "beam": 30, "draft": 10, "block_coefficient": 0.75, "depth": 16},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["volume_m3"] == 40500.0
    assert body["dwt_t"] > 20000
    assert body["pd_kw"] > 500
    assert body["resistance_curve"]
    assert body["froude"] > 0.15
    assert body["surface"]["waterline"]
    assert "educational" in body["note"]
    assert "propulsion" in body["unassessed"]


def test_evaluate_rejects_negative():
    r = client.post(
        "/api/design/evaluate",
        json={"length_pp": -1, "beam": 30, "draft": 10, "block_coefficient": 0.75},
    )
    assert r.status_code == 422


def test_health_model_v2():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "geom-v3"
    assert "OPEN-24" in body["open"]
