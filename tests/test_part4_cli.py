import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "cli.py"
PART4_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part4_outline_generator.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("cli_under_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part4CliTests(unittest.TestCase):
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

    def test_part4_generate_invokes_outline_generator_agent(self):
        run = self.run_cli("part4-generate")

        run.assert_called_once_with([sys.executable, str(PART4_GENERATOR_PATH)])

    def test_part4_generate_passes_dry_run_to_agent(self):
        run = self.run_cli("part4-generate", "--dry-run")

        run.assert_called_once_with(
            [sys.executable, str(PART4_GENERATOR_PATH), "--dry-run"]
        )

    def test_part4_generate_passes_project_root_to_agent(self):
        run = self.run_cli("part4-generate", "--project-root", "/tmp/research-workspace")

        run.assert_called_once_with(
            [
                sys.executable,
                str(PART4_GENERATOR_PATH),
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_part4_generate_passes_force_to_agent(self):
        run = self.run_cli("part4-generate", "--force")

        run.assert_called_once_with(
            [sys.executable, str(PART4_GENERATOR_PATH), "--force"]
        )

    def test_part4_generate_does_not_confirm_outline_gate(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            self.run_cli("part4-generate")

        confirm_gate.assert_not_called()

    def test_part4_confirm_records_outline_gate_with_notes(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(sys, "argv", ["cli.py", "part4-confirm", "--notes", "章节结构已确认"]):
                self.cli.main()

        confirm_gate.assert_called_once_with("outline_confirmed", "章节结构已确认")

    def test_part4_confirm_rejects_blank_notes(self):
        with patch.object(self.cli, "confirm_human_gate") as confirm_gate:
            with patch.object(sys, "argv", ["cli.py", "part4-confirm", "--notes", "   "]):
                with self.assertRaises(SystemExit) as raised:
                    self.cli.main()

        self.assertEqual(raised.exception.code, 1)
        confirm_gate.assert_not_called()

    def test_help_and_docstring_include_part4_commands(self):
        self.assertIn("part4-generate", self.cli.__doc__)
        self.assertIn("part4-confirm", self.cli.__doc__)

        with patch.object(sys, "argv", ["cli.py", "--help"]), patch(
            "sys.stdout"
        ) as stdout, self.assertRaises(SystemExit) as raised:
            self.cli.main()

        self.assertEqual(raised.exception.code, 0)
        help_text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("part4-generate", help_text)
        self.assertIn("part4-confirm", help_text)


if __name__ == "__main__":
    unittest.main()
