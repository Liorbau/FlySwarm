import json


def test_health_check(client):
    test_client, _ = client
    response = test_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signup_writes_to_temp_emails_file(client):
    test_client, temp_emails_file = client
    response = test_client.post("/api/signup", json={"email": "demo@example.com"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "success"
    assert payload["created"] is True
    assert payload["record"]["email"] == "demo@example.com"

    stored = json.loads(temp_emails_file.read_text(encoding="utf-8"))
    assert len(stored) == 1
    assert stored[0]["email"] == "demo@example.com"


def test_duplicate_signup_returns_created_false(client):
    test_client, _ = client
    first = test_client.post("/api/signup", json={"email": "repeat@example.com"})
    second = test_client.post("/api/signup", json={"email": "repeat@example.com"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["created"] is False


def test_invalid_email_returns_422(client):
    test_client, _ = client
    response = test_client.post("/api/signup", json={"email": "not-an-email"})
    assert response.status_code == 422
