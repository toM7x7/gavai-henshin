import importlib.util
import json
import unittest
from pathlib import Path

from henshin.armor_blueprint import axes_from_intent, compile_blueprint, llm_prompt
from henshin.validators import validate_against_schema

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_builder_module():
    path = REPO_ROOT / "tools" / "blender" / "armor_blueprint_builder.py"
    spec = importlib.util.spec_from_file_location("armor_blueprint_builder", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestArmorBlueprintSchema(unittest.TestCase):
    def test_sample_blueprint_validates(self) -> None:
        payload = json.loads(
            (REPO_ROOT / "examples" / "armor-blueprint.sample.json").read_text(encoding="utf-8")
        )
        validate_against_schema(payload, "armor-blueprint")

    def test_compiled_blueprint_validates_and_is_deterministic(self) -> None:
        intent = "手順を省略しない誓い。守護と闘志、鋭いバイザー。"
        a = compile_blueprint(intent)
        b = compile_blueprint(intent)
        self.assertEqual(a, b)
        validate_against_schema(a, "armor-blueprint")
        self.assertTrue(a["blueprint_id"].startswith("ABP-"))
        modules = [p["module"] for p in a["parts"]]
        self.assertIn("helmet", modules)


class TestIntentCompiler(unittest.TestCase):
    def test_guard_keywords_dominate(self) -> None:
        axes = axes_from_intent("仲間を守る盾になる。護りの誓い。")
        self.assertGreater(axes["guard"], axes["fighting"])

    def test_fighting_intent_grows_horns_and_sharp_edges(self) -> None:
        bp = compile_blueprint("闘志。牙を剥き、刃のように戦う。", axes={"fighting": 0.9})
        helmet = next(p for p in bp["parts"] if p["module"] == "helmet")
        kinds = {f["kind"] for f in helmet["features"]}
        self.assertIn("horn_pair", kinds)
        # cross_section is now a continuous exponent; fighting -> sharp (< 2.0)
        self.assertLess(helmet["silhouette"]["cross_section"], 2.0)
        self.assertEqual(helmet["surface"]["edge_style"], "razor")

    def test_neutral_intent_defaults_to_guard_palette(self) -> None:
        # neutral intent stays guard-dominant; palette is jittered per-suit so
        # the emissive is a teal near the guard family, not a fixed hex
        bp = compile_blueprint("")
        self.assertEqual(bp["emotion_axes"], {"guard": 0.5})
        r, g, b = (int(bp["palette"]["emissive"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        self.assertTrue(g > 150 and b > 150 and r < g, "teal-ish guard glow")

    def test_distinct_intents_yield_distinct_suits(self) -> None:
        a = compile_blueprint("闘志。赤い牙、鋭い刃。")
        b = compile_blueprint("哀傷。静かな青、丸い曲線。")
        self.assertNotEqual(a["blueprint_id"], b["blueprint_id"])
        self.assertNotEqual(a["palette"]["base_surface"], b["palette"]["base_surface"])
        ha = next(p for p in a["parts"] if p["module"] == "helmet")["silhouette"]["cross_section"]
        hb = next(p for p in b["parts"] if p["module"] == "helmet")["silhouette"]["cross_section"]
        self.assertLess(ha, hb, "fighting suit sharper than sorrow suit")

    def test_llm_prompt_carries_contract_and_intent(self) -> None:
        prompt = llm_prompt("哀傷の静かな装甲")
        self.assertIn("armor-blueprint.v1", prompt)
        self.assertIn("哀傷の静かな装甲", prompt)
        self.assertIn("起動拒否", prompt)


class TestBuilderPureMath(unittest.TestCase):
    def test_resolve_part_defaults_without_bpy(self) -> None:
        mod = _load_builder_module()
        spec = mod.resolve_part({"module": "helmet"})
        self.assertEqual(spec["module"], "helmet")
        self.assertEqual(spec["envelope"], (0.2856, 0.34, 0.2584))
        self.assertTrue(spec["closed_top"])
        self.assertGreaterEqual(spec["exponent"], 1.2)

    def test_right_side_modules_reuse_left_presets(self) -> None:
        mod = _load_builder_module()
        left = mod.resolve_part({"module": "left_shin"})
        right = mod.resolve_part({"module": "right_shin"})
        self.assertEqual(left["envelope"], right["envelope"])
        self.assertEqual(left["rows"], right["rows"])

    def test_catmull_rom_hits_control_points(self) -> None:
        mod = _load_builder_module()
        pts = [[0.0, 0.8], [0.5, 1.0], [1.0, 0.4]]
        self.assertAlmostEqual(mod.catmull_rom(pts, 0.0), 0.8)
        self.assertAlmostEqual(mod.catmull_rom(pts, 0.5), 1.0)
        self.assertAlmostEqual(mod.catmull_rom(pts, 1.0), 0.4)

    def test_superellipse_exponent_controls_character(self) -> None:
        mod = _load_builder_module()
        import math
        theta = math.pi / 4
        sharp_x, _ = mod.superellipse_point(theta, 1.0, 1.0, 1.5)
        round_x, _ = mod.superellipse_point(theta, 1.0, 1.0, 2.0)
        squared_x, _ = mod.superellipse_point(theta, 1.0, 1.0, 3.4)
        self.assertLess(sharp_x, round_x)
        self.assertLess(round_x, squared_x)


if __name__ == "__main__":
    unittest.main()
