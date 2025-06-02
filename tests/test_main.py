import os
import subprocess
import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app, RunRequest

client = TestClient(app)

class DummyProc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

def fake_run_success(cmd, capture_output, text, check):
    return DummyProc(stdout="Hello, Scala!")

def fake_run_fail(cmd, capture_output, text, check):
    raise subprocess.CalledProcessError(1, cmd, stderr="Docker error!")

@pytest.fixture(autouse=True)
def patch_subprocess(monkeypatch):
    # default to success
    monkeypatch.setattr(subprocess, "run", fake_run_success)

def test_run_with_code(monkeypatch):
    resp = client.post("/run", json={"code": "println(\"Hello, Scala!\")"})
    data = resp.json()
    assert resp.status_code == 200
    assert data["status"] == "success"
    assert "Hello, Scala!" in data["output"]

def test_run_with_file_not_found():
    resp = client.post("/run", json={"file_path": "/no/such/file.sc"})
    assert resp.status_code == 400
    assert "File not found" in resp.json()["detail"]

def test_docker_error(monkeypatch):
    monkeypatch.setattr(subprocess, "run", fake_run_fail)
    resp = client.post("/run", json={"code": "bad code"})
    assert resp.status_code == 500
    assert "Docker error!" in resp.json()["detail"]