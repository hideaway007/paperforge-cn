import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "cli.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("cli_part6_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part6CliTests(unittest.TestCase):
    def setUp(self):
        self.cli = load_cli_module()

    def test_part6_authorize_and_confirm_final_record_human_gates(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate, patch.object(
            self.cli, "_run_agent_script"
        ) as run_agent_script:
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part6-authorize", "--notes", "授权从 Part 5 handoff 进入最终定稿"],
            ):
                self.cli.main()
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part6-confirm-final", "--notes", "最终状态：内部评阅"],
            ):
                self.cli.main()

        self.assertEqual(
            confirm_gate.call_args_list,
            [
                call("part6_finalization_authorized", "授权从 Part 5 handoff 进入最终定稿"),
                call("part6_final_decision_confirmed", "最终状态：内部评阅"),
            ],
        )
        run_agent_script.assert_not_called()

    def test_part6_authorize_rejects_blank_notes(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(sys, "argv", ["cli.py", "part6-authorize", "--notes", "   "]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)
        confirm_gate.assert_not_called()

    def test_part6_confirm_final_rejects_blank_notes(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(sys, "argv", ["cli.py", "part6-confirm-final", "--notes", "   "]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)
        confirm_gate.assert_not_called()

    def test_part6_precheck_calls_validate_gate_without_exiting_on_failure(self):
        with patch.object(self.cli, "validate_gate", return_value=(False, ["missing package"])) as validate_gate:
            with patch.object(sys, "argv", ["cli.py", "part6-precheck"]):
                self.cli.main()

        validate_gate.assert_called_once_with("part6")

    def test_part6_check_calls_validate_gate(self):
        with patch.object(self.cli, "validate_gate", return_value=(True, [])) as validate_gate:
            with patch.object(sys, "argv", ["cli.py", "part6-check"]):
                self.cli.main()

        validate_gate.assert_called_once_with("part6")

    def test_part6_check_failure_exits_one(self):
        with patch.object(
            self.cli, "validate_gate", return_value=(False, ["missing final manuscript"])
        ) as validate_gate:
            with patch.object(sys, "argv", ["cli.py", "part6-check"]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)
        validate_gate.assert_called_once_with("part6")

    def test_part6_finalize_all_with_project_root_calls_finalizer(self):
        with patch.object(self.cli, "_run_agent_script") as run_agent_script:
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part6-finalize", "--step", "all", "--project-root", "/tmp/x"],
            ):
                self.cli.main()

        run_agent_script.assert_called_once_with(
            "part6_mvp_finalizer.py", "--step", "all", "--project-root", "/tmp/x"
        )

    def test_part6_finalize_export_docx_step_calls_finalizer(self):
        with patch.object(self.cli, "_run_agent_script") as run_agent_script:
            with patch.object(sys, "argv", ["cli.py", "part6-finalize", "--step", "export-docx"]):
                self.cli.main()

        run_agent_script.assert_called_once_with("part6_mvp_finalizer.py", "--step", "export-docx")

    def test_part6_export_docx_command_calls_export_step(self):
        with patch.object(self.cli, "_run_agent_script") as run_agent_script:
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part6-export-docx", "--project-root", "/tmp/x"],
            ):
                self.cli.main()

        run_agent_script.assert_called_once_with(
            "part6_mvp_finalizer.py", "--step", "export-docx", "--project-root", "/tmp/x"
        )

    def test_part6_finalize_defaults_to_all_step(self):
        with patch.object(self.cli, "_run_agent_script") as run_agent_script:
            with patch.object(sys, "argv", ["cli.py", "part6-finalize"]):
                self.cli.main()

        run_agent_script.assert_called_once_with("part6_mvp_finalizer.py", "--step", "all")

    def test_help_and_docstring_include_part6_commands(self):
        for command in [
            "part6-precheck",
            "part6-authorize",
            "part6-finalize",
            "part6-export-docx",
            "part6-check",
            "part6-confirm-final",
        ]:
            self.assertIn(command, self.cli.__doc__)

        with patch.object(sys, "argv", ["cli.py", "--help"]), patch(
            "sys.stdout"
        ) as stdout, self.assertRaises(SystemExit) as raised:
            self.cli.main()

        self.assertEqual(raised.exception.code, 0)
        help_text = "".join(call_args.args[0] for call_args in stdout.write.call_args_list)
        for command in [
            "part6-precheck",
            "part6-authorize",
            "part6-finalize",
            "part6-export-docx",
            "part6-check",
            "part6-confirm-final",
        ]:
            self.assertIn(command, help_text)


if __name__ == "__main__":
    unittest.main()
