import json
import os
import shlex
import subprocess

# Project root (one level above harness/)
_PROJECT_ROOT = os.path.realpath(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)
_DEFAULT_TIMEOUT_SECONDS = 30
_MAX_TIMEOUT_SECONDS = 120
_ALLOWED_COMMANDS = {
    "echo",
    "ls",
    "pwd",
    "pytest",
    "uvicorn",
    "rg",
}


SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Run a constrained command from project root with a timeout."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command string (first token must be allowlisted).",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": (
                        "Optional timeout in seconds. Capped to a safe maximum."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}


def execute(args: dict) -> str:
    command = args.get("command", "")
    timeout_raw = args.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)

    if not isinstance(command, str) or not command.strip():
        return json.dumps({"error": "Missing required argument: command"})

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return json.dumps({"error": f"Invalid command syntax: {exc}"})

    if not parts:
        return json.dumps({"error": "Command is empty after parsing."})

    executable = parts[0]
    if executable not in _ALLOWED_COMMANDS:
        return json.dumps(
            {
                "error": f"Command '{executable}' is not allowed.",
                "allowed_commands": sorted(_ALLOWED_COMMANDS),
            }
        )

    if not isinstance(timeout_raw, int):
        return json.dumps({"error": "Invalid argument: timeout_seconds must be an integer"})
    timeout_seconds = max(1, min(timeout_raw, _MAX_TIMEOUT_SECONDS))

    try:
        result = subprocess.run(
            parts,
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        return json.dumps(
            {
                "command": command,
                "cwd": _PROJECT_ROOT,
                "timeout_seconds": timeout_seconds,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
        )
    except subprocess.TimeoutExpired as exc:
        return json.dumps(
            {
                "command": command,
                "cwd": _PROJECT_ROOT,
                "timeout_seconds": timeout_seconds,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "exit_code": -1,
                "error": "Command timed out.",
            }
        )
    except Exception as exc:  # defensive fallback for OS/runtime errors
        return json.dumps({"error": f"Command execution failed: {exc}"})
