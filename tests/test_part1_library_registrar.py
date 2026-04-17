import importlib.util
import json
import unittest
from pathlib import Path

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRAR_PATH = PROJECT_ROOT / "runtime" / "agents" / "library_registrar.py"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part1_source_bundle.schema.json"


def load_registrar_module():
    spec = importlib.util.spec_from_file_location("library_registrar", REGISTRAR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part1LibraryRegistrarTests(unittest.TestCase):
    def complete_record(self, source_id, **overrides):
        record = {
            "source_id": source_id,
            "query_id": "cnki_q1_1",
            "db": "cnki",
            "title": "地域建筑符号空间结构研究",
            "authors": ["张三"],
            "journal": "建筑学报",
            "year": 2025,
            "doi_or_cnki_id": f"CNKI{source_id.upper()}",
            "url": "https://kns.cnki.net/example",
            "abstract": "讨论地域建筑符号与地域建筑空间结构。",
            "keywords": ["地域建筑符号", "地域建筑"],
            "download_status": "success",
            "downloaded_at": "2026-04-15T12:00:00+00:00",
            "local_download_success": True,
            "relevance_score": 75,
            "relevance_tier": "tier_A",
        }
        return {**record, **overrides}

    def test_build_metadata_matches_part1_schema(self):
        registrar = load_registrar_module()
        now = "2026-04-15T16:30:00+00:00"
        report = {
            "failed": 1,
            "results": [
                {
                    "source_id": "cnki_2025_001",
                    "verdict": "pass",
                    "checks": {
                        "identifier_valid": True,
                        "metadata_consistent": True,
                        "journal_verifiable": True,
                        "relevant_to_intake": True,
                        "no_duplicate": True,
                    },
                    "flags": [],
                },
                {
                    "source_id": "cnki_2025_002",
                    "verdict": "fail",
                    "checks": {
                        "identifier_valid": False,
                        "metadata_consistent": True,
                        "journal_verifiable": True,
                        "relevant_to_intake": True,
                        "no_duplicate": True,
                    },
                    "flags": ["suspicious_id"],
                },
            ],
        }
        intake = {"intake_id": "intake_20260415_current_topic_garden"}
        records_by_id = {
            "cnki_2025_001": {
                "source_id": "cnki_2025_001",
                "query_id": "cnki_q1_1",
                "db": "cnki",
                "title": "地域建筑符号空间结构研究",
                "authors": ["张三"],
                "journal": "建筑学报",
                "year": 2025,
                "doi_or_cnki_id": "JZXB202501001",
                "url": "https://kns.cnki.net/example",
                "abstract": "讨论地域建筑符号与地域建筑空间结构。",
                "keywords": ["地域建筑符号", "地域建筑"],
                "download_status": "success",
                "downloaded_at": "2026-04-15T12:00:00+00:00",
                "local_download_success": True,
                "relevance_score": 75,
                "relevance_tier": "tier_A",
            }
        }

        metadata = registrar.build_metadata(
            report=report,
            intake=intake,
            records_by_id=records_by_id,
            generated_at=now,
        )

        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)

        jsonschema.validate(instance=metadata, schema=schema)
        self.assertEqual(metadata["schema_version"], "1.0.0")
        self.assertEqual(metadata["intake_ref"], intake["intake_id"])
        self.assertEqual(metadata["summary"]["total_accepted"], 1)
        self.assertEqual(metadata["summary"]["total_excluded"], 1)
        self.assertEqual(metadata["summary"]["tier1_count"], 1)

        source = metadata["sources"][0]
        self.assertEqual(source["source_tier"], "tier1_chinese_primary")
        self.assertEqual(source["source_name"], "cnki")
        self.assertEqual(source["language"], "zh")
        self.assertEqual(source["authenticity_status"], "verified")
        self.assertEqual(source["relevance_score"], 0.75)
        self.assertEqual(source["local_path"], "raw-library/papers/cnki_2025_001.pdf")
        self.assertEqual(source["provenance_path"], "raw-library/provenance/cnki_2025_001.json")

    def test_build_metadata_excludes_sources_without_pdf_or_complete_provenance(self):
        registrar = load_registrar_module()
        now = "2026-04-15T16:30:00+00:00"
        report = {
            "results": [
                {"source_id": "cnki_valid", "verdict": "pass", "flags": [], "checks": {}},
                {"source_id": "cnki_missing_pdf", "verdict": "pass", "flags": [], "checks": {}},
                {"source_id": "cnki_incomplete_provenance", "verdict": "pass", "flags": [], "checks": {}},
            ],
        }
        records_by_id = {
            "cnki_valid": self.complete_record("cnki_valid"),
            "cnki_missing_pdf": self.complete_record(
                "cnki_missing_pdf",
                local_download_success=False,
            ),
            "cnki_incomplete_provenance": self.complete_record(
                "cnki_incomplete_provenance",
                downloaded_at="",
            ),
        }

        metadata = registrar.build_metadata(
            report=report,
            intake={"intake_id": "intake_20260415_current_topic_garden"},
            records_by_id=records_by_id,
            generated_at=now,
        )

        self.assertEqual(["cnki_valid"], [source["source_id"] for source in metadata["sources"]])
        self.assertEqual(metadata["summary"]["total_accepted"], 1)
        self.assertEqual(metadata["summary"]["total_excluded"], 2)

    def test_final_excluded_log_preserves_download_relevance_and_authenticity_reasons(self):
        registrar = load_registrar_module()
        now = "2026-04-15T16:30:00+00:00"
        report = {
            "results": [
                {"source_id": "cnki_download_failed", "verdict": "pass", "flags": [], "checks": {}},
                {"source_id": "cnki_low_relevance", "verdict": "pass", "flags": [], "checks": {}},
                {"source_id": "cnki_auth_failed", "verdict": "fail", "flags": ["suspicious_id"], "checks": {}},
            ],
        }
        records_by_id = {
            "cnki_download_failed": self.complete_record(
                "cnki_download_failed",
                download_status="failed",
                local_download_success=False,
            ),
            "cnki_low_relevance": self.complete_record(
                "cnki_low_relevance",
                relevance_score=20,
                relevance_tier="tier_C",
            ),
            "cnki_auth_failed": self.complete_record("cnki_auth_failed"),
        }

        excluded_log = registrar.build_final_excluded_log(
            report=report,
            records_by_id=records_by_id,
            generated_at=now,
        )

        reasons_by_source = {
            entry["source_id"]: entry["reason"]
            for entry in excluded_log["excluded"]
        }
        self.assertEqual(3, excluded_log["total_excluded"])
        self.assertEqual("download_failed", reasons_by_source["cnki_download_failed"])
        self.assertEqual("relevance_score_below_0.6", reasons_by_source["cnki_low_relevance"])
        self.assertEqual("suspicious_id", reasons_by_source["cnki_auth_failed"])

    def test_no_canonical_source_feedback_explains_gate_failure_without_relaxing_threshold(self):
        registrar = load_registrar_module()
        now = "2026-04-15T16:30:00+00:00"
        report = {
            "results": [
                {"source_id": "cnki_tier_b", "verdict": "pass", "flags": [], "checks": {}},
                {"source_id": "cnki_auth_failed", "verdict": "fail", "flags": ["suspicious_id"], "checks": {}},
            ],
        }
        records_by_id = {
            "cnki_tier_b": self.complete_record(
                "cnki_tier_b",
                title="地域建筑符号课程转化研究",
                relevance_score=52,
                relevance_tier="tier_B",
            ),
            "cnki_auth_failed": self.complete_record(
                "cnki_auth_failed",
                relevance_score=78,
                relevance_tier="tier_A",
            ),
        }
        excluded_log = registrar.build_final_excluded_log(
            report=report,
            records_by_id=records_by_id,
            generated_at=now,
        )

        feedback = registrar.build_no_canonical_source_feedback(
            report=report,
            records_by_id=records_by_id,
            excluded_log=excluded_log,
        )
        joined = "\n".join(feedback)

        self.assertIn("相关性 >= 0.6", joined)
        self.assertIn("最高相关性", joined)
        self.assertIn("cnki_auth_failed", joined)
        self.assertIn("tier_A", joined)
        self.assertIn("排除原因", joined)
        self.assertIn("不会把 tier_B 或低相关来源降级写入 raw-library/metadata.json", joined)
        self.assertIn("扩大下载数量", joined)


if __name__ == "__main__":
    unittest.main()
