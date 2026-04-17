import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part1_download_queue_builder.py"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("part1_download_queue_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lingnan_intake():
    return {
        "intake_id": "intake_test_lingnan_modernity",
        "research_topic": "岭南建筑创作及其现代性研究",
        "research_question": "岭南建筑创作如何通过地域适应、传统与现代融合形成现代性？",
        "time_range": {"start_year": 1980, "end_year": 2026},
        "keywords_required": ["岭南建筑", "现代性", "建筑创作", "地域性", "现代建筑"],
        "keywords_suggested": ["何静堂", "两观三性", "本土化", "气候环境适应"],
        "exclusions": ["纯结构技术研究", "泛城市规划研究"],
        "scope_notes": "聚焦岭南建筑创作、现代性、地域性、何镜堂与两观三性。",
    }


def candidate(candidate_id, title, **overrides):
    base = {
        "candidate_id": candidate_id,
        "query_id": "cnki_q1_1",
        "db": "cnki",
        "rank": 1,
        "title": title,
        "authors": ["作者"],
        "journal": "建筑学报",
        "year": 2025,
        "url": f"https://kns.cnki.net/{candidate_id}",
        "abstract": "",
        "keywords": [],
        "hasDownload": True,
    }
    base.update(overrides)
    return base


class Part1DownloadQueueBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = load_builder_module()

    def test_queue_prefers_double_anchor_lingnan_candidates_and_skips_wrong_region(self):
        candidates = [
            candidate(
                "cnki_q1_1_rank_001",
                "杂糅的现代性：长春的伪满洲国建筑影像",
                abstract="讨论长春城市建筑影像中的现代性。",
            ),
            candidate(
                "cnki_q1_1_rank_002",
                "岭南文化符号在当代文化建筑中的地域性表达",
                abstract="讨论岭南建筑创作中的地域性表达与传统现代关系。",
                keywords=["岭南建筑", "地域性", "建筑创作"],
            ),
            candidate(
                "cnki_q1_1_rank_003",
                "何镜堂建筑创作思想与两观三性研究",
                abstract="讨论何镜堂、两观三性、本土化和岭南现代建筑创作体系。",
                keywords=["何镜堂", "两观三性", "岭南建筑"],
            ),
        ]

        queue = self.builder.build_download_queue(
            intake=lingnan_intake(),
            search_plan={"source_quota_policy": {"cnki_max_count": 28}},
            candidates_doc={"candidates": candidates},
        )

        queued_ids = [item["candidate_id"] for item in queue["items"]]
        skipped = {item["candidate_id"]: item for item in queue["skipped_items"]}

        self.assertIn("cnki_q1_1_rank_002", queued_ids)
        self.assertIn("cnki_q1_1_rank_003", queued_ids)
        self.assertNotIn("cnki_q1_1_rank_001", queued_ids)
        self.assertIn("cnki_q1_1_rank_001", skipped)
        self.assertIn("missing_double_anchor", skipped["cnki_q1_1_rank_001"]["skip_reasons"])

    def test_researchagent_triage_sidecar_can_skip_candidate_without_becoming_gate(self):
        candidates = [
            candidate(
                "cnki_q1_1_rank_002",
                "岭南文化符号在当代文化建筑中的地域性表达",
                abstract="讨论岭南建筑创作中的地域性表达与现代性。",
                keywords=["岭南建筑", "现代性", "建筑创作"],
            )
        ]
        triage = {
            "triage_items": [
                {
                    "candidate_id": "cnki_q1_1_rank_002",
                    "recommendation": "skip",
                    "semantic_relevance": 0.9,
                    "reason": "测试覆盖：LLM sidecar 可降级，但不写 canonical。",
                }
            ]
        }

        queue = self.builder.build_download_queue(
            intake=lingnan_intake(),
            search_plan={"source_quota_policy": {"cnki_max_count": 28}},
            candidates_doc={"candidates": candidates},
            triage_doc=triage,
        )

        self.assertEqual([], queue["items"])
        self.assertEqual(["cnki_q1_1_rank_002"], [item["candidate_id"] for item in queue["skipped_items"]])
        self.assertIn("researchagent_skip", queue["skipped_items"][0]["skip_reasons"])
        self.assertFalse(queue["llm_triage_is_gate"])

    def test_writes_download_queue_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "outputs" / "part1").mkdir(parents=True)
            (project_root / "outputs" / "part1" / "intake.json").write_text(
                json.dumps(lingnan_intake(), ensure_ascii=False),
                encoding="utf-8",
            )
            (project_root / "outputs" / "part1" / "search_plan.json").write_text(
                json.dumps({"source_quota_policy": {"cnki_max_count": 28}}, ensure_ascii=False),
                encoding="utf-8",
            )
            (project_root / "outputs" / "part1" / "search_results_candidates.json").write_text(
                json.dumps({
                    "candidates": [
                        candidate(
                            "cnki_q1_1_rank_002",
                            "岭南建筑创作现代性与地域性研究",
                            keywords=["岭南建筑", "现代性", "建筑创作"],
                        )
                    ]
                }, ensure_ascii=False),
                encoding="utf-8",
            )

            result = self.builder.build_and_write_download_queue(project_root)

            queue_path = project_root / "outputs" / "part1" / "download_queue.json"
            self.assertTrue(queue_path.exists())
            self.assertEqual(1, result["total_queued"])


if __name__ == "__main__":
    unittest.main()
