---
name: new-source-handler
description: >-
  Onboard a new flight data source (an airline API or a ticketing/agency
  aggregator such as Amadeus, Travelpayouts, Kiwi) into FlySwarm end-to-end: map
  its fields into the project's canonical model and wire a config-swappable
  adapter. Also covers finding/discovering/locating legally usable flight
  providers, sources, or APIs on the web before onboarding them. Use when adding,
  integrating, or wiring up a new flight source/provider API, when finding or
  evaluating a flight-data provider on the web, when exploring an unfamiliar
  travel API response, or when mapping vendor fields (airline, route, dates,
  price, stops, availability, booking link) into the swarm.
disable-model-invocation: true
inputs:
  - name: source
    type: string
    required: true
    description: The flight data source/provider to onboard (name or API), or a request to discover one.
  - name: notes
    type: string
    required: false
    description: Known details such as docs URL, credential availability, or a sample response.
outputs:
  - name: adapter_path
    type: string
    required: true
    description: Path to the created/updated config-swappable adapter.
  - name: field_mapping
    type: object
    required: true
    description: Mapping of vendor fields to the canonical model.
  - name: summary
    type: string
    required: true
    description: What was wired and how to select/swap the source via config.
---

# New Source Handler

Full, end-to-end playbook for plugging a **new flight data source** into FlySwarm
behind a config-swappable adapter. The job: take a vendor's API, map its shape
into the project's **canonical** model, and wire it so that selecting or swapping
a source is a **config + `.env` change only** — never a logic change.

This skill runs **autonomously**. Explore the codebase and the source's official
docs to answer your own questions; only ask the user when you are genuinely
blocked (e.g. you need credentials, a sample response, or a product decision that
docs and code cannot settle).

## Architecture rules this skill enforces (from CLAUDE.md)

- A source is reached **only** through an adapter in `packages/adapters/src/flights/`.
- Business/agent/orchestrator code depends on the **contract**, never on a vendor
  SDK, raw JSON, or vendor field names.
- Adding a source = **one adapter file + a config entry + a `.env` placeholder**.
  No changes to business logic.
- Source selection and credentials are **config-driven**: non-secret routing in
  `config/sources.yaml`, secrets in `.env` (git-ignored). Never commit keys or
  real responses containing PII.
- Stay vendor-agnostic everywhere except inside the source's own adapter file.

## Mirror the existing LLM stack

FlySwarm already implements this exact pattern for models. Read these as the
reference style and copy their structure for sources:

- Contract: `packages/contracts/src/llm_provider.py` — `Protocol` + `@dataclass`,
  `from __future__ import annotations`, OpenAI-style plain shapes, rich docstrings.
- Config loader: `packages/shared/src/config/__init__.py` — a frozen
  `ResolvedLLMConfig`, a `resolve_llm_config()` that layers `.env` over YAML, and
  a `_PROVIDER_ENV_KEYS` map that names which env var holds each secret.
- Routing config: `config/models.yaml` — `default_provider` + a `providers` map
  with `model` + `options`.
- Factory: `packages/adapters/src/llm/__init__.py` — `get_llm_client()` calls the
  resolver and builds the concrete client.

The source stack is the same shape, one layer down. The table below is the target.

## Where things live (route fields and code here)

| Concern | Destination | Notes |
|---|---|---|
| Source contract (Protocol + canonical dataclasses) | `packages/contracts/src/flight_source.py` | **Create on first source.** Mirror `llm_provider.py` style exactly. |
| Canonical domain objects (entities / value objects) | `packages/domain/src/` | Vendor-neutral. The `entities/`, `value_objects/`, and `policies/` subdirs already exist (scaffolded, may be empty) — put entities in `entities/`, value objects in `value_objects/`. Co-design with the user; do not hardcode a fixed field list — see "Canonical model" below. |
| Concrete source adapter (vendor → canonical) | `packages/adapters/src/flights/<source>_source.py` | One file per source. Holds **all** vendor parsing. |
| Source factory | `packages/adapters/src/flights/__init__.py` | **Create on first source.** `get_flight_source()`, mirroring `get_llm_client()`. |
| Source config loader | `packages/shared/src/config/` | **Create on first source.** `resolve_source_config()` + a `_SOURCE_ENV_KEYS` secret map, mirroring `resolve_llm_config()`. |
| Source routing (non-secret) | `config/sources.yaml` | **Create on first source.** `default_source` + a `sources` map with `base_url`, `currency` (project default `USD`), tunables. |
| Credentials | `.env` (git-ignored) + `.env.example` placeholder | e.g. `<SOURCE>_API_KEY=`. Real value only in `.env`. |
| Fixture (sample response) | `packages/adapters/src/flights/fixtures/<source>.json` | A scrubbed sample, no PII. Used by the verification test. |
| Verification test | next to the project's other tests (pytest) | Offline: map fixture → assert canonical output. |

