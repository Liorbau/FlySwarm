import json
import os

# Project root (one level above harness/)
_PROJECT_ROOT = os.path.realpath(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write UTF-8 text to a file inside the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path inside the project directory.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["path", "content"],
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
    content = args.get("content")

    if not path:
        return json.dumps({"error": "Missing required argument: path"})
    if content is None:
        return json.dumps({"error": "Missing required argument: content"})
    if not isinstance(content, str):
        return json.dumps({"error": "Invalid argument: content must be a string"})

    try:
        real_path = _resolve_in_project(path)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})

    parent_dir = os.path.dirname(real_path)
    try:
        os.makedirs(parent_dir, exist_ok=True)
        with open(real_path, "w", encoding="utf-8") as f:
            f.write(content)
    except PermissionError:
        return json.dumps({"error": "Permission denied."})

    return json.dumps({"path": real_path, "bytes_written": len(content.encode("utf-8"))})
