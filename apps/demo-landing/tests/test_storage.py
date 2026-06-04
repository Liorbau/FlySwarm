import json

from backend.storage import JsonSignupRepository, SqliteSignupRepository, get_repository


def test_add_signup_writes_record_and_dedupes(tmp_path):
    emails_file = tmp_path / "emails.json"
    repo = JsonSignupRepository(file_path=emails_file)

    record, created = repo.add_signup("first@example.com")
    assert created is True
    assert record.email == "first@example.com"
    assert emails_file.exists()

    payload = json.loads(emails_file.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["email"] == "first@example.com"
    assert payload[0]["created_at"] == record.created_at

    duplicate_record, duplicate_created = repo.add_signup("FIRST@example.com")
    assert duplicate_created is False
    assert duplicate_record.email == "first@example.com"

    payload_after = json.loads(emails_file.read_text(encoding="utf-8"))
    assert payload_after == payload


def test_json_repository_recovers_from_corrupt_file(tmp_path):
    emails_file = tmp_path / "emails.json"
    emails_file.write_text("{not valid json", encoding="utf-8")
    repo = JsonSignupRepository(file_path=emails_file)

    record, created = repo.add_signup("recovered@example.com")
    assert created is True
    assert record.email == "recovered@example.com"

    payload = json.loads(emails_file.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["email"] == "recovered@example.com"

    backups = list(tmp_path.glob("emails.corrupt.*.json"))
    assert len(backups) == 1


def test_sqlite_repository_writes_and_dedupes(tmp_path):
    sqlite_file = tmp_path / "signups.sqlite3"
    repo = SqliteSignupRepository(db_path=sqlite_file)

    first, first_created = repo.add_signup("sqlite@example.com")
    second, second_created = repo.add_signup("SQLITE@example.com")

    assert first_created is True
    assert second_created is False
    assert first.email == "sqlite@example.com"
    assert second.email == "sqlite@example.com"
    assert sqlite_file.exists()


def test_get_repository_rejects_unsupported_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "postgres")
    monkeypatch.delenv("FLYSWARM_EMAILS_FILE", raising=False)
    monkeypatch.delenv("FLYSWARM_SQLITE_FILE", raising=False)

    try:
        get_repository()
        assert False, "Expected get_repository() to raise for unsupported backend"
    except ValueError as exc:
        assert "Supported values: 'json', 'sqlite'" in str(exc)
