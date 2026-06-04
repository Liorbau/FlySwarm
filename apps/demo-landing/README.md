# Demo Landing App

Landing-page experiment for FlySwarm (demo-only scope).

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Verify Layer 2

```bash
cd /path/to/FlySwarm
python3 -m py_compile apps/demo-landing/backend/main.py apps/demo-landing/backend/models.py apps/demo-landing/backend/storage.py
python3 -m pytest -q apps/demo-landing/tests
```

## Verify Layer 3 (browser end-to-end)

The suite now also includes Playwright browser tests for the demo button, the
waitlist (success + duplicate), and mobile responsiveness. A session-scoped
fixture boots `uvicorn` against a temporary `FLYSWARM_EMAILS_FILE`, so the real
`emails.json` is never touched.

```bash
cd /path/to/FlySwarm
pip install -r apps/demo-landing/backend/requirements-dev.txt
python -m playwright install chromium   # one-time, needs network (~100MB)
python3 -m pytest -q apps/demo-landing/tests   # 9 passed (5 API + 4 browser e2e)
```
