import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app  # Assuming the updated main.py is imported

client = TestClient(app)

@pytest.mark.integration
def test_run_scala_code_directly_with_file_content():
    # Test now uses code directly, simulating what was previously a file-based test
    resp = client.post("/run", json={
        "code": 'println("Integration Test")',
        "scala_version": "2.13",
        "dependency": ""  # no extra deps
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Integration Test" in body["output"]

@pytest.mark.integration
def test_run_scala_code_direct():
    # This test remains similar but is now the primary way to test code execution
    resp = client.post("/run", json={
        "code": 'println("Direct Integration")'
    }, timeout=120)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "Direct Integration" in body["output"]