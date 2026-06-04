import os
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from backend.main import app, get_repo
from backend.storage import JsonSignupRepository


@pytest.fixture
def client(tmp_path: Path):
    temp_emails_file = tmp_path / "emails.json"
    repo = JsonSignupRepository(file_path=temp_emails_file)
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        with TestClient(app) as test_client:
            yield test_client, temp_emails_file
    finally:
        app.dependency_overrides.clear()


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    """Boot the real FastAPI app via uvicorn in a background thread.

    Uses a temp FLYSWARM_EMAILS_FILE so browser e2e never touches the real
    apps/demo-landing/emails.json.
    """
    emails_file = tmp_path_factory.mktemp("e2e_emails") / "emails.json"
    prev_storage_backend = os.environ.get("STORAGE_BACKEND")
    prev_emails_file = os.environ.get("FLYSWARM_EMAILS_FILE")
    os.environ["STORAGE_BACKEND"] = "json"
    os.environ["FLYSWARM_EMAILS_FILE"] = str(emails_file)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15
    healthy = False
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/api/health", timeout=1.0)
            if response.status_code == 200:
                healthy = True
                break
        except Exception:
            pass
        time.sleep(0.15)

    if not healthy:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Live server failed to start within timeout.")

    try:
        yield {"base_url": base_url, "emails_file": emails_file}
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        if prev_storage_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = prev_storage_backend
        if prev_emails_file is None:
            os.environ.pop("FLYSWARM_EMAILS_FILE", None)
        else:
            os.environ["FLYSWARM_EMAILS_FILE"] = prev_emails_file
