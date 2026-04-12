import unittest

from henshin.user_profile_compiler import compile_operator_profile


class TestUserProfileCompiler(unittest.TestCase):
    def test_same_operator_profile_produces_same_user_armor_profile(self) -> None:
        payload = {
            "protect_archetype": "citizens",
            "temperament_bias": "calm",
            "color_mood": "industrial_gray",
        }
        first = compile_operator_profile(payload)
        second = compile_operator_profile(payload)

        self.assertEqual(first["user_armor_profile"]["identity_seed"], second["user_armor_profile"]["identity_seed"])
        self.assertEqual(first["user_armor_profile"]["palette_family"], second["user_armor_profile"]["palette_family"])
        self.assertEqual(first["user_armor_profile"]["motif_family"], second["user_armor_profile"]["motif_family"])

    def test_profile_axes_change_palette_and_seed(self) -> None:
        citizens = compile_operator_profile(
            {
                "protect_archetype": "citizens",
                "temperament_bias": "calm",
                "color_mood": "industrial_gray",
            }
        )
        future = compile_operator_profile(
            {
                "protect_archetype": "future",
                "temperament_bias": "fierce",
                "color_mood": "burnt_red",
            }
        )

        self.assertNotEqual(citizens["user_armor_profile"]["identity_seed"], future["user_armor_profile"]["identity_seed"])
        self.assertNotEqual(citizens["user_armor_profile"]["palette_family"], future["user_armor_profile"]["palette_family"])
        self.assertNotEqual(citizens["user_armor_profile"]["motif_family"], future["user_armor_profile"]["motif_family"])

    def test_override_overlays_stored_profile(self) -> None:
        result = compile_operator_profile(
            {
                "protect_archetype": "citizens",
                "temperament_bias": "calm",
                "color_mood": "industrial_gray",
            },
            {
                "color_mood": "clear_white",
            },
        )

        self.assertEqual(result["operator_profile_resolved"]["protect_archetype"], "citizens")
        self.assertEqual(result["operator_profile_resolved"]["color_mood"], "clear_white")
        self.assertEqual(result["user_armor_profile"]["palette_family"], "Rescue ceramic white")


if __name__ == "__main__":
    unittest.main()
