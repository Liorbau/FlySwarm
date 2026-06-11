"""CLI entrypoint for the FlySwarm skills orchestrator.

    PYTHONPATH=. python -m orchestrator "<goal>" [options]

Options (only the crucial knobs):
    --token-budget N   Total token budget across planner + verifier + all skills.
    --dry-run          Plan and input-validate only; print the would-run plan.
    --provider NAME    Override LLM provider (openai, anthropic, google, ollama).
    --model ID         Override model id (LiteLLM format).
    --only A,B         Allow-list of skills (enables disable-model-invocation ones).
    --skip A,B         Exclude these skills from selection.
"""

from __future__ import annotations

import argparse
import os
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from dotenv import load_dotenv

from orchestrator.orchestrator import Orchestrator, RunConfig
from orchestrator.report import format_report

load_dotenv()

DEFAULT_TOKEN_BUDGET = int(os.getenv("HARNESS_TOKEN_LIMIT", "24000"))


def _csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m orchestrator",
        description="Plan, run and verify FlySwarm skills for a goal.",
    )
    p.add_argument("goal", nargs="?", help="The goal/task. If omitted, you'll be prompted.")
    p.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET,
                   help=f"Total token budget for the run (default: {DEFAULT_TOKEN_BUDGET}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Plan + input-validate only; do not execute skills.")
    p.add_argument("--provider", default=None, help="LLM provider override.")
    p.add_argument("--model", default=None, help="LLM model id override.")
    p.add_argument("--only", default=None,
                   help="Comma-separated allow-list (enables disable-model-invocation skills).")
    p.add_argument("--skip", default=None, help="Comma-separated skills to exclude.")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    goal = (args.goal or input("Goal: ")).strip()
    if not goal:
        raise SystemExit("Goal cannot be empty.")

    config = RunConfig(
        goal=goal,
        token_budget=args.token_budget,
        dry_run=args.dry_run,
        provider=args.provider,
        model=args.model,
        only=_csv(args.only),
        skip=_csv(args.skip),
    )

    result = Orchestrator(config).run()
    print(format_report(result))


if __name__ == "__main__":
    main()
