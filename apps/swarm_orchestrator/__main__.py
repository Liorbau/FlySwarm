"""Run one swarm cycle and print the resulting notifications.

Manual entrypoint (``PYTHONPATH=. python -m apps.swarm_orchestrator [--no-llm]``);
the scheduler calls the same ``run_cycle`` on a cadence.
"""

from __future__ import annotations

import argparse
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from apps.swarm_orchestrator.orchestrate import run_cycle

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m apps.swarm_orchestrator")
    parser.add_argument("--no-llm", action="store_true",
                        help="Use the deterministic judge/prioritizer only (no LLM calls).")
    args = parser.parse_args()

    report, notifications = run_cycle(use_llm=not args.no_llm)
    print(f"[cycle] fetched {report.routes_fetched} route(s), "
          f"recorded {report.observations_recorded} observation(s).")
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
