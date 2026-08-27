import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.main import app  # type: ignore

client = TestClient(app)


def test_root_endpoint():
    """Verify that root endpoint responds with 200 OK and correct message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SmartDocs AI backend is alive"}


def test_health_check():
    """Verify that health check endpoint returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}