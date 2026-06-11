---
name: judge-deal
description: >-
  Judge whether a flight offer is a genuinely good deal worth notifying a user
  about, given the route's price history and the user's optional target price.
  Use when scoring/evaluating a flight price, deciding if a price drop is
  significant, filtering offers down to alert-worthy deals, or explaining in one
  line why a fare is (or isn't) a good deal. Consumed at runtime by the scan in
  apps/swarm_orchestrator (judge.py) and invocable via the orchestrator.
disable-model-invocation: true
inputs:
  - name: offer
    type: object
    required: true
    description: The flight offer under evaluation (price, route, dates, airline).
  - name: price_history
    type: array
    required: false
    description: Prior observed prices for the same route (for baseline min/avg).
  - name: target_price
    type: number
    required: false
    description: The user's budget/threshold, if they set one.
outputs:
  - name: is_deal
    type: boolean
    required: true
    description: Whether to notify the user about this offer.
  - name: score
    type: number
    required: true
    description: Confidence 0..1 that this is a good deal.
  - name: reason
    type: string
    required: true
    description: One concise, user-facing sentence explaining the verdict.
---

# Judge Deal

Decide if a flight offer is worth alerting the user, and explain why in one line.
The runtime implementation is `apps/swarm_orchestrator/judge.py`: a deterministic
gate (cheap) followed by an LLM nuance call (only for candidates).

## Judgment rubric

A deterministic gate decides whether the offer is even a *candidate*:

- **Target met** — `target_price` is set and `offer.price <= target_price`. Always
  alert-worthy (the user asked for this price).
- **New low** — the price is below the previous minimum for the route in
  `price_history`. A real drop, worth a look.

Non-candidates are never deals (`is_deal=false`, `score=0`), and skip the LLM.

For candidates, judge *quality* with skepticism:

- A price only marginally below average is a weak deal; a clear new low or a price
  comfortably under target is a strong one.
- Weight confidence by how much history exists — sparse history ⇒ lower confidence.
- A met target always yields `is_deal=true` (the user's own bar), even if history is thin.

Output (the LLM judge returns exactly this):
```json
{"is_deal": true, "score": 0.0, "reason": "one concise sentence for the user"}
```

## Gotchas (highest-signal)

- **Compare against PRIOR history, not including the current observation.** Read
  history first, then record the new price — otherwise the offer is its own
  baseline and nothing ever looks like a drop.
- **First sighting is not a deal.** With no prior history and no target, there is no
  baseline — record it and stay quiet rather than alerting on the first price seen.
- **A met target overrides LLM hesitation.** If `price <= target_price`, it is a
  deal regardless of how the LLM scores the nuance.
- **`reason` is user-facing.** Keep it to one plain sentence (it goes straight into
  the notification); no internal jargon, scores, or JSON.
- **Currency is assumed consistent** (project default USD). Don't compare across
  currencies; the source layer normalizes before this point.

## Verify

- Offline (gate): `apps/swarm_orchestrator/tests/test_judge.py` covers the
  deterministic gate (target met, new low, non-candidate, first-sighting) with the
  LLM disabled.
- Live: run the scan against real offers and confirm only genuinely good/new prices
  are flagged, each with a sensible one-line reason.

## Anti-patterns

- ❌ Calling the LLM for non-candidates (wasteful) — gate first.
- ❌ Letting a marginal price above target and not a new low count as a deal.
- ❌ Emitting multi-sentence or jargon-filled `reason` strings.
- ❌ Including the current price in the baseline it is compared against.
