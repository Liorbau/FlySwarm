from dataclasses import dataclass, field
from typing import Callable

from .edit_file import SCHEMA as _edit_file_schema, execute as _edit_file_execute
from .list_directory import SCHEMA as _list_dir_schema, execute as _list_dir_execute
from .read_file import SCHEMA as _read_file_schema, execute as _read_file_execute
from .run_command import SCHEMA as _run_command_schema, execute as _run_command_execute
from .write_file import SCHEMA as _write_file_schema, execute as _write_file_execute


@dataclass(frozen=True)
class ToolSet:
    """A pluggable bundle of tools for the harness loop.

    ``schemas`` are OpenAI-style tool schemas passed to the LLM; ``registry``
    maps each tool ``name`` to its ``execute(args: dict) -> str`` callable. The
    same loop runs different tool packs (coding-tools for dev, product-tools for
    the user-facing agent) by swapping the ToolSet.
    """

    schemas: list[dict] = field(default_factory=list)
    registry: dict[str, Callable[[dict], str]] = field(default_factory=dict)


# All tool schemas passed to the LLM (OpenAI-style tool-calling format)
TOOL_SCHEMAS = [
    _read_file_schema,
    _write_file_schema,
    _edit_file_schema,
    _run_command_schema,
    _list_dir_schema,
]

# Maps function name → callable
TOOL_REGISTRY = {
    "read_file": _read_file_execute,
    "write_file": _write_file_execute,
    "edit_file": _edit_file_execute,
    "run_command": _run_command_execute,
    "list_directory": _list_dir_execute,
}

# The default (coding) tool pack — backward-compatible with existing harness use.
CODING_TOOLS = ToolSet(schemas=TOOL_SCHEMAS, registry=TOOL_REGISTRY)
