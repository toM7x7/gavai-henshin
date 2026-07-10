import json
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any


CATALOG_PATH = Path("viewer/assets/armor-parts/variant_catalog.json")
REPO_ROOT = Path(__file__).resolve().parents[1]
PART_SPECS_PATH = REPO_ROOT / "tools" / "blender" / "armor_part_specs.py"
BUILDER_CORE_PATH = REPO_ROOT / "tools" / "blender" / "armor_builder_core.py"

EXPECTED_MODULES = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
)

P0_MIN_VARIANT_MODULES = {
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_shin",
    "right_shin",
}

P0_REQUIRED_TOPPING_SLOTS = {
    "helmet": ("crest", "visor_trim"),
    "chest": ("chest_core", "rib_trim"),
    "back": ("spine_ridge", "rear_core"),
    "waist": ("belt_buckle", "side_clip"),
    "left_shoulder": ("shoulder_fin", "edge_trim"),
    "right_shoulder": ("shoulder_fin", "edge_trim"),
    "left_upperarm": ("bicep_band", "outer_plate"),
    "right_upperarm": ("bicep_band", "outer_plate"),
    "left_forearm": ("forearm_cuff", "wrist_module"),
    "right_forearm": ("forearm_cuff", "wrist_module"),
    "left_hand": ("knuckle", "palm_emitter"),
    "right_hand": ("knuckle", "palm_emitter"),
    "left_shin": ("shin_spike", "ankle_cuff_trim"),
    "right_shin": ("shin_spike", "ankle_cuff_trim"),
}

REQUIRED_TEXTURE_ZONE_NOTE_KEYS = (
    "base_surface",
    "accent",
    "emissive",
    "trim",
    "module_focus",
)


def _load_part_specs() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("armor_part_specs_sidecar_test", PART_SPECS_PATH)
    assert spec and spec.loader, "could not load armor_part_specs module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["armor_part_specs_sidecar_test"] = module
    spec.loader.exec_module(module)
    part_specs = getattr(module, "PART_SPECS", None)
    assert isinstance(part_specs, dict), "armor_part_specs must expose PART_SPECS"
    return part_specs


def _install_blender_import_stubs() -> None:
    sys.modules.setdefault("bmesh", types.ModuleType("bmesh"))
    sys.modules.setdefault("bpy", types.ModuleType("bpy"))
    mathutils = sys.modules.setdefault("mathutils", types.ModuleType("mathutils"))
    setattr(mathutils, "Vector", list)


def _load_builder_core() -> Any:
    _install_blender_import_stubs()
    spec = importlib.util.spec_from_file_location("armor_builder_core_sidecar_test", BUILDER_CORE_PATH)
    assert spec and spec.loader, "could not load armor_builder_core module spec"
    module = importlib.util.module_from_spec(spec)
    sys.modules["armor_builder_core_sidecar_test"] = module
    spec.loader.exec_module(module)
    return module


def _read_catalog() -> dict[str, Any]:
    assert CATALOG_PATH.exists(), (
        "variant_catalog.json must be delivered at "
        "viewer/assets/armor-parts/variant_catalog.json"
    )
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "variant_catalog.json must contain a JSON object"
    return payload


def _modules(payload: dict[str, Any]) -> dict[str, Any]:
    modules = payload.get("modules", payload.get("parts"))
    assert isinstance(modules, dict), "variant catalog must expose a modules object"
    return modules


def _variant_records(module: str, module_payload: Any) -> list[dict[str, Any]]:
    assert isinstance(module_payload, dict), f"{module}: catalog entry must be an object"
    raw_variants = module_payload.get("variants")
    assert isinstance(raw_variants, (list, dict)), f"{module}: variants must be a list or object"
    if isinstance(raw_variants, dict):
        records = []
        for key, value in raw_variants.items():
            assert isinstance(value, dict), f"{module}: variant {key} must be an object"
            records.append({"variant_key": value.get("variant_key", key), **value})
        return records
    for index, value in enumerate(raw_variants):
        assert isinstance(value, dict), f"{module}: variants[{index}] must be an object"
    return raw_variants


