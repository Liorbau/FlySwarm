import json
import os
import sqlite3
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import SignupRecord


class SignupRepository(ABC):
    @abstractmethod
    def add_signup(self, email: str) -> tuple[SignupRecord, bool]:
        """Return (record, created)."""


class JsonSignupRepository(SignupRepository):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def add_signup(self, email: str) -> tuple[SignupRecord, bool]:
        normalized_email = email.strip().lower()
        records = self._read_records()

        for item in records:
            stored_email = str(item.get("email", "")).strip().lower()
            if stored_email == normalized_email:
                return SignupRecord(**item), False

        record = SignupRecord(
            email=normalized_email,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        records.append(record.model_dump())
        self._write_records(records)
        return record, True

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_records([])
            return []

        try:
            with self.file_path.open("r", encoding="utf-8") as source:
                payload = json.load(source)
        except json.JSONDecodeError:
            corrupt_name = (
                f"{self.file_path.stem}.corrupt."
                f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
            )
            corrupt_path = self.file_path.with_name(corrupt_name)
            self.file_path.replace(corrupt_path)
            self._write_records([])
            return []

        if not isinstance(payload, list):
            self._write_records([])
            return []

        cleaned: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            email = str(item.get("email", "")).strip().lower()
            created_at = str(item.get("created_at", "")).strip()
            if not email:
                continue
            if not created_at:
                created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cleaned.append({"email": email, "created_at": created_at})
        return cleaned

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.file_path.parent,
            delete=False,
        ) as temp_file:
            json.dump(records, temp_file, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        os.replace(temp_path, self.file_path)


class SqliteSignupRepository(SignupRepository):
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signups (
                    email TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_signup(self, email: str) -> tuple[SignupRecord, bool]:
        normalized_email = email.strip().lower()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT email, created_at FROM signups WHERE email = ?",
                (normalized_email,),
            ).fetchone()
            if existing is not None:
                return SignupRecord(email=existing[0], created_at=existing[1]), False

            conn.execute(
                "INSERT INTO signups (email, created_at) VALUES (?, ?)",
                (normalized_email, created_at),
            )
            conn.commit()

        return SignupRecord(email=normalized_email, created_at=created_at), True


def get_repository() -> SignupRepository:
    backend = os.getenv("STORAGE_BACKEND", "json").strip().lower()
    project_root = Path(__file__).resolve().parents[1]
    custom_path = os.getenv("FLYSWARM_EMAILS_FILE", "").strip()
    emails_file = Path(custom_path).expanduser() if custom_path else project_root / "emails.json"
    sqlite_custom_path = os.getenv("FLYSWARM_SQLITE_FILE", "").strip()
    sqlite_file = (
        Path(sqlite_custom_path).expanduser()
        if sqlite_custom_path
        else project_root / "data" / "signups.sqlite3"
    )

    if backend == "json":
        return JsonSignupRepository(file_path=emails_file)
    if backend == "sqlite":
        return SqliteSignupRepository(db_path=sqlite_file)

    raise ValueError(
        f"Unsupported STORAGE_BACKEND '{backend}'. "
        "Supported values: 'json', 'sqlite'."
    )