## Canonical model — do NOT hardcode a field list

The canonical model is **co-designed**, not prescribed by this skill. Before
mapping, determine the canonical target by, in order:

1. **Read what already exists** in `packages/domain/src/` and
   `packages/contracts/src/flight_source.py`. If a canonical `FlightOffer` (or
   similar) already exists, map **into it** and only extend it when a real new
   fact appears.
2. If nothing exists yet, **co-design a minimal canonical shape** driven by what
   the swarm actually consumes downstream (price monitoring → price-drop
   analytics → affiliate-link notifications). Keep it small and extensible; add a
   value object only when a genuine new fact shows up. If the right shape is
   ambiguous and the choice is product-significant, ask the user.

Hard rule regardless of shape: **raw vendor fields never leave the adapter.** The
adapter is the only place that knows the vendor's JSON.

## Project normalization conventions

These apply to every source. The adapter performs the normalization so canonical
objects are uniform regardless of vendor quirks.

- **Currency — project default is `USD`.** Do **not** inherit a vendor's default
  (e.g. some APIs default to `RUB`). Always request `USD` where the API supports a
  currency param, store `currency` as ISO 4217 uppercase, and set the per-source
  default in `config/sources.yaml` to `USD`.
- **Currency not in the response body:** some sources return only the price number
  and not the currency (it's implied by the request param). In that case, carry the
  requested currency into the adapter and stamp it on every offer. Convert minor
  units (cents) to major units when needed.
- **Datetimes:** normalize to UTC ISO 8601. Watch for date-only fields (no time)
  and non-UTC offsets — flag reduced granularity rather than inventing a time.
- **Booking / deep link:** a source may return (a) a full booking URL, (b) a
  **partial/relative link** to complete with the affiliate host + `marker`, or
  (c) nothing — in which case construct the affiliate URL. Always emit a complete,
  affiliate-ready link (the Notification Agent depends on it).
- **Stops:** prefer the source's explicit transfer/changes count; otherwise derive
  `max(len(segments) - 1, 0)`.

## Onboarding workflow

Copy this checklist and track progress as you go:

```
New source onboarding:
- [ ] Step 0: Discover a legal, relevant provider on the web (see Provider discovery)
- [ ] Step 1: Discover the API (auth, endpoints, params, sample response)
- [ ] Step 2: Determine the canonical target (read existing model, or co-design)
- [ ] Step 3: Produce an explicit vendor -> canonical mapping table
- [ ] Step 4: Create/confirm the contract + canonical domain objects
- [ ] Step 5: Implement the adapter (vendor JSON -> canonical objects)
- [ ] Step 6: Wire the stack (sources.yaml + resolver + factory + .env.example)
- [ ] Step 7: Verify (offline fixture gate; optional live smoke check)
```

### Step 0 — Discover a legal, relevant provider (web)

Do this when you don't yet have a chosen source — i.e. you need to **find** a
flight provider/source/API on the web before onboarding. Skip it if the user
already named the source.

Goal: locate a candidate, **prove it is legally usable**, and **score its
relevance** before any code is written. Two non-negotiables:

- **Legal compliance is mandatory and default-deny.** Use **only** legally
  permissible sources. Check and respect `robots.txt`; read and honor ToS / API
  terms / acceptable-use; prefer official public APIs or sources that explicitly
  permit programmatic access; never scrape where ToS forbids it; respect rate
  limits; never bypass auth, paywalls, or anti-bot measures; capture
  licensing/affiliate terms. **If permission is unclear, treat it as not
  allowed** and reject the candidate.
- **Relevance to FlySwarm.** Prefer sources with route/region coverage, real
  prices + dates, origin/destination querying, booking/affiliate deep links,
  acceptable cost/rate limits, and good freshness/reliability. Score and triage.

Full legal gate, reject checklist, relevancy rubric/scoring, provider categories,
and the triage template are in
[references/provider-discovery.md](references/provider-discovery.md). Read it
before evaluating a candidate. Once a candidate **passes the legal gate** and is
chosen, carry its auth method, endpoints/params, rate limits, a sample response,
and affiliate `marker`/attribution rules straight into Step 1.

### Step 1 — Discover the API

Prefer the source's **official docs**. Record, before writing code:

- **Auth**: API key / OAuth2 client-credentials / bearer — and which env var will
  hold it (`<SOURCE>_API_KEY`, etc.).
- **Endpoint(s)**: the search/price endpoint and required params (origin,
  destination, dates, passengers, currency).
- **Rate limits / quotas**: note them (the future Orchestrator Agent needs them).
- **Sample response**: obtain one and save a scrubbed copy as a fixture (see Step 7).

If docs are insufficient and you need a real sample or credentials, ask the user.
Never commit real keys or responses containing PII.

### Step 2 — Determine the canonical target

Follow "Canonical model" above: read the existing model and map into it, or
co-design a minimal one. Output a short statement of the canonical fields this
source will populate (and any it cannot).

### Step 3 — Map vendor fields → canonical

Produce an explicit mapping table **before** coding. Shape:

```
| Canonical field      | Vendor path                                      |
|----------------------|--------------------------------------------------|
| airline (code)       | <vendor JSON path>                               |
| origin / destination | <vendor JSON path>                               |
| departure datetime   | <vendor JSON path>  (normalize to UTC)           |
| price.amount         | <vendor JSON path>                               |
| price.currency       | <vendor path, or carry from request>  (ISO 4217; default USD) |
| stops                | <derive, e.g. len(segments) - 1>                 |
| booking / deep link  | <full URL, or complete partial link w/ marker, or construct affiliate URL> |
```

Flag any canonical field the source cannot provide. Decide explicitly: derive it,
leave it empty, or (if it's a real new fact) extend the canonical model.

### Step 4 — Create/confirm the contract + domain objects

- If `packages/contracts/src/flight_source.py` does not exist, **create it**: a
  `@runtime_checkable` `FlightSource` `Protocol` plus the canonical `@dataclass`
  shapes, in the exact style of `llm_provider.py`. Minimal Protocol shape:

```python
@runtime_checkable
class FlightSource(Protocol):
    """Vendor-neutral flight search. Adapters live in packages/adapters/src/flights."""

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        ...
```

- Put canonical entities/value objects under `packages/domain/src/`. Keep them
  vendor-neutral and minimal. Only extend when a real new fact appears.

### Step 5 — Implement the adapter

- File `packages/adapters/src/flights/<source>_source.py`, class
  `<Source>FlightSource`, implementing `FlightSource`.
- It owns **all** vendor parsing and returns **canonical** objects only.
- Read the secret from env (e.g. `os.environ["<SOURCE>_API_KEY"]`); read base URL
  and tunables from resolved config — never hardcode them.
- No vendor JSON, dicts, or field names escape this file.

### Step 6 — Wire the stack (config-only swappability)

Mirror the LLM stack so swapping sources is config-only:

- `config/sources.yaml` (non-secret): `default_source` + a `sources` map; per
  source: `base_url`, `currency` (project default `USD`), limits/tunables. Mirror
  `config/models.yaml`.
- `resolve_source_config()` in `packages/shared/src/config/`: a frozen
  `ResolvedSourceConfig` + a `_SOURCE_ENV_KEYS` map for secrets, layering `.env`
  over YAML and honoring an override env var (mirror `resolve_llm_config`).
- `get_flight_source()` in `packages/adapters/src/flights/__init__.py`: resolve
  config, build the right adapter (mirror `get_llm_client`).
- `.env.example`: add `<SOURCE>_API_KEY=` (placeholder only). Real value goes in
  `.env`, never committed.

After this, **adding the next source = one adapter file + one `sources.yaml`
entry + one `.env.example` placeholder.** Nothing else.

### Step 7 — Verify

- **Offline fixture gate (default, required):** save a scrubbed sample response to
  `packages/adapters/src/flights/fixtures/<source>.json`, map it through the
  adapter, and assert the canonical objects are correct: airline/airport codes,
  datetimes in UTC, price amount + ISO-4217 currency, stops count, booking link.
  Use pytest to match the repo's existing test style. This must pass before done.
- **Optional live smoke check:** if credentials are available, make one real call
  and confirm a real response maps cleanly. Keep it optional and never commit the
  live response or the key.

## Anti-patterns

- ❌ Parsing vendor JSON anywhere but the source's adapter (agents, domain,
  orchestrator must stay vendor-neutral).
- ❌ Hardcoding a source choice, base URL, or key in business logic instead of
  `config/sources.yaml` + `.env`.
- ❌ Committing API keys, tokens, or real flight/price responses containing PII.
- ❌ Hardcoding a rigid canonical field list — co-design and extend the shared
  model instead.
- ❌ Letting vendor field names or shapes leak past the adapter into the contract,
  domain, or callers.
- ❌ Onboarding a source whose `robots.txt`/ToS forbids the access, or where
  permission is unclear (default-deny), or that requires bypassing auth, paywalls,
  or anti-bot measures.
