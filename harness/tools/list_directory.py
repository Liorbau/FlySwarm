import json
import os
import re

# Only allow listing within the project root — never the wider filesystem.
# __file__ = harness/tools/list_directory.py -> project root is three levels up.
_BASE_DIR = os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "List files and subdirectories in a local directory. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to list. Must be inside the project folder.",
                }
            },
            "required": ["path"],
        },
    },
}


def _sanitize(name: str) -> str:
    """Strip control characters from filenames to block prompt injection via crafted file names."""
    return re.sub(r"[\x00-\x1f\x7f]", "", name)


def execute(args: dict) -> str:
    path = args.get("path", ".")
    real_path = os.path.realpath(os.path.expanduser(path))

    # Reject anything outside the project — catches path traversal (../../etc)
    if not (real_path == _BASE_DIR or real_path.startswith(_BASE_DIR + os.sep)):
        return json.dumps({"error": "Access denied: path is outside the project directory."})

    if not os.path.isdir(real_path):
        return json.dumps({"error": f"Not a directory: {path}"})

    try:
        # Return a tokenized list (structured JSON array) instead of a raw string.
        # Each entry is a discrete token — prevents injected text in filenames
        # from being interpreted as LLM instructions.
        entries = [
            {"name": _sanitize(e.name), "type": "dir" if e.is_dir() else "file"}
            for e in sorted(os.scandir(real_path), key=lambda e: (e.is_file(), e.name))
        ]
        return json.dumps({"path": real_path, "entries": entries})
    except PermissionError:
        return json.dumps({"error": "Permission denied."})
