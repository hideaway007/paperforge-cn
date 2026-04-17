import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEW_WORKSPACE_PATH = PROJECT_ROOT / "scripts" / "new_workspace.py"
CLI_PATH = PROJECT_ROOT / "cli.py"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_intake() -> dict:
    return {
        "schema_version": "1.0.0",
        "intake_id": "intake_test_workspace",
        "research_topic": "地域建筑符号结构化的当代思考",
        "research_question": "地域建筑符号的空间结构有哪些可识别类型？",
        "core_research_questions": ["地域建筑符号的空间结构有哪些可识别类型？"],
        "keywords_required": ["地域建筑符号", "地域建筑美学"],
        "time_range": {"start_year": 2005, "end_year": 2025},
        "source_preference": {"document_types": ["期刊论文"]},
        "scope_notes": "聚焦研究对象、应用场景和空间结构。",
    }


class Part1WorkspaceBootstrapTests(unittest.TestCase):
    def test_create_workspace_for_intake_copies_intake_and_confirms_gate_inside_workspace(self):
        module = load_module("new_workspace_part1_bootstrap", NEW_WORKSPACE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_root = tmp_path / "source"
            module.copy_harness(PROJECT_ROOT, source_root)
            intake_path = source_root / "outputs" / "part1" / "intake.json"
            intake_path.parent.mkdir(parents=True, exist_ok=True)
            intake_path.write_text(json.dumps(valid_intake(), ensure_ascii=False), encoding="utf-8")
            target = tmp_path / "workspace"

            result = module.create_workspace_for_intake(
                src=source_root,
                dst=target,
                intake_path=intake_path,
                confirm_intake=True,
                notes="workspace bootstrap test",
            )

            self.assertTrue(result["created"])
            self.assertEqual(target.resolve(), result["workspace_path"])
            workspace_intake = json.loads(
                (target / "outputs" / "part1" / "intake.json").read_text(encoding="utf-8")
            )
            self.assertEqual(workspace_intake["intake_id"], "intake_test_workspace")
            self.assertFalse((target / "raw-library" / "metadata.json").exists())
            state = json.loads((target / "runtime" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual("part1", state["current_stage"])
            self.assertEqual("in_progress", state["stages"]["part1"]["status"])
            self.assertIn("intake_confirmed", state["stages"]["part1"]["human_gates_completed"])
            manifest = json.loads((target / "workspace_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["intake_id"], "intake_test_workspace")
            self.assertEqual(manifest["isolation_rule"], "harness_only_plus_confirmed_intake")

    def test_ensure_workspace_for_intake_reuses_existing_workspace_for_same_intake_hash(self):
        module = load_module("new_workspace_part1_idempotency", NEW_WORKSPACE_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "source"
            module.copy_harness(PROJECT_ROOT, project_root)
            intake_path = project_root / "outputs" / "part1" / "intake.json"
            intake_path.parent.mkdir(parents=True, exist_ok=True)
            intake_path.write_text(json.dumps(valid_intake(), ensure_ascii=False), encoding="utf-8")

            first = module.ensure_workspace_for_intake(
                src=project_root,
                intake_path=intake_path,
                confirm_intake=True,
                notes="first",
            )
            second = module.ensure_workspace_for_intake(
                src=project_root,
                intake_path=intake_path,
                confirm_intake=True,
                notes="second",
            )

            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["workspace_path"], second["workspace_path"])
            registry = json.loads(
                (project_root / "outputs" / "part1" / "workspace_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(1, len(registry["workspaces"]))

    def test_confirm_intake_cli_bootstraps_workspace_after_gate_confirmation(self):
        cli = load_module("cli_workspace_bootstrap_test", CLI_PATH)
        workspace_path = Path("/tmp/research-workspace/ws_999")
        with patch.object(cli, "confirm_human_gate") as confirm_gate, patch.object(
            cli,
            "_bootstrap_part1_workspace_after_intake",
            return_value=workspace_path,
        ) as bootstrap, patch.object(
            cli,
            "_run_workspace_part1_runner",
        ) as run_workspace, patch.object(
            sys,
            "argv",
            ["cli.py", "confirm-gate", "intake_confirmed", "--notes", "确认 intake"],
        ):
            cli.main()

        confirm_gate.assert_called_once_with("intake_confirmed", "确认 intake")
        bootstrap.assert_called_once_with("确认 intake")
        run_workspace.assert_called_once_with(workspace_path)

    def test_confirm_intake_cli_can_skip_workspace_runner(self):
        cli = load_module("cli_workspace_bootstrap_skip_runner_test", CLI_PATH)
        workspace_path = Path("/tmp/research-workspace/ws_999")
        with patch.object(cli, "confirm_human_gate") as confirm_gate, patch.object(
            cli,
            "_bootstrap_part1_workspace_after_intake",
            return_value=workspace_path,
        ) as bootstrap, patch.object(
            cli,
            "_run_workspace_part1_runner",
        ) as run_workspace, patch.object(
            sys,
            "argv",
            [
                "cli.py",
                "confirm-gate",
                "intake_confirmed",
                "--notes",
                "确认 intake",
                "--no-auto-run-part1",
            ],
        ):
            cli.main()

        confirm_gate.assert_called_once_with("intake_confirmed", "确认 intake")
        bootstrap.assert_called_once_with("确认 intake")
        run_workspace.assert_not_called()


if __name__ == "__main__":
    unittest.main()
