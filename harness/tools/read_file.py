import json
import os

# Project root (one level above harness/)
_PROJECT_ROOT = os.path.realpath(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path inside the project directory.",
                }
            },
            "required": ["path"],
        },
    },
}


def _resolve_in_project(path: str) -> str:
    if os.path.isabs(path):
        real_path = os.path.realpath(path)
    else:
        real_path = os.path.realpath(os.path.join(_PROJECT_ROOT, path))

    if not (real_path == _PROJECT_ROOT or real_path.startswith(_PROJECT_ROOT + os.sep)):
        raise ValueError("Access denied: path is outside the project directory.")
    return real_path


def execute(args: dict) -> str:
    path = args.get("path", "")
    if not path:
        return json.dumps({"error": "Missing required argument: path"})

    try:
        real_path = _resolve_in_project(path)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    if not os.path.exists(real_path):
        return json.dumps({"error": f"File not found: {path}"})
    if not os.path.isfile(real_path):
        return json.dumps({"error": f"Not a file: {path}"})

    try:
        with open(real_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return json.dumps({"error": "File is not valid UTF-8 text."})
    except PermissionError:
        return json.dumps({"error": "Permission denied."})

    return json.dumps({"path": real_path, "content": content})
