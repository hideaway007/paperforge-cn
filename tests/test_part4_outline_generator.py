import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part4_outline_generator.py"
ALIGNMENT_PATH = PROJECT_ROOT / "runtime" / "agents" / "part4_outline_alignment.py"
PART4_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part4_outline.schema.json"


def load_module(name: str, path: Path):
    module_dir = str(path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part4OutlineGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = load_module("part4_outline_generator", GENERATOR_PATH)
        self.alignment = load_module("part4_outline_alignment", ALIGNMENT_PATH)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.original_env = {
            "RTM_OUTLINEAGENT_COMMAND": os.environ.get("RTM_OUTLINEAGENT_COMMAND"),
            "RTM_OUTLINEAGENT_TIMEOUT": os.environ.get("RTM_OUTLINEAGENT_TIMEOUT"),
        }
        self.addCleanup(self.restore_env)
        self.write_fixture_project()

    def restore_env(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def write_fixture_project(self):
        for rel_dir in [
            "outputs/part3",
            "outputs/part4",
            "research-wiki/pages",
            "runtime",
            "writing-policy/rules",
            "writing-policy/style_guides",
            "writing-policy/reference_cases",
            "writing-policy/rubrics",
            "raw-library",
        ]:
            (self.project_root / rel_dir).mkdir(parents=True, exist_ok=True)

        self.write_json(
            "runtime/state.json",
            {
                "stages": {
                    "part3": {
                        "gate_passed": True,
                        "human_gates_completed": ["argument_tree_selected"],
                    },
                    "part4": {
                        "status": "not_started",
                        "gate_passed": False,
                        "human_gates_completed": [],
                    }
                },
                "human_decision_log": [],
            },
        )
        self.write_json(
            "outputs/part3/candidate_comparison.json",
            {
                "schema_version": "1.0.0",
                "candidates": [
                    {"candidate_id": "candidate_a", "summary": "selected"},
                    {"candidate_id": "candidate_b", "summary": "alternative"},
                    {"candidate_id": "candidate_c", "summary": "alternative"},
                ],
            },
        )
        self.write_json(
            "outputs/part3/human_selection_feedback.json",
            {
                "schema_version": "1.0.0",
                "selected_candidate_id": "candidate_a",
                "selection_notes": "选择 candidate_a 作为 Part 4 输入。",
            },
        )
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "pages": [
                    {"page_id": "topic_current_topic_architecture", "path": "research-wiki/pages/topic_current_topic_architecture.md"},
                    {"page_id": "method_space_syntax", "path": "research-wiki/pages/method_space_syntax.md"},
                ],
                "source_mapping_complete": True,
                "health_summary": {"isolated_pages": 0, "contradiction_pages": 0},
            },
        )
        (self.project_root / "research-wiki/pages/topic_current_topic_architecture.md").write_text(
            "# 地域建筑\n",
            encoding="utf-8",
        )
        (self.project_root / "research-wiki/pages/method_space_syntax.md").write_text(
            "# 空间句法\n",
            encoding="utf-8",
        )
        self.write_json(
            "writing-policy/source_index.json",
            {
                "schema_version": "1.0.0",
                "rules": [{"id": "rule_chinese_academic", "title": "中文学术论文表达规范"}],
                "style_guides": [{"id": "guide_tutor", "title": "导师章节结构偏好"}],
            },
        )
        (self.project_root / "writing-policy/reference_cases/case_001.md").write_text(
            "# 中文论文参考案例\n",
            encoding="utf-8",
        )
        (self.project_root / "writing-policy/rubrics/chapter_structure.md").write_text(
            "# 章节结构 rubric\n",
            encoding="utf-8",
        )
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "sources": [
                    {"source_id": "cnki_001", "title": "地域建筑研究"},
                    {"source_id": "cnki_002", "title": "地域建筑符号教学实践"},
                    {"source_id": "cnki_003", "title": "空间句法方法"},
                ],
            },
        )
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "locked_at": "2026-04-16T00:00:00+00:00",
                "selected_candidate_id": "candidate_a",
                "human_selection_ref": "outputs/part3/human_selection_feedback.json",
                "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
                "wiki_ref": "research-wiki/index.json",
                "root": {
                    "node_id": "thesis_001",
                    "claim": "地域建筑符号教学实践结构可以转译为当代建筑设计方法。",
                    "node_type": "thesis",
                    "support_source_ids": ["cnki_001"],
                    "wiki_page_ids": ["topic_current_topic_architecture"],
                    "children": [
                        {
                            "node_id": "arg_001",
                            "claim": "地域建筑符号教学实践具有可识别的组织类型。",
                            "node_type": "main_argument",
                            "support_source_ids": ["cnki_002"],
                            "wiki_page_ids": ["topic_current_topic_architecture"],
                            "children": [
                                {
                                    "node_id": "arg_001_1",
                                    "claim": "空间句法可以描述庭院路径与界面关系。",
                                    "node_type": "sub_argument",
                                    "support_source_ids": ["cnki_003"],
                                    "wiki_page_ids": ["method_space_syntax"],
                                }
                            ],
                        },
                        {
                            "node_id": "arg_002",
                            "claim": "当代转译需要保留地域文化语义。",
                            "node_type": "main_argument",
                            "support_source_ids": ["cnki_001"],
                            "wiki_page_ids": ["topic_current_topic_architecture"],
                        },
                    ],
                },
            },
        )

    def test_generates_outline_package_with_alignment_report(self):
        package = self.generator.generate_outline_package(self.project_root)

        outline = package["paper_outline"]
        self.assertEqual(outline["argument_tree_ref"], "outputs/part3/argument_tree.json")
        self.assertEqual(outline["wiki_ref"], "research-wiki/index.json")
        self.assertIsNone(outline["confirmed_at"])
        self.assertGreaterEqual(len(outline["sections"]), 4)

        with open(PART4_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=outline, schema=schema)

        report = package["reference_alignment_report"]
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["errors"], [])
        self.assertIn("arg_001", report["coverage"]["covered_critical_argument_node_ids"])
        self.assertTrue(outline["reference_cases_used"])
        self.assertTrue(report["inputs"]["rubrics_used"])
        self.assertTrue(report["wiki_traceability"])
        self.assertTrue(report["reference_case_alignment"])
        self.assertTrue(report["rubric_alignment"])

    def test_write_package_runs_outlineagent_sidecar_when_configured(self):
        fake_agent = self.project_root / "fake_outlineagent.py"
        fake_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'outlineagent'\n"
                "assert request['task'] == 'part4_outline_alignment_review'\n"
                "assert request['skill'] == 'outline-alignment'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "for path in ['outputs/part4/paper_outline.json', 'outputs/part3/argument_tree.json']:\n"
                "    assert path in paths, path\n"
                "print(json.dumps({'report': 'outlineagent reviewed outline alignment'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_OUTLINEAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_OUTLINEAGENT_TIMEOUT"] = "5"
        package = self.generator.generate_outline_package(self.project_root)

        self.generator.write_package(self.project_root, package, force=True)

        review = self.generator.load_required_json(self.project_root, "outputs/part4/outlineagent_review.json")
        self.assertEqual("outlineagent reviewed outline alignment", review["report"])
        provenance = self.generator.load_required_json(self.project_root, "outputs/part4/outlineagent_provenance.json")
        self.assertEqual("outlineagent", provenance["agent_name"])
        self.assertEqual("llm", provenance["mode"])
        self.assertEqual("outputs/part4/outlineagent_review.json", provenance["output_ref"])
        self.assertTrue(provenance["does_not_confirm_human_gate"])

    def test_generation_requires_part3_gate_evidence(self):
        state_path = self.project_root / "runtime" / "state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "stages": {
                        "part3": {
                            "gate_passed": False,
                            "human_gates_completed": [],
                        }
                    }
                },
                f,
            )

        with self.assertRaisesRegex(RuntimeError, "argument_tree_selected"):
            self.generator.generate_outline_package(self.project_root)

    def test_generation_requires_part3_gate_passed(self):
        self.write_json(
            "runtime/state.json",
            {
                "stages": {
                    "part3": {
                        "gate_passed": False,
                        "human_gates_completed": ["argument_tree_selected"],
                    }
                }
            },
        )

        with self.assertRaisesRegex(RuntimeError, "Part 3 gate"):
            self.generator.generate_outline_package(self.project_root)

    def test_generation_requires_part3_selection_artifacts(self):
        (self.project_root / "outputs" / "part3" / "human_selection_feedback.json").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "human_selection_feedback"):
            self.generator.generate_outline_package(self.project_root)

    def test_generation_rejects_part3_selection_mismatch(self):
        self.write_json(
            "outputs/part3/human_selection_feedback.json",
            {
                "schema_version": "1.0.0",
                "selected_candidate_id": "candidate_b",
                "selection_notes": "mismatch",
            },
        )

        with self.assertRaisesRegex(RuntimeError, "selected_candidate_id"):
            self.generator.generate_outline_package(self.project_root)

    def test_generation_rejects_comparison_without_selected_candidate(self):
        self.write_json(
            "outputs/part3/candidate_comparison.json",
            {
                "schema_version": "1.0.0",
                "candidates": [
                    {"candidate_id": "candidate_b", "summary": "alternative"},
                    {"candidate_id": "candidate_c", "summary": "alternative"},
                    {"candidate_id": "candidate_d", "summary": "alternative"},
                ],
            },
        )

        with self.assertRaisesRegex(RuntimeError, "candidate_comparison"):
            self.generator.generate_outline_package(self.project_root)

    def test_generation_accepts_refined_candidate_selection(self):
        refined_ref = "outputs/part3/refined_candidate_argument_trees/candidate_a_refined.json"
        self.write_json(
            refined_ref,
            {
                "schema_version": "1.0.0",
                "candidate_id": "candidate_a_refined",
                "strategy": "theory_first",
                "wiki_ref": "research-wiki/index.json",
                "based_on_candidate_ref": "outputs/part3/candidate_argument_trees/candidate_a.json",
                "argument_seed_map_ref": "outputs/part3/argument_seed_map.json",
                "argument_quality_report_ref": "outputs/part3/argument_quality_report.json",
                "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
                "root": {
                    "node_id": "thesis_001",
                    "claim": "Refine 补充后的地域建筑符号教学实践结构论证。",
                    "node_type": "thesis",
                    "support_source_ids": ["cnki_001"],
                    "wiki_page_ids": ["topic_current_topic_architecture"],
                    "children": [],
                },
            },
        )
        self.write_json(
            "outputs/part3/human_selection_feedback.json",
            {
                "schema_version": "1.0.0",
                "selected_candidate_id": "candidate_a_refined",
                "candidate_source": "refined",
                "candidate_tree_ref": refined_ref,
                "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
                "selection_notes": "选择 refined candidate。",
                "locked_artifact": "outputs/part3/argument_tree.json",
            },
        )
        argument_tree = self.generator.load_required_json(
            self.project_root,
            "outputs/part3/argument_tree.json",
        )
        argument_tree["selected_candidate_id"] = "candidate_a_refined"
        argument_tree["candidate_source"] = "refined"
        argument_tree["candidate_tree_ref"] = refined_ref
        argument_tree["root"]["claim"] = "Refine 补充后的地域建筑符号教学实践结构论证。"
        self.write_json("outputs/part3/argument_tree.json", argument_tree)

        package = self.generator.generate_outline_package(self.project_root)

        self.assertEqual(package["paper_outline"]["argument_tree_ref"], "outputs/part3/argument_tree.json")
        outline_text = json.dumps(package["paper_outline"], ensure_ascii=False)
        self.assertNotIn("Refine 补充", outline_text)
        self.assertNotIn("Seed map", outline_text)

    def test_alignment_report_fails_for_unknown_argument_node(self):
        package = self.generator.generate_outline_package(self.project_root)
        outline = package["paper_outline"]
        outline["sections"][0]["argument_node_ids"] = ["missing_node"]

        argument_tree = self.generator.load_required_json(
            self.project_root,
            "outputs/part3/argument_tree.json",
        )
        wiki_index = self.generator.load_required_json(
            self.project_root,
            "research-wiki/index.json",
        )
        report = self.alignment.evaluate_outline_alignment(
            outline,
            argument_tree,
            wiki_index,
            writing_policy_ref_exists=True,
            reference_cases_used=["writing-policy/reference_cases/case_001.md"],
            rubrics_used=["writing-policy/rubrics/chapter_structure.md"],
        )

        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["errors"])
        self.assertIn("missing_node", report["checks"][0]["invalid_node_ids"])

    def test_alignment_report_fails_without_section_wiki_trace(self):
        package = self.generator.generate_outline_package(self.project_root)
        outline = package["paper_outline"]
        argument_tree = self.generator.load_required_json(
            self.project_root,
            "outputs/part3/argument_tree.json",
        )
        wiki_index = {"schema_version": "1.0.0", "pages": []}

        report = self.alignment.evaluate_outline_alignment(
            outline,
            argument_tree,
            wiki_index,
            writing_policy_ref_exists=True,
            reference_cases_used=["writing-policy/reference_cases/case_001.md"],
            rubrics_used=["writing-policy/rubrics/chapter_structure.md"],
        )

        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["wiki_traceability"])
        self.assertTrue(any("research-wiki" in error for error in report["errors"]))

    def test_reference_cases_and_rubrics_are_reported_separately(self):
        package = self.generator.generate_outline_package(self.project_root)
        outline = package["paper_outline"]
        argument_tree = self.generator.load_required_json(
            self.project_root,
            "outputs/part3/argument_tree.json",
        )
        wiki_index = self.generator.load_required_json(
            self.project_root,
            "research-wiki/index.json",
        )

        report = self.alignment.evaluate_outline_alignment(
            outline,
            argument_tree,
            wiki_index,
            writing_policy_ref_exists=True,
            reference_cases_used=[],
            rubrics_used=["writing-policy/rubrics/chapter_structure.md"],
        )
        checks = {check["id"]: check for check in report["checks"]}

        self.assertEqual(report["status"], "pass")
        self.assertEqual(checks["reference_cases"]["status"], "warning")
        self.assertEqual(checks["rubrics"]["status"], "pass")
        self.assertEqual(report["inputs"]["reference_cases_used"], [])
        self.assertEqual(
            report["inputs"]["rubrics_used"],
            ["writing-policy/rubrics/chapter_structure.md"],
        )

    def test_write_package_overwrites_legacy_confirmed_outline_without_force(self):
        package = self.generator.generate_outline_package(self.project_root)
        self.generator.write_package(self.project_root, package)

        outline_path = self.project_root / "outputs" / "part4" / "paper_outline.json"
        with open(outline_path, encoding="utf-8") as f:
            outline = json.load(f)
        outline["confirmed_at"] = "2026-04-16T04:00:00+00:00"
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)

        next_package = self.generator.generate_outline_package(self.project_root)
        self.generator.write_package(self.project_root, next_package)

        with open(outline_path, encoding="utf-8") as f:
            overwritten = json.load(f)
        self.assertIsNone(overwritten["confirmed_at"])

    def test_write_package_force_does_not_invalidate_removed_outline_gate(self):
        package = self.generator.generate_outline_package(self.project_root)
        self.generator.write_package(self.project_root, package)

        outline_path = self.project_root / "outputs" / "part4" / "paper_outline.json"
        with open(outline_path, encoding="utf-8") as f:
            outline = json.load(f)
        outline["confirmed_at"] = "2026-04-16T04:00:00+00:00"
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline, f, ensure_ascii=False, indent=2)
        self.write_json(
            "runtime/state.json",
            {
                "stages": {
                    "part3": {
                        "gate_passed": True,
                        "human_gates_completed": ["argument_tree_selected"],
                    },
                    "part4": {
                        "status": "completed",
                        "completed_at": "2026-04-16T04:00:00+00:00",
                        "gate_passed": True,
                        "human_gates_completed": ["outline_confirmed"],
                    },
                },
                "current_stage": "part4",
                "human_decision_log": [],
            },
        )

        next_package = self.generator.generate_outline_package(self.project_root)
        self.generator.write_package(self.project_root, next_package, force=True)

        with open(outline_path, encoding="utf-8") as f:
            overwritten = json.load(f)
        self.assertIsNone(overwritten["confirmed_at"])
        with open(self.project_root / "runtime/state.json", encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("outline_confirmed", state["stages"]["part4"]["human_gates_completed"])
        self.assertTrue(state["stages"]["part4"]["gate_passed"])
        self.assertFalse(list((self.project_root / "process-memory").glob("*outline_confirmed_invalidated.json")))


if __name__ == "__main__":
    unittest.main()
