import unittest

from henshin.armor_design_team import TEAM_VERSION, compile_armor_design_team


class TestArmorDesignTeam(unittest.TestCase):
    def test_compile_armor_design_team_returns_stable_roles(self) -> None:
        profile = {
            "identity_seed": "abc123",
            "palette_family": "Rescue ceramic white",
            "motif_family": "Civic shield geometry",
            "silhouette_family": "Public shield silhouette",
            "emissive_family": "Clean guidance emissive",
            "tri_view_family": "Public-defense three-view logic",
            "panel_density_family": "Measured service spacing",
        }
        variation = {
            "variation_seed": "run-1",
            "finish_guidance": "Keep surfaces stable.",
            "emissive_guidance": "Lift guidance lines slightly.",
        }

        first = compile_armor_design_team(user_armor_profile=profile, style_variation=variation)
        second = compile_armor_design_team(user_armor_profile=profile, style_variation=variation)

        self.assertEqual(first["team_version"], TEAM_VERSION)
        self.assertEqual(first["team_seed"], second["team_seed"])
        self.assertGreaterEqual(len(first["roles"]), 10)
        roles_by_key = {role["key"]: role for role in first["roles"]}
        self.assertIn("lore_architect", roles_by_key)
        self.assertIn("operator_oath_keeper", roles_by_key)
        self.assertIn("dock_chief", roles_by_key)
        self.assertIn("atlas_compositor", roles_by_key)
        self.assertIn("uv_engineer", roles_by_key)
        self.assertIn("reject_gatekeeper", roles_by_key)
        self.assertIn("normal", roles_by_key["uv_engineer"]["directive"])
        self.assertIn("Rescue ceramic white", roles_by_key["material_director"]["directive"])
        self.assertEqual(first["review_sequence"], [role["key"] for role in first["roles"]])
        self.assertTrue(any("concept sheet" in item for item in first["hard_rejects"]))
        self.assertIn("UV topology", first["operating_rule"])


if __name__ == "__main__":
    unittest.main()
