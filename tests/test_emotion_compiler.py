import unittest

from henshin.emotion_compiler import compile_emotion_request


class TestEmotionCompiler(unittest.TestCase):
    def test_compile_emotion_request_generates_structured_directives(self) -> None:
        result = compile_emotion_request(
            {
                "drive": "protect",
                "scene": "orbit_patrol",
                "protect_target": "the convoy behind me",
                "vow": "No one gets through.",
            },
            "Keep chest maintenance hatches explicit.",
        )

        self.assertEqual(result["emotion_profile_raw"]["drive"], "protect")
        self.assertEqual(result["emotion_profile_resolved"]["scene"], "orbit_patrol")
        self.assertIn("Core emotional trigger: Protect", result["compiled_brief"])
        self.assertIn("Operating scene: Orbital patrol", result["compiled_brief"])
        self.assertIn("maintenance hatches", result["compiled_brief"])
        self.assertEqual(result["emotion_directives"]["drive_label"], "Protect")
        self.assertTrue(result["style_variation"]["palette_family"])
        self.assertIn("Tri-view guidance", result["compiled_brief"])

    def test_compile_emotion_request_defaults_scene_and_vow_for_partial_profile(self) -> None:
        result = compile_emotion_request(
            {
                "drive": "resolve",
                "protect_target": "the shelter line",
            },
            None,
        )

        self.assertEqual(result["emotion_profile_raw"]["drive"], "resolve")
        self.assertEqual(result["emotion_profile_resolved"]["scene"], "urban_night")
        self.assertEqual(result["emotion_profile_resolved"]["vow"], "I go forward.")
        self.assertEqual(result["resolved_defaults"]["scene"], "urban_night")
        self.assertEqual(result["resolved_defaults"]["vow"], "I go forward.")
        self.assertIn("Variation seed", result["compiled_brief"])

    def test_compile_emotion_request_uses_user_armor_profile_as_stable_base(self) -> None:
        result = compile_emotion_request(
            {
                "drive": "hope",
                "protect_target": "the evacuation route",
            },
            None,
            user_armor_profile={
                "identity_seed": "abc123",
                "palette_family": "Orbital audit gray",
                "palette_guidance": "Keep the issued gray baseline.",
                "finish_guidance": "Keep the matte shell family.",
                "emissive_guidance": "Keep diagnostics sparse.",
                "motif_guidance": "Keep the audit spine family.",
                "panel_density_guidance": "Keep panel density medium.",
                "silhouette_guidance": "Keep the silhouette upright.",
                "tri_view_guidance": "Keep all views inspection-readable.",
            },
        )

        self.assertEqual(result["style_variation"]["palette_family"], "Orbital audit gray")
        self.assertIn("Keep the issued gray baseline", result["style_variation"]["palette_guidance"])
        self.assertIn("Current emotional modulation", result["compiled_brief"])

    def test_compile_emotion_request_passthrough_when_no_profile(self) -> None:
        result = compile_emotion_request(None, "Simple note")
        self.assertIsNone(result["emotion_profile"])
        self.assertIsNone(result["emotion_profile_raw"])
        self.assertIsNone(result["emotion_profile_resolved"])
        self.assertIsNone(result["emotion_directives"])
        self.assertIsNone(result["style_variation"])
        self.assertEqual(result["compiled_brief"], "Simple note")


if __name__ == "__main__":
    unittest.main()
