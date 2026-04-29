"""Middleware that sanitizes write_file tool calls before they reach Pydantic."""

import json
import logging
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest

logger = logging.getLogger(__name__)


def _coerce_content_to_str(content: Any) -> str:
    """Coerce dict/list/primitive content to a string for write_file."""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)
    return str(content)
