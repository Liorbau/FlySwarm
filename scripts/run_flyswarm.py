"""FlySwarm combined runtime — Telegram bot + periodic scan/notify in one process.

    PYTHONPATH=. python -m scripts.run_flyswarm

This is the deploy entrypoint (a composition root): it wires the swarm scan and
the Telegram delivery together. Running both in one process means a single shared
SQLite file — inbound criteria and the scheduler's scans see the same data.

Threads:
- a scheduler that runs ``scan_and_notify`` every ``SCAN_INTERVAL_SECONDS`` and
  pushes alerts to each user's chat,
- (optional) a tiny HTTP health server on ``$PORT`` so this can run as a free
  Render *web service* (which must bind a port),
- the Telegram long-poll loop on the main thread.

Required env: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, TRAVELPAYOUTS_API_KEY,
TRAVELPAYOUTS_MARKER. Optional: SCAN_INTERVAL_SECONDS (default 21600 = 6h), PORT.
"""

from __future__ import annotations

import os
import threading
import time
import warnings
from http.server import BaseHTTPRequestHandler, HTTPServer

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from apps.swarm_orchestrator.notify import scan_and_notify
from apps.telegram_bot.delivery.bot import run_polling
from apps.telegram_bot.delivery.telegram_client import TelegramClient
from packages.adapters.src.storage import get_repository

load_dotenv()


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence access logs
        pass


def _serve_health(port: int) -> None:
    HTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()


def _run_scheduler(client: TelegramClient, interval_seconds: int) -> None:
    while True:
        time.sleep(interval_seconds)
        try:
            repo = get_repository()  # own connection for this thread
            notifications = scan_and_notify(repo=repo)
            for note in notifications:
                try:
                    client.send_message(int(note.user_id), note.text)
                except Exception as exc:
                    print(f"[scan] send failed for {note.user_id}: {exc}")
            if notifications:
                print(f"[scan] sent {len(notifications)} alert(s)")
        except Exception as exc:
            print(f"[scan] error: {exc}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required (get one from @BotFather).")

    client = TelegramClient(token)
    interval = int(os.getenv("SCAN_INTERVAL_SECONDS", "21600"))  # 6h default

    port = os.getenv("PORT")
    if port:
        threading.Thread(target=_serve_health, args=(int(port),), daemon=True).start()
        print(f"[flyswarm] health server on :{port}")

    threading.Thread(target=_run_scheduler, args=(client, interval), daemon=True).start()
    print(f"[flyswarm] scheduler every {interval}s; starting Telegram bot")
    run_polling(client)


if __name__ == "__main__":
    main()
