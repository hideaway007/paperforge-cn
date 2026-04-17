import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "cli.py"
PART3_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_candidate_generator.py"
PART3_COMPARISON_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_comparison_generator.py"
PART2_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part2_wiki_generator.py"
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("cli_workflow_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_guidance_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CliWorkflowGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.cli = load_cli_module()

    def run_cli_with_mocked_subprocess(self, *argv):
        completed = Mock(returncode=0)
        with patch.object(sys, "argv", ["cli.py", *argv]), patch.object(
            self.cli.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.cli.main()
        return run

    def test_part3_generate_passes_project_root_to_agent(self):
        run = self.run_cli_with_mocked_subprocess(
            "part3-generate",
            "--project-root",
            "/tmp/research-workspace",
        )

        run.assert_called_once_with(
            [
                sys.executable,
                str(PART3_GENERATOR_PATH),
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_part3_compare_passes_project_root_to_agent(self):
        run = self.run_cli_with_mocked_subprocess(
            "part3-compare",
            "--project-root",
            "/tmp/research-workspace",
        )

        run.assert_called_once_with(
            [
                sys.executable,
                str(PART3_COMPARISON_PATH),
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_part2_health_reports_gate_issues(self):
        with patch.object(self.cli, "validate_gate", return_value=(False, ["wiki unresolved"])):
            with patch.object(sys, "argv", ["cli.py", "part2-health"]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)

    def test_part2_generate_passes_flags_to_agent(self):
        run = self.run_cli_with_mocked_subprocess(
            "part2-generate",
            "--dry-run",
            "--force",
            "--project-root",
            "/tmp/research-workspace",
        )

        run.assert_called_once_with(
            [
                sys.executable,
                str(PART2_GENERATOR_PATH),
                "--dry-run",
                "--force",
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_start_part1_emits_intake_request_before_retrieval_work(self):
        args = Mock(stage="part1")
        events = []

        def emit_intake(*_args):
            events.append("intake")

        def start_stage(_stage_id):
            events.append("start")

        with patch.object(self.cli, "start_stage", side_effect=start_stage) as start_stage_mock, patch.object(
            self.cli,
            "_run_agent_script",
            side_effect=emit_intake,
        ) as run_agent:
            self.cli.cmd_start(args)

        start_stage_mock.assert_called_once_with("part1")
        run_agent.assert_called_once_with("part1_intake.py", "--force")
        self.assertEqual(["intake", "start"], events)

    def test_advance_part1_exports_downloaded_paper_table_after_success(self):
        args = Mock(stage="part1")
        events = []

        def export_table(*_args):
            events.append("export")

        def advance_stage(_stage_id):
            events.append("advance")
            return True, []

        with patch.object(self.cli, "advance_stage", side_effect=advance_stage), patch.object(
            self.cli,
            "_run_agent_script",
            side_effect=export_table,
        ) as run_agent:
            self.cli.cmd_advance(args)

        run_agent.assert_called_once_with("part1_library_table_exporter.py")
        self.assertEqual(["advance", "export"], events)

    def test_next_action_sends_user_to_part1_intake_when_intake_file_missing(self):
        pipeline = load_pipeline_module()
        with tempfile.TemporaryDirectory() as tmp:
            pipeline.PROJECT_ROOT = Path(tmp)
            state = {
                "stages": {
                    "part1": {
                        "status": "in_progress",
                        "gate_passed": False,
                        "human_gates_completed": [],
                    }
                }
            }

            with patch.object(pipeline, "validate_gate", return_value=(False, [
                "人工节点未确认: intake_confirmed",
            ])):
                next_action = pipeline.get_next_action(state)

        self.assertEqual(next_action["command"], "python3 cli.py part1-intake")
        self.assertIn("intake", next_action["reason"])

    def test_part3_review_reads_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            comparison_path = Path(tmp) / "outputs" / "part3" / "candidate_comparison.json"
            comparison_path.parent.mkdir(parents=True)
            with open(comparison_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "candidates": [
                            {
                                "candidate_id": "candidate_problem_solution",
                                "strategy": "problem_solution",
                                "score": 0.9,
                                "strengths": ["问题意识突出"],
                                "risks": ["需人工确认"],
                            }
                        ],
                        "recommendation": {
                            "recommended_candidate_id": "candidate_problem_solution",
                            "reason": "score",
                        },
                    },
                    f,
                )
            with patch.object(sys, "argv", ["cli.py", "part3-review", "--project-root", tmp]), patch(
                "sys.stdout"
            ) as stdout:
                self.cli.main()

            output = "".join(call.args[0] for call in stdout.write.call_args_list)
            self.assertIn("candidate_problem_solution", output)
            self.assertIn("## 可视化对比", output)
            self.assertIn("| 选项 | 推荐 | 候选 ID | 主线 | 分数 | 推荐理由 | 核心主张（约50字） | 论点 | 适合选择情况 | 代价 |", output)
            table_path = Path(tmp) / "outputs" / "part3" / "candidate_selection_table.md"
            self.assertTrue(table_path.exists())
            self.assertIn("candidate_problem_solution", table_path.read_text(encoding="utf-8"))

    def test_help_includes_part2_health(self):
        with patch.object(sys, "argv", ["cli.py", "--help"]), patch(
            "sys.stdout"
        ) as stdout, self.assertRaises(SystemExit) as raised:
            self.cli.main()

        self.assertEqual(raised.exception.code, 0)
        help_text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("part2-health", help_text)
        self.assertIn("part2-generate", help_text)
        self.assertIn("part3-review", help_text)
        self.assertIn("part4-check", help_text)

    def test_next_action_prioritizes_part3_seed_map_when_missing(self):
        pipeline = load_pipeline_module()
        state = {
            "stages": {
                "part1": {"status": "completed", "gate_passed": True, "human_gates_completed": ["intake_confirmed"]},
                "part2": {"status": "completed", "gate_passed": True, "human_gates_completed": []},
                "part3": {"status": "in_progress", "gate_passed": False, "human_gates_completed": []},
                "part4": {"status": "not_started", "gate_passed": False, "human_gates_completed": []},
                "part5": {"status": "not_started", "gate_passed": False, "human_gates_completed": []},
            }
        }

        with patch.object(pipeline, "validate_gate", return_value=(False, [
            "缺少 workflow artifact: outputs/part3/argument_seed_map.json",
            "Part 3 候选 argument tree 必须正好 3 份，当前为 0 份",
        ])):
            next_action = pipeline.get_next_action(state)

        self.assertEqual(next_action["command"], "python3 cli.py part3-seed-map")
        self.assertIn("seed map", next_action["reason"])


if __name__ == "__main__":
    unittest.main()
