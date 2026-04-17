import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_new_workspace_module(module_name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NewWorkspacePart4PolicyTests(unittest.TestCase):
    def load_source_index(self, source_index_path: Path):
        with open(source_index_path, encoding="utf-8") as f:
            return json.load(f)

    def test_workspace_name_rejects_path_segments(self):
        module = load_new_workspace_module("new_workspace_name_validation", PROJECT_ROOT / "scripts" / "new_workspace.py")
        self.assertEqual("ws_alpha-1", module.validate_workspace_name("ws_alpha-1"))
        with self.assertRaises(ValueError):
            module.validate_workspace_name("../outside")
        with self.assertRaises(ValueError):
            module.validate_workspace_name("nested/name")

    def assert_empty_audit_source_index(self, source_index_path: Path):
        source_index = self.load_source_index(source_index_path)

        self.assertEqual(
            source_index["artifact_type"],
            "writing_policy_source_index",
        )
        self.assertEqual(source_index["rules"], [])
        self.assertEqual(source_index["style_guides"], [])
        self.assertEqual(source_index["reference_cases"], [])
        self.assertEqual(source_index["rubrics"], [])
        self.assertIn("pending_human_input", source_index["status"])
        self.assertNotIn("research-wiki/pages", json.dumps(source_index))

    def assert_indexed_baseline_source_index(self, workspace_root: Path):
        source_index_path = workspace_root / "writing-policy" / "source_index.json"
        source_index = self.load_source_index(source_index_path)

        self.assertEqual(source_index["status"], "indexed_baseline_policy_available")
        self.assertTrue(source_index["coverage"]["structure"])
        self.assertTrue(source_index["coverage"]["expression"])
        self.assertNotIn("research-wiki/pages", json.dumps(source_index))

        for group in ("rules", "style_guides"):
            self.assertGreater(len(source_index[group]), 0)
            for item in source_index[group]:
                self.assertFalse(item["may_be_used_as_research_evidence"])
                self.assertTrue((workspace_root / item["path"]).exists(), item["path"])

    def test_root_source_index_registers_existing_policy_files(self):
        source_index_path = PROJECT_ROOT / "writing-policy" / "source_index.json"
        self.assertTrue(source_index_path.exists())
        source_index = self.load_source_index(source_index_path)

        self.assertEqual(
            source_index["artifact_type"],
            "writing_policy_source_index",
        )
        self.assertEqual(source_index["status"], "indexed_baseline_policy_available")
        self.assertNotIn("research-wiki/pages", json.dumps(source_index))

        expected_paths = {
            "writing-policy/rules/struct_chinese_paper_outline.md",
            "writing-policy/rules/ai_style_markers.md",
            "writing-policy/rules/figure_table_caption.md",
            "writing-policy/style_guides/guide_academic_tone.md",
            "writing-policy/reference_cases/case_chinese_architecture_outline.md",
            "writing-policy/rubrics/chapter_argument_alignment.md",
            "writing-policy/rubrics/logic_redline_review.md",
            "writing-policy/rubrics/reviewer_perspective_audit.md",
        }
        indexed_paths = set()
        for group in ("rules", "style_guides", "reference_cases", "rubrics"):
            for item in source_index[group]:
                path = item["path"]
                indexed_paths.add(path)
                self.assertTrue((PROJECT_ROOT / path).exists(), path)
                self.assertIn("only", item["usage"])

        self.assertEqual(indexed_paths, expected_paths)

    def test_auto_name_uses_next_number_after_existing_max_workspace(self):
        script_cases = [
            ("root", PROJECT_ROOT / "scripts" / "new_workspace.py"),
        ]

        for label, script_path in script_cases:
            with self.subTest(label=label):
                module = load_new_workspace_module(f"new_workspace_auto_name_{label}", script_path)
                with tempfile.TemporaryDirectory() as tmpdir:
                    project_root = Path(tmpdir)
                    ws_dir = project_root / "workspaces"
                    (ws_dir / "ws_101").mkdir(parents=True)
                    (ws_dir / "ws_110").mkdir()
                    (ws_dir / "scratch").mkdir()

                    self.assertEqual(ws_dir / "ws_111", module.auto_name(project_root))

    def test_new_workspace_scaffold_creates_part4_writing_policy_audit_entry(self):
        script_cases = [
            ("root", PROJECT_ROOT, PROJECT_ROOT / "scripts" / "new_workspace.py"),
        ]

        for label, source_root, script_path in script_cases:
            with self.subTest(label=label):
                module = load_new_workspace_module(f"new_workspace_{label}", script_path)
                with tempfile.TemporaryDirectory() as tmpdir:
                    target = Path(tmpdir) / "workspace"

                    module.copy_harness(source_root, target)

                    source_index_path = target / "writing-policy" / "source_index.json"
                    self.assertTrue(source_index_path.exists())
                    self.assertTrue((target / "writing-policy" / "reference_cases").is_dir())
                    self.assertTrue((target / "writing-policy" / "rubrics").is_dir())
                    self.assertTrue(
                        (target / "runtime" / "agents" / "part4_outline_generator.py").exists()
                    )
                    self.assertTrue(
                        (target / "runtime" / "agents" / "part4_outline_alignment.py").exists()
                    )
                    self.assertTrue(
                        (target / "runtime" / "agents" / "part5_mvp_generator.py").exists()
                    )
                    self.assertTrue((target / "runtime" / "llm_agent_bridge.py").exists())
                    self.assertTrue((target / "outputs" / "part5" / "chapter_briefs").is_dir())
                    self.assertTrue((target / "outputs" / "part5" / "case_analysis_templates").is_dir())

                    self.assert_indexed_baseline_source_index(target)

                    result = subprocess.run(
                        ["python3", "cli.py", "--help"],
                        cwd=target,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("part4-generate", result.stdout)
                    self.assertIn("part4-confirm", result.stdout)
                    self.assertIn("part5-prep", result.stdout)
                    self.assertIn("part5-revise", result.stdout)


if __name__ == "__main__":
    unittest.main()
