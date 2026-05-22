"""Unit tests for src.middleware."""

import asyncio
import json
import logging

from langgraph.prebuilt.tool_node import ToolCallRequest

from src.middleware import WriteFileSanitizer, _coerce_content_to_str, _sanitize_path


def _make_tool_call_request(name: str, args: dict) -> ToolCallRequest:
    """Build a minimal ToolCallRequest for tests.

    The middleware only reads tool_call["name"] and tool_call["args"]. The
    tool, state, and runtime fields can be None — Python doesn't enforce the
    dataclass type hints at runtime, and request.override() uses
    dataclasses.replace which only re-runs __init__ with the same fields.
    """
    tool_call = {"name": name, "args": args, "id": "test-call-id", "type": "tool_call"}
    return ToolCallRequest(tool_call=tool_call, tool=None, state=None, runtime=None)


def _capture_handled_args(sanitizer: WriteFileSanitizer, request: ToolCallRequest) -> dict:
    """Run sanitizer.wrap_tool_call and return the args observed by the handler."""
    captured: dict = {}

    def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None

    sanitizer.wrap_tool_call(request, fake_handler)
    return captured["args"]


def test_coerce_content_passes_strings_through():
    assert _coerce_content_to_str("hello") == "hello"


def test_coerce_content_serializes_dicts_as_indented_json():
    assert _coerce_content_to_str({"a": 1}) == '{\n  "a": 1\n}'


def test_coerce_content_serializes_lists():
    assert _coerce_content_to_str([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"


def test_coerce_content_stringifies_other_primitives():
    assert _coerce_content_to_str(42) == "42"


def test_sanitize_path_passes_virtual_paths_through():
    assert _sanitize_path("/foo-app/package.json") == "/foo-app/package.json"


def test_sanitize_path_strips_output_marker():
    assert _sanitize_path("/Users/scott/output/foo-app/x.tsx") == "/foo-app/x.tsx"


def test_sanitize_path_strips_user_home_when_no_output_marker():
    assert _sanitize_path("/Users/scott/foo-app/x.tsx") == "/foo-app/x.tsx"


def test_sanitize_path_strips_tmp_prefix():
    assert _sanitize_path("/tmp/foo-app/package.json") == "/foo-app/package.json"


def test_sanitize_path_falls_through_for_short_paths():
    # /etc/passwd has no /output/ marker and only one segment after /etc/.
    # We accept the fallthrough — file ends up at root_dir/etc/passwd, junk
    # location but inside the sandbox.
    assert _sanitize_path("/etc/passwd") == "/etc/passwd"


def test_middleware_rewrites_write_file_args():
    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "content": {"k": "v"}},
    )
    args = _capture_handled_args(WriteFileSanitizer(), request)
    assert args["file_path"] == "/foo/x.json"
    assert args["content"] == '{\n  "k": "v"\n}'


def test_middleware_passes_through_other_tools():
    request = _make_tool_call_request(
        name="edit_file",
        args={
            "file_path": "/Users/scott/output/foo/x.json",
            "old_string": "a",
            "new_string": "b",
        },
    )
    # Non-write_file tools are NOT rewritten by this middleware.
    args = _capture_handled_args(WriteFileSanitizer(), request)
    assert args["file_path"] == "/Users/scott/output/foo/x.json"


def test_middleware_awrap_tool_call_rewrites_async():
    # The async path is what LangGraph Server's astream / ainvoke uses, so
    # this is the path real chat-UI traffic goes through. Structurally it
    # mirrors wrap_tool_call but via _maybe_rewrite + handler awaited.
    sanitizer = WriteFileSanitizer()
    captured = {}

    async def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None

    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "content": {"k": "v"}},
    )
    asyncio.run(sanitizer.awrap_tool_call(request, fake_handler))
    assert captured["args"]["file_path"] == "/foo/x.json"
    assert captured["args"]["content"] == '{\n  "k": "v"\n}'


def test_middleware_passes_through_when_content_is_none():
    # If the model omits content (or sends null), the `original_content is not None`
    # guard prevents the coercion branch from running. Pydantic will then raise
    # a clear "field required" error downstream — we don't try to fabricate a value.
    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/foo/x.json", "content": None},
    )
    args = _capture_handled_args(WriteFileSanitizer(), request)
    # content stays None — Pydantic will reject downstream, model retries.
    assert args["content"] is None
    # Path was already virtual; left alone.
    assert args["file_path"] == "/foo/x.json"


def test_coerce_content_serializes_realistic_package_json():
    # The actual shape models emit when they fumble: a nested package.json
    # dict. This exercises json.dumps on something more representative than
    # the {"a": 1} smoke-test.
    package_json = {
        "name": "foo-app",
        "private": True,
        "version": "1.0.0",
        "scripts": {"dev": "vite", "build": "tsc -b && vite build"},
        "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
    }
    result = _coerce_content_to_str(package_json)
    # Round-trips through json.loads without raising.
    assert json.loads(result) == package_json
    # Indented (each top-level key on its own line) — confirms indent=2 is plumbed through.
    assert '\n  "name": "foo-app"' in result


def test_middleware_logs_when_rewriting(caplog):
    # The INFO logs are the operational signal AGENTS.md tells operators to
    # grep for after a smoke run. Verify they fire when a rewrite happens.
    sanitizer = WriteFileSanitizer()

    def fake_handler(_req):
        return None

    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "content": {"k": "v"}},
    )
    with caplog.at_level(logging.INFO, logger="src.middleware"):
        sanitizer.wrap_tool_call(request, fake_handler)
    messages = [r.getMessage() for r in caplog.records]
    assert any("coerced content (type=dict) to str" in m for m in messages)
    assert any("rewrote path" in m for m in messages)


def test_middleware_does_not_log_on_clean_passthrough(caplog):
    # If the model sends a well-formed call (string content + virtual path),
    # the middleware should be silent. Noisy logs on happy-path traffic would
    # drown out the real signal.
    sanitizer = WriteFileSanitizer()

    def fake_handler(_req):
        return None

    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/foo/x.json", "content": "already a string"},
    )
    with caplog.at_level(logging.INFO, logger="src.middleware"):
        sanitizer.wrap_tool_call(request, fake_handler)
    assert caplog.records == []
