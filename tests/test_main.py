import asyncio
import pytest # type: ignore
from fastapi.testclient import TestClient
from scala_runner.main import app  # adjust import path if needed

client = TestClient(app)

class DummyProcess:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self.stdout, self.stderr

async def fake_success_create(*args, **kwargs):
    # Simulate a successful Docker run
    return DummyProcess(stdout=b"Hello, Scala!", returncode=0)

async def fake_fail_create(*args, **kwargs):
    # Simulate a failed Docker run
    return DummyProcess(stderr=b"Docker error!", returncode=1)

@pytest.fixture(autouse=True)
def patch_async_subprocess(monkeypatch):
    # By default, patch asyncio.create_subprocess_exec to succeed
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_success_create)

def test_run_with_code():
    resp = client.post(
        "/run",
        json={
            "code": "println(\"Hello, Scala!\")",
            "scala_version": "3.6.4",
            "file_extension": "sc"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Hello, Scala!" in data["output"]

def test_docker_error(monkeypatch):
    # Override to simulate Docker failure
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_fail_create)

    resp = client.post(
        "/run",
        json={
            "code": "bad code",
            "scala_version": "3.6.4",
            "file_extension": "sc"
        }
    )
    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert "Docker error!" in detail