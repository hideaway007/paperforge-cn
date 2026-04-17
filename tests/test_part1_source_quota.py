import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUOTA_PATH = PROJECT_ROOT / "runtime" / "source_quota.py"


def load_quota_module():
    spec = importlib.util.spec_from_file_location("source_quota", QUOTA_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(source_id, source_name, language, **overrides):
    base = {
        "source_id": source_id,
        "title": f"{source_id} title",
        "authors": ["Author"],
        "year": 2026,
        "journal": "Journal of Built Environment",
        "source_name": source_name,
        "source_tier": "tier2_english_supplement" if language == "en" else "tier1_chinese_primary",
        "language": language,
        "authenticity_status": "verified",
        "relevance_score": 0.8,
        "local_path": f"raw-library/papers/{source_id}.pdf",
        "provenance_path": f"raw-library/provenance/{source_id}.json",
        "added_at": "2026-04-17T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def metadata(cnki_count=24, english_count=5, other_count=11):
    sources = []
    for index in range(cnki_count):
        sources.append(source(f"cnki_2026_{index:03d}", "cnki", "zh"))
    for index in range(english_count):
        sources.append(source(f"crossref_2026_{index:03d}", "crossref", "en"))
    for index in range(other_count):
        sources.append(source(f"wanfang_2026_{index:03d}", "wanfang", "zh"))
    return {
        "schema_version": "1.0.0",
        "generated_at": "2026-04-17T00:00:00+00:00",
        "intake_ref": "intake_test",
        "sources": sources,
        "summary": {
            "total_accepted": len(sources),
            "total_excluded": 0,
            "tier1_count": cnki_count + other_count,
            "tier2_count": english_count,
            "tier3_count": 0,
        },
    }


class Part1SourceQuotaTests(unittest.TestCase):
    def setUp(self):
        self.quota = load_quota_module()

    def test_quota_passes_for_40_sources_with_cnki_60_percent_and_5_english_journals(self):
        report = self.quota.build_source_quota_report(metadata())

        self.assertTrue(report["passed"])
        self.assertEqual(40, report["counts"]["total"])
        self.assertEqual(24, report["counts"]["cnki"])
        self.assertEqual(5, report["counts"]["english_journal"])
        self.assertEqual(11, report["counts"]["other"])
        self.assertEqual([], report["issues"])

    def test_quota_rejects_cnki_above_70_percent(self):
        report = self.quota.build_source_quota_report(metadata(cnki_count=29, english_count=5, other_count=6))

        self.assertFalse(report["passed"])
        self.assertTrue(any("CNKI" in issue and "24-28" in issue for issue in report["issues"]))

    def test_quota_rejects_missing_english_journals(self):
        report = self.quota.build_source_quota_report(metadata(cnki_count=24, english_count=4, other_count=12))

        self.assertFalse(report["passed"])
        self.assertTrue(any("英文期刊" in issue and "至少 5" in issue for issue in report["issues"]))

    def test_quota_rejects_non_40_total(self):
        report = self.quota.build_source_quota_report(metadata(cnki_count=24, english_count=5, other_count=10))

        self.assertFalse(report["passed"])
        self.assertTrue(any("总量必须为 40" in issue for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
