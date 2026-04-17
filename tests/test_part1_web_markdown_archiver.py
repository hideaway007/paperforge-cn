import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVER_PATH = PROJECT_ROOT / "runtime" / "agents" / "web_markdown_archiver.py"
AUTH_PATH = PROJECT_ROOT / "runtime" / "agents" / "authenticity_verifier.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part1WebMarkdownArchiverTests(unittest.TestCase):
    def setUp(self):
        self.archiver = load_module("web_markdown_archiver", ARCHIVER_PATH)
        self.authenticity = load_module("authenticity_verifier_for_web_archive", AUTH_PATH)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.authenticity.PROJECT_ROOT = self.project_root

    def test_imports_obsidian_markdown_clip_and_writes_provenance(self):
        obsidian_dir = self.project_root / "obsidian-export"
        obsidian_dir.mkdir(parents=True)
        clip_path = obsidian_dir / "paper-page.md"
        clip_path.write_text(
            "# Regional Architecture and Design Education\n\n"
            "This article discusses architecture symbols and design education.",
            encoding="utf-8",
        )

        result = self.archiver.archive_markdown_source(
            project_root=self.project_root,
            source_id="crossref_2026_001",
            url="https://doi.org/10.1234/example",
            markdown_source_path=clip_path,
            metadata={
                "query_id": "crossref_q1_1",
                "db": "crossref",
                "title": "Regional Architecture and Design Education",
                "authors": ["Jane Doe"],
                "journal": "Journal of Design Education",
                "year": 2026,
                "doi_or_cnki_id": "10.1234/example",
                "abstract": "This article discusses architecture symbols and design education.",
                "keywords": ["architecture", "design education"],
            },
            archive_method="obsidian_plugin_import",
        )

        archive_path = self.project_root / "raw-library" / "web-archives" / "crossref_2026_001.md"
        provenance_path = self.project_root / "raw-library" / "provenance" / "crossref_2026_001.json"
        self.assertEqual(archive_path.resolve(), result["archive_path"].resolve())
        self.assertTrue(archive_path.exists())
        self.assertIn("Design Education", archive_path.read_text(encoding="utf-8"))

        record = json.loads(provenance_path.read_text(encoding="utf-8"))
        self.assertEqual("raw-library/web-archives/crossref_2026_001.md", record["local_path"])
        self.assertEqual("markdown", record["local_artifact_type"])
        self.assertEqual("obsidian_plugin_import", record["archive_method"])
        self.assertEqual("success", record["download_status"])

        ok, note = self.authenticity.check_local_download(record)
        self.assertTrue(ok, note)


if __name__ == "__main__":
    unittest.main()
