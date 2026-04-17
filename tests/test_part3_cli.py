import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "cli.py"
SEED_MAP_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_argument_seed_map_generator.py"
GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_candidate_generator.py"
REFINER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_argument_refiner.py"
SELECTION_LOCKER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_selection_locker.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("cli_part3_test", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part3CliTests(unittest.TestCase):
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

    def test_part3_seed_map_invokes_seed_map_agent(self):
        run = self.run_cli("part3-seed-map", "--project-root", "/tmp/research-workspace")

        run.assert_called_once_with(
            [
                sys.executable,
                str(SEED_MAP_GENERATOR_PATH),
                "--project-root",
                "/tmp/research-workspace",
            ]
        )

    def test_part3_generate_passes_explicit_wiki_fallback(self):
        run = self.run_cli("part3-generate", "--allow-wiki-fallback")

        run.assert_called_once_with(
            [sys.executable, str(GENERATOR_PATH), "--allow-wiki-fallback"]
        )

    def test_part3_refine_invokes_refiner_without_safety_flags_by_default(self):
        run = self.run_cli("part3-refine")

        run.assert_called_once_with([sys.executable, str(REFINER_PATH)])

    def test_part3_refine_passes_explicit_safety_flags(self):
        run = self.run_cli(
            "part3-refine",
            "--project-root",
            "/tmp/research-workspace",
            "--force",
            "--allow-after-selection",
        )

        run.assert_called_once_with(
            [
                sys.executable,
                str(REFINER_PATH),
                "--project-root",
                "/tmp/research-workspace",
                "--force",
                "--allow-after-selection",
            ]
        )

    def test_part3_select_passes_candidate_source(self):
        run = self.run_cli(
            "part3-select",
            "--candidate-id",
            "candidate_theory_first_refined",
            "--candidate-source",
            "refined",
            "--notes",
            "选择 refine 后候选",
        )

        run.assert_called_once_with(
            [
                sys.executable,
                str(SELECTION_LOCKER_PATH),
                "--candidate-id",
                "candidate_theory_first_refined",
                "--notes",
                "选择 refine 后候选",
                "--candidate-source",
                "refined",
            ]
        )

    def test_help_and_docstring_include_new_part3_commands(self):
        self.assertIn("part3-seed-map", self.cli.__doc__)
        self.assertIn("part3-refine", self.cli.__doc__)

        with patch.object(sys, "argv", ["cli.py", "--help"]), patch(
            "sys.stdout"
        ) as stdout, self.assertRaises(SystemExit) as raised:
            self.cli.main()

        self.assertEqual(raised.exception.code, 0)
        help_text = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("part3-seed-map", help_text)
        self.assertIn("part3-refine", help_text)


if __name__ == "__main__":
    unittest.main()
