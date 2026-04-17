import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


NEW_SKILLS = {
    "academic-register-polish",
    "logic-redline-check",
    "caption-polish",
    "reviewer-perspective-audit",
}

NEW_POLICY_IDS = {
    "ai_style_markers",
    "figure_table_caption",
    "logic_redline_review",
    "reviewer_perspective_audit",
}


class WritingSkillExtensionsTests(unittest.TestCase):
    def test_new_skills_have_required_files_and_no_placeholders(self):
        for skill_name in NEW_SKILLS:
            with self.subTest(skill_name=skill_name):
                skill_dir = PROJECT_ROOT / "skills" / skill_name
                skill_md = skill_dir / "SKILL.md"
                openai_yaml = skill_dir / "agents" / "openai.yaml"

                self.assertTrue(skill_md.exists())
                self.assertTrue(openai_yaml.exists())

                skill_text = skill_md.read_text(encoding="utf-8")
                openai_text = openai_yaml.read_text(encoding="utf-8")

                self.assertIn(f"name: {skill_name}", skill_text)
                self.assertIn("description:", skill_text)
                self.assertNotIn("TODO", skill_text)
                self.assertIn(f"${skill_name}", openai_text)

    def test_new_skills_preserve_canonical_artifact_boundaries(self):
        for skill_name in NEW_SKILLS:
            with self.subTest(skill_name=skill_name):
                skill_text = (PROJECT_ROOT / "skills" / skill_name / "SKILL.md").read_text(
                    encoding="utf-8"
                )

                self.assertIn("不得", skill_text)
                self.assertIn("research", skill_text.lower())
                self.assertRegex(skill_text, r"不得.*新增.*claim|不新增 claim")
                self.assertRegex(skill_text, r"不得.*research-wiki|research-wiki/")
                self.assertRegex(skill_text, r"raw-library/")

    def test_new_writing_policy_items_are_indexed_as_non_evidence(self):
        source_index = json.loads(
            (PROJECT_ROOT / "writing-policy" / "source_index.json").read_text(encoding="utf-8")
        )
        indexed_items = {
            item["id"]: item
            for category in ("rules", "rubrics")
            for item in source_index[category]
        }

        for policy_id in NEW_POLICY_IDS:
            with self.subTest(policy_id=policy_id):
                self.assertIn(policy_id, indexed_items)
                item = indexed_items[policy_id]
                self.assertFalse(item["may_be_used_as_research_evidence"])
                self.assertTrue((PROJECT_ROOT / item["path"]).exists())

    def test_external_prompt_repository_was_not_vendored(self):
        checked_roots = [
            PROJECT_ROOT / "skills",
            PROJECT_ROOT / "writing-policy",
        ]
        blocked_markers = [
            "awesome-ai-research-writing",
            "github.com/Leey21",
        ]

        for root in checked_roots:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                for marker in blocked_markers:
                    with self.subTest(path=path, marker=marker):
                        self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
