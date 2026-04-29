"""Unit tests for src.middleware."""

from src.middleware import _coerce_content_to_str


def test_coerce_content_passes_strings_through():
    assert _coerce_content_to_str("hello") == "hello"


def test_coerce_content_serializes_dicts_as_indented_json():
    assert _coerce_content_to_str({"a": 1}) == '{\n  "a": 1\n}'


def test_coerce_content_serializes_lists():
    assert _coerce_content_to_str([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"


def test_coerce_content_stringifies_other_primitives():
    assert _coerce_content_to_str(42) == "42"
