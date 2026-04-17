import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"
FINALIZER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part6_mvp_finalizer.py"
WRITER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part6_writer.py"
WRITER_SKILL_DIR = PROJECT_ROOT / "skills" / "part6-write-manuscript-body"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part6MvpFinalizerTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_module(PIPELINE_PATH, "pipeline_part6_finalizer_test")
        self.finalizer = load_module(FINALIZER_PATH, "part6_mvp_finalizer_test")
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.desktop_dir = self.project_root / "Desktop"
        self.original_desktop_env = {
            "PART6_DESKTOP_DIR": os.environ.get("PART6_DESKTOP_DIR"),
            "PART5_DESKTOP_DIR": os.environ.get("PART5_DESKTOP_DIR"),
            "RTM_WRITEAGENT_COMMAND": os.environ.get("RTM_WRITEAGENT_COMMAND"),
            "RTM_WRITEAGENT_TIMEOUT": os.environ.get("RTM_WRITEAGENT_TIMEOUT"),
            "RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK": os.environ.get("RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"),
            "RTM_CLAIMAUDITOR_COMMAND": os.environ.get("RTM_CLAIMAUDITOR_COMMAND"),
            "RTM_CLAIMAUDITOR_TIMEOUT": os.environ.get("RTM_CLAIMAUDITOR_TIMEOUT"),
            "RTM_CITATIONAUDITOR_COMMAND": os.environ.get("RTM_CITATIONAUDITOR_COMMAND"),
            "RTM_CITATIONAUDITOR_TIMEOUT": os.environ.get("RTM_CITATIONAUDITOR_TIMEOUT"),
        }
        os.environ["PART6_DESKTOP_DIR"] = str(self.desktop_dir)
        os.environ["PART5_DESKTOP_DIR"] = str(self.desktop_dir)
        for key in [
            "RTM_CLAIMAUDITOR_COMMAND",
            "RTM_CLAIMAUDITOR_TIMEOUT",
            "RTM_CITATIONAUDITOR_COMMAND",
            "RTM_CITATIONAUDITOR_TIMEOUT",
        ]:
            os.environ.pop(key, None)
        self.addCleanup(self.restore_desktop_env)

        self.configure_pipeline_module(self.pipeline)
        self.configure_pipeline_module(self.finalizer.pipeline)

        for rel_dir in [
            "runtime",
            "raw-library",
            "research-wiki",
            "outputs/part1",
            "outputs/part5/chapter_briefs",
            "outputs/part5/case_analysis_templates",
            "outputs/part6",
            "schemas",
            "process-memory",
        ]:
            (self.project_root / rel_dir).mkdir(parents=True, exist_ok=True)

        self.copy_part6_schemas()

    def configure_pipeline_module(self, module):
        module.PROJECT_ROOT = self.project_root
        module.STATE_FILE = self.project_root / "runtime" / "state.json"
        module.PROCESS_MEMORY_DIR = self.project_root / "process-memory"
        module.SCHEMA_MAP = {
            "outputs/part6/claim_risk_report.json": "schemas/part6_claim_risk_report.schema.json",
            "outputs/part6/citation_consistency_report.json": "schemas/part6_citation_consistency_report.schema.json",
            "outputs/part6/submission_package_manifest.json": "schemas/part6_submission_package_manifest.schema.json",
            "outputs/part6/final_readiness_decision.json": "schemas/part6_final_readiness_decision.schema.json",
        }

    def copy_part6_schemas(self):
        for rel_path in self.pipeline.SCHEMA_MAP.values():
            source = PROJECT_ROOT / rel_path
            target = self.project_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def restore_desktop_env(self):
        for key, value in self.original_desktop_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read_json(self, rel_path):
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def write_text(self, rel_path, text):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_text(self, rel_path):
        return (self.project_root / rel_path).read_text(encoding="utf-8")

    def completed_stage(self, gates=None):
        return {
            "status": "completed",
            "started_at": "2026-04-16T00:00:00+00:00",
            "completed_at": "2026-04-16T00:10:00+00:00",
            "gate_passed": True,
            "human_gates_completed": gates or [],
        }

    def allow_deterministic_writer_fallback(self):
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)
        os.environ["RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"] = "1"

    def write_state(self, *, part6_gates=None):
        self.write_json(
            "runtime/state.json",
            {
                "schema_version": "1.0.0",
                "pipeline_id": "research-to-manuscript-v1",
                "initialized_at": "2026-04-16T00:00:00+00:00",
                "current_stage": "part6",
                "stages": {
                    "part1": self.completed_stage(["intake_confirmed"]),
                    "part2": self.completed_stage(),
                    "part3": self.completed_stage(["argument_tree_selected"]),
                    "part4": self.completed_stage(),
                    "part5": self.completed_stage(),
                    "part6": {
                        "status": "in_progress",
                        "started_at": "2026-04-16T01:00:00+00:00",
                        "completed_at": None,
                        "gate_passed": False,
                        "human_gates_completed": part6_gates or [],
                    },
                },
                "last_failure": None,
                "repair_log": [],
                "human_decision_log": [],
            },
        )

    def write_valid_part5_handoff(self, *, readiness_verdict="ready_for_part6_with_research_debt"):
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "sources": [
                    {
                        "source_id": "cnki_001",
                        "title": "地域建筑符号空间研究",
                        "authenticity_verdict": "pass",
                        "authenticity_status": "verified",
                    }
                ],
            },
        )
        self.write_json(
            "outputs/part1/accepted_sources.json",
            {
                "created_at": "2026-04-16T00:20:00+00:00",
                "intake_id": "intake_001",
                "min_tier": "tier_B",
                "total": 1,
                "source_ids": ["cnki_001"],
            },
        )
        self.write_json(
            "outputs/part1/authenticity_report.json",
            {
                "report_id": "auth_report_001",
                "created_at": "2026-04-16T00:20:00+00:00",
                "based_on_manifest": "download_manifest_001",
                "total_checked": 1,
                "passed": 1,
                "failed": 0,
                "warnings": 0,
                "pass_rate": 100.0,
                "results": [
                    {
                        "source_id": "cnki_001",
                        "title": "地域建筑符号空间研究",
                        "checks": [],
                        "flags": [],
                        "verdict": "pass",
                        "notes": "通过",
                    }
                ],
            },
        )
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "pages": [
                    {
                        "page_id": "wiki_001",
                        "file_path": "research-wiki/pages/wiki_001.md",
                        "source_ids": ["cnki_001"],
                    }
                ],
                "source_mapping_complete": True,
            },
        )
        self.write_text("outputs/part5/chapter_briefs/sec_1.md", "# 绪论\n")
        self.write_text("outputs/part5/case_analysis_templates/case_1.md", "# 案例模板\n")
        self.write_json(
            "outputs/part5/claim_evidence_matrix.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": "地域建筑符号空间可作为设计方法参照。",
                        "evidence_level": "hard_evidence",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["wiki_001"],
                        "risk_level": "low",
                        "status": "mapped",
                    }
                ],
            },
        )
        self.write_json(
            "outputs/part5/citation_map.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "source_refs": [
                    {
                        "source_id": "cnki_001",
                        "claim_ids": ["claim_001"],
                        "citation_status": "accepted_source",
                    }
                ],
                "unmapped_sources": [],
            },
        )
        self.write_json(
            "outputs/part5/figure_plan.json",
            {"schema_version": "1.0.0", "generated_at": "2026-04-16T00:30:00+00:00", "figures": []},
        )
        self.write_json(
            "outputs/part5/open_questions.json",
            {"schema_version": "1.0.0", "generated_at": "2026-04-16T00:30:00+00:00", "questions": []},
        )
        self.write_text("outputs/part5/manuscript_v1.md", "# 论文初稿\n\n## 绪论\n\n文本。\n")
        self.write_json(
            "outputs/part5/review_matrix.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:40:00+00:00",
                "manuscript_ref": "outputs/part5/manuscript_v1.md",
                "reviews": [
                    {
                        "review_id": "review_001",
                        "dimension": "evidence",
                        "severity": "medium",
                        "finding": "保留 residual risk。",
                        "claim_ids": ["claim_001"],
                        "status": "registered",
                    }
                ],
            },
        )
        self.write_text("outputs/part5/review_summary.md", "# Review Summary\n")
        self.write_text("outputs/part5/review_report.md", "# Part 5 Review Report\n")
        self.write_json(
            "outputs/part5/claim_risk_report.json",
            {"schema_version": "1.0.0", "generated_at": "2026-04-16T00:40:00+00:00", "risk_items": []},
        )
        self.write_json(
            "outputs/part5/citation_consistency_precheck.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:40:00+00:00",
                "status": "pass",
                "checked_claim_ids": ["claim_001"],
                "warnings": [],
                "errors": [],
            },
        )
        self.write_json(
            "outputs/part5/revision_log.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:50:00+00:00",
                "source_review_ref": "outputs/part5/review_matrix.json",
                "revisions": [
                    {
                        "revision_id": "rev_001",
                        "review_id": "review_001",
                        "action": "保守修订",
                        "status": "applied",
                    }
                ],
                "residual_risks": [],
            },
        )
        manuscript = (
            "# 论文修订稿 v2\n\n"
            "## 绪论\n\n"
            "本文围绕地域建筑符号的空间结构展开，采用保守表述。\n\n"
            "## 结论\n\n"
            "地域建筑符号空间结构只能作为方法参照，仍需保留证据债务说明。\n"
        )
        self.write_text("outputs/part5/manuscript_v2.md", manuscript)
        self.write_json(
            "outputs/part5/part6_readiness_decision.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:55:00+00:00",
                "verdict": readiness_verdict,
                "registered_blockers": [],
                "residual_risks": (
                    ["仍有研究债务。"]
                    if readiness_verdict == "ready_for_part6_with_research_debt"
                    else []
                ),
                "handoff_artifacts": [
                    "outputs/part5/manuscript_v2.md",
                    "outputs/part5/review_matrix.json",
                    "outputs/part5/review_report.md",
                    "outputs/part5/revision_log.json",
                    "outputs/part5/claim_evidence_matrix.json",
                    "outputs/part5/citation_map.json",
                    "outputs/part5/figure_plan.json",
                    "outputs/part5/part6_readiness_decision.json",
                ],
            },
        )

    def authorize_part6(self):
        self.pipeline.confirm_human_gate("part6_finalization_authorized", "授权 Part 6")

    def write_body_composition_inputs(self):
        self.write_json(
            "outputs/part4/paper_outline.json",
            {
                "schema_version": "1.0.0",
                "sections": [
                    {
                        "section_id": "sec_1",
                        "title": "绪论",
                        "level": 1,
                        "brief": "提出研究背景、问题意识、研究对象与主论题。",
                        "argument_node_ids": ["claim_001"],
                        "support_source_ids": ["cnki_001"],
                        "subsections": [
                            {
                                "section_id": "sec_1_1",
                                "title": "研究背景与问题提出",
                                "level": 2,
                                "brief": "说明研究缘起与现实问题。",
                                "argument_node_ids": ["claim_001"],
                                "support_source_ids": ["cnki_001"],
                                "subsections": [],
                            }
                        ],
                    },
                    {
                        "section_id": "sec_2",
                        "title": "教学实践路径",
                        "level": 1,
                        "brief": "围绕课程组织、案例分析与创作转化展开正文。",
                        "argument_node_ids": ["claim_001"],
                        "support_source_ids": ["cnki_001"],
                        "subsections": [],
                    },
                    {
                        "section_id": "sec_3",
                        "title": "结论与研究债务",
                        "level": 1,
                        "brief": "收束论证并登记仍需人工复核的证据债务。",
                        "argument_node_ids": ["claim_001"],
                        "support_source_ids": ["cnki_001"],
                        "subsections": [],
                    },
                ],
            },
        )

    def test_all_generates_required_package_files_without_confirming_final_decision(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_json(
            "outputs/part1/intake.json",
            {
                "research_topic": "地域建筑符号在设计教育中的转化应用",
                "student_name": "李同学",
            },
        )
        readiness = self.read_json("outputs/part5/part6_readiness_decision.json")
        readiness["residual_risks"] = [
            "案例分析需要借助Part 2 Evidence... 需要图纸/动线/视线材料支撑，缺失时只能保守表述。",
            "evidence_001_1未在manuscript_v1中形成可见论证位置。",
        ]
        self.write_json("outputs/part5/part6_readiness_decision.json", readiness)
        self.write_json(
            "outputs/part5/claim_risk_report.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:40:00+00:00",
                "risk_items": [
                    {
                        "claim_id": "claim_001",
                        "risk_level": "medium",
                        "risk_type": "source_sufficiency",
                        "finding": "evidence_001_1未在manuscript_v1中形成可见论证位置。",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["wiki_001"],
                    }
                ],
            },
        )
        citation_map = self.read_json("outputs/part5/citation_map.json")
        citation_map["source_refs"][0]["claim_ids"] = ["evidence_001_1"]
        self.write_json("outputs/part5/citation_map.json", citation_map)
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "all")

        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        self.assertEqual(9, len(manifest["required_files"]))
        for rel_path in manifest["required_files"]:
            self.assertTrue((self.project_root / rel_path).exists(), rel_path)
        self.assertIn("outputs/part6/final_manuscript.docx", manifest["required_files"])
        self.assertIn("outputs/part6/docx_format_report.json", manifest["required_files"])
        self.assertIn(
            "writing-policy/rules/scut_course_paper_format.md",
            manifest["policy_refs"],
        )
        format_report = self.read_json("outputs/part6/docx_format_report.json")
        self.assertIn(format_report["status"], {"pass", "pass_with_warnings"})
        self.assertTrue(format_report["cover_excluded"])
        self.assertEqual("地域建筑符号在设计教育中的转化应用", format_report["paper_title"])
        self.assertEqual(
            str(self.desktop_dir / "地域建筑符号在设计教育中的转化应用.docx"),
            format_report["desktop_docx_ref"],
        )
        self.assertTrue((self.project_root / "outputs/part6/final_manuscript.docx").exists())
        self.assertTrue((self.desktop_dir / "地域建筑符号在设计教育中的转化应用.docx").exists())
        doc = Document(self.project_root / "outputs/part6/final_manuscript.docx")
        doc_text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        self.assertIn("地域建筑符号在设计教育中的转化应用", doc_text)
        self.assertIn("李同学", doc_text)
        self.assertNotIn("教师评语", doc_text)
        self.assertNotIn("正式上交课程论文时，请删除蓝色字体内容", doc_text)
        state = self.read_json("runtime/state.json")
        self.assertNotIn(
            "part6_final_decision_confirmed",
            state["stages"]["part6"]["human_gates_completed"],
        )
        package_text = "\n".join([
            self.read_text("outputs/part6/claim_risk_report.json"),
            self.read_text("outputs/part6/citation_consistency_report.json"),
            self.read_text("outputs/part6/final_readiness_decision.json"),
            self.read_text("outputs/part6/submission_checklist.md"),
        ])
        final_text = self.read_text("outputs/part6/final_manuscript.md")
        self.assertNotIn("## 风险与残余说明", final_text)
        self.assertIn("研究债务", package_text)
        self.assertIn("claim_risk_report", package_text)
        self.assertIn("final_readiness_decision", package_text)
        for marker in ["Part 2 Evidence", "manuscript_v1", "evidence_001_1", "Part 5 claim-evidence matrix"]:
            self.assertNotIn(marker, package_text)

    def test_finalize_composes_continuous_body_instead_of_wrapping_scaffold(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.write_text(
            "outputs/part5/manuscript_v2.md",
            (
                "# 论文修订稿 v2\n\n"
                "> 本稿是 Part 5 MVP 的审稿驱动修订稿。\n\n"
                "## 绪论\n\n"
                "提出研究背景、问题意识、研究对象与主论题。\n\n"
                "本节核心论点：\n"
                "- 地域建筑符号空间可作为设计方法参照。（证据：cnki_001；风险：low）\n\n"
                "写作提示：本节应避免新增未登记引用。\n"
            ),
        )
        self.desktop_dir.mkdir(parents=True, exist_ok=True)
        for stale_name in [
            "part6_final_abstract.md",
            "part6_final_keywords.json",
            "part6_writer_body.md",
        ]:
            (self.desktop_dir / stale_name).write_text("stale", encoding="utf-8")
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        final_text = self.read_text("outputs/part6/final_manuscript.md")
        body = final_text.split("## 正文", 1)[1].split("## 结论", 1)[0]
        forbidden_markers = [
            "Part 5 MVP",
            "本节核心论点",
            "写作提示",
            "待补证据",
            "scaffold",
            "写作骨架",
            "outline",
            "argument tree",
            "claim-evidence matrix",
            "raw-library",
            "research-wiki",
            "citation_map",
            "researchwiki",
            "Part2",
            "argumenttree",
            "canonical artifact",
            "Part 1-5",
            "source_id",
            "cnki_",
            "已登记证据",
            "证据层显示",
            "章节brief",
            "risk_level",
            "当前风险等级",
            "风险等级控制结论强度",
            "low 风险等级",
            "medium 风险等级",
            "high 风险等级",
            "blocked 风险等级",
            "unknown 风险等级",
            "Part 2 Evidence",
        ]
        for marker in forbidden_markers:
            self.assertNotIn(marker, final_text)
        self.assertNotIn("## 风险与残余说明", final_text)
        self.assertNotIn("## 证据边界与研究不足", final_text)
        self.assertNotIn("## 残余研究债务", final_text)
        desktop_manuscript = self.desktop_dir / "part6_final_manuscript.md"
        self.assertTrue(desktop_manuscript.exists())
        desktop_text = desktop_manuscript.read_text(encoding="utf-8").strip()
        self.assertEqual(final_text.strip(), desktop_text)
        self.assertIn("## 摘要", desktop_text)
        self.assertIn("## 关键词", desktop_text)
        self.assertIn("## 正文", desktop_text)
        self.assertIn("## 结论", desktop_text)
        self.assertNotIn("## 风险与残余说明", desktop_text)
        self.assertNotIn("## 证据边界与研究不足", desktop_text)
        for stale_name in [
            "part6_final_abstract.md",
            "part6_final_keywords.json",
            "part6_writer_body.md",
        ]:
            self.assertFalse((self.desktop_dir / stale_name).exists(), stale_name)
        paragraphs = [
            line.strip()
            for line in body.splitlines()
            if line.strip()
            and not line.lstrip().startswith("#")
            and not line.lstrip().startswith("-")
            and not line.lstrip().startswith(">")
        ]
        self.assertGreaterEqual(len(paragraphs), 6)
        self.assertGreater(len(body), 900)
        self.assertNotIn("cnki_001", body)
        self.assertIn("地域建筑符号空间研究", body)
        self.assertIn("研究背景与问题提出", body)

    def test_finalize_writes_article_like_academic_draft_not_repeated_template(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.write_json(
            "outputs/part1/intake.json",
            {
                "research_topic": "地域建筑符号在设计教育中的转化应用",
                "research_question": (
                    "设计教育中，如何系统挖掘、提炼并应用地域建筑符号，"
                    "以提升学生审美素养、创作能力与传统文化理解，同时形成可落地的课程、教学与成果转化路径？"
                ),
                "keywords_required": ["地域建筑符号", "设计教育", "教学实践"],
                "keywords_suggested": ["课程体系", "实践教学", "文化传承", "审美素养", "文创转化"],
                "scope_notes": "聚焦设计教育中的课程构建、教学方法、实践创作与成果转化。",
            },
        )
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        final_text = self.read_text("outputs/part6/final_manuscript.md")
        body = final_text.split("## 正文", 1)[1].split("## 结论", 1)[0]
        repeated_template_phrases = [
            "相关判断限定在",
            "该判断对应的来源链为",
            "从教学转化看，本节承担的是",
            "进一步说，本节的论述重点不是罗列材料",
            "其材料边界仍回到",
        ]
        for phrase in repeated_template_phrases:
            self.assertLessEqual(body.count(phrase), 1, phrase)
        expected_terms = [
            "对象界定",
            "问题诊断",
            "路径论证",
            "实施条件",
            "应用路径",
            "成果转化",
            "证据边界",
        ]
        for term in expected_terms:
            self.assertIn(term, body)
        self.assertIn("已核验资料", body)
        self.assertIn("单一来源", body)
        self.assertNotIn("ISBN", final_text)
        self.assertNotIn("《《", final_text)
        self.assertNotIn("》:", final_text)
        abstract = self.read_text("outputs/part6/final_abstract.md").strip()
        self.assertIn("对象识别—问题诊断—路径建构—条件说明—边界收束", abstract)
        self.assertTrue(abstract.endswith("。"))
        self.assertNotIn("课程。", abstract[-6:])
        self.assertGreater(len(body), 2200)

    def test_part6_writer_is_dedicated_agent_and_finalizer_uses_its_body(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()

        self.assertTrue(WRITER_PATH.exists())
        writer_source = WRITER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from runtime.agents import part6_mvp_finalizer", writer_source)
        self.assertNotIn("from runtime.agents.part6_mvp_finalizer", writer_source)
        writer = load_module(WRITER_PATH, "part6_writer_agent_boundary_test")
        self.assertTrue(hasattr(writer, "Part6WriterAgent"))
        writer_agent = writer.Part6WriterAgent(self.project_root)
        self.assertEqual("part6_writer", writer_agent.agent_id)
        self.assertTrue(hasattr(writer_agent, "run"))
        self.assertFalse(hasattr(self.finalizer, "academic_writer_body"))
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        writer_body = self.read_text("outputs/part6/writer_body.md").strip()
        final_text = self.read_text("outputs/part6/final_manuscript.md")
        final_body = final_text.split("## 正文", 1)[1].split("## 结论", 1)[0].strip()
        self.assertEqual(writer_body, final_body)
        self.assertIn("绪论：研究背景与问题提出", writer_body)
        self.assertIn("路径机制与实施条件", writer_body)

    def test_finalize_uses_configured_writeagent_command_for_final_body(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        fake_writer = self.project_root / "fake_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'writeagent'\n"
                "assert request['task'] == 'part6_finalize_manuscript'\n"
                "assert request['skill'] == 'part6-finalize-manuscript'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "for path in [\n"
                "  'outputs/part5/manuscript_v2.md',\n"
                "  'outputs/part4/paper_outline.json',\n"
                "  'outputs/part3/argument_tree.json',\n"
                "  'writing-policy/style_guides/author_style_profile.md',\n"
                "  'skills/academic-register-polish/SKILL.md',\n"
                "  'skills/paper-manuscript-style-profile/SKILL.md',\n"
                "]:\n"
                "  assert path in paths, path\n"
                "joined_instructions = '\\n'.join(request['instructions'])\n"
                "assert 'paper-manuscript-style-profile' in joined_instructions\n"
                "assert '证据边界与研究不足' in joined_instructions\n"
                "print(json.dumps({\n"
                "  'body': '## LLM 最终正文\\n\\n"
                "LLM writer 对 manuscript_v2 进行保守收束，保留证据边界和研究债务。\\n',\n"
                "  'abstract': '本文基于已核验资料对最终稿进行保守收束。',\n"
                "  'keywords': ['地域建筑符号', '设计教育', '证据边界'],\n"
                "  'conclusion': '最终稿只确认内部审阅状态，不自动提交。'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"

        self.finalizer.run_step(self.project_root, "finalize")

        writer_body = self.read_text("outputs/part6/writer_body.md")
        final_text = self.read_text("outputs/part6/final_manuscript.md")
        self.assertIn("LLM 最终正文", writer_body)
        self.assertIn("LLM 最终正文", final_text)
        self.assertIn("本文基于已核验资料", self.read_text("outputs/part6/final_abstract.md"))
        self.assertEqual(
            ["地域建筑符号", "设计教育", "证据边界"],
            self.read_json("outputs/part6/final_keywords.json")["keywords"],
        )
        provenance = self.read_json("outputs/part6/writer_provenance.json")
        self.assertEqual("llm", provenance["mode"])
        self.assertEqual("writeagent", provenance["agent_name"])
        self.assertEqual("part6-finalize-manuscript", provenance["skill"])

    def test_finalize_rejects_writeagent_output_with_internal_markers(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        fake_writer = self.project_root / "fake_dirty_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "json.load(sys.stdin)\n"
                "print(json.dumps({\n"
                "  'body': '## 修订后论证整合\\n\\nPart2 Evidence 显示：source_id=cnki_001；risk_level=low；"
                "相关判断限定在 review_matrix 与 claim-evidence matrix；该判断对应的来源链为 cnki_001。\\n'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"

        with self.assertRaisesRegex(RuntimeError, "内部工作标记"):
            self.finalizer.run_step(self.project_root, "finalize")

        self.assertFalse((self.project_root / "outputs/part6/final_manuscript.md").exists())
        self.assertFalse((self.project_root / "outputs/part6/writer_body.md").exists())

    def test_finalize_rejects_writeagent_output_with_standalone_risk_section(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        fake_writer = self.project_root / "fake_risk_section_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "json.load(sys.stdin)\n"
                "print(json.dumps({\n"
                "  'body': '## 正文\\n\\n本文围绕研究对象展开。\\n\\n"
                "## 证据边界与研究不足\\n\\n这里不应作为独立正文 section。\\n'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"

        with self.assertRaisesRegex(RuntimeError, "独立风险/证据边界章节"):
            self.finalizer.run_step(self.project_root, "finalize")

        self.assertFalse((self.project_root / "outputs/part6/final_manuscript.md").exists())
        self.assertFalse((self.project_root / "outputs/part6/writer_body.md").exists())

    def test_finalize_does_not_append_duplicate_conclusion_when_body_has_conclusion(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        fake_writer = self.project_root / "fake_conclusion_writeagent.py"
        fake_writer.write_text(
            (
                "import json, sys\n"
                "json.load(sys.stdin)\n"
                "print(json.dumps({\n"
                "  'body': '一、绪论\\n\\n历史街区居住建筑更新需要回应居住品质与历史文化延续。\\n\\n"
                "七、结论与展望\\n\\n后续研究可结合居民访谈和现场资料继续验证。\\n',\n"
                "  'abstract': '本文围绕历史街区居住建筑更新展开。',\n"
                "  'keywords': ['历史街区居住建筑', '保护更新'],\n"
                "  'conclusion': '不应重复追加的结论。'\n"
                "}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WRITEAGENT_COMMAND"] = f"{sys.executable} {fake_writer}"

        self.finalizer.run_step(self.project_root, "finalize")

        final_text = self.read_text("outputs/part6/final_manuscript.md")
        self.assertIn("七、结论与展望", final_text)
        self.assertNotIn("\n## 结论\n", final_text)
        self.assertNotIn("## 风险与残余说明", final_text)
        self.assertNotIn("不应重复追加的结论", final_text)

    def test_finalize_requires_writeagent_command_when_fallback_disabled(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        os.environ.pop("RTM_WRITEAGENT_COMMAND", None)

        with self.assertRaisesRegex(RuntimeError, "RTM_WRITEAGENT_COMMAND"):
            self.finalizer.run_step(self.project_root, "finalize")

        self.assertFalse((self.project_root / "outputs/part6/final_manuscript.md").exists())
        self.assertFalse((self.project_root / "outputs/part6/writer_body.md").exists())

    def test_finalize_can_use_explicit_deterministic_fallback_escape_hatch(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        provenance = self.read_json("outputs/part6/writer_provenance.json")
        self.assertEqual("deterministic_fallback", provenance["mode"])
        self.assertEqual("writeagent", provenance["agent_name"])
        self.assertFalse(provenance["command_configured"])

    def test_finalize_does_not_leak_education_template_for_non_education_topic(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.write_json(
            "outputs/part1/intake.json",
            {
                "research_topic": "历史街区居住建筑更新与社区居住品质提升",
                "research_question": "如何在历史风貌保护前提下改善历史街区居住建筑的居住条件？",
                "keywords_required": ["历史街区居住建筑", "保护更新", "居住品质"],
                "keywords_suggested": ["旧城片区", "微改造", "风貌保护"],
            },
        )
        metadata = self.read_json("raw-library/metadata.json")
        metadata["sources"] = [
            {
                "source_id": "cnki_old",
                "title": "地域建筑符号在设计教育中的课程转化",
                "authenticity_verdict": "pass",
                "authenticity_status": "verified",
            },
            {
                "source_id": "cnki_001",
                "title": "历史街区居住建筑更新研究",
                "keywords": ["历史街区居住建筑", "保护更新", "居住品质"],
                "authenticity_verdict": "pass",
                "authenticity_status": "verified",
            },
        ]
        self.write_json("raw-library/metadata.json", metadata)
        citation_map = self.read_json("outputs/part5/citation_map.json")
        citation_map["source_refs"] = [
            {
                "source_id": "cnki_001",
                "claim_ids": ["claim_001"],
                "citation_status": "accepted_source",
            }
        ]
        self.write_json("outputs/part5/citation_map.json", citation_map)
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        final_text = self.read_text("outputs/part6/final_manuscript.md")
        self.assertIn("历史街区居住建筑更新", final_text)
        self.assertNotIn("设计教育", final_text)
        self.assertNotIn("课程导入", final_text)
        self.assertNotIn("教学实践", final_text)

    def test_part6_writer_has_workflow_skill_surface(self):
        skill_md = WRITER_SKILL_DIR / "SKILL.md"
        openai_yaml = WRITER_SKILL_DIR / "agents" / "openai.yaml"

        self.assertTrue(skill_md.exists())
        self.assertTrue(openai_yaml.exists())
        skill_text = skill_md.read_text(encoding="utf-8")
        openai_text = openai_yaml.read_text(encoding="utf-8")
        self.assertIn("name: part6-write-manuscript-body", skill_text)
        self.assertIn("outputs/part6/writer_body.md", skill_text)
        self.assertIn("不得写或修改", skill_text)
        self.assertIn("part6_writer.py", skill_text)
        self.assertNotIn("TODO", skill_text)
        self.assertIn("$part6-write-manuscript-body", openai_text)

    def test_finalize_preserves_non_scaffold_part5_revision_paragraphs(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_body_composition_inputs()
        self.write_text(
            "outputs/part5/manuscript_v2.md",
            (
                "# 论文修订稿 v2\n\n"
                "## 教学实践路径\n\n"
                "人工修订后的连续正文强调，地域建筑符号进入设计教育时，"
                "应先完成视觉元素、文化含义与课堂任务之间的转换，"
                "再通过创作训练形成可评价的学习成果。\n"
            ),
        )
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()

        self.finalizer.run_step(self.project_root, "finalize")

        final_text = self.read_text("outputs/part6/final_manuscript.md")
        self.assertIn("人工修订后的连续正文强调", final_text)
        self.assertIn("## 补充论证", final_text)
        self.assertNotIn("修订后论证整合", final_text)
        self.assertNotIn("Part 5 MVP", final_text)
        self.assertNotIn("本节核心论点", final_text)

    def test_keywords_and_empty_abstract_do_not_inject_stale_topic(self):
        manuscript = (
            "# 论文修订稿 v2\n\n"
            "## 关键词\n\n"
            "历史街区居住建筑；保护更新；旧城片区；居住品质提升\n\n"
            "## 正文\n\n"
            "本文围绕历史街区居住建筑更新与社区居住品质提升展开。\n"
        )

        keywords = self.finalizer.keywords_from_text(manuscript)
        empty_abstract = self.finalizer.abstract_from_manuscript("")

        self.assertIn("历史街区居住建筑", keywords)
        self.assertIn("保护更新", keywords)
        self.assertNotIn("空间结构", keywords)
        self.assertNotIn("设计方法", keywords)
        self.assertIn("保守收束", empty_abstract)

    def test_precheck_without_finalization_authorization_fails_without_writing_part6(self):
        self.write_state()
        self.write_valid_part5_handoff()

        with self.assertRaises(RuntimeError):
            self.finalizer.run_step(self.project_root, "precheck")

        part6_files = list((self.project_root / "outputs" / "part6").glob("*"))
        self.assertEqual([], part6_files)

    def test_audit_steps_do_not_modify_final_manuscript(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()
        self.finalizer.run_step(self.project_root, "finalize")
        before = self.read_text("outputs/part6/final_manuscript.md")

        self.finalizer.run_step(self.project_root, "audit-claim")
        self.finalizer.run_step(self.project_root, "audit-citation")

        after = self.read_text("outputs/part6/final_manuscript.md")
        self.assertEqual(before, after)

    def test_audit_steps_run_llm_auditor_sidecars_when_configured(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()
        self.finalizer.run_step(self.project_root, "finalize")
        fake_claim_agent = self.project_root / "fake_claimauditor.py"
        fake_claim_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'claimauditor'\n"
                "assert request['skill'] == 'part6-audit-claim-risk'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "assert 'outputs/part6/final_manuscript.md' in paths\n"
                "assert 'outputs/part6/claim_risk_report.json' in paths\n"
                "print(json.dumps({'report': 'claim auditor reviewed part6 claim risk'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        fake_citation_agent = self.project_root / "fake_citationauditor.py"
        fake_citation_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'citationauditor'\n"
                "assert request['skill'] == 'part6-audit-citation-consistency'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "assert 'outputs/part6/final_manuscript.md' in paths\n"
                "assert 'outputs/part6/citation_consistency_report.json' in paths\n"
                "print(json.dumps({'report': 'citation auditor reviewed part6 citations'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_CLAIMAUDITOR_COMMAND"] = f"{sys.executable} {fake_claim_agent}"
        os.environ["RTM_CLAIMAUDITOR_TIMEOUT"] = "5"
        os.environ["RTM_CITATIONAUDITOR_COMMAND"] = f"{sys.executable} {fake_citation_agent}"
        os.environ["RTM_CITATIONAUDITOR_TIMEOUT"] = "5"
        before = self.read_text("outputs/part6/final_manuscript.md")

        self.finalizer.run_step(self.project_root, "audit-claim")
        self.finalizer.run_step(self.project_root, "audit-citation")

        self.assertEqual(before, self.read_text("outputs/part6/final_manuscript.md"))
        claim_sidecar = self.read_json("outputs/part6/llm_agent_audits/claimauditor_claim_audit.json")
        self.assertEqual("claim auditor reviewed part6 claim risk", claim_sidecar["report"])
        claim_provenance = self.read_json("outputs/part6/claimauditor_provenance.json")
        self.assertEqual("claimauditor", claim_provenance["agent_name"])
        self.assertEqual("llm", claim_provenance["mode"])
        citation_sidecar = self.read_json("outputs/part6/llm_agent_audits/citationauditor_citation_audit.json")
        self.assertEqual("citation auditor reviewed part6 citations", citation_sidecar["report"])
        citation_provenance = self.read_json("outputs/part6/citationauditor_provenance.json")
        self.assertEqual("citationauditor", citation_provenance["agent_name"])
        self.assertEqual("llm", citation_provenance["mode"])

    def test_citation_audit_accepts_warning_authenticity_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff()
        metadata = self.read_json("raw-library/metadata.json")
        metadata["sources"][0]["authenticity_verdict"] = "warning"
        self.write_json("raw-library/metadata.json", metadata)
        report = self.read_json("outputs/part1/authenticity_report.json")
        report["results"][0]["verdict"] = "warning"
        report["passed"] = 1
        report["warnings"] = 1
        self.write_json("outputs/part1/authenticity_report.json", report)
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()
        self.finalizer.run_step(self.project_root, "finalize")

        self.finalizer.run_step(self.project_root, "audit-citation")
        citation_report = self.read_json("outputs/part6/citation_consistency_report.json")

        self.assertEqual("pass_with_warnings", citation_report["status"])
        self.assertEqual([], citation_report["errors"])
        self.assertEqual("verified", citation_report["citation_items"][0]["authenticity_status"])

    def test_audit_steps_fail_without_final_manuscript_and_do_not_write_reports(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()

        with self.assertRaises(FileNotFoundError):
            self.finalizer.run_step(self.project_root, "audit-claim")
        with self.assertRaises(FileNotFoundError):
            self.finalizer.run_step(self.project_root, "audit-citation")

        self.assertFalse((self.project_root / "outputs/part6/claim_risk_report.json").exists())
        self.assertFalse((self.project_root / "outputs/part6/citation_consistency_report.json").exists())

    def test_package_decide_final_manifest_closes_and_passes_after_final_confirm(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.write_json(
            "outputs/part1/intake.json",
            {"research_topic": "地域建筑符号空间结构研究"},
        )
        self.authorize_part6()
        self.allow_deterministic_writer_fallback()
        for step in [
            "finalize",
            "audit-claim",
            "audit-citation",
            "package-draft",
            "export-docx",
            "decide",
            "package-final",
        ]:
            self.finalizer.run_step(self.project_root, step)

        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        self.assertEqual(decision["verdict"], manifest["submission_class"])
        self.assertIn(decision["manifest_ref"], ["outputs/part6/submission_package_manifest.json"])
        self.assertEqual(sorted(manifest["included_files"]), sorted(manifest["required_files"]))

        passed, issues = self.pipeline.validate_gate("part6")
        self.assertFalse(passed)
        self.assertTrue(any("part6_final_decision_confirmed" in issue for issue in issues))

        self.pipeline.confirm_human_gate("part6_final_decision_confirmed", "确认最终状态")
        passed, issues = self.pipeline.validate_gate("part6")
        self.assertTrue(passed, issues)


if __name__ == "__main__":
    unittest.main()
