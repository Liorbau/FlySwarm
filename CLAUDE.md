# CLAUDE.md — FlySwarm

Guidance for AI coding agents working in this repository.

---

## 1. What this project is

**FlySwarm** is a *Personalized Flight Monitoring Agent Swarm*. This repo is being
built during Masterschool's "Agentic Workshop" fellowship, where the end goal is to
present a working agent-swarm product.

### Ultimate vision (long-term — DO NOT build this yet)
A multi-agent flight-price monitoring system delivered over Telegram, coordinated by
an orchestrator:

1. **Telegram Interface Agent** — parses natural-language flight requests from users and saves criteria to a DB.
2. **Orchestrator Agent** — optimizes API rate limits and schedules periodic background scans.
3. **Fetching / API Agent** — connects to official travel APIs (Amadeus / Travelpayouts) to monitor live prices.
4. **Analytics Agent** — evaluates price drops against historical trends.
5. **Notification Agent** — alerts users via Telegram with legally compliant affiliate monetization links.

---

## 2. Current session scope (STRICT)

> **CRITICAL:** Do **NOT** build the backend swarm or connect to any live flight API
> in this session.

The only deliverable right now is a **Simple Landing Page** that introduces and
validates the product idea. It must implement **exactly three features**:

1. **Features List** — explains how the Flight Monitoring Swarm works.
2. **Interactive Button** — e.g. a "Try Demo" or other interactive UI component.
3. **Waitlist / Signup Form** — captures user emails and appends them to a local
   `emails.json` file via a minimal local backend.

### Constraints
- The artifact must be ready to commit to a **public Git repository**.
- `emails.json` holds PII and is **git-ignored** — never commit captured emails.
- Secrets live in `.env` (git-ignored); see `.env.example` for the template.

---

## 3. The Three-Layer Experiment (3-hour total budget)

The landing page is built three separate times, once per workflow "layer", to compare
the experience. Work on **only the layer the user explicitly selects**; keep the other
layers' context in mind but do not act on them.

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

### Configuration split (convention)
- **Secrets → `.env`** (git-ignored): API keys and base URLs, e.g.
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`.
- **Provider/model selection & routing → dedicated config file** (committed, no secrets):
  a `config/models.*` file (JSON/YAML) defining the active provider, model name per
  role/agent, and tunables (temperature, max tokens). The active provider may also be
  overridden via an env var such as `LLM_PROVIDER` for quick switching.

> Note: this abstraction is **infrastructure for the swarm**, not a current-session
> deliverable. Keep it in mind so the landing-page code stays compatible, but do not
> build the model layer during the landing-page session unless explicitly asked.

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
- **Current session (landing page):** no DB — emails go to a local **`emails.json`**
  flat file. Keep it this way for the landing-page scope.
- **Local swarm dev:** **SQLite** — single local file, no server, no cost. Default for
  development.
- **Hosted later (still free):** **Postgres** on a free tier (**Supabase** or **Neon**)
  when a real client/server DB is needed. SQLite → Postgres is the intended upgrade path.

### Design rules
- Access data through a **storage/repository abstraction** — agents never call a DB
  driver directly, so swapping SQLite ↔ Postgres is **config-only**.
- Connection details live in **`.env`** as `DATABASE_URL` (git-ignored); never commit
  real data or credentials.
- Prefer SQL-compatible tooling (e.g. Prisma/Drizzle for Node, SQLAlchemy for Python)
  so the same schema works across SQLite and Postgres.

> Note: this is swarm infrastructure, not a current-session deliverable. The landing
> page stays on `emails.json`; do not introduce a DB unless explicitly asked.

---

## 6. "The harness" — what the user means

The user built a **harness** during class. Whenever they reference "the harness" or
"my harness", they mean that custom agent environment/tooling. It becomes directly
relevant at **Layer 2** and **Layer 3**. When the work reaches a point that needs the
harness, **flag it to the user** rather than assuming or inventing its behavior.

---

## 7. Working agreement

- Stay strictly within the **current session scope** (landing page) and the **selected layer**.
- Do not scaffold or implement future swarm agents, DBs, or live API integrations.
- Keep the project public-repo-safe: no secrets, no real user data committed.
- Ask before expanding scope or taking destructive actions.
