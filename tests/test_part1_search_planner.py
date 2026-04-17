import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLANNER_PATH = PROJECT_ROOT / "runtime" / "agents" / "search_planner.py"


def load_planner_module():
    spec = importlib.util.spec_from_file_location("search_planner", PLANNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def architecture_elements_art_education_intake():
    return {
        "intake_id": "intake_test_architecture_elements_art_education",
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
            "跨学科融合",
            "文化传承",
            "审美素养",
            "文创转化",
            "历史街区活化",
            "数字媒介艺术",
        ],
        "source_preference": {
            "document_types": [
                "中文核心期刊论文",
                "CSSCI 期刊论文",
                "教育学硕士论文",
                "艺术学硕士论文",
                "设计学硕士论文",
                "高校课程改革与教学案例研究",
                "建筑文化与设计教育交叉研究论文",
            ],
            "priority_sources": ["cnki", "wanfang", "vip"],
        },
        "scope_notes": (
            "纳入高校设计、设计实践、数字媒介艺术等教学中的课程构建、教学方法、实践创作、"
            "成果转化、文化传承研究；不纳入纯地域建筑保护工程、纯建筑史考据、非高校阶段设计教育。"
        ),
    }


def traditional_residential_renewal_intake():
    return {
        "intake_id": "intake_test_traditional_residential_renewal",
        "research_topic": "历史街区居住建筑更新与社区居住品质提升",
        "research_question": (
            "在历史风貌保护前提下，如何通过保护更新、节能改造、微改造、"
            "产权政策与财政支持，推动历史街区居住建筑改善居住条件？"
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
            "公房私房",
            "财政专项资金",
            "历史文化名城保护",
        ],
        "source_preference": {
            "document_types": [
                "城乡规划类核心期刊论文",
                "建筑学类核心期刊论文",
                "历史文化遗产保护类核心期刊论文",
                "城市更新与历史街区保护硕博论文",
                "政策研究报告",
            ],
            "priority_sources": ["cnki", "wanfang", "vip"],
        },
        "scope_notes": (
            "纳入历史街区居住建筑在旧城片区、历史文化街区中的保护更新、居民居住条件改善、"
            "节能与基础设施改造、微改造路径、产权与补助政策、财政支持机制。"
        ),
    }


def db_by_id(plan, db_id):
    return next(db for db in plan["databases"] if db["db_id"] == db_id)


def query_by_id(db, query_id):
    for group in db["query_groups"]:
        for query in group["queries"]:
            if query["query_id"] == query_id:
                return query
    raise AssertionError(f"query not found: {query_id}")


