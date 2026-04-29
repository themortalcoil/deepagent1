"""Middleware that sanitizes write_file tool calls before they reach Pydantic."""

import json
import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest

logger = logging.getLogger(__name__)

_HOST_PREFIXES = ("/Users/", "/home/", "/tmp/", "/var/", "/opt/", "/etc/")


def _coerce_content_to_str(content: Any) -> str:
    """Coerce dict/list/primitive content to a string for write_file."""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)
    return str(content)


def _sanitize_path(path: str) -> str:
    """Collapse host-absolute paths emitted by the model into virtual paths.

    Models occasionally emit paths like /Users/scott/output/foo/bar.tsx instead
    of /foo/bar.tsx. virtual_mode treats the leading "/" as anchored to
    root_dir, so those resolve to ~/.deepagent/output/Users/scott/output/foo/...
    — wrong location, but inside root_dir, so no exception fires. We rewrite
    them here.
    """
    if not path.startswith(_HOST_PREFIXES):
        return path
    idx = path.find("/output/")
    if idx >= 0:
        return path[idx + len("/output"):]  # leaves the leading "/"
    parts = Path(path).parts  # ('/', 'Users', 'scott', 'foo', 'bar.tsx')
    if path.startswith(("/Users/", "/home/")) and len(parts) > 3:
        return "/" + "/".join(parts[3:])
    if len(parts) > 3:
        return "/" + "/".join(parts[2:])
    return path


class WriteFileSanitizer(AgentMiddleware):
    """Coerce write_file content to str and sanitize host-absolute file_paths.

    Runs before tool args reach Pydantic validation, so dict content passes
    through and host paths get rewritten to virtual paths. No-op for other tools.
    """

    def _maybe_rewrite(self, request: ToolCallRequest) -> ToolCallRequest:
        if request.tool_call["name"] != "write_file":
            return request
        args = dict(request.tool_call["args"])
        original_path = args.get("file_path")
        original_content = args.get("content")
        if original_content is not None:
            args["content"] = _coerce_content_to_str(original_content)
            if not isinstance(original_content, str):
                logger.info(
                    "WriteFileSanitizer: coerced content (type=%s) to str",
                    type(original_content).__name__,
                )
        if isinstance(original_path, str):
            sanitized = _sanitize_path(original_path)
            if sanitized != original_path:
                args["file_path"] = sanitized
                logger.info(
                    "WriteFileSanitizer: rewrote path %r -> %r",
                    original_path,
                    sanitized,
                )
        return request.override(tool_call={**request.tool_call, "args": args})

    def wrap_tool_call(self, request, handler):
        return handler(self._maybe_rewrite(request))

    async def awrap_tool_call(self, request, handler):
        return await handler(self._maybe_rewrite(request))
