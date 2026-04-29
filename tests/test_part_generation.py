import json
import os
import shutil
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from henshin.image_providers import GeneratedImage
from henshin.part_generation import (
    GenerationRequest,
    build_generation_cache_key,
    build_generation_waves,
    normalize_provider_profile_name,
    resolve_provider_profile,
    run_generate_parts,
)


class TestPartGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tests/.tmp/test_part_generation") / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        mesh_dir = self.root / "viewer" / "assets" / "meshes"
        mesh_dir.mkdir(parents=True, exist_ok=True)
        mesh_payload = {
            "format": "mesh.v1",
            "positions": [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0],
            "normals": [0, 0, 1] * 4,
            "uv": [0.12, 0.12, 0.88, 0.12, 0.88, 0.88, 0.12, 0.88],
            "indices": [0, 1, 2, 0, 2, 3],
        }
        for part in ("helmet", "chest", "back", "left_forearm"):
            (mesh_dir / f"{part}.mesh.json").write_text(
                json.dumps(mesh_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        self.spec_path = self.root / "spec.json"
        self.spec_path.write_text(
            json.dumps(
                {
                    "style_tags": ["metal", "audit"],
                    "operator_profile": {
                        "protect_archetype": "citizens",
                        "temperament_bias": "calm",
                        "color_mood": "industrial_gray",
                    },
                    "palette": {"primary": "#112233", "secondary": "#ccddee", "emissive": "#22ccff"},
                    "generation": {},
                    "modules": {
                        "helmet": {"enabled": True, "asset_ref": "viewer/assets/meshes/helmet.mesh.json"},
                        "chest": {"enabled": True, "asset_ref": "viewer/assets/meshes/chest.mesh.json"},
                        "back": {"enabled": True, "asset_ref": "viewer/assets/meshes/back.mesh.json"},
                        "left_forearm": {"enabled": True, "asset_ref": "viewer/assets/meshes/left_forearm.mesh.json"},
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)

    def test_build_generation_waves_prioritizes_showcase_parts(self) -> None:
        waves = build_generation_waves(["left_forearm", "helmet", "back", "chest"])
        self.assertEqual(waves[0], ["helmet", "chest"])
        self.assertEqual(waves[1], ["back", "left_forearm"])

    def test_cache_key_changes_with_reference_hash(self) -> None:
        key_a = build_generation_cache_key(
            provider="fal",
            model_id="fal-ai/flux/schnell",
            part="helmet",
            texture_mode="mesh_uv",
            prompt="a",
            reference_hash="ref-a",
            suitspec_generation_version="v1",
        )
        key_b = build_generation_cache_key(
            provider="fal",
            model_id="fal-ai/flux/schnell",
            part="helmet",
            texture_mode="mesh_uv",
            prompt="a",
            reference_hash="ref-b",
            suitspec_generation_version="v1",
        )
        self.assertNotEqual(key_a, key_b)

    def test_resolve_provider_profile_nano_banana_uses_gemini_models(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GEMINI_FAST_MODEL": "gemini-2.5-flash-image",
                "GEMINI_REFINE_MODEL": "gemini-2.5-flash-image",
                "GEMINI_HERO_MODEL": "gemini-3-pro-image-preview",
                "GEMINI_FALLBACK_MODEL": "gemini-3.1-flash-image-preview",
            },
            clear=False,
        ):
            profile = resolve_provider_profile("nano_banana")

        self.assertEqual(profile["fast_draft"].provider, "gemini")
        self.assertEqual(profile["fast_draft"].model_id, "gemini-2.5-flash-image")
        self.assertEqual(profile["quality_refine"].provider, "gemini")
        self.assertEqual(profile["hero_render"].model_id, "gemini-3-pro-image-preview")
        self.assertEqual(profile["fallback_fast"].model_id, "gemini-3.1-flash-image-preview")

    def test_legacy_exhibition_profile_aliases_to_nano_banana(self) -> None:
        with patch.dict(os.environ, {"GEMINI_FALLBACK_MODEL": "gemini-2.5-flash-image"}, clear=False):
            profile = resolve_provider_profile("exhibition")

        self.assertEqual(normalize_provider_profile_name("exhibition"), "nano_banana")
        self.assertEqual(profile["fast_draft"].provider, "gemini")
        self.assertEqual(profile["quality_refine"].provider, "gemini")
        self.assertEqual(profile["hero_render"].provider, "gemini")
        self.assertEqual(profile["fallback_fast"].provider, "gemini")
        self.assertEqual(profile["fallback_fast"].model_id, "gemini-2.5-flash-image")

    def test_nano_banana_profile_ignores_legacy_gemini_model_id_for_speed(self) -> None:
        with patch.dict(os.environ, {"GEMINI_MODEL_ID": "gemini-3-pro-image-preview"}, clear=False):
            profile = resolve_provider_profile("nano_banana")

        self.assertEqual(profile["fast_draft"].model_id, "gemini-2.5-flash-image")

    def test_run_generate_parts_hits_cache_on_second_run(self) -> None:
        call_count = {"value": 0}

        def fake_provider(*args, **kwargs):
            call_count["value"] += 1
            return GeneratedImage(
                provider="fal",
                model_id="fal-ai/flux/schnell",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-1",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=12,
                inference_ms=34,
                total_ms=46,
            )

        req = GenerationRequest(
            suitspec="spec.json",
            root="sessions",
            session_id="S-CACHE-1",
            parts=["helmet"],
            use_cache=True,
            texture_mode="mesh_uv",
            provider_profile="exhibition",
        )
        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            first = run_generate_parts(req, repo_root=self.root)
            second = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-CACHE-2",
                    parts=["helmet"],
                    use_cache=True,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                ),
                repo_root=self.root,
            )

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(call_count["value"], 1)
        self.assertEqual(second["cache_hit_count"], 1)
        first_summary = json.loads((self.root / first["summary_path"]).read_text(encoding="utf-8"))
        second_summary = json.loads((self.root / second["summary_path"]).read_text(encoding="utf-8"))
        self.assertEqual(first_summary["provider_profile"], "nano_banana")
        self.assertEqual(second_summary["provider_profile"], "nano_banana")

    def test_update_suitspec_runtime_metadata_does_not_poison_cache(self) -> None:
        call_count = {"value": 0}

        def fake_provider(*args, **kwargs):
            call_count["value"] += 1
            return GeneratedImage(
                provider="fal",
                model_id="fal-ai/flux/schnell",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id=f"resp-{call_count['value']}",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=12,
                inference_ms=34,
                total_ms=46,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            first = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-CACHE-STABLE-1",
                    parts=["helmet"],
                    use_cache=True,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                    update_suitspec=True,
                ),
                repo_root=self.root,
            )
            second = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-CACHE-STABLE-2",
                    parts=["helmet"],
                    use_cache=True,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                    update_suitspec=True,
                ),
                repo_root=self.root,
            )

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(call_count["value"], 1)
        self.assertEqual(second["cache_hit_count"], 1)
        saved_spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_spec["generation"]["provider_profile"], "nano_banana")
        self.assertIn("part_prompts", saved_spec["generation"])
        self.assertNotIn("texture_path", saved_spec["modules"]["helmet"])

    def test_writes_final_texture_with_passing_gate_updates_suitspec_texture_path(self) -> None:
        def fake_provider(*args, **kwargs):
            return GeneratedImage(
                provider="fal",
                model_id="fal-ai/flux/schnell",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-final-texture",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=12,
                inference_ms=34,
                total_ms=46,
            )

        with (
            patch("henshin.part_generation._provider_attempt", side_effect=fake_provider),
            patch("henshin.part_generation.audit_viewer_mesh_assets", return_value={"status": "pass"}),
        ):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-FINAL-TEXTURE-1",
                    parts=["helmet"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                    update_suitspec=True,
                    writes_final_texture=True,
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        saved_spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        expected_texture_path = result["summary_path"].rsplit("/", 1)[0] + "/helmet.generated.png"
        self.assertEqual(saved_spec["modules"]["helmet"]["texture_path"], expected_texture_path)

    def test_run_generate_parts_clamps_zero_parallelism(self) -> None:
        call_count = {"value": 0}

        def fake_provider(*args, **kwargs):
            call_count["value"] += 1
            return GeneratedImage(
                provider="fal",
                model_id="fal-ai/flux/schnell",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-1",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=0,
                inference_ms=10,
                total_ms=10,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-PARALLEL-ZERO",
                    parts=["helmet"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                    max_parallel=0,
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(call_count["value"], 1)

    def test_generation_summary_orders_parts_by_request(self) -> None:
        def fake_provider(*args, **kwargs):
            prompt = kwargs["prompt"]
            if "Target module: helmet" in prompt:
                time.sleep(0.05)
            return GeneratedImage(
                provider="fal",
                model_id="fal-ai/flux/schnell",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=prompt,
                response_id="resp-1",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=0,
                inference_ms=10,
                total_ms=10,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-SUMMARY-ORDER",
                    parts=["helmet", "chest"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    provider_profile="exhibition",
                    max_parallel=2,
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        summary = json.loads((self.root / result["summary_path"]).read_text(encoding="utf-8"))
        self.assertEqual(list(summary["generated"].keys()), ["helmet", "chest"])
        self.assertEqual(list(summary["part_metrics"].keys()), ["helmet", "chest"])

    def test_run_generate_parts_dry_run_returns_uv_contracts_and_design_dna(self) -> None:
        result = run_generate_parts(
            GenerationRequest(
                suitspec="spec.json",
                root="sessions",
                parts=["helmet"],
                dry_run=True,
                texture_mode="mesh_uv",
                provider_profile="nano_banana",
                emotion_profile={"drive": "protect", "scene": "urban_night", "protect_target": "citizens"},
            ),
            repo_root=self.root,
        )

        self.assertTrue(result["ok"])
        self.assertIn("design_dna", result)
        self.assertIn("uv_contracts", result)
        self.assertIn("emotion_profile", result)
        self.assertIn("emotion_directives", result)
        self.assertIn("style_variation", result)
        self.assertIn("uv_guides", result)
        self.assertIn("operator_profile_raw", result)
        self.assertIn("operator_profile_resolved", result)
        self.assertIn("user_armor_profile", result)
        self.assertIn("helmet", result["uv_contracts"])
        self.assertEqual(result["uv_contracts"]["helmet"]["fill_ratio_target"], [88, 96])
        self.assertIn("Core emotional trigger", result["generation_brief_compiled"])
        self.assertIn("Variation seed", result["generation_brief_compiled"])
        self.assertIn("emotion_profile_raw", result)
        self.assertIn("emotion_profile_resolved", result)
        self.assertIn("guide_hash", result["uv_guides"]["helmet"])
        self.assertEqual(result["user_armor_profile"]["palette_family"], "Orbital audit gray")

    def test_run_generate_parts_uses_uv_guide_reference_for_mesh_uv(self) -> None:
        captured_references = []

        def fake_provider(*args, **kwargs):
            captured_references.append(kwargs.get("references"))
            return GeneratedImage(
                provider="gemini",
                model_id="gemini-2.5-flash-image",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-1",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=0,
                inference_ms=10,
                total_ms=10,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-UVGUIDE-1",
                    parts=["helmet"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    provider_profile="nano_banana",
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(len(captured_references), 1)
        self.assertEqual(len(captured_references[0]), 1)
        self.assertEqual(captured_references[0][0].mime_type, "image/png")
        summary = json.loads((self.root / result["summary_path"]).read_text(encoding="utf-8"))
        self.assertIn("uv_guide_path", summary["generated"]["helmet"])
        self.assertEqual(summary["generated"]["helmet"]["reference_stack"][0]["role"], "uv_engineering_guide")

    def test_run_generate_parts_uv_refine_uses_guide_then_concept(self) -> None:
        captured_references = []

        def fake_provider(*args, **kwargs):
            captured_references.append(kwargs.get("references"))
            return GeneratedImage(
                provider="gemini",
                model_id="gemini-2.5-flash-image",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-2",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=0,
                inference_ms=10,
                total_ms=10,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-UVGUIDE-2",
                    parts=["helmet"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    uv_refine=True,
                    provider_profile="nano_banana",
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        self.assertIsNone(captured_references[0])
        self.assertEqual(len(captured_references[1]), 2)
        self.assertEqual(captured_references[1][0].mime_type, "image/png")
        self.assertEqual(captured_references[1][1].mime_type, "image/png")
        summary = json.loads((self.root / result["summary_path"]).read_text(encoding="utf-8"))
        self.assertEqual(summary["generated"]["helmet"]["reference_stack"][0]["role"], "uv_engineering_guide")
        self.assertEqual(summary["generated"]["helmet"]["reference_stack"][1]["role"], "style_concept")

    def test_operator_profile_override_changes_user_profile_without_mutating_file(self) -> None:
        result = run_generate_parts(
            GenerationRequest(
                suitspec="spec.json",
                root="sessions",
                parts=["helmet"],
                dry_run=True,
                texture_mode="mesh_uv",
                provider_profile="nano_banana",
                operator_profile_override={
                    "protect_archetype": "future",
                    "temperament_bias": "fierce",
                    "color_mood": "clear_white",
                },
            ),
            repo_root=self.root,
        )

        self.assertEqual(result["operator_profile_resolved"]["protect_archetype"], "future")
        self.assertEqual(result["user_armor_profile"]["palette_family"], "Rescue ceramic white")

        stored_spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        self.assertEqual(stored_spec["operator_profile"]["protect_archetype"], "citizens")

    def test_user_armor_profile_stays_stable_across_emotion_changes(self) -> None:
        first = run_generate_parts(
            GenerationRequest(
                suitspec="spec.json",
                root="sessions",
                parts=["helmet"],
                dry_run=True,
                texture_mode="mesh_uv",
                provider_profile="nano_banana",
                emotion_profile={"drive": "protect", "protect_target": "the crowd"},
            ),
            repo_root=self.root,
        )
        second = run_generate_parts(
            GenerationRequest(
                suitspec="spec.json",
                root="sessions",
                parts=["helmet"],
                dry_run=True,
                texture_mode="mesh_uv",
                provider_profile="nano_banana",
                emotion_profile={"drive": "rage", "protect_target": "the line"},
            ),
            repo_root=self.root,
        )

        self.assertEqual(first["user_armor_profile"]["palette_family"], second["user_armor_profile"]["palette_family"])
        self.assertEqual(
            first["user_armor_profile"]["silhouette_family"],
            second["user_armor_profile"]["silhouette_family"],
        )
        self.assertNotEqual(first["style_variation"]["variation_seed"], second["style_variation"]["variation_seed"])

    def test_update_suitspec_writes_last_operator_profile_metadata(self) -> None:
        def fake_provider(*args, **kwargs):
            return GeneratedImage(
                provider="gemini",
                model_id="gemini-2.5-flash-image",
                mime_type="image/png",
                image_bytes=b"fakepng",
                prompt=kwargs["prompt"],
                response_id="resp-3",
                timestamp="2026-04-09T00:00:00+00:00",
                queue_wait_ms=0,
                inference_ms=10,
                total_ms=10,
            )

        with patch("henshin.part_generation._provider_attempt", side_effect=fake_provider):
            result = run_generate_parts(
                GenerationRequest(
                    suitspec="spec.json",
                    root="sessions",
                    session_id="S-OPMETA-1",
                    parts=["helmet"],
                    use_cache=False,
                    texture_mode="mesh_uv",
                    provider_profile="nano_banana",
                    update_suitspec=True,
                    operator_profile_override={
                        "protect_archetype": "future",
                        "temperament_bias": "gentle",
                        "color_mood": "clear_white",
                    },
                ),
                repo_root=self.root,
            )

        self.assertTrue(result["ok"])
        saved_spec = json.loads(self.spec_path.read_text(encoding="utf-8"))
        generation = saved_spec["generation"]
        self.assertEqual(generation["last_operator_profile_resolved"]["protect_archetype"], "future")
        self.assertEqual(generation["last_user_armor_profile"]["palette_family"], "Rescue ceramic white")


if __name__ == "__main__":
    unittest.main()
