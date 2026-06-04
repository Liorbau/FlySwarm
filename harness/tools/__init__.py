from .edit_file import SCHEMA as _edit_file_schema, execute as _edit_file_execute
from .list_directory import SCHEMA as _list_dir_schema, execute as _list_dir_execute
from .read_file import SCHEMA as _read_file_schema, execute as _read_file_execute
from .run_command import SCHEMA as _run_command_schema, execute as _run_command_execute
from .write_file import SCHEMA as _write_file_schema, execute as _write_file_execute

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