def _slot_names(value: Any) -> set[str]:
    assert isinstance(value, list), "P0 catalog topping_slots must be an object list"
    names: set[str] = set()
    for index, slot in enumerate(value):
        assert isinstance(slot, dict), f"topping_slots[{index}] must be an object"
        slot_name = slot.get("topping_slot")
        assert isinstance(slot_name, str) and slot_name.strip(), (
            f"topping_slots[{index}].topping_slot missing"
        )
        names.add(slot_name.strip())
    return names


def _assert_sidecar_slot_contract(module: str, slot: Any) -> None:
    assert isinstance(slot, dict), f"{module}: topping slot must be an object"
    slot_name = slot.get("topping_slot")
    assert isinstance(slot_name, str) and slot_name.strip(), f"{module}: topping_slot missing"
    assert slot.get("parent_module") == module, f"{module}:{slot_name}: parent_module mismatch"

    transform = slot.get("slot_transform")
    assert isinstance(transform, dict), f"{module}:{slot_name}: slot_transform missing"
    anchor = transform.get("anchor")
    rotation = transform.get("rotation_deg")
    assert isinstance(anchor, list) and len(anchor) == 3, f"{module}:{slot_name}: anchor must be xyz"
    assert isinstance(rotation, list) and len(rotation) == 3, (
        f"{module}:{slot_name}: rotation_deg must be xyz"
    )

    max_bbox = slot.get("max_bbox_m")
    assert isinstance(max_bbox, dict), f"{module}:{slot_name}: max_bbox_m missing"
    for axis in ("x", "y", "z"):
        value = max_bbox.get(axis)
        assert isinstance(value, (int, float)) and value > 0, (
            f"{module}:{slot_name}: max_bbox_m.{axis} must be positive"
        )

    conflicts = slot.get("conflicts_with")
    assert isinstance(conflicts, list), f"{module}:{slot_name}: conflicts_with must be a list"


def test_variant_catalog_covers_modules_variants_and_detail_contracts() -> None:
    payload = _read_catalog()

    assert payload.get("contract_version") == "armor-part-variant-catalog.v1"
    modules = _modules(payload)
    missing_modules = [module for module in EXPECTED_MODULES if module not in modules]
    assert missing_modules == []

    for module in EXPECTED_MODULES:
        variants = _variant_records(module, modules[module])
        minimum_variant_count = 2 if module in P0_MIN_VARIANT_MODULES else 1
        assert len(variants) >= minimum_variant_count, (
            f"{module}: expected at least {minimum_variant_count} variant(s)"
        )

        seen_variant_keys: set[str] = set()
        for variant in variants:
            variant_key = variant.get("variant_key")
            assert isinstance(variant_key, str) and variant_key.startswith(f"{module}:")
            assert variant_key not in seen_variant_keys, f"{module}: duplicate {variant_key}"
            seen_variant_keys.add(variant_key)

            display_name = variant.get("display_name", variant.get("label"))
            assert isinstance(display_name, str) and display_name.strip(), (
                f"{variant_key}: display_name missing"
            )

            motif_link = variant.get("base_motif_link")
            assert isinstance(motif_link, dict), f"{variant_key}: base_motif_link must be an object"
            assert isinstance(motif_link.get("name"), str) and motif_link["name"].strip()
            assert isinstance(motif_link.get("surface_zone"), str) and motif_link["surface_zone"].strip()

            detail_features = variant.get("detail_features")
            assert isinstance(detail_features, list), f"{variant_key}: detail_features must be a list"
            assert len([item for item in detail_features if isinstance(item, str) and item.strip()]) >= 2, (
                f"{variant_key}: detail_features must prevent flat/no-detail variants"
            )

        if module in P0_REQUIRED_TOPPING_SLOTS:
            slot_names = _slot_names(modules[module].get("topping_slots"))
            missing_slots = [
                slot
                for slot in P0_REQUIRED_TOPPING_SLOTS[module]
                if slot not in slot_names
            ]
            assert missing_slots == [], f"{module}: missing P0 topping slots {missing_slots}"


