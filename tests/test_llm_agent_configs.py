import re
import tomllib
import unittest
from pathlib import Path


CODEX_DIR = Path.home() / ".codex"
CODEX_CONFIG = CODEX_DIR / "config.toml"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_AGENT_NAMES = [
    "researchagent",
    "wikisynthesisagent",
    "outlineagent",
    "writeagent",
    "writeragent",
    "claimauditor",
    "citationauditor",
    "argumentagent",
]

RESEARCH_EVIDENCE_AGENTS = [
    "researchagent",
    "wikisynthesisagent",
]

REPORT_ONLY_AUDITORS = [
    "claimauditor",
    "citationauditor",
]

WRITING_AGENT_SKILLS = [
    "author-style-profile-build",
    "academic-register-polish",
    "paper-manuscript-style-profile",
]

NEGATION = r"(不得|不能|禁止|不可|严禁|不要|不允许|cannot|can't|must\s+not|do\s+not|never|forbid|forbidden)"


class LLMAgentConfigContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.codex_config = cls.load_toml(CODEX_CONFIG)
        cls.registered_agents = cls.codex_config.get("agents", {})

    @staticmethod
    def load_toml(path):
        with open(path, "rb") as f:
            return tomllib.load(f)

    def assert_contains_forbidden_boundary(self, text, guarded_terms, action_terms, message):
        guarded = r"|".join(guarded_terms)
        actions = r"|".join(action_terms)
        patterns = [
            re.compile(rf"{NEGATION}.{{0,180}}({actions}).{{0,180}}({guarded})"),
            re.compile(rf"{NEGATION}.{{0,180}}({guarded}).{{0,180}}({actions})"),
            re.compile(rf"({actions}).{{0,180}}{NEGATION}.{{0,180}}({guarded})"),
            re.compile(rf"({guarded}).{{0,180}}{NEGATION}.{{0,180}}({actions})"),
        ]
        self.assertTrue(
            any(pattern.search(text) for pattern in patterns),
            message,
        )

    def agent_config_path(self, agent_name):
        agent_registration = self.registered_agents.get(agent_name, {})
        config_file = agent_registration.get("config_file")
        self.assertIsInstance(
            config_file,
            str,
            f"{agent_name} must declare config_file in {CODEX_CONFIG}",
        )
        return CODEX_DIR / config_file

    def require_registered_agent_config(self, agent_name):
        if agent_name not in self.registered_agents:
            self.skipTest(f"{agent_name} registration is covered by the registration test")
        return self.load_agent_config(agent_name)

    def load_agent_config(self, agent_name):
        config_path = self.agent_config_path(agent_name)
        self.assertTrue(
            config_path.exists(),
            f"{agent_name} config_file does not exist: {config_path}",
        )
        return self.load_toml(config_path)

    def normalized_instructions(self, agent_name):
        agent_config = self.require_registered_agent_config(agent_name)
        instructions = agent_config.get("developer_instructions", "")
        self.assertIsInstance(
            instructions,
            str,
            f"{agent_name} must declare developer_instructions",
        )
        self.assertTrue(
            instructions.strip(),
            f"{agent_name} developer_instructions must not be empty",
        )
        return instructions.lower()

    def test_required_llm_agents_are_registered_with_existing_config_files(self):
        for agent_name in REQUIRED_AGENT_NAMES:
            with self.subTest(agent=agent_name):
                self.assertIn(
                    agent_name,
                    self.registered_agents,
                    f"{agent_name} must be registered in {CODEX_CONFIG}",
                )
                self.assertTrue(
                    self.agent_config_path(agent_name).exists(),
                    f"{agent_name} registered config file must exist",
                )

    def test_required_llm_agent_configs_use_gpt54_workspace_write(self):
        for agent_name in REQUIRED_AGENT_NAMES:
            with self.subTest(agent=agent_name):
                agent_config = self.require_registered_agent_config(agent_name)
                self.assertEqual(agent_config.get("model"), "gpt-5.4")
                self.assertEqual(agent_config.get("sandbox_mode"), "workspace-write")

    def test_required_llm_agents_forbid_canonical_writes_and_human_gate_autoconfirm(self):
        for agent_name in REQUIRED_AGENT_NAMES:
            with self.subTest(agent=agent_name):
                instructions = self.normalized_instructions(agent_name)
                self.assertIn(
                    "canonical",
                    instructions,
                    f"{agent_name} must mention canonical artifact boundaries",
                )
                self.assertRegex(
                    instructions,
                    re.compile(
                        r"(gate|human selection|human confirmation|intake_confirmed|argument_tree_selected|人工)"
                    ),
                    f"{agent_name} must mention human gate or explicit selection boundaries",
                )
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"canonical",
                        r"canonical artifact",
                        r"canonical artifacts",
                        r"artifact",
                        r"outputs/",
                        r"argument_tree",
                        r"paper_outline",
                        r"manuscript",
                        r"产物",
                    ],
                    action_terms=[
                        r"write",
                        r"overwrite",
                        r"lock",
                        r"own",
                        r"写",
                        r"覆盖",
                        r"锁",
                        r"锁定",
                    ],
                    message=f"{agent_name} must forbid writing or locking canonical artifacts",
                )
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"human gate",
                        r"gate",
                        r"human confirmation",
                        r"人工",
                        r"intake_confirmed",
                        r"argument_tree_selected",
                    ],
                    action_terms=[
                        r"auto-confirm",
                        r"auto confirm",
                        r"automatically confirm",
                        r"confirm",
                        r"确认",
                        r"自动确认",
                    ],
                    message=f"{agent_name} must forbid auto-confirming human gates",
                )

    def test_research_and_wiki_agents_preserve_cnki_authenticity_and_evidence_layers(self):
        for agent_name in RESEARCH_EVIDENCE_AGENTS:
            with self.subTest(agent=agent_name):
                instructions = self.normalized_instructions(agent_name)
                self.assertIn("cnki", instructions)
                self.assertRegex(instructions, re.compile(r"(authenticity|真实性)"))
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"cnki",
                        r"authenticity",
                        r"真实性",
                    ],
                    action_terms=[
                        r"bypass",
                        r"skip",
                        r"绕过",
                        r"跳过",
                    ],
                    message=f"{agent_name} must forbid bypassing CNKI or authenticity checks",
                )
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"research evidence",
                        r"research-wiki",
                        r"evidence layer",
                        r"证据",
                    ],
                    action_terms=[
                        r"pollute",
                        r"mix",
                        r"contaminate",
                        r"treat",
                        r"污染",
                        r"混入",
                    ],
                    message=f"{agent_name} must forbid polluting the research evidence layer",
                )

    def test_writeagent_keeps_author_style_out_of_research_evidence(self):
        for agent_name in ["writeagent", "writeragent"]:
            with self.subTest(agent=agent_name):
                instructions = self.normalized_instructions(agent_name)
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"research evidence",
                        r"evidence",
                        r"证据",
                    ],
                    action_terms=[
                        r"author style",
                        r"author-style",
                        r"style samples",
                        r"写作风格",
                        r"作者风格",
                    ],
                    message=f"{agent_name} must forbid treating author style as research evidence",
                )
                for skill_name in WRITING_AGENT_SKILLS:
                    self.assertIn(skill_name, instructions)
                    skill_file = PROJECT_ROOT / "skills" / skill_name / "SKILL.md"
                    self.assertTrue(skill_file.exists(), f"Missing writing skill: {skill_file}")

    def test_llm_roles_are_separated_from_runtime_script_agents(self):
        for agent_name in REQUIRED_AGENT_NAMES:
            with self.subTest(agent=agent_name):
                instructions = self.normalized_instructions(agent_name)
                self.assertRegex(
                    instructions,
                    re.compile(r"(deterministic|runtime|script|integrator|validation)"),
                    f"{agent_name} must mention deterministic/runtime ownership boundaries",
                )

        architecture_doc = PROJECT_ROOT / "docs" / "02_architecture.md"
        self.assertTrue(architecture_doc.exists())
        architecture_text = architecture_doc.read_text(encoding="utf-8")
        self.assertIn("LLM agent roles", architecture_text)
        self.assertIn("runtime scripts", architecture_text)

    def test_claim_and_citation_auditors_are_report_only(self):
        for agent_name in REPORT_ONLY_AUDITORS:
            with self.subTest(agent=agent_name):
                instructions = self.normalized_instructions(agent_name)
                self.assertRegex(
                    instructions,
                    re.compile(r"(only|只能|仅).{0,120}(report|报告)"),
                    f"{agent_name} must be limited to reports",
                )
                self.assert_contains_forbidden_boundary(
                    instructions,
                    guarded_terms=[
                        r"manuscript",
                        r"draft",
                        r"稿",
                        r"正文",
                    ],
                    action_terms=[
                        r"edit",
                        r"modify",
                        r"rewrite",
                        r"revise",
                        r"change",
                        r"改稿",
                        r"修改",
                        r"重写",
                        r"修订",
                    ],
                    message=f"{agent_name} must forbid direct manuscript edits",
                )


if __name__ == "__main__":
    unittest.main()
