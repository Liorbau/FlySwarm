"""Parse YAML frontmatter out of a SKILL.md file.

Skills declare their metadata (name, description, disable-model-invocation) and
their I/O contract (inputs/outputs) in a leading ``---`` fenced YAML block. This
keeps the contract co-located with the skill so discovery is zero-config.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import yaml


def parse_frontmatter(text: str) -> Tuple[Optional[dict[str, Any]], str]:
    """Return ``(frontmatter_dict_or_None, body)``.

    Returns ``(None, text)`` when there is no well-formed leading ``---`` block,
    or when the block is not a YAML mapping.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text

    fm_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:]).strip("\n")

    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None, body

    if not isinstance(data, dict):
        return None, body
    return data, body
