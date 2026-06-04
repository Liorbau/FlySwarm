#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile apps/demo-landing/backend/main.py apps/demo-landing/backend/models.py apps/demo-landing/backend/storage.py
python3 -m pytest -q apps/demo-landing/tests
