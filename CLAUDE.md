# CLAUDE.md — FlySwarm

Guidance for AI coding agents working in this repository.

---

## 1. What this project is

**FlySwarm** is a *Personalized Flight Monitoring Agent Swarm*. This repo is being
built during Masterschool's "Agentic Workshop" fellowship, where the end goal is to
present a working agent-swarm product.

### Ultimate vision (now in active development)
A multi-agent flight-price monitoring system delivered over Telegram, coordinated by
an orchestrator:

1. **Telegram Interface Agent** — parses natural-language flight requests from users and saves criteria to a DB.
2. **Orchestrator Agent** — optimizes API rate limits and schedules periodic background scans.
3. **Fetching / API Agent** — connects to official travel APIs (Amadeus / Travelpayouts) to monitor live prices.
4. **Analytics Agent** — evaluates price drops against historical trends.
5. **Notification Agent** — alerts users via Telegram with legally compliant affiliate monetization links.

---

## 2. Project scope

> **⚠️ LEGACY — no longer a limitation.** The "landing-page-only, do not build the
> backend swarm" rule below was a *starting* constraint for the kickoff session. That
> phase is **complete**. The project is now free to build swarm infrastructure
> (orchestration, agents, storage, live API integrations). Treat the boxed text below
> as historical context only.

<details>
<summary>Legacy kickoff constraint (no longer in force)</summary>

> **CRITICAL (legacy):** Do **NOT** build the backend swarm or connect to any live
> flight API in this session.

The only deliverable for the kickoff session was a **Simple Landing Page** that
introduced and validated the product idea, implementing **exactly three features**:

1. **Features List** — explains how the Flight Monitoring Swarm works.
2. **Interactive Button** — e.g. a "Try Demo" or other interactive UI component.
3. **Waitlist / Signup Form** — captured user emails to a local `emails.json` file.

</details>

### Standing constraints (still in force)
- Artifacts must stay ready to commit to a **public Git repository**.
- `emails.json` holds PII and is **git-ignored** — never commit captured emails.
- Secrets live in `.env` (git-ignored); see `.env.example` for the template.

---

## 3. The Three-Layer Experiment (LEGACY — kickoff exercise)

> **⚠️ LEGACY — no longer a limitation.** This three-layer exercise was part of the
> kickoff session and is **done**. You are no longer restricted to one selected
> "layer." Kept below for historical context.

The landing page was built three separate times, once per workflow "layer", to compare
the experience.

### Layer 1 — Raw LLM (API, no tools) · ≤ 1 hr
- Pretend you have **zero tools**: no filesystem, no terminal, no execution/verification.
- Output **only clean, self-contained code blocks** (HTML/CSS/JS + a minimal Node.js or
  Python backend that appends to `emails.json`).
- The user manually copies, runs, and debugs everything.

### Layer 2 — Harness (assisted) · ≤ 1 hr
- You have local tools (file create/modify, terminal).
- Create the files step-by-step (`index.html`, `server.js`, empty `emails.json`, etc.).
- Run a quick syntax/unit check to verify the form writes test input to `emails.json`.

### Layer 3 — Agent Harness (fully autonomous, Claude-Code style) · ≤ 1 hr
- Take the single instruction, plan, execute, and auto-fix end-to-end.
- Build a beautiful, modern, responsive UI; wire the live form to the backend;
  create `emails.json`; launch the local server; run automated browser/API checks.
- Deliver a fully tested, locally working app, 100% ready to commit.

---

## 4. Model provider abstraction (architecture requirement)

The system must be **model-agnostic and modular**: any agent must be able to run
against either a **local model** (e.g. Ollama) or **any cloud model** (OpenAI,
Anthropic/Claude, Google Gemini, etc.) without changing agent logic.

### Design rules
- Access models through a **single provider abstraction layer** (one common interface
  / client factory). Agents call the abstraction, never a vendor SDK directly.
- **Swapping providers must be config-only** — no code changes required.
- Adding a new provider should mean implementing one adapter against the shared
  interface, nothing more.

### Current implementation map (now in repo)
- Contract: `packages/contracts/src/llm_provider.py`
- Config loader: `packages/shared/src/config/__init__.py`
- LiteLLM adapter + client factory: `packages/adapters/src/llm/litellm_client.py`,
  `packages/adapters/src/llm/__init__.py`
- Routing config: `config/models.yaml`

`LiteLLM` is the normalization layer for provider differences and cost/token metadata.
Agent code (including `harness/`) must always call `get_llm_client()` instead of a
vendor SDK directly.

