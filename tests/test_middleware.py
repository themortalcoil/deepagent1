"""Unit tests for src.middleware."""

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
    sanitizer = WriteFileSanitizer()
    captured = {}

    def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None

    request = _make_tool_call_request(
        name="write_file",
        args={"file_path": "/Users/scott/output/foo/x.json", "content": {"k": "v"}},
    )
    sanitizer.wrap_tool_call(request, fake_handler)
    assert captured["args"]["file_path"] == "/foo/x.json"
    assert captured["args"]["content"] == '{\n  "k": "v"\n}'


def test_middleware_passes_through_other_tools():
    sanitizer = WriteFileSanitizer()
    captured = {}

    def fake_handler(req):
        captured["args"] = req.tool_call["args"]
        return None

    request = _make_tool_call_request(
        name="edit_file",
        args={
            "file_path": "/Users/scott/output/foo/x.json",
            "old_string": "a",
            "new_string": "b",
        },
    )
    sanitizer.wrap_tool_call(request, fake_handler)
    # Non-write_file tools are NOT rewritten by this middleware.
    assert captured["args"]["file_path"] == "/Users/scott/output/foo/x.json"
