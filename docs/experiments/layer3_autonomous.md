# Layer 3 — Autonomous Agent Harness (UI polish + browser e2e)

**Status: DONE.** The demo-landing page received a real "beautiful, modern,
responsive" polish pass and gained automated browser + API end-to-end checks
(Playwright + uvicorn) that all pass. Build ran in place on `apps/demo-landing`,
keeping exactly the three required features (features list, interactive demo
button, waitlist form). No swarm/Telegram/live-flight/DB scope was added.

## Model

- Real build on **`openai/gpt-4o`** via the vendored harness (`python -m harness`).
  `OPENAI_API_KEY` set in `.env`; `config/models.yaml` `default_provider: openai`.
  No mock fallback was used.
- Preflight smoke confirmed the harness reaches gpt-4o (1 step, $0.0013).

## What was built

- **UI polish** (`apps/demo-landing/frontend/index.html`, `styles.css`): aurora
  gradient background, gradient-clipped hero headline + eyebrow badge + CTA
  buttons, feature list as a responsive auto-fit card grid with emoji markers and
  hover lift, glassmorphism cards, refined chat bubbles / monospace agent log,
  focus-visible outlines, `prefers-reduced-motion` support, and tablet/mobile
  breakpoints. All required element ids preserved; `app.js` and the `/api/signup`
  contract unchanged.
- **Browser e2e** (`apps/demo-landing/tests/test_e2e_browser.py`): Playwright
  (Chromium) tests for the demo button (5 streamed agent-log entries + chat
  messages), waitlist success + duplicate handling, invalid-email error, and a
  mobile-viewport responsiveness check (demo grid collapses to one column).
- **Server fixture** (`apps/demo-landing/tests/conftest.py`): session-scoped
  `live_server` fixture boots `uvicorn` in a background thread on a free port with
  `FLYSWARM_EMAILS_FILE` pointed at a temp file, polls `/api/health`, and tears
  down cleanly. Email safety: the real `apps/demo-landing/emails.json` is never
  touched.
- **Tooling**: `apps/demo-landing/backend/requirements-dev.txt` gained
  `pytest-playwright` + `playwright`; `scripts/checks/verify_layer3.sh` added.

## How to run the e2e

```bash
pip install -r apps/demo-landing/backend/requirements.txt
pip install -r apps/demo-landing/backend/requirements-dev.txt
python -m playwright install chromium          # one-time, needs network (~100MB)
python -m pytest -q apps/demo-landing/tests     # 9 passed (5 API + 4 browser e2e)
```

## Harness run metrics (gpt-4o)

| Run | Purpose | Steps | Tool calls | Tokens | Est. cost |
|-----|---------|-------|-----------|--------|-----------|
| 0 | Preflight smoke | 1 | 0 | 403 | $0.001277 |
| 1 | UI polish (autonomous) | 6 | 13 | 37,768 | $0.098568 |
| 2 | UI overhaul (corrective resume) | 16 | 4 | 74,324 | $0.151378 |
| 3 | Run pytest suite (verification) | 2 | 1 | 1,368 | $0.003975 |
| **Total** | | **25** | **18** | **113,863** | **≈ $0.2552** |

Final verification: `9 passed` (5 API/unit + 4 browser e2e), `/api/health` 200,
page serves with hero + `app.js` + 5 feature cards.

## Friction / supervisor interventions

- **`edit_file` arg mismatch**: gpt-4o repeatedly called `edit_file` with
  `old_text`/`replacement_text`; the tool requires `old_text`/`new_text`, so those
  edits no-op'd and the model fell back to `write_file`.
- **Weak first polish, then a regression**: Run 1 reproduced near-identical files
  (no real polish). Run 2's full rewrite regressed the page — it replaced the
  FlySwarm-specific copy with generic placeholder text, flattened the demo grid,
  and dropped the `<script src="/app.js">` include (which would have killed all
  interactivity). The supervisor corrected this by authoring the final
  `index.html` + `styles.css` directly, preserving all ids, the five-agent feature
  copy, the demo grid, the waitlist form, and the script include.
- **Critical e2e infra authored by supervisor**: the uvicorn-in-a-thread
  `live_server` fixture and the Playwright tests were written directly (error-prone
  infrastructure); the harness was then used as the executor to run the suite to
  green. This matches the plan's "supervisor unblocks real limitations" intent.
- **`run_command` allowlist** excludes `bash`/`source`, and a long-running server
  can't be backgrounded by the tool — so the server is launched inside a pytest
  fixture and verification uses direct `python3 -m py_compile` / `pytest`.
- **`python` vs `python3`**: only `python3` exists on PATH; the harness's
  `python -m py_compile` call failed for that reason (cosmetic — the file writes
  had already succeeded).
- **Playwright browser arch**: inside the command sandbox Python reports `mac-x64`
  while the downloaded Chromium is `mac-arm64`; tests must run outside the sandbox
  (or in the harness, which executes outside it) to find the browser binary.
- **Chromium download** (~92MB) needed network permission (supervisor-granted).

## Optional bonus — Ollama plug-and-play (SKIPPED, non-blocking)

The model-agnostic provider swap was **not** exercised: `ollama list` is empty, so
`qwen2.5-coder:14b` is not pulled. Per scope, the model was not pulled here. To run
this demo later:

```bash
ollama pull qwen2.5-coder:14b
# then temporarily set config/models.yaml default_provider: ollama
#   (ollama_chat/qwen2.5-coder:14b, options.num_ctx: 16384)
# run a small harness slice to prove the config-only provider swap, then revert.
```

This is a demonstration of CLAUDE.md §4 (model-agnostic abstraction), not part of
the gpt-4o deliverable. A local 14B model is also less reliable at the agentic
tool-call/JSON protocol than gpt-4o.
