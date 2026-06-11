# Telegram Bot App

The user-facing surface of FlySwarm. The **interface agent** (`agent/`) is the
custom harness loop wearing product tools (`tools/`) — it turns natural-language
travel requests into saved monitoring criteria. The **delivery layer**
(`delivery/`) is a dependency-free Telegram client (long-poll + send) and the
polling bot.

The combined runtime (`scripts/run_flyswarm.py`) runs this bot **and** the swarm
scheduler in one process, so inbound criteria and the periodic scan share one DB.

## Layout

- `agent/interface_agent.py` — `handle_message(user_id, text, history=…)`; builds a
  per-user `AgentHarness` with the criteria tools.
- `tools/criteria_tools.py` — `save_criterion`, `list_criteria`,
  `deactivate_criterion`, `route_insight` (bound to a user + the repository).
- `delivery/telegram_client.py` — `TelegramClient` (sendMessage / getUpdates) and
  `parse_updates`.
- `delivery/bot.py` — `run_polling` + per-chat conversation memory + `/start`.

## Run locally

1. Create a bot with **@BotFather** in Telegram (`/newbot`) and copy the token.
2. Add to `.env` (git-ignored):
   ```
   TELEGRAM_BOT_TOKEN=<token from BotFather>
   ```
   (You also need `OPENAI_API_KEY`, `TRAVELPAYOUTS_API_KEY`, `TRAVELPAYOUTS_MARKER`.)
3. Start the combined runtime:
   ```bash
   PYTHONPATH=. python -m scripts.run_flyswarm
   ```
4. Message your bot in Telegram: *"cheap flight from Tel Aviv to London in August
   under $300"*. It saves the watch; the scheduler scans every
   `SCAN_INTERVAL_SECONDS` (default 6h) and DMs you good deals.

## Deploy (Render, free)

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point it at the repo (`render.yaml` is included).
3. Set the secret env vars (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`,
   `TRAVELPAYOUTS_API_KEY`, `TRAVELPAYOUTS_MARKER`) in the dashboard.
4. Deploy. The service binds a health port and polls Telegram.

**Free-tier caveats:**
- Free web services **sleep after inactivity** — keep it awake with a free uptime
  pinger (e.g. UptimeRobot) hitting the service URL, or upgrade the plan.
- The free disk is **ephemeral**, so SQLite resets on restart. For durable storage,
  set `SWARM_STORAGE_BACKEND=postgres` + `DATABASE_URL` (Supabase/Neon free) — the
  storage layer is config-swappable, so no code changes are needed.
