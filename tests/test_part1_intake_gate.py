import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_part1_intake_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part1IntakeGateTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.pipeline.PROJECT_ROOT = self.project_root
        self.pipeline.STATE_FILE = self.project_root / "runtime" / "state.json"
        self.pipeline.PROCESS_MEMORY_DIR = self.project_root / "process-memory"
        (self.project_root / "runtime").mkdir(parents=True)
        self.write_state()

    def test_part1_metadata_paths_reject_absolute_and_parent_segments(self):
        valid_path, valid_issue = self.pipeline._safe_part1_metadata_path(
            "raw-library/papers/cnki_2026_001.pdf",
            "raw-library/papers/",
            ".pdf",
            "local_path",
        )
        self.assertIsNone(valid_issue)
        self.assertEqual(self.project_root / "raw-library/papers/cnki_2026_001.pdf", valid_path)

        _, absolute_issue = self.pipeline._safe_part1_metadata_path(
            "/tmp/cnki_2026_001.pdf",
            "raw-library/papers/",
            ".pdf",
            "local_path",
        )
        self.assertIn("相对路径", absolute_issue)

        _, traversal_issue = self.pipeline._safe_part1_metadata_path(
            "raw-library/papers/../../outside.pdf",
            "raw-library/papers/",
            ".pdf",
            "local_path",
        )
        self.assertIn("相对路径", traversal_issue)

    def write_state(self):
        state = {
            "schema_version": "1.0.0",
            "pipeline_id": "research-to-manuscript-v1",
            "initialized_at": "2026-04-16T00:00:00+00:00",
            "current_stage": "part1",
            "stages": {
                stage_id: {
                    "status": "in_progress" if stage_id == "part1" else "not_started",
                    "started_at": None,
                    "completed_at": None,
                    "gate_passed": False,
                    "human_gates_completed": [],
                }
                for stage_id in self.pipeline.STAGE_ORDER
            },
            "last_failure": None,
            "repair_log": [],
            "human_decision_log": [],
        }
        with open(self.pipeline.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def write_intake(self, **overrides):
        intake = {
            "intake_id": "intake_test_current_topic_garden",
            "research_topic": "地域建筑符号结构化的当代思考",
            "research_question": "地域建筑符号的空间结构有哪些可识别类型？",
            "core_research_questions": ["地域建筑符号的空间结构有哪些可识别类型？"],
            "keywords_required": ["地域建筑符号", "地域建筑美学"],
            "time_range": {"start_year": 2005, "end_year": 2025},
            "source_preference": {"document_types": ["期刊论文"]},
            "scope_notes": "聚焦研究对象、应用场景和空间结构。",
        }
        intake.update(overrides)
        path = self.project_root / "outputs" / "part1" / "intake.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(intake, f, ensure_ascii=False, indent=2)

    def test_confirm_intake_gate_requires_existing_intake_json(self):
        with self.assertRaisesRegex(RuntimeError, "intake.json"):
            self.pipeline.confirm_human_gate("intake_confirmed", "确认 intake")

    def test_confirm_intake_gate_rejects_blank_research_questions(self):
        self.write_intake(research_question="", core_research_questions=[])

        with self.assertRaisesRegex(RuntimeError, "research_question"):
            self.pipeline.confirm_human_gate("intake_confirmed", "确认 intake")

    def test_confirm_intake_gate_accepts_structured_intake(self):
        self.write_intake()

        self.pipeline.confirm_human_gate("intake_confirmed", "确认 intake")

        with open(self.pipeline.STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("intake_confirmed", state["stages"]["part1"]["human_gates_completed"])

    def test_confirm_intake_gate_rejects_blank_research_question_even_with_core_questions(self):
        self.write_intake(
            research_question="",
            core_research_questions=["地域建筑符号的空间结构有哪些可识别类型？"],
        )

        with self.assertRaisesRegex(RuntimeError, "research_question"):
            self.pipeline.confirm_human_gate("intake_confirmed", "确认 intake")

    def test_part1_contract_gate_requires_downloaded_table_outputs(self):
        issues = self.pipeline.check_part1_contract_gate()

        self.assertTrue(any("downloaded_papers_table.csv" in issue for issue in issues))
        self.assertTrue(any("downloaded_papers_table.md" in issue for issue in issues))

    def test_validate_gate_part1_wires_downloaded_table_checks(self):
        self.write_intake()
        _passed, issues = self.pipeline.validate_gate("part1")

        self.assertTrue(any("downloaded_papers_table.csv" in issue for issue in issues))

    def test_part1_contract_gate_accepts_project_local_downloaded_tables(self):
        output_dir = self.project_root / "outputs" / "part1"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "downloaded_papers_table.csv").write_text("project csv\n", encoding="utf-8")
        (output_dir / "downloaded_papers_table.md").write_text("project md\n", encoding="utf-8")

        issues = self.pipeline.check_part1_contract_gate()

        self.assertFalse(any("downloaded_papers_table" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
