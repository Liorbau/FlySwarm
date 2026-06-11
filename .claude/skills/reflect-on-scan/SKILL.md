---
name: reflect-on-scan
description: >-
  Turn a scan's outcomes into stored learnings so the swarm improves over time:
  record earned wins (good deals surfaced) and hard lessons (criteria that expired
  without ever hitting their target), then feed them back to the interface agent as
  route insights. Use when capturing what a monitoring run learned, recording
  wins/lessons, or making the system self-improving. Runtime: reflect() in
  apps/swarm_orchestrator and route_insight_text in packages/domain policies.
disable-model-invocation: true
inputs:
  - name: scan_report
    type: object
    required: true
    description: The ScanReport from a scan pass (deals + expired criterion ids).
outputs:
  - name: learnings
    type: array
    required: true
    description: The Learning records created (wins and lessons).
---

# Reflect on Scan

Close the self-improving loop. After each scan, write durable knowledge the swarm
reads back later. Write side: `apps/swarm_orchestrator/reflect.py`. Read side (fed
to the interface agent): `route_insight_text` in `packages/domain/src/policies`.

## What it records

- **Wins** — for every alert-worthy deal this pass, a route-scoped note ("surfaced
  a deal TLV->LON at 314 USD, score 0.85").
- **Lessons** — for every criterion that expired *this pass without ever alerting*,
  a note with the lowest price actually seen ("watched TLV->NYC until the deadline;
  target 100 never met; lowest seen 480"). These are what teach the system that a
  target was unrealistic.

## Feedback loop

When a user sets up a new monitor, the interface agent calls `route_insight`, which
combines price history + recent lessons into one line ("23 prices seen: low 310,
avg 360; a target of 250 is below the lowest ever seen"). That is the system
*using* what it learned to give better guidance.

## Gotchas (highest-signal)

- **Only log a lesson for expired criteria that never alerted.** Check
  `alerts_for_criterion` first — a criterion that *did* find a deal is a success, not
  a lesson. Skipping this floods the store with false negatives.
- **"Lowest seen" can be empty.** If no prices were ever recorded, say "no prices
  seen" rather than emitting a bogus number.
- **Learnings are route-scoped, not user-private.** Route price behavior is general
  knowledge shared across users — but never put PII (names, raw user ids in text)
  into a learning's `text`; keep ids in structured `data` only.
- **Write side and read side are separate.** `reflect()` records (needs the repo);
  `route_insight_text` is a pure policy over already-fetched data. Don't make the
  pure policy hit the database.

## Verify

- Offline: `apps/swarm_orchestrator/tests/test_reflect.py` (win recorded, lesson only
  when expired-without-alert) and `packages/domain/tests/test_insights.py`
  (history summary, unrealistic-target warning, lessons surfaced).
- Live: run two scans across a price change and confirm a win is recorded; let a
  criterion expire and confirm a lesson with the right "lowest seen".

## Anti-patterns

- ❌ Logging a lesson for a criterion that already alerted (it succeeded).
- ❌ Putting user PII in learning text.
- ❌ Letting the pure insight policy read the database directly.
- ❌ Fabricating a "lowest seen" when no prices were observed.
