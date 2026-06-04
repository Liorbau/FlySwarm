from __future__ import annotations

import json

from harness.tools import edit_file, read_file, run_command, write_file


def test_write_read_edit_file_flow(tmp_path, monkeypatch):
    project_root = str(tmp_path)
    monkeypatch.setattr(write_file, "_PROJECT_ROOT", project_root)
    monkeypatch.setattr(read_file, "_PROJECT_ROOT", project_root)
    monkeypatch.setattr(edit_file, "_PROJECT_ROOT", project_root)

    target = "nested/example.txt"
    write_res = json.loads(write_file.execute({"path": target, "content": "hello world"}))
    assert "error" not in write_res
    assert write_res["bytes_written"] == len("hello world".encode("utf-8"))

    read_res = json.loads(read_file.execute({"path": target}))
    assert "error" not in read_res
    assert read_res["content"] == "hello world"

    edit_res = json.loads(
        edit_file.execute(
            {"path": target, "old_text": "world", "new_text": "flyswarm"}
        )
    )
    assert "error" not in edit_res
    assert edit_res["replacements"] == 1
    assert edit_res["matches_found"] == 1

    reread_res = json.loads(read_file.execute({"path": target}))
    assert reread_res["content"] == "hello flyswarm"


def test_read_file_rejects_outside_project(tmp_path, monkeypatch):
    monkeypatch.setattr(read_file, "_PROJECT_ROOT", str(tmp_path))
    outside_path = "/tmp/outside.txt"
    result = json.loads(read_file.execute({"path": outside_path}))
    assert "error" in result
    assert "outside the project directory" in result["error"]


def test_run_command_allows_readonly_command(tmp_path, monkeypatch):
    monkeypatch.setattr(run_command, "_PROJECT_ROOT", str(tmp_path))
    result = json.loads(run_command.execute({"command": "pwd", "timeout_seconds": 5}))
    assert result["exit_code"] == 0
    assert result["stdout"].strip() == str(tmp_path)


def test_run_command_rejects_disallowed_command(tmp_path, monkeypatch):
    monkeypatch.setattr(run_command, "_PROJECT_ROOT", str(tmp_path))
    result = json.loads(run_command.execute({"command": "git status"}))
    assert "error" in result
    assert "not allowed" in result["error"]
