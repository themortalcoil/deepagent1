"""Unit tests for src.middleware."""

from src.middleware import _coerce_content_to_str, _sanitize_path


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
