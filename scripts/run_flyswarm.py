"""FlySwarm combined runtime — Telegram bot + periodic scan/notify in one process.

    PYTHONPATH=. python -m scripts.run_flyswarm

This is the deploy entrypoint (a composition root): it wires the swarm scan and
the Telegram delivery together. Running both in one process means one shared
storage backend (SQLite locally, Postgres in production via SWARM_STORAGE_BACKEND
+ DATABASE_URL) — inbound criteria and the scheduler's scans see the same data.

This single process is also the only deployment: when ``$PORT`` is set (Render
web service) it serves the demo landing page + waitlist signup + a ``/health``
probe by mounting the self-contained ``apps/demo-landing`` FastAPI app — so one
free service hosts both the public page and the live bot at one URL.

Threads:
- a scheduler that runs one swarm ``run_cycle`` every ``SCAN_INTERVAL_SECONDS``
  (fetch prices for seed + watched routes → judge → notify → reflect) and pushes
  alerts to each user's chat,
- (when ``$PORT`` is set) a uvicorn web server on ``$PORT`` serving the landing
  page + ``/health`` (FastAPI handles GET and HEAD, so HEAD-based uptime monitors
  get HTTP 200),
- the Telegram long-poll loop on the main thread.

Required env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, TRAVELPAYOUTS_API_KEY,
TRAVELPAYOUTS_MARKER (+ DATABASE_URL when SWARM_STORAGE_BACKEND=postgres).
Optional: SCAN_INTERVAL_SECONDS (default 21600 = 6h), PORT.
"""

from __future__ import annotations

import os
import threading
import time
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from apps.swarm_orchestrator.orchestrate import run_cycle
from apps.telegram_bot.delivery.bot import run_polling
from apps.telegram_bot.delivery.telegram_client import TelegramClient
from packages.adapters.src.storage import get_storage

load_dotenv()


def _serve_web(port: int) -> None:
    """Serve the demo-landing FastAPI app (page + signup + /health) on ``port``.

    Run in a daemon thread; uvicorn skips signal-handler install off the main
    thread. The landing app is self-contained, so add its dir to ``sys.path`` and
    import it lazily (only when running as a web service).
    """
    import sys
    from pathlib import Path

    landing_dir = Path(__file__).resolve().parents[1] / "apps" / "demo-landing"
    if str(landing_dir) not in sys.path:
        sys.path.append(str(landing_dir))

    import uvicorn
    from backend.main import app as landing_app

    config = uvicorn.Config(landing_app, host="0.0.0.0", port=port, log_level="warning")
    uvicorn.Server(config).run()


def _run_scheduler(client: TelegramClient, interval_seconds: int) -> None:
    # One storage handle for this thread, reused across cycles. (Building it per
    # cycle would open — and leak — a new Postgres connection pool every interval.)
    storage = get_storage()
    while True:
        time.sleep(interval_seconds)
        try:
            report, notifications = run_cycle(storage=storage)
            for note in notifications:
                try:
                    client.send_message(int(note.user_id), note.text)
                except Exception as exc:
                    print(f"[cycle] send failed for {note.user_id}: {exc}")
            if report.observations_recorded or notifications:
                print(
                    f"[cycle] fetched {report.routes_fetched} route(s), "
                    f"recorded {report.observations_recorded} observation(s), "
                    f"sent {len(notifications)} alert(s)"
                )
        except Exception as exc:
            print(f"[cycle] error: {exc}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required (get one from @BotFather).")

    client = TelegramClient(token)
    interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "21600"))  # 6h default

    port = os.getenv("PORT")
    if port:
        threading.Thread(target=_serve_web, args=(int(port),), daemon=True).start()
        print(f"[flyswarm] web server (landing page + /health) on :{port}")

    threading.Thread(target=_run_scheduler, args=(client, interval), daemon=True).start()
    print(f"[flyswarm] scheduler every {interval}s; starting Telegram bot")
    run_polling(client)


if __name__ == "__main__":
    main()
