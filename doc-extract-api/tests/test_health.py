"""Smoke test for /health that doesn't require the model.

The model is loaded in FastAPI's lifespan, which TestClient triggers. Loading
GOT-OCR takes 10-30s and downloads ~1.5GB on first run, so this test is marked
slow — skip it in fast CI runs with `pytest -m 'not slow'`.
"""

from __future__ import annotations

import pytest


@pytest.mark.slow
def test_health_returns_ok_after_model_load():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["model_loaded"] is True
        assert body["status"] == "ok"
