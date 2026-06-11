"""Run one scan + notify pass and print the resulting notifications.

    PYTHONPATH=. python -m apps.swarm_orchestrator [--no-llm]

This is the manual entrypoint the scheduler will call on a cadence to make
notifications "active".
"""

from __future__ import annotations

import argparse
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from apps.swarm_orchestrator.notify import scan_and_notify

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m apps.swarm_orchestrator")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use the deterministic judge only (no LLM nuance call).",
    )
    args = parser.parse_args()

    notifications = scan_and_notify(use_llm=not args.no_llm)
    if not notifications:
        print("No new deals to notify.")
        return
    print(f"{len(notifications)} new notification(s):\n")
    for n in notifications:
        print("─" * 40)
        print(f"to user {n.user_id} (criterion {n.criterion_id}):")
        print(n.text)
    print("─" * 40)


if __name__ == "__main__":
    main()