class Part1SearchPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = load_planner_module()
        self.intake = architecture_elements_art_education_intake()
        self.original_env = {
            "RTM_RESEARCHAGENT_COMMAND": os.environ.get("RTM_RESEARCHAGENT_COMMAND"),
            "RTM_RESEARCHAGENT_TIMEOUT": os.environ.get("RTM_RESEARCHAGENT_TIMEOUT"),
        }
        self.addCleanup(self.restore_env)
        for key in self.original_env:
            os.environ.pop(key, None)

    def restore_env(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_cnki_q1_1_uses_confirmed_intake_anchors(self):
        plan = self.planner.generate_plan(self.intake)
        cnki = db_by_id(plan, "cnki")
        query = query_by_id(cnki, "cnki_q1_1")

        query_text = " ".join(query["terms"])

        self.assertIn("地域建筑符号", query_text)
        self.assertIn("设计教育", query_text)
        self.assertIn("地域建筑美学", query_text)
        self.assertTrue(
            any(anchor in query_text for anchor in ["课程转化", "教学实践", "设计教育"]),
            "cnki_q1_1 should pair the research object with education/application anchors",
        )
        self.assertTrue(
            any("地域建筑符号" in term and "设计教育" in term for term in query["terms"]),
            "cnki_q1_1 should contain focused phrases that pair research object and education scene",
        )
        self.assertTrue(
            any("地域建筑美学" in term and ("设计教育" in term or "设计教育" in term) for term in query["terms"]),
            "cnki_q1_1 should not leave theory anchors as standalone broad terms",
        )
        self.assertFalse(
            query["operator"] == "OR"
            and set(query["terms"]) == set(self.intake["keywords_required"]),
            "cnki_q1_1 must remain a focused core query, not a broad OR over all required keywords",
        )

    def test_search_plan_contains_application_and_teaching_clues(self):
        plan = self.planner.generate_plan(self.intake)
        plan_text = json.dumps(plan, ensure_ascii=False)

        expected_clues = {"课程体系", "实践教学", "设计创作", "数字媒介艺术", "文创转化"}
        matched_clues = {clue for clue in expected_clues if clue in plan_text}

        self.assertGreaterEqual(
            len(matched_clues),
            4,
            "search plan should preserve teaching, creation, media, and transformation clues from intake",
        )

    def test_search_plan_does_not_inject_fixed_case_template(self):
        plan = self.planner.generate_plan(self.intake)
        plan_text = json.dumps(plan, ensure_ascii=False)

        self.assertIn("地域建筑符号", plan_text)
        self.assertNotIn("固定案例模板", plan_text)

    def test_search_plan_does_not_inject_art_education_template_for_housing_topic(self):
        plan = self.planner.generate_plan(traditional_residential_renewal_intake())
        cnki = db_by_id(plan, "cnki")
        query = query_by_id(cnki, "cnki_q1_1")
        query_text = " ".join(query["terms"])
        plan_text = json.dumps(plan, ensure_ascii=False)

        self.assertIn("历史街区居住建筑", query_text)
        self.assertTrue(
            any(anchor in query_text for anchor in ["保护更新", "旧城片区", "历史文化街区", "居住品质提升"]),
            "cnki_q1_1 should pair the research object with protection/renewal/housing-quality anchors",
        )
        self.assertIn("微改造", plan_text)
        self.assertIn("产权政策", plan_text)
        self.assertIn("财政专项资金", plan_text)
        self.assertNotIn("课程、教学", plan_text)
        self.assertNotIn("设计创作", plan_text)

    def test_cnki_remains_first_priority_and_wanfang_vip_are_supplementary(self):
        plan = self.planner.generate_plan(self.intake)
        cnki = db_by_id(plan, "cnki")
        wanfang = db_by_id(plan, "wanfang")
        vip = db_by_id(plan, "vip")

        self.assertEqual(cnki["priority"], 1)
        self.assertEqual(plan["retrieval_sequence"][0], "cnki")
        self.assertEqual(
            cnki["max_results_total"],
            28,
            "Part 1 CNKI cap should allow at most 70% of the 40-source target",
        )

        for db in (wanfang, vip):
            with self.subTest(db_id=db["db_id"]):
                self.assertGreater(db["priority"], cnki["priority"])
                self.assertNotEqual(db["download_priority"], "high")
                db_text = json.dumps(db, ensure_ascii=False)
                self.assertIn("补充", db_text)

    def test_search_plan_encodes_40_source_quota_and_english_journal_sources(self):
        plan = self.planner.generate_plan(self.intake)
        quota = plan["source_quota_policy"]

        self.assertEqual(40, quota["target_total"])
        self.assertEqual(24, quota["cnki_min_count"])
        self.assertEqual(28, quota["cnki_max_count"])
        self.assertEqual(5, quota["english_journal_min_count"])
        self.assertEqual("accepted_sources", quota["enforced_on"])
        self.assertEqual(["cnki", "wanfang", "vip", "crossref", "openalex", "doaj"], plan["retrieval_sequence"])

        for db_id in ["crossref", "openalex", "doaj"]:
            with self.subTest(db_id=db_id):
                db = db_by_id(plan, db_id)
                self.assertEqual("tier2", db["tier"])
                self.assertGreaterEqual(db["max_results_total"], 1)
                self.assertTrue(db["english_journal_required"])
                db_text = json.dumps(db, ensure_ascii=False).lower()
                self.assertIn("journal", db_text)
                self.assertTrue(
                    any(term in db_text for term in ["architecture", "design education", "cultural heritage"]),
                    "English supplement queries should expose English journal search terms",
                )

    def test_researchagent_sidecar_runs_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            old_root = self.planner.PROJECT_ROOT
            self.planner.PROJECT_ROOT = project_root
            self.addCleanup(setattr, self.planner, "PROJECT_ROOT", old_root)
            (project_root / "outputs" / "part1").mkdir(parents=True)
            (project_root / "manifests").mkdir()
            self.planner.DEFAULT_CNKI_MAX_RESULTS_TOTAL = 20
            (project_root / "outputs" / "part1" / "intake.json").write_text(
                json.dumps(self.intake, ensure_ascii=False),
                encoding="utf-8",
            )
            plan = self.planner.generate_plan(self.intake)
            (project_root / "outputs" / "part1" / "search_plan.json").write_text(
                json.dumps(plan, ensure_ascii=False),
                encoding="utf-8",
            )
            (project_root / "manifests" / "source-policy.json").write_text(
                json.dumps({"primary": "cnki"}, ensure_ascii=False),
                encoding="utf-8",
            )
            fake_agent = project_root / "fake_researchagent.py"
            fake_agent.write_text(
                (
                    "import json, sys\n"
                    "request = json.load(sys.stdin)\n"
                    "assert request['agent_name'] == 'researchagent'\n"
                    "assert request['task'] == 'part1_search_strategy_review'\n"
                    "assert request['skill'] == 'part1-search-plan-review'\n"
                    "paths = [item['path'] for item in request['inputs']]\n"
                    "assert 'outputs/part1/search_plan.json' in paths\n"
                    "assert 'manifests/source-policy.json' in paths\n"
                    "print(json.dumps({'report': 'researchagent reviewed search plan'}, ensure_ascii=False))\n"
                ),
                encoding="utf-8",
            )
            os.environ["RTM_RESEARCHAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"
            os.environ["RTM_RESEARCHAGENT_TIMEOUT"] = "5"

            self.planner.write_researchagent_sidecar()

            review = json.loads((project_root / "outputs/part1/researchagent_search_plan_review.json").read_text(encoding="utf-8"))
            self.assertEqual("researchagent reviewed search plan", review["report"])
            provenance = json.loads((project_root / "outputs/part1/researchagent_provenance.json").read_text(encoding="utf-8"))
            self.assertEqual("researchagent", provenance["agent_name"])
            self.assertEqual("llm", provenance["mode"])

    def test_researchagent_runtime_skill_exists(self):
        skill_path = PROJECT_ROOT / "skills" / "part1-search-plan-review" / "SKILL.md"
        self.assertTrue(skill_path.exists())
        text = skill_path.read_text(encoding="utf-8")
        self.assertIn("不得改写 `outputs/part1/search_plan.json`", text)
        self.assertIn("不得确认、跳过或伪造 `intake_confirmed`", text)


if __name__ == "__main__":
    unittest.main()
