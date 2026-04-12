import unittest

from henshin.forge import create_draft_suitspec
from henshin.part_prompts import build_part_prompt, build_uv_refine_prompt, list_enabled_parts, resolve_part_prompts


class TestPartPrompts(unittest.TestCase):
    def test_list_enabled_parts(self) -> None:
        spec = create_draft_suitspec()
        parts = list_enabled_parts(spec)
        self.assertIn("helmet", parts)
        self.assertIn("right_forearm", parts)

    def test_build_part_prompt_default(self) -> None:
        spec = create_draft_suitspec()
        prompt = build_part_prompt("helmet", spec)
        self.assertIn("single isolated armor part image", prompt)
        self.assertIn("helmet", prompt)

    def test_build_part_prompt_mesh_uv_mode(self) -> None:
        spec = create_draft_suitspec()
        prompt = build_part_prompt("right_forearm", spec, texture_mode="mesh_uv")
        self.assertIn("UV-ready texture atlas", prompt)
        self.assertIn("Flat texture sheet only", prompt)
        self.assertIn("Texture fill ratio target", prompt)
        self.assertIn("right_forearm", prompt)

    def test_build_part_prompt_override(self) -> None:
        spec = create_draft_suitspec()
        spec["modules"]["helmet"]["generation_prompt"] = "custom helmet prompt"
        prompt = build_part_prompt("helmet", spec, texture_mode="mesh_uv")
        self.assertIn("custom helmet prompt", prompt)
        self.assertIn("UV engineering contract", prompt)
        self.assertIn("Manufacturer family", prompt)

    def test_resolve_part_prompts(self) -> None:
        spec = create_draft_suitspec()
        prompts = resolve_part_prompts(spec, ["helmet", "chest"])
        self.assertEqual(set(prompts.keys()), {"helmet", "chest"})

    def test_resolve_part_prompts_with_mode(self) -> None:
        spec = create_draft_suitspec()
        prompts = resolve_part_prompts(spec, ["helmet"], texture_mode="mesh_uv")
        self.assertIn("UV-ready texture atlas", prompts["helmet"])

    def test_build_part_prompt_includes_generation_brief(self) -> None:
        spec = create_draft_suitspec()
        prompt = build_part_prompt("helmet", spec, generation_brief="Mass-produced lunar salvage unit with maintenance scars")
        self.assertIn("Creative direction from the current request", prompt)
        self.assertIn("lunar salvage unit", prompt)
        self.assertIn("mechanical purpose", prompt)
        self.assertIn("Whole-suit design DNA", prompt)
        self.assertIn("UV engineering contract", build_part_prompt("helmet", spec, texture_mode="mesh_uv"))

    def test_build_part_prompt_includes_variation_and_three_view_rules(self) -> None:
        spec = create_draft_suitspec()
        prompt = build_part_prompt(
            "helmet",
            spec,
            texture_mode="mesh_uv",
            generation_brief="Keep the unit rescue-legible.",
            user_armor_profile={
                "identity_seed": "abc123",
                "palette_family": "Rescue ceramic white",
                "palette_guidance": "Keep the user's rescue ceramic white shell family.",
                "finish_family": "Calm ceramic matte",
                "finish_guidance": "Favor matte ceramic shell breaks.",
                "motif_family": "Civic shield geometry",
                "motif_guidance": "Use civic guard motifs.",
                "panel_density_family": "Measured service spacing",
                "panel_density_guidance": "Keep panel density medium and rational.",
                "silhouette_family": "Public shield silhouette",
                "silhouette_guidance": "Keep the profile broad and trustworthy.",
                "emissive_family": "Clean guidance emissive",
                "emissive_guidance": "Keep emissives thin and trustworthy.",
                "tri_view_family": "Public-defense three-view logic",
                "tri_view_guidance": "All views must stay protection-first and readable.",
                "continuity_rule": "Same user, same production lineage.",
            },
            style_variation={
                "palette_family": "Rescue signal",
                "palette_guidance": "Use pale ceramic shell plates and rescue red-orange latch accents.",
                "finish_guidance": "Favor matte ceramic shell breaks.",
                "emissive_guidance": "Keep emissives thin and trustworthy.",
                "motif_guidance": "Use split chevrons.",
                "panel_guidance": "Keep panel density medium and deliberate.",
                "silhouette_guidance": "Keep the profile broad and trustworthy.",
            },
        )
        self.assertIn("User-specific armor DNA", prompt)
        self.assertIn("Current emotional modulation", prompt)
        self.assertIn("Rescue signal", prompt)
        self.assertIn("Three-view discipline", prompt)
        self.assertIn("Think like an orthographic three-view sheet translated into UV islands", prompt)

    def test_build_uv_refine_prompt(self) -> None:
        spec = create_draft_suitspec()
        prompt = build_uv_refine_prompt(
            "helmet",
            spec,
            user_armor_profile={
                "identity_seed": "abc123",
                "palette_family": "Orbital audit gray",
                "palette_guidance": "Keep the issued gray baseline.",
                "finish_family": "Calm ceramic matte",
                "finish_guidance": "Keep matte shell breaks.",
                "motif_family": "Audit spine geometry",
                "motif_guidance": "Keep audit strip motifs.",
                "panel_density_family": "Measured service spacing",
                "panel_density_guidance": "Keep panel density medium.",
                "silhouette_family": "Investigative silhouette",
                "silhouette_guidance": "Keep the silhouette regulator-stable.",
                "emissive_family": "Audit diagnostic emissive",
                "emissive_guidance": "Keep sparse diagnostics.",
                "tri_view_family": "Inspection-led three-view logic",
                "tri_view_guidance": "Keep every view inspection-readable.",
                "continuity_rule": "Same user, same production lineage.",
            },
        )
        self.assertIn("reference concept image", prompt)
        self.assertIn("UV-ready flat texture sheet", prompt)
        self.assertIn("UV engineering contract", prompt)
        self.assertIn("Reference A = UV engineering guide", prompt)
        self.assertIn("Preserve front, side, and rear logic while translating it into UV space", prompt)
        self.assertIn("User-specific armor DNA", prompt)


if __name__ == "__main__":
    unittest.main()
