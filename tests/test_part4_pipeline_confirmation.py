import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part4PipelineConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.pipeline.PROJECT_ROOT = self.project_root
        self.pipeline.STATE_FILE = self.project_root / "runtime" / "state.json"
        self.pipeline.PROCESS_MEMORY_DIR = self.project_root / "process-memory"

        (self.project_root / "runtime").mkdir(parents=True)
        (self.project_root / "outputs" / "part4").mkdir(parents=True)
        self.write_json(
            "runtime/state.json",
            {
                "stages": {
                    "part4": {
                        "human_gates_completed": [],
                        "gate_passed": False,
                    }
                },
                "human_decision_log": [],
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
                "sections": [{"section_id": "sec_1", "title": "绪论", "level": 1}],
            },
        )
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "wiki_ref": "research-wiki/index.json",
                "root": {"node_id": "thesis_001", "claim": "x", "node_type": "thesis"},
            },
        )
        self.write_json(
            "outputs/part4/reference_alignment_report.json",
            {
                "schema_version": "1.0.0",
                "status": "pass",
                "coverage": {"uncovered_critical_argument_node_ids": []},
                "errors": [],
            },
        )
        (self.project_root / "writing-policy").mkdir(parents=True, exist_ok=True)

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read_json(self, rel_path):
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def test_outline_confirmation_is_deprecated_noop(self):
        self.pipeline.confirm_human_gate("outline_confirmed", "兼容旧命令")

        outline = self.read_json("outputs/part4/paper_outline.json")
        state = self.read_json("runtime/state.json")

        self.assertIsNone(outline["confirmed_at"])
        self.assertNotIn("outline_confirmed", state["stages"]["part4"]["human_gates_completed"])
        self.assertFalse((self.project_root / "outputs" / "part4" / "paper_outline.json.bak").exists())
        self.assertEqual(state["human_decision_log"][0]["status"], "deprecated_noop")

    def test_outline_confirmation_noop_allows_blank_notes(self):
        self.pipeline.confirm_human_gate("outline_confirmed", "")

        outline = self.read_json("outputs/part4/paper_outline.json")
        state = self.read_json("runtime/state.json")
        self.assertIsNone(outline["confirmed_at"])
        self.assertNotIn("outline_confirmed", state["stages"]["part4"]["human_gates_completed"])

    def test_outline_confirmation_noop_does_not_require_outline_artifact(self):
        (self.project_root / "outputs" / "part4" / "paper_outline.json").unlink()

        self.pipeline.confirm_human_gate("outline_confirmed", "兼容旧命令")

        state = self.read_json("runtime/state.json")
        self.assertNotIn("outline_confirmed", state["stages"]["part4"]["human_gates_completed"])

    def test_part4_alignment_gate_allows_unconfirmed_outline(self):
        issues = self.pipeline.check_part4_alignment_gate()

        self.assertFalse(any("confirmed_at" in issue for issue in issues))

    def test_part4_alignment_gate_recomputes_current_outline_alignment(self):
        (self.project_root / "writing-policy" / "rules").mkdir(parents=True, exist_ok=True)
        (self.project_root / "writing-policy" / "style_guides").mkdir(parents=True, exist_ok=True)
        (self.project_root / "writing-policy" / "rules" / "rule.md").write_text(
            "# rule\n",
            encoding="utf-8",
        )
        (self.project_root / "writing-policy" / "style_guides" / "guide.md").write_text(
            "# guide\n",
            encoding="utf-8",
        )
        self.write_json(
            "writing-policy/source_index.json",
            {
                "schema_version": "1.0.0",
                "rules": [
                    {
                        "id": "rule",
                        "path": "writing-policy/rules/rule.md",
                        "usage": "structure_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "style_guides": [
                    {
                        "id": "guide",
                        "path": "writing-policy/style_guides/guide.md",
                        "usage": "expression_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "coverage": {"structure": True, "expression": True},
            },
        )
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "pages": [{"page_id": "page_1", "source_ids": ["cnki_001"]}],
                "source_mapping_complete": True,
                "health_summary": {
                    "total_pages": 1,
                    "orphan_pages": 0,
                    "unsourced_pages": 0,
                    "contradiction_count": 0,
                },
            },
        )
        self.write_json(
            "raw-library/metadata.json",
            {"schema_version": "1.0.0", "sources": [{"source_id": "cnki_001"}]},
        )
        self.write_json(
            "outputs/part4/paper_outline.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "confirmed_at": "2026-04-16T01:00:00+00:00",
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "wiki_ref": "research-wiki/index.json",
                "writing_policy_ref": "writing-policy/source_index.json",
                "sections": [
                    {
                        "section_id": "sec_1",
                        "title": "绪论",
                        "level": 1,
                        "argument_node_ids": ["missing_node"],
                        "support_source_ids": ["cnki_001"],
                    }
                ],
            },
        )
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "wiki_ref": "research-wiki/index.json",
                "root": {
                    "node_id": "thesis_001",
                    "claim": "x",
                    "node_type": "thesis",
                    "support_source_ids": ["cnki_001"],
                    "wiki_page_ids": ["page_1"],
                },
            },
        )
        self.write_json(
            "outputs/part4/outline_rationale.json",
            {
                "schema_version": "1.0.0",
                "inputs": {
                    "argument_tree_ref": "outputs/part3/argument_tree.json",
                    "wiki_ref": "research-wiki/index.json",
                    "writing_policy_ref": "writing-policy/source_index.json",
                },
                "section_mappings": [{"section_id": "sec_1", "argument_node_ids": ["missing_node"]}],
                "human_gate": {
                    "id": "outline_confirmed",
                    "required_before_writing": True,
                    "status": "pending",
                },
            },
        )
        self.write_json(
            "outputs/part4/reference_alignment_report.json",
            {
                "schema_version": "1.0.0",
                "status": "pass",
                "inputs": {
                    "argument_tree_ref": "outputs/part3/argument_tree.json",
                    "wiki_ref": "research-wiki/index.json",
                    "writing_policy_ref": "writing-policy/source_index.json",
                },
                "coverage": {"uncovered_critical_argument_node_ids": []},
                "errors": [],
            },
        )

        issues = self.pipeline.check_part4_alignment_gate()

        self.assertTrue(any("实时 alignment" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
