import unittest

from henshin.forge import create_draft_suitspec
from henshin.part_prompts import build_part_prompt, list_enabled_parts, resolve_part_prompts


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

    def test_build_part_prompt_override(self) -> None:
        spec = create_draft_suitspec()
        spec["modules"]["helmet"]["generation_prompt"] = "custom helmet prompt"
        prompt = build_part_prompt("helmet", spec)
        self.assertEqual(prompt, "custom helmet prompt")

    def test_resolve_part_prompts(self) -> None:
        spec = create_draft_suitspec()
        prompts = resolve_part_prompts(spec, ["helmet", "chest"])
        self.assertEqual(set(prompts.keys()), {"helmet", "chest"})


if __name__ == "__main__":
    unittest.main()