def test_part_specs_sidecar_metadata_contract_covers_wave2_fields() -> None:
    part_specs = _load_part_specs()

    for module in EXPECTED_MODULES:
        part_spec = part_specs.get(module)
        assert isinstance(part_spec, dict), f"{module}: PART_SPECS entry missing"

        conflicts = part_spec.get("conflicts_with")
        assert isinstance(conflicts, list), f"{module}: conflicts_with must be a list"

        texture_zone_notes = part_spec.get("texture_zone_notes")
        assert isinstance(texture_zone_notes, dict), f"{module}: texture_zone_notes must be an object"
        missing_note_keys = [
            key
            for key in REQUIRED_TEXTURE_ZONE_NOTE_KEYS
            if not isinstance(texture_zone_notes.get(key), str) or not texture_zone_notes[key].strip()
        ]
        assert missing_note_keys == [], f"{module}: missing texture_zone_notes {missing_note_keys}"

        slots = part_spec.get("topping_slots")
        assert isinstance(slots, list) and slots, f"{module}: topping_slots must be non-empty"
        for slot in slots:
            _assert_sidecar_slot_contract(module, slot)

        if module in P0_REQUIRED_TOPPING_SLOTS:
            slot_names = _slot_names(slots)
            missing_slots = [
                slot
                for slot in P0_REQUIRED_TOPPING_SLOTS[module]
                if slot not in slot_names
            ]
            assert missing_slots == [], f"{module}: missing sidecar topping slots {missing_slots}"


def test_modeler_sidecar_output_includes_wave2_metadata(tmp_path: Path) -> None:
    builder_core = _load_builder_core()

    class FakeObject(dict):
        name = "armor_left_forearm_v001"
        data = None

    sidecar_path = tmp_path / "left_forearm.modeler.json"
    payload = builder_core.write_modeler_sidecar(
        FakeObject(),
        sidecar_path,
        {"module": "left_forearm", "part_id": "armor_left_forearm_v001", "category": "arm"},
        {},
    )

    assert payload.get("contract_version") == "modeler-part-sidecar.v1"
    assert isinstance(payload.get("conflicts_with"), list)
    texture_zone_notes = payload.get("texture_zone_notes")
    assert isinstance(texture_zone_notes, dict)
    assert all(isinstance(texture_zone_notes.get(key), str) for key in REQUIRED_TEXTURE_ZONE_NOTE_KEYS)
    slot_names = _slot_names(payload.get("topping_slots"))
    assert {"forearm_cuff", "wrist_module"}.issubset(slot_names)

    written = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert "conflicts_with" in written
    assert "texture_zone_notes" in written


def test_committed_modeler_sidecars_include_wave2_metadata() -> None:
    for module in EXPECTED_MODULES:
        sidecar_path = REPO_ROOT / "viewer" / "assets" / "armor-parts" / module / f"{module}.modeler.json"
        assert sidecar_path.exists(), f"{module}: committed modeler sidecar missing"
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))

        assert isinstance(payload.get("conflicts_with"), list), f"{module}: conflicts_with missing"
        texture_zone_notes = payload.get("texture_zone_notes")
        assert isinstance(texture_zone_notes, dict), f"{module}: texture_zone_notes missing"
        missing_note_keys = [
            key
            for key in REQUIRED_TEXTURE_ZONE_NOTE_KEYS
            if not isinstance(texture_zone_notes.get(key), str) or not texture_zone_notes[key].strip()
        ]
        assert missing_note_keys == [], f"{module}: missing texture_zone_notes {missing_note_keys}"

        slots = payload.get("topping_slots")
        assert isinstance(slots, list) and slots, f"{module}: committed sidecar topping_slots missing"
        for slot in slots:
            _assert_sidecar_slot_contract(module, slot)
