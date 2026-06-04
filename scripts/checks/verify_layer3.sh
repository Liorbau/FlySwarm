#!/usr/bin/env bash
set -euo pipefail

# Layer 3 verification: backend compiles, and the full suite (API unit tests +
# Playwright browser e2e) is green. The browser e2e boots uvicorn in a pytest
# fixture against a temp FLYSWARM_EMAILS_FILE, so the real emails.json is never
# touched.
#
# One-time setup (needs network, ~100MB):
#   pip install -r apps/demo-landing/backend/requirements.txt
#   pip install -r apps/demo-landing/backend/requirements-dev.txt
#   python -m playwright install chromium

python3 -m py_compile apps/demo-landing/backend/main.py apps/demo-landing/backend/models.py apps/demo-landing/backend/storage.py
python3 -m pytest -q apps/demo-landing/tests
