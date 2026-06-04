#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT"

echo "[verify_harness] Running syntax checks..."
python3 - <<'PY'
from pathlib import Path

targets = [
    Path("harness"),
    Path("packages/contracts"),
    Path("packages/adapters"),
    Path("packages/shared"),
]

for target in targets:
    for py_file in target.rglob("*.py"):
        compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
PY

echo "[verify_harness] Running import checks..."
python3 -c "import harness.loop; import harness.tools; import harness.__main__"

echo "[verify_harness] Running harness tests..."
python3 -m pytest -q harness/tests

echo "[verify_harness] All checks passed."
