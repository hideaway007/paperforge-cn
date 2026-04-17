import re
import tomllib
import unittest
from pathlib import Path


CODEX_DIR = Path.home() / ".codex"
CODEX_CONFIG = CODEX_DIR / "config.toml"
ARGUMENT_AGENT_CONFIG_FILE = "agents/argumentagent.toml"
ARGUMENT_AGENT_CONFIG = CODEX_DIR / ARGUMENT_AGENT_CONFIG_FILE
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PART3_ARGUMENT_GENERATE_SKILL = (
    PROJECT_ROOT / "skills" / "part3-argument-generate" / "SKILL.md"
)
ARGUMENTAGENT_CODEX_ADAPTER = PROJECT_ROOT / "runtime" / "agents" / "argumentagent_codex_cli.py"
PART3_SKILLS = [
    "part3-argument-generate",
    "part3-argument-divergent-generate",
    "part3-argument-compare",
    "part3-argument-stress-test",
    "part3-argument-refine",
    "part3-human-selection",
]


class ArgumentAgentConfigTests(unittest.TestCase):
    def load_toml(self, path):
        self.assertTrue(path.exists(), f"Missing TOML config: {path}")
        with open(path, "rb") as f:
            return tomllib.load(f)

    def load_text(self, path):
        self.assertTrue(path.exists(), f"Missing text file: {path}")
        return path.read_text(encoding="utf-8")

    def test_argumentagent_is_registered_in_codex_config(self):
        config = self.load_toml(CODEX_CONFIG)
        agents = config.get("agents", {})

        self.assertIn("argumentagent", agents)
        self.assertEqual(
            agents["argumentagent"].get("config_file"),
            ARGUMENT_AGENT_CONFIG_FILE,
        )

    def test_argumentagent_config_contract(self):
        agent_config = self.load_toml(ARGUMENT_AGENT_CONFIG)
        developer_instructions = agent_config.get("developer_instructions", "")

        self.assertEqual(agent_config.get("model"), "gpt-5.4")
        for required_skill in PART3_SKILLS:
            self.assertIn(required_skill, developer_instructions)

        normalized_instructions = developer_instructions.lower()
        self.assertIn("canonical", normalized_instructions)
        self.assertIn("argument_tree.json", normalized_instructions)
        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"(不得|cannot|must\s+not|do\s+not|never|forbid|forbidden).{0,80}(write|写)"
            ),
            "developer_instructions must forbid writing canonical argument_tree.json",
        )

        for evidence_term in [
            r"sources?",
            r"citations?",
            r"research\s+evidence",
        ]:
            self.assertRegex(normalized_instructions, evidence_term)
        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"(不得|cannot|must\s+not|do\s+not|never|forbid|forbidden).{0,120}(新增|add|create|invent)"
            ),
            "developer_instructions must forbid adding source/citation/research evidence",
        )

    def test_argumentagent_referenced_skills_exist(self):
        for skill_name in PART3_SKILLS:
            skill_file = PROJECT_ROOT / "skills" / skill_name / "SKILL.md"
            self.assertTrue(skill_file.exists(), f"Missing required skill: {skill_file}")

    def test_argumentagent_codex_adapter_exists(self):
        adapter_text = self.load_text(ARGUMENTAGENT_CODEX_ADAPTER)
        self.assertIn("artifacts.candidate_trees", adapter_text)
        self.assertIn("argumentagent.toml", adapter_text)
        self.assertIn("Do not write files", adapter_text)

    def test_argumentagent_hard_boundaries_are_explicit(self):
        agent_config = self.load_toml(ARGUMENT_AGENT_CONFIG)
        normalized_instructions = agent_config.get("developer_instructions", "").lower()

        for required_boundary in [
            "argument_seed_map.json",
            "part3-seed-map",
            "argument_tree_selected",
            "writing-policy",
            "part3-human-selection",
        ]:
            self.assertIn(required_boundary, normalized_instructions)

        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"(do\s+not|never|cannot|must\s+not).{0,80}(generate|rewrite|own).{0,80}argument_seed_map\.json"
            ),
            "developer_instructions must keep seed-map ownership deterministic",
        )
        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"part3-human-selection.{0,120}(explicit user selection|never decide)"
            ),
            "part3-human-selection must guide explicit user selection only",
        )
        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"(do\s+not|never|cannot|must\s+not).{0,80}auto-confirm.{0,80}argument_tree_selected"
            ),
            "argumentagent must not auto-confirm argument_tree_selected",
        )
        self.assertRegex(
            normalized_instructions,
            re.compile(
                r"(do\s+not|never|cannot|must\s+not).{0,80}writing-policy.{0,80}research evidence"
            ),
            "writing-policy must not be treated as research evidence",
        )

    def test_argument_generate_skill_keeps_seed_map_deterministic(self):
        skill_text = self.load_text(PART3_ARGUMENT_GENERATE_SKILL)
        normalized_skill = skill_text.lower()

        for required_phrase in [
            "existing outputs/part3/argument_seed_map.json",
            "existing deterministic seed map",
            "deterministic script",
            "正式 part 3 候选论点必须由 llm 生成",
            "--allow-deterministic-fallback",
            "python3 cli.py part3-seed-map",
            "source_ids",
            "wiki_page_ids",
            "outputs/part3/candidate_argument_trees/",
            "outputs/part3/argument_tree.json",
            "part3-human-selection",
        ]:
            self.assertIn(required_phrase, normalized_skill)

        self.assertRegex(
            normalized_skill,
            re.compile(
                r"(不得|do\s+not|never|cannot|must\s+not).{0,80}(生成|generate|改写|rewrite|拥有|own).{0,80}argument_seed_map\.json"
            ),
            "part3-argument-generate must forbid LLM ownership of argument_seed_map.json",
        )
        self.assertRegex(
            normalized_skill,
            re.compile(
                r"argumentagent.{0,80}(不得|do\s+not|never|cannot|must\s+not).{0,80}(从 research wiki|generate|生成).{0,80}seed map"
            ),
            "skill must not let argumentagent claim it generates seed map from wiki",
        )
        self.assertRegex(
            normalized_skill,
            re.compile(
                r"(不得|do\s+not|never|cannot|must\s+not).{0,80}(写入|write|覆盖|overwrite).{0,80}outputs/part3/argument_tree\.json"
            ),
            "skill must forbid writing canonical argument_tree.json",
        )
        self.assertIn("不得跳过人工选择 gate", normalized_skill)

        for stale_phrase in [
            "先从 research wiki 提炼 `argument_seed_map`",
            "生成 `outputs/part3/argument_seed_map.json`，提炼研究问题",
            "写入 seed map 和候选文件",
        ]:
            self.assertNotIn(stale_phrase, normalized_skill)


if __name__ == "__main__":
    unittest.main()
