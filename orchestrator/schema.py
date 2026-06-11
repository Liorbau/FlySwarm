"""Mechanical validation of skill inputs/outputs against a declared schema.

A schema is the ``inputs:`` or ``outputs:`` block from a skill's frontmatter.
Two shapes are accepted for authoring convenience:

1. A list of field specs::

       inputs:
         - name: goal
           type: string
           required: true
           description: What to do.

2. A mapping of field name to spec::

       inputs:
         goal: { type: string, required: true }

Supported types: string, number, integer, boolean, array, object, any.
Validation is deliberately shallow (presence + top-level type) — it is the fast,
deterministic gate; semantic judgement is the LLM fallback's job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "any": lambda v: True,
}


@dataclass
class FieldSpec:
    name: str
    type: str = "any"
    required: bool = True
    description: str = ""


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


class SchemaError(Exception):
    """Raised when a declared schema is itself malformed/unparseable."""


def parse_schema(raw: Any) -> Optional[list[FieldSpec]]:
    """Normalize a raw frontmatter inputs/outputs block into FieldSpecs.

    Returns ``None`` when no schema was declared (``raw`` is falsy/missing).
    Raises :class:`SchemaError` when a schema *is* declared but malformed, so the
    caller can fall back to the LLM judge per the agreed verifier precedence.
    """
    if raw is None:
        return None
    specs: list[FieldSpec] = []

    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict) or "name" not in item:
                raise SchemaError(f"field spec must be a mapping with 'name': {item!r}")
            specs.append(_to_field_spec(item["name"], item))
    elif isinstance(raw, dict):
        for name, item in raw.items():
            spec = item if isinstance(item, dict) else {}
            specs.append(_to_field_spec(name, spec))
    else:
        raise SchemaError(f"schema must be a list or mapping, got {type(raw).__name__}")

    return specs


def _to_field_spec(name: str, item: dict) -> FieldSpec:
    ftype = str(item.get("type", "any")).lower()
    if ftype not in _TYPE_CHECKS:
        raise SchemaError(f"unknown type {ftype!r} for field {name!r}")
    return FieldSpec(
        name=str(name),
        type=ftype,
        required=bool(item.get("required", True)),
        description=str(item.get("description", "")),
    )


def validate(data: Any, specs: list[FieldSpec]) -> ValidationResult:
    """Validate a data object against parsed field specs (clean pass/fail)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ValidationResult(False, [f"expected an object, got {type(data).__name__}"])

    for spec in specs:
        if spec.name not in data:
            if spec.required:
                errors.append(f"missing required field {spec.name!r}")
            continue
        value = data[spec.name]
        if value is None:
            if spec.required:
                errors.append(f"required field {spec.name!r} is null")
            continue
        if not _TYPE_CHECKS[spec.type](value):
            errors.append(f"field {spec.name!r} must be {spec.type} (got {type(value).__name__})")

    return ValidationResult(not errors, errors)


def describe(specs: Optional[list[FieldSpec]]) -> str:
    """Human/LLM-readable one-line-per-field schema description."""
    if not specs:
        return "(no declared schema)"
    lines = []
    for s in specs:
        req = "required" if s.required else "optional"
        desc = f" — {s.description}" if s.description else ""
        lines.append(f"- {s.name} ({s.type}, {req}){desc}")
    return "\n".join(lines)
