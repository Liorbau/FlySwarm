"""CLI entrypoint for running the FlySwarm harness loop."""

from __future__ import annotations

import argparse

from harness.loop import AgentHarness


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the FlySwarm harness loop.")
    parser.add_argument(
        "task",
        nargs="?",
        help="Task prompt for the harness. If omitted, you'll be prompted.",
    )
    parser.add_argument(
        "--provider",
        dest="provider_override",
        help="Override provider from config/models.yaml (e.g. openai, anthropic, ollama).",
    )
    parser.add_argument(
        "--model",
        dest="model_override",
        help="Override model id (LiteLLM format, e.g. openai/gpt-4o).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive follow-up prompts between model steps.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum loop steps before exiting (default: 10).",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    task = (args.task or input("Insert request: ")).strip()
    if not task:
        raise SystemExit("Task prompt cannot be empty.")

    harness = AgentHarness(
        model=args.model_override,
        provider_override=args.provider_override,
    )
    harness.run(task, max_steps=args.max_steps, interactive=args.interactive)
    print(harness.get_run_log())


if __name__ == "__main__":
    main()
