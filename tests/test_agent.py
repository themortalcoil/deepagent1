"""Unit tests for src.agent module configuration.

The agent itself (a CompiledStateGraph) is exercised end-to-end in the manual
smoke test documented in AGENTS.md. These unit tests cover the pieces of the
module that have actual logic — primarily the _build_model helper's
conditional handling of OLLAMA_BASE_URL — plus the import-time invariant
that OUTPUT_DIR is created before any tool call lands.
"""

from langchain_ollama import ChatOllama

from src.agent import OUTPUT_DIR, _build_model


def test_build_model_returns_chat_ollama_with_requested_model_and_no_base_url(monkeypatch):
    # When OLLAMA_BASE_URL is unset, _build_model should pass only `model` to
    # ChatOllama, leaving base_url at its default (None — which lets the
    # underlying ollama client use http://localhost:11434).
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    model = _build_model("test-model:cloud")
    assert isinstance(model, ChatOllama)
    assert model.model == "test-model:cloud"
    assert model.base_url is None


def test_build_model_passes_base_url_when_env_var_set(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom.example:11434")
    model = _build_model("test-model:cloud")
    assert model.base_url == "http://custom.example:11434"


def test_output_dir_exists_after_module_import():
    # OUTPUT_DIR.mkdir(...) runs at import time. If that ever regresses,
    # FilesystemBackend fails on the first write — guard against it here.
    assert OUTPUT_DIR.is_dir()
