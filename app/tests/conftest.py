import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from freetier_prep.config import Settings  # noqa: E402
from freetier_prep.main import create_app  # noqa: E402
from freetier_prep.ttl import FakeClock  # noqa: E402

TTL = 3600


@pytest.fixture()
def env(tmp_path):
    settings = Settings(mode="dev", var_dir=tmp_path / "var")
    settings.ttl_seconds = TTL
    clock = FakeClock(start=1_000_000.0)
    app = create_app(settings, clock)
    with TestClient(app) as client:
        yield app, client, clock


def connect(client, email="maya@example.com"):
    r = client.post("/api/connect", json={"email": email})
    assert r.status_code == 200, r.text
    return r.json()


def start_lab(client):
    r = client.post("/api/start", json={"lab_id": "first-vpc"})
    assert r.status_code == 200, r.text
    return r.json()["session"]


def complete_all_tasks(client, session_id):
    task_ids = [f"t{i:02d}" for i in range(1, 13)]
    for tid in task_ids:
        client.post(f"/api/session/{session_id}/task/{tid}/simulate")
        r = client.post(f"/api/session/{session_id}/task/{tid}/validate")
        assert r.json()["ok"], f"{tid}: {r.json()}"
