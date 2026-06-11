"""Discover project skills at runtime so the orchestrator scales automatically.

Globs ``.claude/skills/*/SKILL.md`` from the repo root, parses each frontmatter
into a :class:`SkillSpec`, and parses the declared input/output schemas. Adding a
new skill directory requires **zero** code changes — it is picked up on the next
run. Skills with ``disable-model-invocation: true`` are excluded from autonomous
planning but remain runnable when named explicitly via ``--only``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from orchestrator.frontmatter import parse_frontmatter
from orchestrator.schema import FieldSpec, SchemaError, parse_schema


def _repo_root() -> Path:
    # orchestrator/discovery.py -> repo root is one level up.
    return Path(__file__).resolve().parents[1]


SKILLS_GLOB = ".claude/skills/*/SKILL.md"


@dataclass
class SkillSpec:
    name: str
    description: str
    path: Path
    body: str
    disable_model_invocation: bool = False
    input_specs: Optional[list[FieldSpec]] = None
    output_specs: Optional[list[FieldSpec]] = None
    schema_error: Optional[str] = None

    @property
    def has_input_schema(self) -> bool:
        return self.input_specs is not None

    @property
    def has_output_schema(self) -> bool:
        return self.output_specs is not None

    @property
    def has_full_schema(self) -> bool:
        return self.has_input_schema and self.has_output_schema


def _load_spec(skill_md: Path) -> Optional[SkillSpec]:
    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return None

    name = str(fm.get("name") or skill_md.parent.name)
    description = str(fm.get("description") or "").strip()
    disable = bool(fm.get("disable-model-invocation", False))

    input_specs = output_specs = None
    schema_error = None
    try:
        input_specs = parse_schema(fm.get("inputs"))
        output_specs = parse_schema(fm.get("outputs"))
    except SchemaError as exc:
        schema_error = str(exc)

    return SkillSpec(
        name=name,
        description=description,
        path=skill_md,
        body=body,
        disable_model_invocation=disable,
        input_specs=input_specs,
        output_specs=output_specs,
        schema_error=schema_error,
    )


def discover_skills(root: Optional[Path] = None) -> list[SkillSpec]:
    """Return all discoverable skills, sorted by name."""
    root = root or _repo_root()
    specs: list[SkillSpec] = []
    for skill_md in sorted(root.glob(SKILLS_GLOB)):
        spec = _load_spec(skill_md)
        if spec is not None:
            specs.append(spec)
    specs.sort(key=lambda s: s.name)
    return specs


def select_skills(
    skills: list[SkillSpec],
    only: Optional[list[str]] = None,
    skip: Optional[list[str]] = None,
) -> tuple[list[SkillSpec], list[str]]:
    """Apply --only / --skip filters and the disable-model-invocation rule.

    Returns ``(invocable, notes)`` where ``invocable`` is the catalog the planner
    may choose from, and ``notes`` are human-readable exclusion reasons.
    """
    only_set = {n.strip() for n in only} if only else None
    skip_set = {n.strip() for n in skip} if skip else set()
    invocable: list[SkillSpec] = []
    notes: list[str] = []

    for s in skills:
        if s.name in skip_set:
            notes.append(f"{s.name}: excluded by --skip")
            continue
        if only_set is not None:
            if s.name in only_set:
                invocable.append(s)  # --only overrides disable-model-invocation
            else:
                notes.append(f"{s.name}: not in --only allow-list")
            continue
        if s.disable_model_invocation:
            notes.append(f"{s.name}: disable-model-invocation (run via --only to enable)")
            continue
        invocable.append(s)

    if only_set:
        unknown = only_set - {s.name for s in skills}
        for name in sorted(unknown):
            notes.append(f"{name}: requested in --only but not found")

    return invocable, notes
