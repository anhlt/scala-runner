import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app  # Assuming the updated main.py is imported

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

def test_run_with_code():
    resp = client.post("/run", json={"code": "println(\"Hello, Scala!\")"})
    data = resp.json()
    assert resp.status_code == 200
    assert data["status"] == "success"
    assert "Hello, Scala!" in data["output"]

# Removed test_run_with_file_not_found as file_path is no longer supported

def test_docker_error(monkeypatch):
    monkeypatch.setattr(subprocess, "run", fake_run_fail)
    resp = client.post("/run", json={"code": "bad code"})  # Updated to use code instead of file_path if applicable
    assert resp.status_code == 500
    assert "Error running Docker" in resp.json()["detail"]