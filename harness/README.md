# FlySwarm Harness

The harness is a local autonomous loop that uses FlySwarm's provider abstraction and project-safe tools to execute tasks step-by-step.

## What it uses

- Loop runtime: `harness/loop.py`
- CLI entrypoint: `python -m harness`
- Tool registry: `harness/tools/__init__.py`
- Provider factory: `packages/adapters/src/llm/get_llm_client()`
- Provider config: `config/models.yaml`

## Setup

```bash
python3 -m pip install -r harness/requirements.txt
```

## Provider configuration

Model/provider routing is configured in `config/models.yaml`:

- `default_provider`: active provider by default
- `providers.<name>.model`: LiteLLM model id (for example `openai/gpt-4o`)
- `providers.<name>.options`: shared completion options

You can override provider and model at runtime from the CLI.

## Environment variables

Set only secrets and runtime overrides in `.env`:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- `OLLAMA_BASE_URL` (for local models)
- `LLM_PROVIDER` (optional provider override)

Optional loop tuning:

- `HARNESS_TOKEN_LIMIT` (default: `24000`)
- `HARNESS_COMPACT_AT` (default: `18000`)
- `HARNESS_COMPACT_WORDS` (default: `120`)
- `HARNESS_MAX_NO_PROGRESS_STEPS` (default: `2`)

## Usage

Run with a one-shot prompt:

```bash
python3 -m harness "Create a test file and run pytest -q harness/tests" --max-steps 8
```

Interactive follow-ups between steps:

```bash
python3 -m harness "Inspect harness tools and summarize" --interactive
```

Provider/model override:

```bash
python3 -m harness "Run harness smoke check" --provider ollama --model ollama_chat/llama3.1
```

## Verification script

Run the local harness checks:

```bash
bash scripts/checks/verify_harness.sh
```

This script runs:

1. Python syntax compilation checks for harness and provider packages
2. Basic import checks
3. `pytest -q harness/tests`

## `run_command` safety model

The `run_command` tool is intentionally constrained:

- Executes from repo root only
- Uses a strict allowlist of low-risk executables (`echo`, `ls`, `pwd`, `pytest`, `uvicorn`, `rg`)
- Enforces timeout (`timeout_seconds`, bounded to a safe max)
- Captures `stdout`, `stderr`, and `exit_code`
- Blocks shell injection by running with `shell=False`

This keeps automation useful while reducing accidental destructive command execution.
It is still a development helper, not a hardened OS-level sandbox.
