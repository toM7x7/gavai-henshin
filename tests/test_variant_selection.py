from __future__ import annotations

from henshin.variant_selection import (
    LOCAL_RULE_PROVIDER,
    VariantSelectionRequest,
    load_variant_catalog,
    select_variants,
    select_variants_payload,
)


def test_variant_selection_catalog_exists_and_exposes_keys() -> None:
    catalog = load_variant_catalog()

    assert "helmet" in catalog.modules
    assert "chest" in catalog.modules
    assert "helmet:sleek" in catalog.variant_keys_by_module["helmet"]
    assert "chest:broad_guard" in catalog.variant_keys_by_module["chest"]


def test_local_rule_selection_returns_catalog_keys_for_representative_profile() -> None:
    catalog = load_variant_catalog()
    request = VariantSelectionRequest(
        display_name="Aoi Sentinel",
        protection_target="protect the city and friends",
        temperament_mood="calm guardian shield",
        height_cm=172,
        colors=["blue", "white"],
        selected_parts=["helmet", "chest", "left_shoulder", "back"],
        memo_prompt="hero guard suit with a readable stage silhouette",
    )

    result = select_variants(request, catalog=catalog)

    assert result.llm_provider == LOCAL_RULE_PROVIDER
    assert set(result.modules) == {"helmet", "chest", "left_shoulder", "back"}
    for module, selection in result.modules.items():
        assert selection.llm_provider == LOCAL_RULE_PROVIDER
        assert selection.selected_variant_key in catalog.variant_keys_by_module[module]
        assert selection.selection_reason

    assert result.modules["chest"].selected_variant_key == "chest:broad_guard"


def test_wing_vocabulary_selects_existing_wing_variant_when_available() -> None:
    catalog = load_variant_catalog()

    result = select_variants(
        {
            "display_name": "Skyline",
            "mood": "swift aerial",
            "selected_parts": ["left_shoulder", "right_shoulder"],
            "prompt": "wing flight sky feather armor",
        },
        catalog=catalog,
    )

    assert result.modules["left_shoulder"].selected_variant_key == "left_shoulder:winged_fin"
    assert result.modules["right_shoulder"].selected_variant_key == "right_shoulder:winged_fin"


def test_explicit_user_variants_are_honored_with_full_or_suffix_keys() -> None:
    catalog = load_variant_catalog()

    payload = select_variants_payload(
        {
            "selected_parts": {
                "helmet": "sleek",
                "chest": {"selected_variant_key": "chest:v_core"},
            },
            "memo": "guardian wing hero would normally influence rules",
        },
        catalog=catalog,
    )

    assert payload["llm_provider"] == LOCAL_RULE_PROVIDER
    assert payload["modules"]["helmet"]["selected_variant_key"] == "helmet:sleek"
    assert payload["modules"]["helmet"]["explicit"] is True
    assert payload["modules"]["chest"]["selected_variant_key"] == "chest:v_core"
    assert payload["modules"]["chest"]["explicit"] is True
