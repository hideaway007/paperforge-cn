import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part5_mvp_generator.py"


def load_generator_module():
    module_dir = str(GENERATOR_PATH.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location("part5_mvp_generator_test", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part5MvpGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = load_generator_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.original_writer_env = {
            "RTM_WRITEAGENT_COMMAND": os.environ.get("RTM_WRITEAGENT_COMMAND"),
            "RTM_WRITEAGENT_TIMEOUT": os.environ.get("RTM_WRITEAGENT_TIMEOUT"),
            "RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK": os.environ.get("RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"),
        }
        self.addCleanup(self.restore_writer_env)
        self.write_fixture_project(part5_gates=[])

    def restore_writer_env(self):
        for key, value in self.original_writer_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def allow_deterministic_writer_fallback(self):
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)
        os.environ["RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"] = "1"

    def test_safe_project_path_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            self.generator.write_text(self.project_root, "outputs/part5/chapter_briefs/../../escape.md", "bad")
        self.assertFalse((self.project_root / "outputs" / "escape.md").exists())

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read_json(self, rel_path):
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def write_state(self, part5_gates):
        def completed(gates=None):
            return {
                "status": "completed",
                "gate_passed": True,
                "started_at": "2026-04-16T00:00:00+00:00",
                "completed_at": "2026-04-16T00:10:00+00:00",
                "human_gates_completed": gates or [],
            }

        self.write_json(
            "runtime/state.json",
            {
                "schema_version": "1.0.0",
                "stages": {
                    "part1": completed(["intake_confirmed"]),
                    "part2": completed(),
                    "part3": completed(["argument_tree_selected"]),
                    "part4": completed(),
                    "part5": {
                        "status": "in_progress",
                        "gate_passed": False,
                        "started_at": "2026-04-16T00:20:00+00:00",
                        "completed_at": None,
                        "human_gates_completed": part5_gates,
                    },
                },
                "human_decision_log": [],
            },
        )

    def write_fixture_project(self, part5_gates):
        for rel_dir in [
            "runtime",
            "outputs/part3",
            "outputs/part4",
            "research-wiki/pages",
            "raw-library",
            "writing-policy/rules",
            "writing-policy/style_guides",
        ]:
            (self.project_root / rel_dir).mkdir(parents=True, exist_ok=True)
        self.write_state(part5_gates)
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "sources": [
                    {"source_id": "cnki_001", "title": "地域建筑研究"},
                    {"source_id": "cnki_002", "title": "空间句法与空间场景"},
                ],
            },
        )
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "pages": [
                    {
                        "page_id": "page_current_topic",
                        "file_path": "research-wiki/pages/page_current_topic.md",
                        "source_ids": ["cnki_001", "cnki_002"],
                    }
                ],
                "source_mapping_complete": True,
            },
        )
        (self.project_root / "research-wiki/pages/page_current_topic.md").write_text(
            "# 地域建筑\n\n空间场景与地域经验。\n",
            encoding="utf-8",
        )
        self.write_json(
            "writing-policy/source_index.json",
            {
                "schema_version": "1.0.0",
                "rules": [
                    {
                        "id": "rule_chinese_academic",
                        "path": "writing-policy/rules/rule.md",
                        "usage": "structure_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "style_guides": [
                    {
                        "id": "guide_expression",
                        "path": "writing-policy/style_guides/guide.md",
                        "usage": "expression_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "coverage": {"structure": True, "expression": True},
            },
        )
        (self.project_root / "writing-policy/rules/rule.md").write_text("# 规则\n", encoding="utf-8")
        (self.project_root / "writing-policy/style_guides/guide.md").write_text("# 表达\n", encoding="utf-8")
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "locked_at": "2026-04-16T00:00:00+00:00",
                "wiki_ref": "research-wiki/index.json",
                "root": {
                    "node_id": "thesis_001",
                    "node_type": "thesis",
                    "claim": "地域建筑符号教学实践可为当代建筑设计提供方法参照。",
                    "support_source_ids": ["cnki_001"],
                    "wiki_page_ids": ["page_current_topic"],
                    "children": [
                        {
                            "node_id": "arg_001",
                            "node_type": "main_argument",
                            "claim": "空间句法可用于描述庭院路径与界面关系。",
                            "support_source_ids": ["cnki_002"],
                            "wiki_page_ids": ["page_current_topic"],
                        }
                    ],
                },
            },
        )
        self.write_json(
            "outputs/part4/paper_outline.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "confirmed_at": None,
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "wiki_ref": "research-wiki/index.json",
                "writing_policy_ref": "writing-policy/source_index.json",
                "sections": [
                    {
                        "section_id": "sec_1",
                        "title": "绪论",
                        "level": 1,
                        "brief": "说明研究缘起与问题意识。",
                        "argument_node_ids": ["thesis_001"],
                        "support_source_ids": ["cnki_001"],
                    },
                    {
                        "section_id": "sec_2",
                        "title": "案例分析",
                        "level": 1,
                        "brief": "说明案例作为概念参照的使用边界。",
                        "argument_node_ids": ["arg_001"],
                        "support_source_ids": ["cnki_002"],
                    },
                ],
            },
        )

    def test_prep_generates_writing_package_without_creating_draft(self):
        self.generator.run_step(self.project_root, "prep")

        self.assertTrue((self.project_root / "outputs/part5/chapter_briefs/sec_1.md").exists())
        matrix = self.read_json("outputs/part5/claim_evidence_matrix.json")
        self.assertEqual(len(matrix["claims"]), 2)
        self.assertFalse((self.project_root / "outputs/part5/manuscript_v1.md").exists())

    def test_prep_draft_review_and_revise_run_without_part5_human_gates(self):
        self.generator.run_step(self.project_root, "prep")
        self.allow_deterministic_writer_fallback()
        self.generator.run_step(self.project_root, "draft")
        self.generator.run_step(self.project_root, "review")
        review_matrix = self.read_json("outputs/part5/review_matrix.json")
        self.assertTrue(all("review_id" in item for item in review_matrix["reviews"]))
        self.assertTrue((self.project_root / "outputs/part5/review_report.md").exists())

        self.generator.run_step(self.project_root, "revise")

        self.assertTrue((self.project_root / "outputs/part5/manuscript_v2.md").exists())
        readiness = self.read_json("outputs/part5/part6_readiness_decision.json")
        self.assertIn(
            readiness["verdict"],
            ["ready_for_part6", "ready_for_part6_with_research_debt", "blocked_by_evidence_debt"],
        )

    def test_revision_writes_review_driven_manuscript_responses(self):
        self.generator.run_step(self.project_root, "prep")
        self.allow_deterministic_writer_fallback()
        self.generator.run_step(self.project_root, "draft")
        self.generator.run_step(self.project_root, "review")

        review_matrix = self.read_json("outputs/part5/review_matrix.json")
        review_matrix["reviews"].append(
            {
                "review_id": "evidence_review_custom",
                "dimension": "evidence",
                "severity": "medium",
                "finding": "arg_001 的案例材料仍需降低断言强度。",
                "claim_ids": ["arg_001"],
                "status": "registered",
            }
        )
        self.write_json("outputs/part5/review_matrix.json", review_matrix)

        self.generator.run_step(self.project_root, "revise")

        manuscript_v2 = (self.project_root / "outputs/part5/manuscript_v2.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 证据边界与修订后表述", manuscript_v2)
        self.assertNotIn("## Review 驱动修订", manuscript_v2)
        self.assertNotIn("evidence_review_custom", manuscript_v2)
        self.assertNotIn("source_ids=", manuscript_v2)
        self.assertNotIn("risk_level=", manuscript_v2)
        self.assertNotIn("## Claim 级修订处理", manuscript_v2)

        revision_log = self.read_json("outputs/part5/revision_log.json")
        custom_revision = next(
            item
            for item in revision_log["revisions"]
            if item["review_id"] == "evidence_review_custom"
        )
        self.assertEqual(custom_revision["review_dimension"], "evidence")
        self.assertEqual(custom_revision["manuscript_anchor"], "Review 驱动修订 / evidence")
        self.assertIn("applied_text", custom_revision)

    def test_draft_uses_configured_writeagent_command_before_fallback(self):
        fake_writer = self.project_root / "fake_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'writeagent'\n"
                "assert request['task'] == 'part5_draft_manuscript'\n"
                "assert request['skill'] == 'part5-draft-manuscript'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "for path in [\n"
                "  'outputs/part4/paper_outline.json',\n"
                "  'outputs/part3/argument_tree.json',\n"
                "  'writing-policy/style_guides/author_style_profile.md',\n"
                "  'skills/academic-register-polish/SKILL.md',\n"
                "  'skills/paper-manuscript-style-profile/SKILL.md',\n"
                "  'skills/part5-formal-manuscript-authoring/SKILL.md',\n"
                "]:\n"
                "  assert path in paths, path\n"
                "joined_instructions = '\\n'.join(request['instructions'])\n"
                "assert 'paper-manuscript-style-profile' in joined_instructions\n"
                "assert 'part5-formal-manuscript-authoring' in joined_instructions\n"
                "assert '证据边界与研究不足' in joined_instructions\n"
                "print(json.dumps({\n"
                "  'text': '# 论文初稿 v1\\n\\n## LLM 写作章节\\n\\n"
                "LLM writer 根据已确认大纲与证据矩阵生成正文，并保持保守学术表述。\\n'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"
        self.generator.run_step(self.project_root, "prep")

        self.generator.run_step(self.project_root, "draft")

        manuscript = (self.project_root / "outputs/part5/manuscript_v1.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("LLM 写作章节", manuscript)
        provenance = self.read_json("outputs/part5/writer_provenance.json")
        self.assertEqual("llm", provenance["mode"])
        self.assertEqual("writeagent", provenance["agent_name"])
        self.assertEqual("part5-draft-manuscript", provenance["skill"])

    def test_draft_rejects_writeagent_output_with_internal_markers(self):
        fake_writer = self.project_root / "fake_dirty_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "json.load(sys.stdin)\n"
                "print(json.dumps({\n"
                "  'text': '# 论文初稿 v1\\n\\n## 脏正文\\n\\n"
                "Part2 Evidence 显示：source_id=cnki_001，risk_level=low。\\n'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"
        self.generator.run_step(self.project_root, "prep")

        with self.assertRaisesRegex(RuntimeError, "内部工作标记"):
            self.generator.run_step(self.project_root, "draft")

        self.assertFalse((self.project_root / "outputs/part5/manuscript_v1.md").exists())

    def test_draft_requires_writeagent_command_when_fallback_disabled(self):
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)
        self.generator.run_step(self.project_root, "prep")

        with self.assertRaisesRegex(RuntimeError, "RTM_WRITEAGENT_COMMAND"):
            self.generator.run_step(self.project_root, "draft")

        self.assertFalse((self.project_root / "outputs/part5/manuscript_v1.md").exists())

    def test_draft_can_use_explicit_deterministic_fallback_escape_hatch(self):
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)
        os.environ["RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"] = "1"
        self.generator.run_step(self.project_root, "prep")

        self.generator.run_step(self.project_root, "draft")

        manuscript = (self.project_root / "outputs/part5/manuscript_v1.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 绪论", manuscript)
        self.assertIn("论述范围限定在现有材料可以支持的边界内", manuscript)
        self.assertNotIn("Part 5 MVP", manuscript)
        self.assertNotIn("本节核心论点", manuscript)
        self.assertNotIn("本节围绕已确认论证", manuscript)
        self.assertNotIn("写作提示", manuscript)
        provenance = self.read_json("outputs/part5/writer_provenance.json")
        self.assertEqual("deterministic_fallback", provenance["mode"])
        self.assertEqual("writeagent", provenance["agent_name"])
        self.assertFalse(provenance["command_configured"])


if __name__ == "__main__":
    unittest.main()
