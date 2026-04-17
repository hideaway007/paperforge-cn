import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORER_PATH = PROJECT_ROOT / "runtime" / "agents" / "relevance_scorer.py"


def load_scorer_module():
    spec = importlib.util.spec_from_file_location("relevance_scorer", SCORER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def art_education_intake():
    return {
        "research_topic": "地域建筑符号在设计教育中的转化应用",
        "research_question": (
            "设计教育中，如何系统挖掘、提炼并应用地域建筑符号，"
            "以提升学生审美素养、创作能力与传统文化理解，同时形成可落地的课程、教学与成果转化路径？"
        ),
        "time_range": {"start_year": 2015, "end_year": 2026},
        "keywords_required": [
            "地域建筑符号",
            "设计教育",
            "设计教育",
            "地域建筑美学",
            "课程转化",
            "教学实践",
        ],
        "keywords_suggested": [
            "地域建筑美学",
            "传统建筑装饰元素",
            "设计创作",
            "课程体系",
            "实践教学",
            "文化传承",
            "审美素养",
            "文创转化",
            "数字媒介艺术",
        ],
        "exclusions": [
            "纯地域建筑保护工程",
            "纯建筑史考据",
            "非高校阶段设计教育",
        ],
    }


def traditional_residential_renewal_intake():
    return {
        "research_topic": "历史街区居住建筑更新与社区居住品质提升",
        "research_question": (
            "在历史风貌保护前提下，如何通过保护更新、节能改造、微改造、产权政策与财政支持，"
            "推动历史街区居住建筑改善居住条件，并实现旧城片区居民住上适居住房？"
        ),
        "time_range": {"start_year": 2015, "end_year": 2026},
        "keywords_required": [
            "历史街区居住建筑",
            "保护更新",
            "旧城片区",
            "历史文化街区",
            "适居住房",
            "居住品质提升",
        ],
        "keywords_suggested": [
            "风貌保护",
            "微改造",
            "节能改造",
            "成套化改造",
            "独立厨房卫生间",
            "市政基础设施入户",
            "居民意愿",
            "产权政策",
            "财政专项资金",
            "历史文化名城保护",
        ],
        "exclusions": [
            "纯文物考古研究",
            "纯建筑形制史研究",
            "脱离居民居住改善目标的旅游商业开发",
        ],
    }


class Part1RelevanceScorerTests(unittest.TestCase):
    def setUp(self):
        self.scorer = load_scorer_module()
        self.intake = art_education_intake()

    def test_scores_architecture_elements_art_education_record_as_tier_a(self):
        record = {
            "source_id": "cnki_architecture_elements_art_education",
            "title": "《地域建筑研究》:地域建筑符号在设计教育中的转化应用",
            "abstract": (
                "地域建筑是中华文明数千年积淀的艺术瑰宝。将地域建筑符号融入设计教育，"
                "不仅能丰富设计教育资源，更能提升学生的设计审美与创作能力。本文就地域建筑符号在"
                "设计教育中的挖掘与应用展开探讨。"
            ),
            "keywords": ["地域建筑符号", "设计教育", "教学实践"],
            "journal": "建筑学报",
            "authors": ["王作川"],
            "year": 2026,
        }

        result = self.scorer.score_source(record, self.intake)

        self.assertGreaterEqual(result["score"], 60)
        self.assertEqual(result["tier"], "tier_A")
        self.assertTrue(result["matched_research_anchors"]["has_intake_object_anchor"])
        self.assertTrue(result["matched_research_anchors"]["has_intake_context_anchor"])
        self.assertTrue(result["matched_research_anchors"]["has_intake_application_anchor"])
        self.assertTrue(result["matched_research_anchors"]["qualifies_for_tier_A"])

    def test_generic_art_education_without_architecture_element_anchor_does_not_enter_tier_a(self):
        record = {
            "source_id": "cnki_generic_art_education",
            "title": "设计教育中非物质文化遗产传承策略分析",
            "abstract": "文章讨论非物质文化遗产融入设计教育的课程体系与实践教学路径。",
            "keywords": ["设计教育", "非物质文化遗产", "课程体系"],
            "journal": "设计教育研究",
            "authors": ["李四"],
            "year": 2025,
        }

        result = self.scorer.score_source(record, self.intake)

        self.assertLess(result["score"], 60)
        self.assertNotEqual(result["tier"], "tier_A")
        self.assertFalse(result["matched_research_anchors"]["qualifies_for_tier_A"])

    def test_architecture_history_without_higher_art_education_anchor_does_not_enter_tier_a(self):
        record = {
            "source_id": "cnki_architecture_history_only",
            "title": "地域建筑符号的历史演变与保护工程研究",
            "abstract": "文章从建筑史和保护工程角度讨论地域建筑符号的形制源流。",
            "keywords": ["地域建筑符号", "建筑史", "保护工程"],
            "journal": "古建园林技术",
            "authors": ["张三"],
            "year": 2024,
        }

        result = self.scorer.score_source(record, self.intake)

        self.assertLess(result["score"], 60)
        self.assertNotEqual(result["tier"], "tier_A")
        self.assertTrue(result["matched_research_anchors"]["has_intake_object_anchor"])
        self.assertFalse(result["matched_research_anchors"]["has_intake_context_anchor"])
        self.assertTrue(result["matched_research_anchors"]["has_intake_exclusion_anchor"])

    def test_unrelated_place_or_agriculture_record_scores_as_noise(self):
        record = {
            "source_id": "cnki_2025_noise",
            "title": "北疆地区庭院经济栽培体系的路径探索",
            "abstract": "在新疆北部农牧区利用庭院空地开展园艺栽培，提高农牧民经济收益。",
            "keywords": ["庭院经济", "乡村振兴"],
            "year": 2025,
        }

        result = self.scorer.score_source(record, self.intake)

        self.assertLess(result["score"], 30)
        self.assertEqual(result["tier"], "tier_C")
        self.assertFalse(result["matched_research_anchors"]["qualifies_for_tier_A"])

    def test_infers_missing_keywords_from_intake_anchor_matches(self):
        record = {
            "source_id": "cnki_missing_keywords",
            "title": "地域建筑符号融入设计教育的课程转化路径",
            "abstract": "文章讨论地域建筑美学、教学实践与实践教学之间的关系。",
            "keywords": [],
            "year": 2025,
        }
        result = self.scorer.score_source(record, self.intake)

        inferred = self.scorer.infer_keywords_for_provenance(record, result)

        self.assertIn("设计教育", inferred)
        self.assertTrue(any(term in inferred for term in ["地域建筑符号", "地域建筑美学"]))

    def test_scores_traditional_residential_renewal_record_as_tier_a(self):
        record = {
            "source_id": "cnki_residential_renewal",
            "title": "加强历史街区居住建筑更新，让旧城片区居民住上适居住房",
            "abstract": (
                "历史街区居住建筑是旧城片区居民安身立命之所，是历史文化名城保护的重要内容。"
                "文章讨论历史文化街区中历史街区居住建筑的保护更新、房屋修缮、卫生条件改善、"
                "财政支持和产权政策，以提升居民居住条件。"
            ),
            "keywords": ["历史街区居住建筑", "保护更新", "旧城片区", "历史文化街区", "适居住房"],
            "journal": "建筑",
            "authors": ["张三"],
            "year": 2026,
        }

        result = self.scorer.score_source(record, traditional_residential_renewal_intake())

        self.assertGreaterEqual(result["score"], 60)
        self.assertEqual(result["tier"], "tier_A")
        anchors = result["matched_research_anchors"]
        self.assertTrue(anchors["has_intake_object_anchor"])
        self.assertTrue(anchors["has_intake_context_anchor"])
        self.assertTrue(anchors["has_intake_application_anchor"])

    def test_traditional_residential_topic_accepts_protection_and_update_variant(self):
        record = {
            "source_id": "cnki_historic_district_update",
            "title": "基于城市触媒理论的历史文化街区保护与更新",
            "abstract": (
                "文章以历史文化街区为对象，讨论保护更新、空间优化、功能激活和文化传承，"
                "为旧城片区类似街区的城市更新实践提供参考。"
            ),
            "keywords": ["历史文化街区", "保护更新", "空间优化", "城市更新"],
            "journal": "山西建筑",
            "authors": ["李四"],
            "year": 2026,
        }

        result = self.scorer.score_source(record, traditional_residential_renewal_intake())

        self.assertEqual(result["tier"], "tier_A")
        self.assertTrue(result["matched_research_anchors"]["qualifies_for_tier_A"])

    def test_traditional_residential_topic_rejects_unrelated_general_housing(self):
        record = {
            "source_id": "cnki_general_housing",
            "title": "新建商品住宅户型优化与市场需求研究",
            "abstract": "文章讨论一般住房建设中的户型设计、市场需求和商品房销售策略。",
            "keywords": ["商品住宅", "户型设计", "市场需求"],
            "journal": "住宅科技",
            "authors": ["王五"],
            "year": 2025,
        }

        result = self.scorer.score_source(record, traditional_residential_renewal_intake())

        self.assertLess(result["score"], 60)
        self.assertNotEqual(result["tier"], "tier_A")
        self.assertFalse(result["matched_research_anchors"]["qualifies_for_tier_A"])


if __name__ == "__main__":
    unittest.main()
