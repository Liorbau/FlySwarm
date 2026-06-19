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

Building the full swarm is **in scope**: orchestration, agents, storage, live API
integrations. (The kickoff session's landing-page-only constraint and the
"build it three times, once per workflow layer" experiment are **done** — they no
longer restrict new work. The legacy landing page still lives in `apps/demo-landing/`.)

### Standing constraints (still in force)
- Artifacts must stay ready to commit to a **public Git repository**.
- `emails.json` holds PII and is **git-ignored** — never commit captured emails.
- Secrets live in `.env` (git-ignored); see `.env.example` for the template.

---

## 3. Model provider abstraction (architecture requirement)

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
- **Provider/model selection & routing → `config/models.yaml`** (committed, no secrets):
  active provider, model name per role/agent, and tunables (temperature, max tokens).
  The active provider can also be overridden via `LLM_PROVIDER` for quick switching.

---

## 4. Data storage / DB strategy (free-to-develop)

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
- **Local swarm dev (current):** **SQLite** — single local file, no server, no cost.
  Default for development.
- **Hosted later (still free):** **Postgres** on a free tier (**Supabase** or **Neon**)
  when a real client/server DB is needed. SQLite → Postgres is the intended upgrade path.
- (The legacy landing page stays on its `emails.json` flat file; new swarm work uses
  the storage abstraction below.)

### Design rules
- Access data through a **storage/repository abstraction** — agents never call a DB
  driver directly, so swapping SQLite ↔ Postgres is **config-only**.
- Connection details live in **`.env`** as `DATABASE_URL` (git-ignored); never commit
  real data or credentials.
- Prefer SQL-compatible tooling (e.g. Prisma/Drizzle for Node, SQLAlchemy for Python)
  so the same schema works across SQLite and Postgres.

---

## 5. Repository structure rule (current proposal)

This repository must keep a **hard separation** between demo artifacts and the real
system, while allowing both to reuse shared contracts/domain logic.

> This is the **current structure idea** we agreed on. It is a rule for now, but it
> may be adjusted later if project needs change.

### Target layout
- `apps/demo-landing/` — demo/experiment-only landing app and validation artifacts.
- `apps/telegram-bot/` — real Telegram product surface (handlers = **controllers**, chat flows, delivery).
- `apps/swarm-orchestrator/` — real orchestration runtime (scheduler, workers, coordination).
- `harness/` — internal agent harness (loop, tool registry, local tests, validation scripts).
- `packages/domain/` — **domain modules** + pure model. Each business domain is a
  package with its own repository **port** and **service**:
  `flights/` (criteria + price corpus), `alerts/`, `learnings/`, `conversations/`
  (durable chat history). Shared pure model stays in `entities/`, `value_objects/`,
  `policies/`. No vendor SDKs.
- `packages/contracts/` — cross-cutting provider interfaces (model, flight, notification).
  (Per-domain storage ports now live with their domain in `packages/domain/<domain>/repository.py`.)
- `packages/adapters/` — swappable implementations. Storage is **per engine, per domain**:
  `storage/sqlite/` and `storage/postgres/` each expose a `Storage` **bundle**
  (`.criteria/.prices/.alerts/.learnings/.conversations`) over one shared connection;
  `storage/base.py` is the bundle protocol; `storage/__init__.py` is the `get_storage()`
  factory. Also LLM (`llm/`) and flight (`flights/`) adapters.
- `packages/shared/` — cross-cutting utilities (config loading, logging, observability).
- `config/` — committed, non-secret routing/config files (models/storage/sources).
- `data/` — local runtime data files in development.
- `docs/` — architecture notes, decisions, and experiment outcomes.

### Layered flow (the "controller → service → repository → adapter" rule)
Controllers (Telegram handlers, orchestrator steps) call domain **services**, which
call per-domain **repository ports**, which the per-engine **adapters** implement.
Business logic lives in services, never in controllers or adapters.

### Boundary rules
- Real apps (`apps/telegram-bot`, `apps/swarm-orchestrator`) must not depend on demo code from `apps/demo-landing`.
- Cross-app reuse must go through `packages/domain`, `packages/contracts`, or `packages/shared`.
- External services must be accessed through adapters in `packages/adapters`, never directly from business logic.
- Provider/DB swaps must remain config-driven (`config/*` + `.env` secrets), not logic-driven.

---

## 6. "The harness" — what the user means

The user built a **harness** during class. Whenever they reference "the harness" or
"my harness", they mean that custom agent environment/tooling (now in `harness/`, with
the skills orchestration layer in `orchestrator/`). It is general swarm infrastructure.
When the work reaches a point that needs the harness, prefer reusing it; if its
behavior is genuinely unclear, **flag it to the user** rather than inventing it.

---

## 7. Working agreement

- Keep new work behind the established abstractions (contracts → adapters, config-driven
  provider/DB swaps); respect the §5 boundary rules.
- Keep the project public-repo-safe: no secrets, no real user data committed.
- Ask before destructive actions; otherwise proceed and note your decisions.

<!-- captain:begin AI engineering policy (managed - do not edit inside) -->
# Engineering Ownership Protocol

This repository uses AI coding agents, but the human engineer owns the system design, tradeoffs, and final decisions.

## Before implementation

Before writing code:
- Restate the task in your own words.
- Identify affected files, modules, APIs, data models, or workflows.
- Identify meaningful design decisions.
- Present 2-4 options for important architecture or product decisions. (use the multiple-choice question tool, e.g. AskUserQuestion in Claude Code)
- Recommend one option, but wait for human approval before implementing high-impact decisions.
- Do not begin large implementation without an approved plan.

## During implementation

When writing code:
- Prefer small, reviewable diffs.
- Change at most 3 files or around 150 lines before pausing, unless explicitly approved.
- Implement step by step.
- Explain why each changed file is needed.
- Avoid unnecessary abstractions.

## Quality gates

For behavior changes:
- Add or update tests.
- Run relevant lint, typecheck, and tests when possible.
- If commands cannot be run, explain why.
- Call out hidden assumptions.
- Call out edge cases and failure modes.
- Call out security, privacy, performance, or migration risks when relevant.

## Human decision points

Pause and ask for human input before deciding:
- system architecture
- data model changes
- API contracts
- database migrations
- authentication or authorization behavior
- error-handling strategy
- major dependency additions
- irreversible or hard-to-migrate choices

## After implementation

After coding:
- Summarize changed files.
- Explain the final design.
- Explain how to verify behavior.
- List tests run.
- List remaining risks or TODOs.
- For non-trivial tasks, ask 1-3 questions to check that the human understands the implementation.
<!-- captain:end -->
