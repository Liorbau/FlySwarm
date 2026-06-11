---
name: parse-flight-request
description: >-
  Turn a natural-language travel request into a canonical SearchQuery and a
  persisted MonitoringCriterion. Use when a user describes a trip in free text
  ("cheap flight from Tel Aviv to London in August under $300", "watch NYC to Rome
  next month"), when parsing/normalizing a flight request into origin,
  destination, dates, budget, or when saving/listing/stopping a user's monitored
  routes. This is the FlySwarm interface-agent capability; it is consumed at
  runtime by apps/telegram_bot (the harness loop wearing product tools) and can
  also be invoked via the orchestrator.
disable-model-invocation: true
inputs:
  - name: request
    type: string
    required: true
    description: The user's natural-language travel request.
  - name: user_id
    type: string
    required: true
    description: Stable id of the requesting user (e.g. Telegram chat id).
outputs:
  - name: saved
    type: boolean
    required: true
    description: Whether a criterion was persisted (false if clarification needed).
  - name: criterion_id
    type: integer
    required: false
    description: Id of the persisted MonitoringCriterion, when saved.
  - name: response
    type: string
    required: true
    description: The user-facing reply (confirmation or clarifying question).
---

# Parse Flight Request

Turn fuzzy travel language into a saved monitoring criterion. The runtime
implementation is the interface agent in
`apps/telegram_bot/agent/interface_agent.py`: the harness loop
(`harness/loop.py`) running the criteria tools
(`apps/telegram_bot/tools/criteria_tools.py`) instead of the coding tools. This
file is the single source of truth for *how* parsing should behave; keep the
agent's system prompt aligned with it.

## What it does

1. Extract `origin` and `destination` as IATA codes, plus optional
   `depart_date`/`return_date`, `target_price`, and `currency` (default USD).
2. If origin or destination is missing/ambiguous, ask ONE brief question and save
   nothing.
3. Otherwise call `save_criterion`, then confirm in plain language.

Output a `MonitoringCriterion` (vendor-neutral) the scan workflow later consumes.

## House rules

- Persistence goes through the `Repository` contract (`packages/contracts`), never
  a DB driver. Storage backend stays config-driven (`config/storage.yaml`).
- The agent supplies flight fields only; `user_id` is bound by the runtime, never
  chosen by the model (a user must not write another user's data).
- No secrets or PII in code or logs.

## Gotchas (highest-signal — built from real runs)

- **IATA, not city names.** Downstream (flight source) needs codes. Map metros to
  their main code: Tel Aviv→TLV, London→LON, New York→NYC, Paris→PAR, Rome→ROM.
  When a city is genuinely ambiguous, ask rather than guess.
- **Relative dates need "today".** "August", "next month", "this weekend" are
  meaningless without the current date — the agent is given today's date and must
  resolve against it and never emit a past date. Month-only requests → `YYYY-MM`.
- **One-way vs round-trip.** No `return_date` ⇒ `one_way=True`. Don't invent a
  return leg. (Note: the Travelpayouts `cheap` endpoint may still return a
  round-trip offer — that's a source quirk handled later, not here.)
- **Clarifying questions look like a "stall" in non-interactive mode.** When the
  agent asks for missing info, the harness reports `status=stalled_no_progress`
  with `satisfied=false`. That is the correct behavior (it saved nothing and is
  awaiting the user), not a failure — the caller should treat it as "needs reply".
- **Stateless per call (for now).** Each message builds a fresh agent, so there is
  no cross-message memory yet; a follow-up that supplies the missing city must
  restate enough context. Conversation memory arrives with the Telegram layer.

## Verify

- Offline (gate): `apps/telegram_bot/tests/test_criteria_tools.py` exercises the
  tools deterministically (persist, normalize, requirement enforcement, per-user
  isolation) with no LLM/network.
- Live smoke: run a fuzzy request through `handle_message(...)` and confirm a
  correct `MonitoringCriterion` is persisted, and that a request missing
  origin/destination asks instead of saving.

## Anti-patterns

- ❌ Saving with a city name instead of an IATA code.
- ❌ Inventing an origin/destination/date the user didn't give.
- ❌ Letting the model set `user_id`, or reading/writing another user's criteria.
- ❌ Parsing raw vendor flight JSON here — that belongs in the source adapter.
