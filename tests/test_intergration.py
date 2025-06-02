import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app, RunRequest

client = TestClient(app)

@pytest.mark.integration
def test_run_scala_file(tmp_path):
    # 1) create a small .worksheet.sc file
    code = 'println("Integration Test")'
    file_path = tmp_path / "int_test.worksheet.sc"
    file_path.write_text(code)

    # 2) call your /run endpoint
    resp = client.post("/run", json={
        "file_path": str(file_path),
        "scala_version": "2.13",
        "dependency": ""  # no extra deps
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Integration Test" in body["output"]

@pytest.mark.integration
def test_run_scala_code_direct():
    # pass code directly, let FastAPI write the temp file
    resp = client.post("/run", json={
        "code": 'println("Direct Integration")'
    }, timeout=120)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "Direct Integration" in body["output"]