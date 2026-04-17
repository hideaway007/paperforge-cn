import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_part2_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part2PipelineGateTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.pipeline.PROJECT_ROOT = self.project_root
        self.pipeline.STATE_FILE = self.project_root / "runtime" / "state.json"
        self.pipeline.PROCESS_MEMORY_DIR = self.project_root / "process-memory"

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def test_wiki_health_blocks_unresolved_references(self):
        page_path = self.project_root / "research-wiki/pages/concept_a.md"
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text("# concept a\n", encoding="utf-8")
        wiki_index = {
            "source_mapping_complete": True,
            "pages": [
                {
                    "page_id": "concept_a",
                    "source_ids": ["cnki_001"],
                    "file_path": "research-wiki/pages/concept_a.md",
                    "related_pages": [],
                }
            ],
            "health_summary": {
                "total_pages": 1,
                "orphan_pages": 0,
                "unsourced_pages": 0,
                "contradiction_count": 0,
                "unresolved_references": 1,
            },
            "unresolved_references": [
                {"page_id": "concept_a", "unresolved_title": "缺失概念"}
            ],
        }

        issues = self.pipeline.check_wiki_health_gate(wiki_index)

        self.assertTrue(any("unresolved_references" in issue for issue in issues))
        self.assertTrue(any("缺失概念" in issue for issue in issues))

    def test_writing_policy_gate_validates_indexed_paths(self):
        self.write_json(
            "writing-policy/source_index.json",
            {
                "schema_version": "1.0.0",
                "rules": [
                    {
                        "id": "rule_001",
                        "path": "writing-policy/rules/missing.md",
                    }
                ],
                "style_guides": [
                    {
                        "id": "guide_001",
                        "path": "research-wiki/pages/not_allowed.md",
                    }
                ],
                "coverage": {"structure": True, "expression": True},
            },
        )

        issues = self.pipeline.check_writing_policy_gate()

        self.assertTrue(any("不存在的文件" in issue for issue in issues))
        self.assertTrue(any("writing-policy/ 外部文件" in issue for issue in issues))

    def test_wiki_source_traceability_requires_raw_metadata_source(self):
        self.write_json(
            "raw-library/metadata.json",
            {"schema_version": "1.0.0", "sources": [{"source_id": "cnki_001"}]},
        )
        wiki_index = {
            "pages": [
                {"page_id": "concept_a", "source_ids": ["missing_source"]},
                {"page_id": "concept_b", "source_ids": ["cnki_001"]},
            ]
        }

        issues = self.pipeline.check_wiki_source_traceability(wiki_index)

        self.assertTrue(any("missing_source" in issue for issue in issues))

    def test_wiki_source_traceability_accepts_warning_verdict_sources(self):
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "sources": [
                    {
                        "source_id": "cnki_warning",
                        "authenticity_status": "verified",
                        "authenticity_verdict": "warning",
                    }
                ],
            },
        )
        wiki_index = {
            "pages": [
                {"page_id": "source_digest_warning", "source_ids": ["cnki_warning"]},
            ]
        }

        issues = self.pipeline.check_wiki_source_traceability(wiki_index)

        self.assertEqual([], issues)

    def test_part4_alignment_gate_requires_rationale_and_policy_source_index(self):
        self.write_json(
            "outputs/part4/paper_outline.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "confirmed_at": "2026-04-16T01:00:00+00:00",
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "wiki_ref": "research-wiki/index.json",
                "writing_policy_ref": "writing-policy/source_index.json",
                "sections": [{"section_id": "sec_1", "title": "绪论", "level": 1}],
            },
        )
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "wiki_ref": "research-wiki/index.json",
                "root": {"node_id": "thesis_001", "node_type": "thesis", "claim": "x"},
            },
        )
        self.write_json(
            "outputs/part4/reference_alignment_report.json",
            {
                "schema_version": "1.0.0",
                "status": "pass",
                "inputs": {
                    "argument_tree_ref": "outputs/part3/argument_tree.json",
                    "wiki_ref": "research-wiki/index.json",
                    "writing_policy_ref": "writing-policy/source_index.json",
                },
                "coverage": {"uncovered_critical_argument_node_ids": []},
                "errors": [],
            },
        )
        (self.project_root / "writing-policy").mkdir(parents=True, exist_ok=True)

        issues = self.pipeline.check_part4_alignment_gate()

        self.assertTrue(any("outline_rationale" in issue for issue in issues))
        self.assertTrue(any("writing-policy/source_index.json" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
