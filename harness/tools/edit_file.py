import json
import os

# Project root (one level above harness/)
_PROJECT_ROOT = os.path.realpath(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "Edit a UTF-8 text file by replacing one substring with another "
            "inside the project directory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target file path inside the project directory.",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to replace.",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text.",
                },
            },
            "required": ["path", "old_text", "new_text"],
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
    old_text = args.get("old_text")
    new_text = args.get("new_text")

    if not path:
        return json.dumps({"error": "Missing required argument: path"})
    if not isinstance(old_text, str) or not isinstance(new_text, str):
        return json.dumps({"error": "Invalid arguments: old_text/new_text must be strings"})
    if old_text == "":
        return json.dumps({"error": "Invalid argument: old_text cannot be empty"})

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

    occurrences = content.count(old_text)
    if occurrences == 0:
        return json.dumps({"error": "old_text not found in file."})

    updated = content.replace(old_text, new_text, 1)
    try:
        with open(real_path, "w", encoding="utf-8") as f:
            f.write(updated)
    except PermissionError:
        return json.dumps({"error": "Permission denied."})

    return json.dumps({"path": real_path, "replacements": 1, "matches_found": occurrences})
