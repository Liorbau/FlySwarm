"""FlySwarm skills orchestration layer.

A manually-triggered workflow that discovers every project skill, plans which
(if any) to use for a goal, runs each as an isolated sub-agent, and verifies
each skill's input and output. Run it with::

    PYTHONPATH=. python -m orchestrator "<goal>" [--token-budget N] [--dry-run]

See the module docstrings for the moving parts (discovery, planner, verifier,
skill_runner, orchestrator, report).
"""

from orchestrator.orchestrator import Orchestrator

__all__ = ["Orchestrator"]
