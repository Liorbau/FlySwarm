# FlySwarm

FlySwarm keeps **demo artifacts** clearly separate from the **real swarm system**, while allowing both to share stable contracts and adapters.

## Tech stack

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-4051B5?logo=uvicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-Validation-E92063?logo=pydantic&logoColor=white)
![Pytest](https://img.shields.io/badge/pytest-Testing-0A9EDC?logo=pytest&logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-Client-000000?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-E2E-2EAD33?logo=playwright&logoColor=white)
![LiteLLM](https://img.shields.io/badge/LiteLLM-Provider%20Abstraction-7C3AED?logo=openai&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20Models-000000?logo=ollama&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-Cloud%20Model-412991?logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-Cloud%20Model-191919?logo=anthropic&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-Cloud%20Model-4285F4?logo=google&logoColor=white)

Backend, harness, and tests are Python-based; model routing is provider-agnostic via LiteLLM, with both local (`ollama`) and cloud backends.

## Repository layout

- `apps/demo-landing/` - landing-page experiment and validation demos
- `apps/telegram-bot/` - real Telegram chat product surface
- `apps/swarm-orchestrator/` - real scheduler/orchestration runtime
- `packages/domain/` - shared business entities and rules
- `packages/contracts/` - shared interfaces (LLM/storage/flights/notifier)
- `packages/adapters/` - swappable implementations (json/sqlite, ollama/cloud, mock/live APIs)
- `packages/shared/` - shared config/logging/observability utilities
- `harness/` - autonomous local builder loop and tool registry
- `orchestrator/` - skills abstraction layer: discovers, plans, runs and verifies skills
- `config/` - committed non-secret routing and environment config
- `data/` - local runtime data (git-ignored content)
- `docs/` - architecture decisions and experiments

## Run the demo landing app

```bash
cd apps/demo-landing
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`

## Run tests

### API + storage tests

```bash
python3 -m pytest -q apps/demo-landing/tests/test_storage.py apps/demo-landing/tests/test_signup_api.py
```

### Full suite (includes browser e2e)

One-time browser install (network required, ~100MB):

```bash
python3 -m pip install -r apps/demo-landing/backend/requirements.txt
python3 -m pip install -r apps/demo-landing/backend/requirements-dev.txt
python3 -m playwright install chromium
python3 -m pytest -q apps/demo-landing/tests
```

Or use the verification scripts:

```bash
bash scripts/checks/verify_layer2.sh
bash scripts/checks/verify_layer3.sh
```

## Run the harness

Install harness dependencies:

```bash
python3 -m pip install -r harness/requirements.txt
```

Run a task:

```bash
python3 -m harness "Inspect demo-landing tests and summarize coverage" --max-steps 8
```

Provider/model override examples:

```bash
python3 -m harness "Run a short planning loop" --provider openai --model openai/gpt-4o
python3 -m harness "Run a short planning loop" --provider ollama --model ollama_chat/llama3.1
```

## Run the skills orchestrator

Discovers every skill under `.claude/skills/`, plans which (if any) to use for a goal,
runs each as an isolated sub-agent, and verifies each skill's input/output. New skills
are picked up automatically — no code changes.

```bash
# Preview the plan without executing any skill:
PYTHONPATH=. python3 -m orchestrator "<goal>" --dry-run

# Execute, with a total token budget across planner + verifier + all skills:
PYTHONPATH=. python3 -m orchestrator "<goal>" --token-budget 30000

# Enable a disable-model-invocation skill explicitly, or exclude skills:
PYTHONPATH=. python3 -m orchestrator "<goal>" --only skill-builder
PYTHONPATH=. python3 -m orchestrator "<goal>" --skip grill-me
```

## Configuration notes

- LLM routing is configured in `config/models.yaml`
- Secrets and runtime overrides live in `.env` (git-ignored)
- Supported waitlist storage backends in this scope:
  - `STORAGE_BACKEND=json` with `FLYSWARM_EMAILS_FILE` override
  - `STORAGE_BACKEND=sqlite` with `FLYSWARM_SQLITE_FILE` override
- `config/agents.yaml` and `config/storage.yaml` are placeholder templates for later phases

## Manual sanity checks

- `GET /api/health` returns `{"status":"ok"}`
- Click `Try Telegram Demo` and verify log progression:
  `Interface -> Orchestrator -> Fetching/API -> Analytics -> Notification`
- Submit waitlist form:
  - first submit returns success
  - duplicate submit returns already-on-waitlist
  - records are persisted to selected backend

For the autonomous run write-up and harness metrics, see `docs/experiments/layer3_autonomous.md`.
