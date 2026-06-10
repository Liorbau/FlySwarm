# Provider discovery — find legal, relevant flight sources

Detailed reference for **Step 0** of the new-source-handler skill: locating a
flight-data provider on the web, proving it is **legally usable**, and scoring it
for **relevance** to FlySwarm before any onboarding code is written.

FlySwarm is a personalized flight-price monitoring swarm (see `CLAUDE.md`): it
watches routes for users, detects price drops against history, and notifies users
with affiliate-monetized booking links. A source is only worth onboarding if it is
**legally permissible to use** and **relevant to that mission**.

## Contents

1. [Default-deny stance](#default-deny-stance)
2. [Discovery workflow](#discovery-workflow)
3. [Candidate provider categories](#candidate-provider-categories)
4. [Legal compliance gate (mandatory)](#legal-compliance-gate-mandatory)
5. [Reject checklist — do NOT use if…](#reject-checklist--do-not-use-if)
6. [Relevancy rubric + scoring](#relevancy-rubric--scoring)
7. [Triage record template](#triage-record-template)
8. [Hand-off into onboarding](#hand-off-into-onboarding)

## Default-deny stance

Treat every candidate as **not allowed until proven allowed**. Permission must be
*affirmative and documented* — an official API, published API terms, or a written
license that explicitly permits programmatic access. If permission is **unclear,
silent, or ambiguous, treat it as forbidden** and move on. Never rationalize a
"probably fine." When in doubt, drop the candidate or ask the user with the
specific clause that is unclear.

Why: FlySwarm runs continuously and monetizes via affiliate links. Using data a
site forbids creates legal and reputational liability for the whole product, and
an affiliate program will revoke access for ToS violations.

## Discovery workflow

Work one candidate at a time; do not batch-scrape the web to "see what sticks."

1. **Frame the need.** Which routes/regions/markets is the user (or roadmap)
   asking about? Discovery is demand-driven, not collect-everything.
2. **Search for official, permitted access first.** Look for the provider's
   *developer / API / partner / affiliate* pages — e.g. "<brand> flight API",
   "<brand> developer portal", "<brand> affiliate program", "flight data API
   free tier". Prefer first-party docs over blog posts.
3. **Identify the legal surface.** Locate, for the candidate: `robots.txt`, Terms
   of Service / Terms of Use, API terms / developer agreement, acceptable-use
   policy, and any affiliate/partner agreement. Save the URLs.
4. **Run the legal gate** (below). If it fails on any line, **reject and record
   why**. Do not proceed to relevance.
5. **Run the relevancy rubric** (below) and score. Triage: onboard now / backlog /
   reject.
6. **Record the triage** using the template and hand the winner to onboarding.

Use `WebSearch`/`WebFetch` to read official docs, terms, and `robots.txt`. Reading
public terms and docs is fine; **do not** fetch behind auth, paywalls, or anything
the gate forbids.

## Candidate provider categories

Map the landscape so you know what kind of source you are evaluating; each has
different legality and data shape:

- **Airline direct APIs / NDC** — e.g. an airline's official developer program.
  Often require partner agreements; highest data quality for that carrier only.
- **GDS / aggregators** — Amadeus (Self-Service has a free tier), Sabre,
  Travelport. Broad coverage, official APIs, clear terms; usually the best first
  target.
- **OTAs / ticketing agencies** — online travel agencies with affiliate APIs
  (e.g. Travelpayouts/Aviasales, Kiwi/Tequila). Strong affiliate/monetization fit.
- **Metasearch** — Skyscanner, Kayak, Google Flights. Powerful coverage but
  frequently **partner-gated or scraping-prohibited**; check terms carefully —
  many forbid programmatic use without a partnership.
- **Open / government / dataset sources** — open schedule or airport datasets.
  Useful for reference data (airports, carriers) but usually lack live prices.

Prefer categories that ship an **official API with permissive terms and an
affiliate path**. A site with flight data but no permitted programmatic access is
out of scope no matter how good the data looks.

## Legal compliance gate (mandatory)

A candidate passes **only if every line is satisfied and documented**:

- [ ] **robots.txt** retrieved and the intended access path is **not disallowed**
      for the agent you would use.
- [ ] **Terms of Service / Terms of Use** read; they **permit** the intended
      programmatic use (or an API path exists that does).
- [ ] **API terms / developer agreement** read (if an API exists); access method,
      allowed use, and redistribution/caching limits understood and acceptable.
- [ ] **Official / public API or licensed access** is the access method — not
      scraping a UI that forbids it.
- [ ] **Rate limits / quotas** are published or discoverable and can be honored.
- [ ] **No auth/paywall/anti-bot bypass** is required at any step.
- [ ] **Licensing & affiliate terms** captured: may FlySwarm cache prices, show
      them to users, and attach affiliate/booking links? Note attribution and
      `marker`/affiliate-id requirements (the Notification Agent needs them).
- [ ] **PII / data-handling** terms compatible with storing only non-PII offer
      data; no requirement to commit secrets or user data.

Record the exact URLs and the relevant clauses for each box. "I assume it's
allowed" is a fail.

## Reject checklist — do NOT use if…

Reject immediately (default-deny) if **any** is true:

- ❌ `robots.txt` disallows the path, or ToS forbids scraping/automated access and
  no permitted API exists.
- ❌ Using the data requires **bypassing** authentication, a paywall, CAPTCHAs, or
  other anti-bot measures.
- ❌ Terms prohibit caching, storing, redistributing, or displaying prices to end
  users — FlySwarm must store history and show offers.
- ❌ Terms forbid commercial use or affiliate monetization with the data.
- ❌ Permission is **unclear, silent, or contradictory** (default-deny → treat as
  forbidden).
- ❌ Access depends on credentials, scraping, or workarounds the user has not
  authorized.
- ❌ The provider has revoked, deprecated, or sunset the API, or the program is
  closed to new partners with no alternative.

When rejecting, write one line: candidate, the failing rule, and the source URL.

## Relevancy rubric + scoring

Only score candidates that **passed the legal gate**. Rate each criterion 0–2
(0 = no/unknown, 1 = partial, 2 = strong) and sum (max 20):

| # | Criterion | What "strong" (2) looks like |
|---|---|---|
| 1 | **Route/region coverage** | Covers the routes/regions FlySwarm users care about. |
| 2 | **Prices present** | Returns actual fares/prices, not just schedules. |
| 3 | **Dates queryable** | Searchable by specific departure/return dates. |
| 4 | **Origin/destination query** | Queryable by origin + destination (IATA). |
| 5 | **Booking / deep links** | Provides booking or affiliate deep links per offer. |
| 6 | **Affiliate / monetization** | Has an affiliate program with a `marker`/ID. |
| 7 | **Refresh / freshness** | Near-real-time prices; clear update cadence. |
| 8 | **Cost / free tier** | Free tier or affordable pricing for monitoring volume. |
| 9 | **Rate limits headroom** | Limits allow periodic scans for many routes. |
| 10 | **Reliability / data quality** | Documented uptime, stable schema, accurate data. |

Triage by total score:

- **≥ 16** — strong fit; onboard now (proceed to hand-off).
- **10–15** — viable; backlog or onboard if it fills a coverage gap.
- **< 10** — weak; reject unless it uniquely covers a needed route/region.

A criterion you cannot verify scores **0** (consistent with default-deny). Prices
(2), date+route queryability (3,4), and a booking/affiliate path (5,6) are the
load-bearing criteria for a price-monitoring swarm — a candidate weak on those is
rarely worth onboarding regardless of total.

## Triage record template

Capture this for each evaluated candidate (store findings in your working notes /
the onboarding PR description — never commit secrets):

```
Candidate: <provider/brand>
Category: <airline | GDS/aggregator | OTA | metasearch | open/dataset>
Access method: <official API | licensed feed | none>
Legal gate: PASS | FAIL
  robots.txt: <url> -> <allowed? path>
  ToS / API terms: <url> -> <key clauses on automated use, caching, display>
  Affiliate/license: <url> -> <marker/attribution requirements>
Relevancy score: <n>/20  (per-criterion: 1:_ 2:_ 3:_ 4:_ 5:_ 6:_ 7:_ 8:_ 9:_ 10:_)
Decision: ONBOARD NOW | BACKLOG | REJECT
Reason: <one line>
```

## Hand-off into onboarding

Once a candidate is **PASS + ONBOARD NOW**, it enters the normal onboarding flow
in `SKILL.md` (Steps 1–7). Carry forward exactly what onboarding needs:

- **Auth method** and the env var that will hold the secret (`<SOURCE>_API_KEY`,
  etc.) → goes in `.env` (placeholder in `.env.example`).
- **Endpoints + required params** (origin, destination, dates, passengers,
  currency) and **rate limits** → drive the adapter and `config/sources.yaml`.
- **A sample response** → scrubbed fixture for the verification gate.
- **Affiliate `marker`/attribution rules** → used when the adapter builds
  booking/deep links.

Boundary reminder (non-negotiable): all extraction/parsing logic lives **only** in
the adapter `packages/adapters/src/flights/<source>_source.py`; non-secret routing
in `config/sources.yaml`; secrets in `.env`. Vendor JSON and field names never
leave the adapter — discovery findings are mapped into the canonical model exactly
as `SKILL.md` Steps 2–7 describe.
