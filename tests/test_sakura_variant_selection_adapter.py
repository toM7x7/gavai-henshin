from __future__ import annotations

import inspect
import json
from importlib import import_module
from typing import Any
from urllib.error import URLError

import pytest

from henshin.sakura_ai_engine import SakuraAIEngineConfig
from henshin.variant_selection import (
    LOCAL_RULE_PROVIDER,
    LocalRuleVariantSelectionAdapter,
    VariantCatalog,
    VariantSelectionRequest,
)


ADAPTER_CANDIDATES = (
    ("henshin.sakura_variant_selection", "SakuraAIVariantSelectionAdapter"),
    ("henshin.variant_selection", "SakuraAIVariantSelectionAdapter"),
)


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _load_adapter_class() -> type[Any]:
    for module_name, class_name in ADAPTER_CANDIDATES:
        try:
            module = import_module(module_name)
        except ModuleNotFoundError:
            continue
        adapter_cls = getattr(module, class_name, None)
        if adapter_cls is not None:
            return adapter_cls

    candidates = ", ".join(f"{module}.{name}" for module, name in ADAPTER_CANDIDATES)
    pytest.skip(f"SakuraAI variant adapter is not implemented yet. Expected one of: {candidates}")


def _catalog() -> VariantCatalog:
    return VariantCatalog.from_payload(
        {
            "modules": {
                "helmet": {
                    "variants": [
                        {"variant_key": "helmet:base", "display_name": "Base"},
                        {"variant_key": "helmet:sleek", "display_name": "Sleek visor"},
                    ]
                },
                "chest": {
                    "variants": [
                        {"variant_key": "chest:base", "display_name": "Base"},
                        {"variant_key": "chest:broad_guard", "display_name": "Broad guard"},
                        {"variant_key": "chest:v_core", "display_name": "V core"},
                    ]
                },
            }
        }
    )


def _request() -> VariantSelectionRequest:
    return VariantSelectionRequest(
        display_name="Aoi Sentinel",
        protection_target="protect the city and friends",
        temperament_mood="calm guardian shield",
        selected_parts=["helmet", "chest"],
        memo_prompt="hero guard suit with a readable stage silhouette",
    )


def _instantiate_adapter(
    adapter_cls: type[Any],
    *,
    config: SakuraAIEngineConfig | None = None,
) -> Any:
    signature = inspect.signature(adapter_cls)
    kwargs: dict[str, Any] = {}
    if "config" in signature.parameters and config is not None:
        kwargs["config"] = config
    if "fallback_adapter" in signature.parameters:
        kwargs["fallback_adapter"] = LocalRuleVariantSelectionAdapter()
    elif "fallback" in signature.parameters:
        kwargs["fallback"] = LocalRuleVariantSelectionAdapter()
    if "model" in signature.parameters:
        kwargs["model"] = "gpt-oss-120b"
    return adapter_cls(**kwargs)


def _patch_adapter_urlopen(monkeypatch: pytest.MonkeyPatch, adapter_cls: type[Any], fake_urlopen: Any) -> None:
    module = import_module(adapter_cls.__module__)
    if hasattr(module, "urlopen"):
        monkeypatch.setattr(module, "urlopen", fake_urlopen)

    import henshin.sakura_ai_engine as sakura_ai_engine

    monkeypatch.setattr(sakura_ai_engine, "urlopen", fake_urlopen)


def test_sakura_adapter_reads_same_environment_contract_as_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter_cls = _load_adapter_class()
    captured: dict[str, Any] = {}

    monkeypatch.setenv("SAKURA_AI_ENGINE_TOKEN", "env-token")
    monkeypatch.setenv("SAKURA_AI_ENGINE_BASE_URL", "https://sakura.example.test/v1")
    monkeypatch.setenv("SAKURA_AI_ENGINE_TIMEOUT", "11")
    monkeypatch.setenv("SAKURA_LLM_MODEL", "gpt-oss-120b")

    def fake_urlopen(request: Any, timeout: int | None = None) -> _FakeHTTPResponse:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeHTTPResponse(
            {
                "selected_variant_keys": {
                    "helmet": "helmet:sleek",
                    "chest": "chest:v_core",
                },
                "selection_reasons": {
                    "helmet": "API selected a sharper silhouette.",
                    "chest": "API selected a heroic core.",
                },
            }
        )

    _patch_adapter_urlopen(monkeypatch, adapter_cls, fake_urlopen)

    result = _instantiate_adapter(adapter_cls).select(_request(), _catalog())

    assert captured["url"].startswith("https://sakura.example.test/v1/")
    assert captured["headers"]["Authorization"] == "Bearer env-token"
    assert captured["body"]["model"] == "gpt-oss-120b"
    assert captured["timeout"] == 11
    assert result.modules["helmet"].selected_variant_key == "helmet:sleek"
    assert result.modules["chest"].selected_variant_key == "chest:v_core"


def test_sakura_adapter_extracts_selected_variant_keys_from_api_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_cls = _load_adapter_class()

    def fake_urlopen(_request: Any, timeout: int | None = None) -> _FakeHTTPResponse:
        return _FakeHTTPResponse(
            {
                "selected_variant_keys": {
                    "helmet": "helmet:sleek",
                    "chest": "chest:v_core",
                }
            }
        )

    _patch_adapter_urlopen(monkeypatch, adapter_cls, fake_urlopen)
    config = SakuraAIEngineConfig(
        token="test-token",
        base_url="https://sakura.example.test/v1",
        timeout_seconds=5,
    )

    result = _instantiate_adapter(adapter_cls, config=config).select(_request(), _catalog())

    assert result.modules["helmet"].selected_variant_key == "helmet:sleek"
    assert result.modules["chest"].selected_variant_key == "chest:v_core"
    assert result.llm_provider != LOCAL_RULE_PROVIDER


def test_sakura_adapter_falls_back_to_local_rule_when_api_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_cls = _load_adapter_class()

    def fake_urlopen(_request: Any, timeout: int | None = None) -> _FakeHTTPResponse:
        raise URLError("simulated Sakura outage")

    _patch_adapter_urlopen(monkeypatch, adapter_cls, fake_urlopen)
    config = SakuraAIEngineConfig(
        token="test-token",
        base_url="https://sakura.example.test/v1",
        timeout_seconds=5,
    )

    result = _instantiate_adapter(adapter_cls, config=config).select(_request(), _catalog())

    assert result.llm_provider == LOCAL_RULE_PROVIDER
    assert result.modules["chest"].selected_variant_key == "chest:broad_guard"
    for selection in result.modules.values():
        assert selection.llm_provider == LOCAL_RULE_PROVIDER
