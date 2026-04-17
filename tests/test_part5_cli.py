import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "cli.py"
PART5_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part5_mvp_generator.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("cli_part5_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part5CliTests(unittest.TestCase):
    def setUp(self):
        self.cli = load_cli_module()

    def run_cli(self, *argv):
        completed = Mock(returncode=0)
        with patch.object(sys, "argv", ["cli.py", *argv]), patch.object(
            self.cli.subprocess,
            "run",
            return_value=completed,
        ) as run:
            self.cli.main()
        return run

    def test_part5_prep_invokes_generator_step(self):
        run = self.run_cli("part5-prep", "--project-root", "/tmp/research-workspace")

        run.assert_called_once_with(
            [
                sys.executable,
                str(PART5_GENERATOR_PATH),
                "--step",
                "prep",
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_part5_draft_review_and_revise_invoke_staged_generator(self):
        draft_run = self.run_cli("part5-draft")
        review_run = self.run_cli("part5-review")
        revise_run = self.run_cli("part5-revise")

        draft_run.assert_called_once_with(
            [sys.executable, str(PART5_GENERATOR_PATH), "--step", "draft"]
        )
        review_run.assert_called_once_with(
            [sys.executable, str(PART5_GENERATOR_PATH), "--step", "review"]
        )
        revise_run.assert_called_once_with(
            [sys.executable, str(PART5_GENERATOR_PATH), "--step", "revise"]
        )

    def test_part5_authorize_and_accept_record_human_gates(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part5-authorize", "--notes", "允许进入正文写作准备"],
            ):
                self.cli.main()
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part5-confirm-prep", "--notes", "章节 brief 与案例角色已确认"],
            ):
                self.cli.main()
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part5-confirm-review", "--notes", "review priorities 已确认"],
            ):
                self.cli.main()
            with patch.object(
                sys,
                "argv",
                ["cli.py", "part5-accept", "--notes", "接受 manuscript_v2 作为 Part 5 canonical draft"],
            ):
                self.cli.main()

        self.assertEqual(
            confirm_gate.call_args_list,
            [
                call("writing_phase_authorized", "允许进入正文写作准备"),
                call("part5_prep_confirmed", "章节 brief 与案例角色已确认"),
                call("part5_review_completed", "review priorities 已确认"),
                call("manuscript_v2_accepted", "接受 manuscript_v2 作为 Part 5 canonical draft"),
            ],
        )

    def test_part5_human_commands_reject_blank_notes(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(sys, "argv", ["cli.py", "part5-authorize", "--notes", "   "]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)
        confirm_gate.assert_not_called()

    def test_help_and_docstring_include_part5_commands(self):
        self.assertIn("part5-prep", self.cli.__doc__)
        self.assertIn("part5-accept", self.cli.__doc__)

        with patch.object(sys, "argv", ["cli.py", "--help"]), patch(
            "sys.stdout"
        ) as stdout, self.assertRaises(SystemExit) as raised:
            self.cli.main()

        self.assertEqual(raised.exception.code, 0)
        help_text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("part5-prep", help_text)
        self.assertIn("part5-revise", help_text)
        self.assertIn("part5-accept", help_text)


if __name__ == "__main__":
    unittest.main()
