import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part1_runner.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("part1_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part1RunnerPreflightTests(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.runner.PROJECT_ROOT = self.project_root
        (self.project_root / "runtime").mkdir(parents=True)
        (self.project_root / "outputs" / "part1").mkdir(parents=True)

    def write_state(self, completed_gates=None):
        state = {
            "stages": {
                "part1": {
                    "human_gates_completed": completed_gates or [],
                    "gate_passed": False,
                }
            }
        }
        with open(self.project_root / "runtime" / "state.json", "w", encoding="utf-8") as f:
            json.dump(state, f)

    def write_manifest(self, **overrides):
        manifest = {
            "manifest_id": "manifest_test",
            "task_type": "cnki_search_download",
            "run_status": "success",
            "dry_run": False,
            "total_found": 1,
            "total_downloaded": 1,
            "failed_downloads": [],
        }
        manifest.update(overrides)
        with open(
            self.project_root / "outputs" / "part1" / "download_manifest.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(manifest, f)

    def write_metadata(self):
        (self.project_root / "raw-library").mkdir(parents=True)
        with open(self.project_root / "raw-library" / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "schema_version": "1.0.0",
                    "generated_at": "2026-04-16T12:00:00+00:00",
                    "intake_ref": "intake_test",
                    "sources": [
                        {
                            "source_id": "cnki_2025_001",
                            "title": "地域建筑符号空间结构研究",
                            "authors": ["张三", "李四"],
                            "year": 2025,
                            "journal": "建筑学报",
                            "doi": "10.1234/test",
                            "abstract": "讨论地域建筑符号空间结构与教学链。",
                            "keywords": ["地域建筑符号", "空间结构"],
                            "source_tier": "tier1_chinese_primary",
                            "source_name": "cnki",
                            "language": "zh",
                            "authenticity_status": "verified",
                            "relevance_score": 0.91,
                            "relevance_tier": "tier_A",
                            "local_path": "raw-library/papers/cnki_2025_001.pdf",
                            "provenance_path": "raw-library/provenance/cnki_2025_001.json",
                            "url": "https://kns.cnki.net/example",
                            "added_at": "2026-04-16T12:00:00+00:00",
                        }
                    ],
                    "summary": {
                        "total_accepted": 1,
                        "total_excluded": 0,
                        "tier1_count": 1,
                        "tier2_count": 0,
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def write_provenance(self):
        provenance_dir = self.project_root / "raw-library" / "provenance"
        provenance_dir.mkdir(parents=True)
        with open(provenance_dir / "cnki_2025_001.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source_id": "cnki_2025_001",
                    "query_id": "cnki_q1_1",
                    "db": "cnki",
                    "title": "地域建筑符号空间结构研究",
                    "authors": ["张三", "李四"],
                    "journal": "建筑学报",
                    "year": 2025,
                    "doi_or_cnki_id": "10.1234/test",
                    "url": "https://kns.cnki.net/example",
                    "abstract": "讨论地域建筑符号空间结构与教学链。",
                    "keywords": ["地域建筑符号", "空间结构"],
                    "download_status": "success",
                    "downloaded_at": "2026-04-16T12:00:00+00:00",
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def test_step_2_entry_is_blocked_when_intake_gate_is_not_confirmed(self):
        self.write_state(completed_gates=[])

        with mock.patch.object(self.runner, "run_script", return_value=True) as run_script:
            ok = self.runner.run_single_step(2)

        self.assertFalse(ok)
        run_script.assert_not_called()

    def test_step_1_entry_is_blocked_when_gate_confirmed_but_intake_file_missing(self):
        self.write_state(completed_gates=["intake_confirmed"])

        with mock.patch.object(self.runner, "run_script", return_value=True) as run_script:
            ok = self.runner.run_single_step(1)

        self.assertFalse(ok)
        run_script.assert_not_called()
        self.assertTrue((self.project_root / "outputs" / "part1" / "intake_request.md").exists())

    def test_default_resume_does_not_treat_completed_part1_as_done_when_intake_is_missing(self):
        self.write_state(completed_gates=["intake_confirmed"])
        state_path = self.project_root / "runtime" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["stages"]["part1"]["gate_passed"] = True
        state_path.write_text(json.dumps(state), encoding="utf-8")

        pending = self.runner.first_pending_step()

        self.assertEqual(0, pending)

    def test_download_manifest_contract_rejects_invalid_terminal_manifests(self):
        cases = [
            ("dry_run", {"dry_run": True}),
            ("zero_downloads", {"total_downloaded": 0}),
            ("wrong_task_type", {"task_type": "crossref_search"}),
            ("fatal_run_status", {"run_status": "fatal"}),
        ]

        for _name, overrides in cases:
            with self.subTest(_name):
                self.write_manifest(**overrides)
                self.assertFalse(self.runner.run_step3(skip_wait=True))

    def test_step_3_exports_downloaded_paper_table_after_manifest_is_valid(self):
        self.write_manifest()
        self.write_provenance()

        ok = self.runner.run_step3(skip_wait=True)

        self.assertTrue(ok)
        output_csv = self.project_root / "outputs" / "part1" / "downloaded_papers_table.csv"
        output_md = self.project_root / "outputs" / "part1" / "downloaded_papers_table.md"
        self.assertTrue(output_csv.exists())
        self.assertTrue(output_md.exists())
        csv_text = output_csv.read_text(encoding="utf-8-sig")
        self.assertIn("地域建筑符号空间结构研究", csv_text)
        self.assertIn("讨论地域建筑符号空间结构与教学链。", csv_text)

    def test_step_0_creates_intake_request_when_intake_is_missing(self):
        self.write_state(completed_gates=[])

        ok = self.runner.run_step0()

        self.assertFalse(ok)
        request_path = self.project_root / "outputs" / "part1" / "intake_request.md"
        template_path = self.project_root / "outputs" / "part1" / "intake_template.json"
        self.assertTrue(request_path.exists())
        self.assertTrue(template_path.exists())
        self.assertIn("研究主题", request_path.read_text(encoding="utf-8"))
        template = json.loads(template_path.read_text(encoding="utf-8"))
        self.assertIn("keywords_required", template)

    def test_step_6_exports_downloaded_paper_table_after_metadata_registration(self):
        self.write_state(completed_gates=["intake_confirmed"])
        self.write_metadata()

        with mock.patch.object(self.runner, "run_script", return_value=True):
            ok = self.runner.run_step6()

        self.assertTrue(ok)
        output_csv = self.project_root / "outputs" / "part1" / "downloaded_papers_table.csv"
        output_md = self.project_root / "outputs" / "part1" / "downloaded_papers_table.md"
        self.assertTrue(output_csv.exists())
        self.assertTrue(output_md.exists())
        csv_text = output_csv.read_text(encoding="utf-8-sig")
        self.assertIn("title", csv_text)
        self.assertIn("地域建筑符号空间结构研究", csv_text)
        self.assertIn("讨论地域建筑符号空间结构与教学链。", csv_text)


if __name__ == "__main__":
    unittest.main()