### Configuration split (convention)
- **Secrets → `.env`** (git-ignored): API keys and base URLs, e.g.
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`.
- **Provider/model selection & routing → dedicated config file** (committed, no secrets):
  a `config/models.*` file (JSON/YAML) defining the active provider, model name per
  role/agent, and tunables (temperature, max tokens). The active provider may also be
  overridden via an env var such as `LLM_PROVIDER` for quick switching.

> Note: this abstraction is **core infrastructure for the swarm** and is in active
> use (see `harness/` and `orchestrator/`). Build against it freely; the earlier
> "don't build the model layer during the landing-page session" restriction is legacy
> and no longer applies.

---

## 5. Data storage / DB strategy (free-to-develop)

No database engine is locked in. Everything must stay **free to develop** at this stage,
so storage follows the same swappable-by-config principle as the model layer.

### Hard requirement: PLUG-AND-PLAY
Storage must be **plug-and-play** — easy to change and scale to a permanent cloud DB
later **without touching agent/business logic**. Concretely:
- Switching engines (e.g. SQLite → cloud Postgres) is a **config/credentials change only**.
- All data access goes through **one repository interface**; adding an engine = writing
  one adapter behind that interface, nothing else.
- No vendor-specific calls leak into the rest of the codebase.

### Phased plan
- **Kickoff (landing page) — LEGACY:** emails went to a local **`emails.json`** flat
  file. This was the kickoff-only choice; it no longer constrains new work.
- **Local swarm dev (current):** **SQLite** — single local file, no server, no cost.
  Default for development.
- **Hosted later (still free):** **Postgres** on a free tier (**Supabase** or **Neon**)
  when a real client/server DB is needed. SQLite → Postgres is the intended upgrade path.

### Design rules
- Access data through a **storage/repository abstraction** — agents never call a DB
  driver directly, so swapping SQLite ↔ Postgres is **config-only**.
- Connection details live in **`.env`** as `DATABASE_URL` (git-ignored); never commit
  real data or credentials.
- Prefer SQL-compatible tooling (e.g. Prisma/Drizzle for Node, SQLAlchemy for Python)
  so the same schema works across SQLite and Postgres.

> Note: this is swarm infrastructure and is now fair game to build. The legacy landing
> page stays on `emails.json`, but new swarm work should use the storage abstraction
> (SQLite locally, Postgres later) — no need to ask first.

---

## 6. Repository structure rule (current proposal)

This repository must keep a **hard separation** between demo artifacts and the real
system, while allowing both to reuse shared contracts/domain logic.

> This is the **current structure idea** we agreed on. It is a rule for now, but it
> may be adjusted later if project needs change.

### Target layout
- `apps/demo-landing/` — demo/experiment-only landing app and validation artifacts.
- `apps/telegram-bot/` — real Telegram product surface (handlers, chat flows, delivery).
- `apps/swarm-orchestrator/` — real orchestration runtime (scheduler, workers, coordination).
- `harness/` — internal agent harness (loop, tool registry, local tests, validation scripts).
- `packages/domain/` — pure business entities, value objects, and policies (no vendor SDKs).
- `packages/contracts/` — shared interfaces for model, storage, flight, and notification providers.
- `packages/adapters/` — swappable provider implementations (local/cloud LLMs, json/sqlite/postgres, mock/live flight APIs).
- `packages/shared/` — cross-cutting utilities (config loading, logging, observability).
- `config/` — committed, non-secret routing/config files (models/storage/agents).
- `data/` — local runtime data files in development.
- `docs/` — architecture notes, decisions, and experiment outcomes.

### Boundary rules
- Real apps (`apps/telegram-bot`, `apps/swarm-orchestrator`) must not depend on demo code from `apps/demo-landing`.
- Cross-app reuse must go through `packages/domain`, `packages/contracts`, or `packages/shared`.
- External services must be accessed through adapters in `packages/adapters`, never directly from business logic.
- Provider/DB swaps must remain config-driven (`config/*` + `.env` secrets), not logic-driven.

---

## 7. "The harness" — what the user means

The user built a **harness** during class. Whenever they reference "the harness" or
"my harness", they mean that custom agent environment/tooling (now in `harness/`, with
the skills orchestration layer in `orchestrator/`). It is general swarm infrastructure.
When the work reaches a point that needs the harness, prefer reusing it; if its
behavior is genuinely unclear, **flag it to the user** rather than inventing it.

---

## 8. Working agreement

- The landing-page-only scope and per-layer restriction are **legacy**; building swarm
  agents, storage, orchestration, and live API integrations is now in scope.
- Keep new work behind the established abstractions (contracts → adapters, config-driven
  provider/DB swaps); respect the §6 boundary rules.
- Keep the project public-repo-safe: no secrets, no real user data committed.
- Ask before destructive actions; otherwise proceed and note your decisions.
