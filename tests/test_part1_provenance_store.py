import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = PROJECT_ROOT / "runtime" / "agents" / "provenance_store.py"


def load_store_module():
    spec = importlib.util.spec_from_file_location("provenance_store", STORE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def complete_record(source_id="cnki_2026_001"):
    return {
        "source_id": source_id,
        "query_id": "query_current_topic_001",
        "db": "cnki",
        "title": "地域建筑符号教学实践形态研究",
        "authors": ["张三", "李四"],
        "journal": "建筑学报",
        "year": 2026,
        "doi_or_cnki_id": "CNKI:SUN:JZXB.0.2026-01-001",
        "url": "https://kns.cnki.net/example",
        "abstract": "讨论地域建筑符号教学实践形态与气候适应策略。",
        "keywords": ["地域建筑符号", "空间形态"],
        "download_status": "success",
        "downloaded_at": "2026-04-16T09:00:00+08:00",
    }


class Part1ProvenanceStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = load_store_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.provenance_dir = Path(self.tempdir.name) / "raw-library" / "provenance"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_writes_and_loads_record_atomically(self):
        record = complete_record()

        path = self.store.write_record(self.provenance_dir, record)
        loaded = self.store.load_record(self.provenance_dir, record["source_id"])
        records = self.store.list_records(self.provenance_dir)

        self.assertEqual(path, self.provenance_dir / "cnki_2026_001.json")
        self.assertTrue(path.exists())
        self.assertEqual(loaded, record)
        self.assertEqual(records, [record])
        self.assertFalse(list(self.provenance_dir.glob("*.tmp")))

    def test_patch_record_preserves_source_id_and_validates_result(self):
        record = complete_record()
        self.store.write_record(self.provenance_dir, record)

        patched = self.store.patch_record(
            self.provenance_dir,
            "cnki_2026_001",
            {
                "relevance": {
                    "score": 0.82,
                    "tier": "tier_A",
                    "scored_at": "2026-04-16T09:05:00+08:00",
                },
                "registration": {
                    "status": "registered",
                    "registered_at": "2026-04-16T09:10:00+08:00",
                },
            },
        )

        self.assertEqual(patched["source_id"], "cnki_2026_001")
        self.assertEqual(patched["relevance"]["score"], 0.82)
        self.assertEqual(
            self.store.load_record(self.provenance_dir, "cnki_2026_001"),
            patched,
        )

    def test_incomplete_record_fails_complete_check_and_schema_validation(self):
        record = complete_record()
        del record["downloaded_at"]

        self.assertFalse(self.store.provenance_complete(record))
        with self.assertRaises(self.store.ProvenanceSchemaError) as ctx:
            self.store.validate_against_schema(record)

        self.assertIn("downloaded_at", str(ctx.exception))

    def test_rejects_path_like_source_id(self):
        with self.assertRaises(ValueError):
            self.store.provenance_path(self.provenance_dir, "../escape")


if __name__ == "__main__":
    unittest.main()
