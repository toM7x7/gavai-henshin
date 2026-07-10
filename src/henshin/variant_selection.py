"""Variant auto-selection for Web Forge armor modules.

The selector is intentionally provider-shaped: callers use the adapter
protocol today with local rules, and a Sakura AI backed adapter can replace
that implementation later without changing the backend contract.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ._env import load_dotenv as _load_dotenv
from .sakura_ai_engine import SakuraAIEngineConfig, SakuraAIEngineError, resolve_sakura_config


DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "viewer"
    / "assets"
    / "armor-parts"
    / "variant_catalog.json"
)

LOCAL_RULE_PROVIDER = "local_rule"
SAKURA_AI_PROVIDER = "sakura_ai"
DEFAULT_SAKURA_LLM_MODEL = "gpt-oss-120b"
DEFAULT_SAKURA_LLM_ENDPOINT = "/chat/completions"

THEME_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "hero": (
        "hero",
        "heroic",
        "brave",
        "champion",
        "rider",
        "tokusatsu",
        "warrior",
        "knight",
        "hero",
        "ヒーロー",
        "特撮",
        "勇者",
        "戦士",
        "騎士",
        "変身",
    ),
    "sleek": (
        "sleek",
        "slim",
        "speed",
        "fast",
        "swift",
        "stream",
        "agile",
        "sharp",
        "light",
        "ninja",
        "速い",
        "高速",
        "疾走",
        "俊敏",
        "軽量",
        "細身",
        "忍者",
    ),
    "guard": (
        "guard",
        "guardian",
        "protect",
        "protection",
        "shield",
        "defense",
        "defend",
        "tank",
        "fortress",
        "守る",
        "守護",
        "防御",
        "盾",
        "救助",
        "市民",
        "保護",
        "堅牢",
    ),
    "wing": (
        "wing",
        "winged",
        "flight",
        "fly",
        "sky",
        "aerial",
        "feather",
        "angel",
        "翼",
        "羽",
        "飛行",
        "空",
        "天使",
    ),
    "bold": (
        "bold",
        "heavy",
        "power",
        "strong",
        "tough",
        "broad",
        "impact",
        "大胆",
        "重装",
        "力強い",
        "強い",
        "豪快",
        "パワー",
    ),
}

VARIANT_THEME_MARKERS: Mapping[str, tuple[str, ...]] = {
    "hero": ("hero", "heroic", "v_core", "crest", "buckle", "toe_hero"),
    "sleek": ("sleek", "stream", "visor", "cap", "line"),
    "guard": ("guard", "guardian", "shield", "broad", "heavy", "heel_guard"),
    "wing": ("wing", "winged", "flight", "aerial"),
    "bold": ("bold", "heavy", "broad", "spike", "guard", "power"),
}

TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class VariantCatalog:
    modules: Mapping[str, Mapping[str, Any]]
    variant_records_by_module: Mapping[str, tuple[Mapping[str, Any], ...]]
    variant_keys_by_module: Mapping[str, frozenset[str]]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "VariantCatalog":
        raw_modules = payload.get("modules", payload.get("parts"))
        if not isinstance(raw_modules, Mapping):
            raise ValueError("variant catalog must expose a modules object")

        module_payloads: dict[str, Mapping[str, Any]] = {}
        records_by_module: dict[str, tuple[Mapping[str, Any], ...]] = {}
        keys_by_module: dict[str, frozenset[str]] = {}

        for module, raw_module_payload in raw_modules.items():
            if not isinstance(module, str) or not module.strip():
                continue
            if not isinstance(raw_module_payload, Mapping):
                raise ValueError(f"{module}: catalog entry must be an object")

            records = tuple(_variant_records(module, raw_module_payload))
            if not records:
                raise ValueError(f"{module}: variants must not be empty")

            keys: set[str] = set()
            for record in records:
                variant_key = record.get("variant_key")
                if not isinstance(variant_key, str) or not variant_key.strip():
                    raise ValueError(f"{module}: variant_key missing")
                keys.add(variant_key.strip())

            module_payloads[module] = raw_module_payload
            records_by_module[module] = records
            keys_by_module[module] = frozenset(keys)

        return cls(
            modules=module_payloads,
            variant_records_by_module=records_by_module,
            variant_keys_by_module=keys_by_module,
        )


@dataclass(frozen=True)
class VariantSelectionRequest:
    display_name: str = ""
    guardian_target: str = ""
    protection_target: str = ""
    temperament_mood: str = ""
    height_cm: float | None = None
    colors: Sequence[str] | Mapping[str, Any] | None = None
    selected_parts: Sequence[Any] | Mapping[str, Any] | None = None
    memo_prompt: str = ""
    explicit_variants: Mapping[str, str] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "VariantSelectionRequest":
        return cls(
            display_name=_string(payload.get("display_name") or payload.get("name")),
            guardian_target=_string(payload.get("guardian") or payload.get("guardian_target")),
            protection_target=_string(
                payload.get("protection_target")
                or payload.get("protect_target")
                or payload.get("target")
            ),
            temperament_mood=_string(
                payload.get("temperament_mood")
                or payload.get("temperament")
                or payload.get("mood")
            ),
            height_cm=_float_or_none(payload.get("height_cm") or payload.get("height")),
            colors=payload.get("colors"),
            selected_parts=payload.get("selected_parts") or payload.get("parts"),
            memo_prompt=_string(payload.get("memo_prompt") or payload.get("memo") or payload.get("prompt")),
            explicit_variants=_string_mapping(
                payload.get("explicit_variants")
                or payload.get("selected_variants")
                or payload.get("variants")
            ),
        )


@dataclass(frozen=True)
class ModuleVariantSelection:
    module: str
    selected_variant_key: str
    selection_reason: str
    llm_provider: str = LOCAL_RULE_PROVIDER
    matched_themes: tuple[str, ...] = ()
    explicit: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "selected_variant_key": self.selected_variant_key,
            "selection_reason": self.selection_reason,
            "llm_provider": self.llm_provider,
            "matched_themes": list(self.matched_themes),
            "explicit": self.explicit,
        }


@dataclass(frozen=True)
class VariantSelectionResult:
    modules: Mapping[str, ModuleVariantSelection]
    llm_provider: str = LOCAL_RULE_PROVIDER

    def to_payload(self) -> dict[str, Any]:
        return {
            "llm_provider": self.llm_provider,
            "modules": {
                module: selection.to_payload()
                for module, selection in self.modules.items()
            },
        }


class VariantSelectionAdapter(Protocol):
    llm_provider: str

    def select(
        self,
        request: VariantSelectionRequest,
        catalog: VariantCatalog,
    ) -> VariantSelectionResult:
        ...


class LocalRuleVariantSelectionAdapter:
    llm_provider = LOCAL_RULE_PROVIDER

    def select(
        self,
        request: VariantSelectionRequest,
        catalog: VariantCatalog,
    ) -> VariantSelectionResult:
        themes = _detect_themes(request)
        selected_modules = _selected_modules(request, catalog)
        explicit_variants = _explicit_variants(request)

        selections: dict[str, ModuleVariantSelection] = {}
        for module in selected_modules:
            records = catalog.variant_records_by_module[module]
            valid_keys = catalog.variant_keys_by_module[module]
            explicit_key = _resolve_explicit_variant(
                module,
                explicit_variants.get(module),
                valid_keys,
            )
            if explicit_key:
                selections[module] = ModuleVariantSelection(
                    module=module,
                    selected_variant_key=explicit_key,
                    selection_reason="User explicit variant selection honored.",
                    llm_provider=self.llm_provider,
                    matched_themes=themes,
                    explicit=True,
                )
                continue

            selected, matched = _select_record_by_rules(module, records, themes)
            reason = _selection_reason(module, selected, matched)
            raw_explicit = explicit_variants.get(module)
            if raw_explicit:
                reason = (
                    f"Explicit variant '{raw_explicit}' was not present in the catalog; "
                    + reason
                )
            selections[module] = ModuleVariantSelection(
                module=module,
                selected_variant_key=str(selected["variant_key"]),
                selection_reason=reason,
                llm_provider=self.llm_provider,
                matched_themes=matched,
            )

        return VariantSelectionResult(
            modules=selections,
            llm_provider=self.llm_provider,
        )


class SakuraAIVariantSelectionAdapter:
    """Sakura AI backed variant selector with local-rule fallback.

    The HTTP shape intentionally follows the same Sakura AI Engine base URL and
    bearer token contract as the existing Whisper/TTS bridge. The response
    parser accepts both a direct JSON object and OpenAI-compatible chat
    completion envelopes so the backend can tolerate small provider differences.
    """

    llm_provider = SAKURA_AI_PROVIDER

    def __init__(
        self,
        *,
        config: SakuraAIEngineConfig | None = None,
        model: str | None = None,
        fallback_adapter: VariantSelectionAdapter | None = None,
        endpoint_path: str = DEFAULT_SAKURA_LLM_ENDPOINT,
        dotenv_path: str | Path = ".env",
    ) -> None:
        self.config = config or resolve_sakura_config(dotenv_path=dotenv_path)
        self.model = model or resolve_sakura_llm_model(dotenv_path=dotenv_path)
        self.fallback_adapter = fallback_adapter or LocalRuleVariantSelectionAdapter()
        self.endpoint_path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"

    def select(
        self,
        request: VariantSelectionRequest,
        catalog: VariantCatalog,
    ) -> VariantSelectionResult:
        if not self.config.token:
            return self.fallback_adapter.select(request, catalog)

        try:
            payload = self._post_selection_request(request, catalog)
            return self._result_from_payload(payload, request, catalog)
        except (SakuraAIEngineError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return self.fallback_adapter.select(request, catalog)

    def _post_selection_request(
        self,
        request: VariantSelectionRequest,
        catalog: VariantCatalog,
    ) -> Mapping[str, Any]:
        token = self.config.token
        if not token:
            raise SakuraAIEngineError("Sakura AI Engine token is missing.")

        body = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You select tokusatsu hero armor variants. Return only JSON with "
                        "selected_variant_keys and optional selection_reasons. Use only "
                        "variant keys that exist in the provided catalog."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        _sakura_selection_prompt_payload(request, catalog),
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        http_request = Request(
            url=f"{self.config.base_url}{self.endpoint_path}",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SakuraAIEngineError(f"Sakura AI Engine HTTP error: status={exc.code} body={detail}") from exc
        except URLError as exc:
            raise SakuraAIEngineError(f"Sakura AI Engine connection error: {exc}") from exc

        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, Mapping):
            raise SakuraAIEngineError("Sakura AI Engine returned a non-object JSON payload.")
        return parsed

    def _result_from_payload(
        self,
        payload: Mapping[str, Any],
        request: VariantSelectionRequest,
        catalog: VariantCatalog,
    ) -> VariantSelectionResult:
        normalized_payload = _extract_sakura_selection_payload(payload)
        selected_keys = normalized_payload.get("selected_variant_keys")
        if not isinstance(selected_keys, Mapping):
            raise SakuraAIEngineError("Sakura variant response did not include selected_variant_keys.")

        reasons = normalized_payload.get("selection_reasons")
        if not isinstance(reasons, Mapping):
            reasons = {}

        fallback = self.fallback_adapter.select(request, catalog)
        target_modules = _selected_modules(request, catalog)
        selections: dict[str, ModuleVariantSelection] = {}
        for module in target_modules:
            valid_keys = catalog.variant_keys_by_module.get(module, frozenset())
            selected_key = _resolve_explicit_variant(module, _string(selected_keys.get(module)), valid_keys)
            if selected_key:
                selections[module] = ModuleVariantSelection(
                    module=module,
                    selected_variant_key=selected_key,
                    selection_reason=_string(reasons.get(module))
                    or f"Sakura AI {self.model} selected this catalog variant from the user profile.",
                    llm_provider=f"{self.llm_provider}:{self.model}",
                    explicit=False,
                )
                continue
            fallback_selection = fallback.modules.get(module)
            if fallback_selection is not None:
                selections[module] = fallback_selection

        if not selections:
            return fallback

        return VariantSelectionResult(
            modules=selections,
            llm_provider=f"{self.llm_provider}:{self.model}",
        )


def load_variant_catalog(path: str | Path | None = None) -> VariantCatalog:
    catalog_path = Path(path) if path is not None else DEFAULT_CATALOG_PATH
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("variant catalog root must be an object")
    return VariantCatalog.from_payload(payload)


def select_variants(
    request: VariantSelectionRequest | Mapping[str, Any],
    *,
    catalog: VariantCatalog | None = None,
    catalog_path: str | Path | None = None,
    adapter: VariantSelectionAdapter | None = None,
) -> VariantSelectionResult:
    normalized_request = (
        VariantSelectionRequest.from_payload(request)
        if isinstance(request, Mapping)
        else request
    )
    resolved_catalog = catalog or load_variant_catalog(catalog_path)
    resolved_adapter = adapter or LocalRuleVariantSelectionAdapter()
    return resolved_adapter.select(normalized_request, resolved_catalog)


def select_variants_payload(
    request: VariantSelectionRequest | Mapping[str, Any],
    *,
    catalog: VariantCatalog | None = None,
    catalog_path: str | Path | None = None,
    adapter: VariantSelectionAdapter | None = None,
) -> dict[str, Any]:
    return select_variants(
        request,
        catalog=catalog,
        catalog_path=catalog_path,
        adapter=adapter,
    ).to_payload()


def resolve_sakura_llm_model(
    *,
    explicit: str | None = None,
    dotenv_path: str | Path = ".env",
) -> str:
    dotenv = _load_dotenv(dotenv_path)
    return (
        explicit
        or os.getenv("SAKURA_LLM_MODEL")
        or dotenv.get("SAKURA_LLM_MODEL")
        or DEFAULT_SAKURA_LLM_MODEL
    )


def _sakura_selection_prompt_payload(
    request: VariantSelectionRequest,
    catalog: VariantCatalog,
) -> dict[str, Any]:
    modules = _selected_modules(request, catalog)
    return {
        "task": "select_armor_variants",
        "rules": [
            "Select exactly one variant_key for each selected module.",
            "Use only keys listed in catalog.modules[module].variants.",
            "Prefer a cohesive bright tokusatsu hero suit silhouette.",
            "Honor explicit user variants if present and valid.",
        ],
        "user_profile": {
            "display_name": request.display_name,
            "guardian_target": request.guardian_target,
            "protection_target": request.protection_target,
            "temperament_mood": request.temperament_mood,
            "height_cm": request.height_cm,
            "colors": request.colors,
            "memo_prompt": request.memo_prompt,
            "explicit_variants": dict(request.explicit_variants or {}),
        },
        "selected_modules": list(modules),
        "catalog": {
            module: {
                "variants": [
                    {
                        key: value
                        for key, value in record.items()
                        if key
                        in {
                            "variant_key",
                            "display_name",
                            "label",
                            "silhouette",
                            "detail_features",
                            "recommended_topping_slots",
                            "base_motif_link",
                        }
                    }
                    for record in catalog.variant_records_by_module[module]
                ]
            }
            for module in modules
        },
        "expected_json": {
            "selected_variant_keys": {module: f"{module}:<variant>" for module in modules},
            "selection_reasons": {module: "<short reason>" for module in modules},
        },
    }


def _extract_sakura_selection_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(payload.get("selected_variant_keys"), Mapping):
        return payload

    choices = payload.get("choices")
    if isinstance(choices, Sequence) and not isinstance(choices, (str, bytes)):
        for choice in choices:
            if not isinstance(choice, Mapping):
                continue
            message = choice.get("message")
            if not isinstance(message, Mapping):
                continue
            content = message.get("content")
            parsed = _parse_jsonish_object(content)
            if isinstance(parsed, Mapping) and isinstance(parsed.get("selected_variant_keys"), Mapping):
                return parsed

    output = payload.get("output")
    if isinstance(output, Sequence) and not isinstance(output, (str, bytes)):
        for item in output:
            if not isinstance(item, Mapping):
                continue
            for content_item in item.get("content", ()):
                if not isinstance(content_item, Mapping):
                    continue
                parsed = _parse_jsonish_object(content_item.get("text"))
                if isinstance(parsed, Mapping) and isinstance(parsed.get("selected_variant_keys"), Mapping):
                    return parsed

    parsed = _parse_jsonish_object(payload.get("content") or payload.get("text"))
    if isinstance(parsed, Mapping):
        return parsed
    return payload


def _parse_jsonish_object(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, Mapping) else None


def _variant_records(
    module: str,
    module_payload: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    raw_variants = module_payload.get("variants")
    if isinstance(raw_variants, Mapping):
        records: list[Mapping[str, Any]] = []
        for key, raw_value in raw_variants.items():
            if not isinstance(raw_value, Mapping):
                raise ValueError(f"{module}: variant {key} must be an object")
            records.append({"variant_key": raw_value.get("variant_key", key), **raw_value})
        return records
    if isinstance(raw_variants, Sequence) and not isinstance(raw_variants, (str, bytes)):
        records = []
        for index, raw_value in enumerate(raw_variants):
            if not isinstance(raw_value, Mapping):
                raise ValueError(f"{module}: variants[{index}] must be an object")
            records.append(raw_value)
        return records
    raise ValueError(f"{module}: variants must be a list or object")


def _detect_themes(request: VariantSelectionRequest) -> tuple[str, ...]:
    text = " ".join(
        part
        for part in (
            request.display_name,
            request.guardian_target,
            request.protection_target,
            request.temperament_mood,
            _colors_text(request.colors),
            request.memo_prompt,
        )
        if part
    ).lower()

    hits: list[str] = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(_contains_term(text, keyword) for keyword in keywords):
            hits.append(theme)

    if request.height_cm is not None:
        if request.height_cm >= 180 and not any(theme in hits for theme in ("sleek", "wing")) and "bold" not in hits:
            hits.append("bold")
        elif request.height_cm <= 155 and "sleek" not in hits:
            hits.append("sleek")

    return tuple(hits)


def _select_record_by_rules(
    module: str,
    records: Sequence[Mapping[str, Any]],
    themes: Sequence[str],
) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    if not themes:
        return _base_or_first(records), ()

    scored: list[tuple[int, int, Mapping[str, Any], tuple[str, ...]]] = []
    for index, record in enumerate(records):
        profile = _variant_profile(module, record)
        score = 0
        matched: list[str] = []
        for theme in themes:
            markers = VARIANT_THEME_MARKERS.get(theme, ())
            theme_score = sum(1 for marker in markers if _contains_term(profile, marker))
            if theme_score:
                score += theme_score
                matched.append(theme)
        scored.append((score, -index, record, tuple(matched)))

    best_score, _, best_record, matched_themes = max(scored, key=lambda item: (item[0], item[1]))
    if best_score <= 0:
        return _base_or_first(records), ()
    return best_record, matched_themes


def _selection_reason(
    module: str,
    record: Mapping[str, Any],
    matched_themes: Sequence[str],
) -> str:
    variant_key = _string(record.get("variant_key"))
    if matched_themes:
        return (
            f"Selected {variant_key} for {module} because local rules matched "
            f"{', '.join(matched_themes)} vocabulary in the user profile."
        )
    return (
        f"Selected {variant_key} for {module} as the catalog base/default variant "
        "because no rule vocabulary matched this module."
    )


def _base_or_first(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    for record in records:
        if _string(record.get("variant_key")).endswith(":base"):
            return record
    return records[0]


def _selected_modules(
    request: VariantSelectionRequest,
    catalog: VariantCatalog,
) -> tuple[str, ...]:
    selected = _modules_from_selected_parts(request.selected_parts)
    selected.extend(_explicit_variants(request).keys())
    if not selected:
        selected = list(catalog.modules.keys())

    ordered: list[str] = []
    seen: set[str] = set()
    for module in selected:
        if module in catalog.modules and module not in seen:
            ordered.append(module)
            seen.add(module)
    return tuple(ordered)


def _modules_from_selected_parts(selected_parts: Any) -> list[str]:
    modules: list[str] = []
    if isinstance(selected_parts, Mapping):
        for key, value in selected_parts.items():
            if _part_enabled(value):
                modules.append(_string(key))
        return [module for module in modules if module]

    if isinstance(selected_parts, Sequence) and not isinstance(selected_parts, (str, bytes)):
        for item in selected_parts:
            if isinstance(item, Mapping):
                if not _part_enabled(item):
                    continue
                modules.append(
                    _string(item.get("module") or item.get("part") or item.get("key") or item.get("name"))
                )
            else:
                modules.append(_string(item))
    return [module for module in modules if module]


def _part_enabled(value: Any) -> bool:
    if value is False or value is None:
        return False
    if isinstance(value, Mapping):
        return value.get("enabled", True) is not False and value.get("selected", True) is not False
    return True


def _explicit_variants(request: VariantSelectionRequest) -> dict[str, str]:
    explicit: dict[str, str] = dict(request.explicit_variants or {})
    selected_parts = request.selected_parts

    if isinstance(selected_parts, Mapping):
        for module, value in selected_parts.items():
            variant = _variant_from_part_value(value)
            if variant:
                explicit[_string(module)] = variant
        return {module: variant for module, variant in explicit.items() if module and variant}

    if isinstance(selected_parts, Sequence) and not isinstance(selected_parts, (str, bytes)):
        for item in selected_parts:
            if not isinstance(item, Mapping):
                continue
            module = _string(item.get("module") or item.get("part") or item.get("key") or item.get("name"))
            variant = _variant_from_part_value(item)
            if module and variant:
                explicit[module] = variant

    return {module: variant for module, variant in explicit.items() if module and variant}


def _variant_from_part_value(value: Any) -> str:
    if isinstance(value, str):
        return value if value.strip() else ""
    if not isinstance(value, Mapping):
        return ""
    for key in (
        "selected_variant_key",
        "variant_key",
        "variant",
        "selected_variant",
    ):
        variant = _string(value.get(key))
        if variant:
            return variant
    return ""


def _resolve_explicit_variant(
    module: str,
    raw_variant: str | None,
    valid_keys: frozenset[str],
) -> str | None:
    variant = _string(raw_variant)
    if not variant:
        return None
    if variant in valid_keys:
        return variant
    if ":" not in variant:
        expanded = f"{module}:{variant}"
        if expanded in valid_keys:
            return expanded
    return None


def _variant_profile(module: str, record: Mapping[str, Any]) -> str:
    chunks = [module]
    for key in ("variant_key", "display_name", "label", "asset_key"):
        value = record.get(key)
        if isinstance(value, str):
            chunks.append(value)
    for key in ("detail_features", "recommended_topping_slots"):
        value = record.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            chunks.extend(_string(item) for item in value)
    return " ".join(chunks).lower()


def _colors_text(colors: Sequence[str] | Mapping[str, Any] | None) -> str:
    if isinstance(colors, Mapping):
        return " ".join(_string(value) for value in colors.values())
    if isinstance(colors, Sequence) and not isinstance(colors, (str, bytes)):
        return " ".join(_string(value) for value in colors)
    return _string(colors)


def _contains_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    tokens = TOKEN_RE.findall(text.lower())
    if term in tokens:
        return True
    return term in text.lower().replace("-", "_")


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _string_mapping(value: Any) -> dict[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    return {
        _string(key): _string(item)
        for key, item in value.items()
        if _string(key) and _string(item)
    }


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
