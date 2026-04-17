import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_part6_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part6PipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)

        self.pipeline.PROJECT_ROOT = self.project_root
        self.pipeline.STATE_FILE = self.project_root / "runtime" / "state.json"
        self.pipeline.PROCESS_MEMORY_DIR = self.project_root / "process-memory"
        self.pipeline.SCHEMA_MAP = {
            "outputs/part6/claim_risk_report.json": "schemas/part6_claim_risk_report.schema.json",
            "outputs/part6/citation_consistency_report.json": "schemas/part6_citation_consistency_report.schema.json",
            "outputs/part6/submission_package_manifest.json": "schemas/part6_submission_package_manifest.schema.json",
            "outputs/part6/final_readiness_decision.json": "schemas/part6_final_readiness_decision.schema.json",
        }

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

    def copy_part6_schemas(self):
        for rel_path in self.pipeline.SCHEMA_MAP.values():
            source = PROJECT_ROOT / rel_path
            target = self.project_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def completed_stage(self, gates=None):
        return {
            "status": "completed",
            "started_at": "2026-04-16T00:00:00+00:00",
            "completed_at": "2026-04-16T00:10:00+00:00",
            "gate_passed": True,
            "human_gates_completed": gates or [],
        }

    def write_state(self, *, part5_completed=True, part6_gates=None):
        part5_state = self.completed_stage()
        if not part5_completed:
            part5_state = {
                "status": "in_progress",
                "started_at": "2026-04-16T00:20:00+00:00",
                "completed_at": None,
                "gate_passed": False,
                "human_gates_completed": [],
            }

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
                    "part5": part5_state,
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
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:40:00+00:00",
                "risk_items": [],
            },
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
        self.write_text("outputs/part5/manuscript_v2.md", "# 论文修订稿 v2\n\n## 绪论\n\n保守表述。\n")
        self.write_json(
            "outputs/part5/part6_readiness_decision.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:55:00+00:00",
                "verdict": readiness_verdict,
                "registered_blockers": (
                    [{"dimension": "evidence", "finding": "关键证据债务阻断。"}]
                    if readiness_verdict == "blocked_by_evidence_debt"
                    else []
                ),
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

    def write_valid_part6_package(self):
        self.write_text(
            "outputs/part6/final_manuscript.md",
            (
                "# 最终稿\n\n"
                "## 摘要\n\n"
                "本文以地域建筑符号空间结构为研究对象，形成保守的设计方法归纳。\n\n"
                "## 关键词\n\n"
                "地域建筑符号；空间结构\n\n"
                "## 绪论\n\n"
                "正文讨论地域建筑符号空间结构与当代设计方法之间的关系。\n\n"
                "## 结论\n\n"
                "结论认为相关方法只能作为保守参照，后续研究可继续扩展材料范围。\n"
            ),
        )
        self.write_text(
            "outputs/part6/final_abstract.md",
            "本文以地域建筑符号空间结构为研究对象，形成保守的设计方法归纳。\n",
        )
        self.write_json(
            "outputs/part6/final_keywords.json",
            {"keywords": ["地域建筑符号", "空间结构"]},
        )
        desktop_docx = self.project_root / "Desktop" / "地域建筑符号空间结构研究.docx"
        desktop_docx.parent.mkdir(parents=True, exist_ok=True)
        desktop_docx.write_text("docx placeholder", encoding="utf-8")
        self.write_text("outputs/part6/final_manuscript.docx", "docx placeholder")
        self.write_json(
            "outputs/part6/docx_format_report.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T01:09:00+00:00",
                "status": "pass",
                "source_manuscript_ref": "outputs/part6/final_manuscript.md",
                "docx_ref": "outputs/part6/final_manuscript.docx",
                "desktop_docx_ref": str(desktop_docx),
                "format_policy_ref": "writing-policy/rules/scut_course_paper_format.md",
                "cover_excluded": True,
                "paper_title": "地域建筑符号空间结构研究",
                "style_checks": [],
                "content_checks": [],
                "warnings": [],
                "errors": [],
            },
        )
        self.write_text(
            "outputs/part6/submission_checklist.md",
            (
                "# Submission Checklist\n\n"
                "- [ ] 人工确认最终状态。\n"
                "- [x] 风险与残余研究债务保留在 claim_risk_report / final_readiness_decision。\n"
            ),
        )
        self.write_json(
            "outputs/part6/claim_risk_report.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T01:10:00+00:00",
                "manuscript_ref": "outputs/part6/final_manuscript.md",
                "source_manuscript_ref": "outputs/part5/manuscript_v2.md",
                "claim_evidence_matrix_ref": "outputs/part5/claim_evidence_matrix.json",
                "part5_claim_risk_report_ref": "outputs/part5/claim_risk_report.json",
                "risk_items": [
                    {
                        "risk_id": "risk_001",
                        "claim_id": "claim_001",
                        "risk_level": "medium_risk",
                        "risk_type": "source_sufficiency",
                        "finding": "仍有研究债务。",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["wiki_001"],
                        "recommended_action": "defer_to_future_research",
                        "applied_action": "defer_to_future_research",
                        "status": "deferred",
                        "residual_debt": "仍有研究债务。",
                    }
                ],
                "summary": {"status": "pass_with_debt", "residual_risks": ["仍有研究债务。"]},
            },
        )
        self.write_json(
            "outputs/part6/citation_consistency_report.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T01:10:00+00:00",
                "manuscript_ref": "outputs/part6/final_manuscript.md",
                "citation_map_ref": "outputs/part5/citation_map.json",
                "raw_metadata_ref": "raw-library/metadata.json",
                "wiki_index_ref": "research-wiki/index.json",
                "accepted_sources_ref": "outputs/part1/accepted_sources.json",
                "authenticity_report_ref": "outputs/part1/authenticity_report.json",
                "status": "pass",
                "checked_claim_ids": ["claim_001"],
                "checked_source_ids": ["cnki_001"],
                "citation_items": [
                    {
                        "source_id": "cnki_001",
                        "claim_ids": ["claim_001"],
                        "citation_status": "accepted_source",
                        "raw_metadata_present": True,
                        "wiki_mapped": True,
                        "authenticity_status": "verified",
                        "reference_entry_status": "present",
                        "drift_detected": False,
                        "issues": [],
                        "action": "keep",
                    }
                ],
                "warnings": [],
                "errors": [],
            },
        )
        self.write_json(
            "outputs/part6/final_readiness_decision.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T01:15:00+00:00",
                "verdict": "internal_review_only",
                "manifest_ref": "outputs/part6/submission_package_manifest.json",
                "claim_risk_report_ref": "outputs/part6/claim_risk_report.json",
                "citation_consistency_report_ref": "outputs/part6/citation_consistency_report.json",
                "blocking_issues": [],
                "residual_risks": ["仍有研究债务。", "仍需人工最终判断。"],
                "residual_research_debts": ["仍有研究债务。"],
                "required_human_decisions": ["part6_final_decision_confirmed"],
                "does_not_advance_part7": True,
            },
        )
        self.write_json(
            "outputs/part6/submission_package_manifest.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T01:20:00+00:00",
                "package_id": "part6_package_001",
                "status": "complete",
                "submission_class": "internal_review_only",
                "included_files": [
                    "outputs/part6/final_manuscript.md",
                    "outputs/part6/final_abstract.md",
                    "outputs/part6/final_keywords.json",
                    "outputs/part6/submission_checklist.md",
                    "outputs/part6/final_manuscript.docx",
                    "outputs/part6/docx_format_report.json",
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json",
                    "outputs/part6/final_readiness_decision.json",
                ],
                "required_files": [
                    "outputs/part6/final_manuscript.md",
                    "outputs/part6/final_abstract.md",
                    "outputs/part6/final_keywords.json",
                    "outputs/part6/submission_checklist.md",
                    "outputs/part6/final_manuscript.docx",
                    "outputs/part6/docx_format_report.json",
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json",
                    "outputs/part6/final_readiness_decision.json",
                ],
                "missing_files": [],
                "audit_refs": [
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json",
                ],
                "policy_refs": ["writing-policy/rules/scut_course_paper_format.md"],
                "evidence_refs": [],
                "human_decision_required": True,
            },
        )

    def add_source_traceability(
        self,
        source_id,
        *,
        citation_map=True,
        raw_metadata=True,
        wiki_mapping=True,
        accepted_sources=True,
        authenticity_verdict="pass",
    ):
        if raw_metadata:
            metadata = self.read_json("raw-library/metadata.json")
            metadata["sources"] = [
                source for source in metadata["sources"]
                if source.get("source_id") != source_id
            ]
            metadata["sources"].append(
                {
                    "source_id": source_id,
                    "title": f"{source_id} 测试来源",
                    "authenticity_verdict": authenticity_verdict or "pass",
                    "authenticity_status": "verified",
                }
            )
            self.write_json("raw-library/metadata.json", metadata)

        if wiki_mapping:
            wiki = self.read_json("research-wiki/index.json")
            wiki["pages"].append(
                {
                    "page_id": f"wiki_{source_id}",
                    "file_path": f"research-wiki/pages/{source_id}.md",
                    "source_ids": [source_id],
                }
            )
            self.write_json("research-wiki/index.json", wiki)

        if citation_map:
            citation = self.read_json("outputs/part5/citation_map.json")
            citation["source_refs"] = [
                ref for ref in citation["source_refs"]
                if ref.get("source_id") != source_id
            ]
            citation["source_refs"].append(
                {
                    "source_id": source_id,
                    "claim_ids": ["claim_001"],
                    "citation_status": "accepted_source",
                }
            )
            self.write_json("outputs/part5/citation_map.json", citation)

        if accepted_sources:
            accepted = self.read_json("outputs/part1/accepted_sources.json")
            source_ids = [
                item for item in accepted.get("source_ids", [])
                if item != source_id
            ]
            source_ids.append(source_id)
            accepted["source_ids"] = source_ids
            accepted["total"] = len(source_ids)
            self.write_json("outputs/part1/accepted_sources.json", accepted)

        if authenticity_verdict is not None:
            report = self.read_json("outputs/part1/authenticity_report.json")
            report["results"] = [
                item for item in report["results"]
                if item.get("source_id") != source_id
            ]
            report["results"].append(
                {
                    "source_id": source_id,
                    "title": f"{source_id} 测试来源",
                    "checks": [],
                    "flags": [],
                    "verdict": authenticity_verdict,
                    "notes": "测试",
                }
            )
            report["total_checked"] = len(report["results"])
            report["passed"] = len([
                item for item in report["results"]
                if item.get("verdict") == "pass"
            ])
            report["failed"] = len([
                item for item in report["results"]
                if item.get("verdict") == "fail"
            ])
            report["warnings"] = len([
                item for item in report["results"]
                if item.get("verdict") == "warning"
            ])
            report["pass_rate"] = round(report["passed"] / report["total_checked"] * 100, 1)
            self.write_json("outputs/part1/authenticity_report.json", report)

    def set_part6_citation_source(self, source_id):
        report = self.read_json("outputs/part6/citation_consistency_report.json")
        report["status"] = "pass"
        report["errors"] = []
        report["checked_source_ids"] = [source_id]
        report["citation_items"][0]["source_id"] = source_id
        report["citation_items"][0]["citation_status"] = "accepted_source"
        report["citation_items"][0]["raw_metadata_present"] = True
        report["citation_items"][0]["wiki_mapped"] = True
        report["citation_items"][0]["authenticity_status"] = "verified"
        report["citation_items"][0]["issues"] = []
        report["citation_items"][0]["action"] = "keep"
        self.write_json("outputs/part6/citation_consistency_report.json", report)

    def authorize_part6(self):
        self.pipeline.confirm_human_gate("part6_finalization_authorized", "授权 Part 6")

    def confirm_final_decision(self):
        self.pipeline.confirm_human_gate("part6_final_decision_confirmed", "确认最终状态")

    def test_part6_does_not_pass_when_part5_is_not_completed(self):
        self.write_state(part5_completed=False)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("part5" in issue and "gate" in issue for issue in issues))

    def test_blocked_by_evidence_debt_blocks_part6(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="blocked_by_evidence_debt")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("blocked_by_evidence_debt" in issue for issue in issues))
        with self.assertRaises(RuntimeError):
            self.authorize_part6()

    def test_missing_part6_finalization_authorization_blocks_part6(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.write_valid_part6_package()

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("part6_finalization_authorized" in issue for issue in issues))

    def test_part6_missing_artifacts_are_not_reported_twice(self):
        self.write_state()
        self.write_valid_part5_handoff()

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        final_manuscript_issues = [
            issue for issue in issues
            if "outputs/part6/final_manuscript.md" in issue
        ]
        self.assertEqual(
            ["缺少 artifact: outputs/part6/final_manuscript.md"],
            final_manuscript_issues,
        )

    def test_authorization_is_invalidated_when_handoff_changes(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.write_text("outputs/part5/manuscript_v2.md", "# 论文修订稿 v2\n\n授权后被修改。\n")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("handoff artifact 已变化" in issue for issue in issues))

    def test_complete_part6_package_and_final_decision_passes(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertTrue(passed, issues)

    def test_final_manuscript_missing_abstract_keywords_or_conclusion_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.write_text(
            "outputs/part6/final_manuscript.md",
            "# 最终稿\n\n## 绪论\n\n正文存在，但没有必要的最终稿结构。\n",
        )

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("摘要" in issue for issue in issues))
        self.assertTrue(any("关键词" in issue for issue in issues))
        self.assertTrue(any("结论" in issue for issue in issues))

    def test_final_manuscript_with_scaffold_markers_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.write_text(
            "outputs/part6/final_manuscript.md",
            (
                "# 最终稿\n\n"
                "## 摘要\n\n"
                "本文以地域建筑符号空间结构为研究对象，形成保守的设计方法归纳。\n\n"
                "## 关键词\n\n"
                "地域建筑符号；空间结构\n\n"
                "## 正文\n\n"
                "## 绪论\n\n"
                "本节核心论点：\n"
                "- 地域建筑符号空间可作为设计方法参照。（证据：cnki_001；风险：low）\n\n"
                "并按 low 风险等级控制结论强度。\n\n"
                "写作提示：本节应避免新增未登记引用。\n\n"
                "## 结论\n\n"
                "结论认为相关方法只能作为保守参照，后续研究可继续扩展材料范围。\n"
            ),
        )

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("scaffold" in issue or "骨架" in issue for issue in issues))

    def test_part5_residual_risks_must_be_carried_into_part6_reports(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        claim_risk = self.read_json("outputs/part6/claim_risk_report.json")
        claim_risk["risk_items"] = []
        claim_risk["summary"] = {"status": "pass"}
        self.write_json("outputs/part6/claim_risk_report.json", claim_risk)
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["residual_risks"] = ["仍需人工最终判断。"]
        decision["residual_research_debts"] = []
        self.write_json("outputs/part6/final_readiness_decision.json", decision)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("Part 5 residual_risks" in issue for issue in issues))

    def test_citation_blocked_prevents_formal_submission_ready_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        citation = self.read_json("outputs/part6/citation_consistency_report.json")
        citation["status"] = "blocked"
        citation["errors"] = ["引用漂移。"]
        self.write_json("outputs/part6/citation_consistency_report.json", citation)
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["verdict"] = "formal_submission_ready"
        decision["residual_risks"] = []
        decision["residual_research_debts"] = []
        self.write_json("outputs/part6/final_readiness_decision.json", decision)
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["submission_class"] = "formal_submission_ready"
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("citation_consistency_report" in issue for issue in issues))

    def test_citation_blocked_requires_blocked_by_evidence_debt_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        citation = self.read_json("outputs/part6/citation_consistency_report.json")
        citation["status"] = "blocked"
        citation["errors"] = ["引用漂移。"]
        self.write_json("outputs/part6/citation_consistency_report.json", citation)
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["verdict"] = "internal_review_only"
        self.write_json("outputs/part6/final_readiness_decision.json", decision)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("blocked_by_evidence_debt" in issue for issue in issues))

    def test_part6_citation_source_missing_from_part5_citation_map_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.add_source_traceability("cnki_missing_map", citation_map=False)
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.set_part6_citation_source("cnki_missing_map")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("citation_map.json" in issue and "cnki_missing_map" in issue for issue in issues))

    def test_part6_citation_source_missing_from_raw_metadata_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.add_source_traceability("cnki_missing_raw", raw_metadata=False)
        self.set_part6_citation_source("cnki_missing_raw")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("raw-library/metadata.json" in issue and "cnki_missing_raw" in issue for issue in issues))

    def test_part6_citation_source_missing_from_wiki_mapping_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.add_source_traceability("cnki_missing_wiki", wiki_mapping=False)
        self.set_part6_citation_source("cnki_missing_wiki")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("research-wiki/index.json.pages[].source_ids" in issue and "cnki_missing_wiki" in issue for issue in issues))

    def test_part6_citation_source_missing_from_part1_accepted_sources_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.add_source_traceability("cnki_missing_accepted", accepted_sources=False)
        self.set_part6_citation_source("cnki_missing_accepted")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("accepted_sources.json.source_ids" in issue and "cnki_missing_accepted" in issue for issue in issues))

    def test_part6_citation_source_with_non_pass_authenticity_report_fails(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        report = self.read_json("outputs/part1/authenticity_report.json")
        report["results"][0]["verdict"] = "fail"
        report["passed"] = 0
        report["failed"] = 1
        report["pass_rate"] = 0.0
        self.write_json("outputs/part1/authenticity_report.json", report)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("authenticity_report.json" in issue and "verdict 非 pass/warning" in issue for issue in issues))

    def test_part6_citation_source_with_warning_authenticity_report_passes_traceability(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.add_source_traceability("cnki_warning", authenticity_verdict="warning")
        self.authorize_part6()
        self.write_valid_part6_package()
        self.set_part6_citation_source("cnki_warning")
        self.confirm_final_decision()

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertTrue(passed, issues)

    def test_part6_citation_source_must_not_be_writing_policy_ref(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        self.set_part6_citation_source("writing-policy/source_index.json")

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("writing-policy" in issue and "citation source_id" in issue for issue in issues))

    def test_incomplete_manifest_prevents_formal_submission_ready_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["verdict"] = "formal_submission_ready"
        decision["residual_risks"] = []
        decision["residual_research_debts"] = []
        self.write_json("outputs/part6/final_readiness_decision.json", decision)
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["status"] = "incomplete"
        manifest["submission_class"] = "formal_submission_ready"
        manifest["missing_files"] = ["outputs/part6/final_abstract.md"]
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("submission_package_manifest" in issue for issue in issues))

    def test_incomplete_manifest_blocks_completion_even_with_blocked_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.authorize_part6()
        self.write_valid_part6_package()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["verdict"] = "blocked_by_evidence_debt"
        decision["blocking_issues"] = ["submission package 不完整。"]
        self.write_json("outputs/part6/final_readiness_decision.json", decision)
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["status"] = "incomplete"
        manifest["submission_class"] = "blocked_by_evidence_debt"
        manifest["missing_files"] = ["outputs/part6/final_abstract.md"]
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        with self.assertRaises(RuntimeError):
            self.confirm_final_decision()

        state = self.read_json("runtime/state.json")
        state["stages"]["part6"]["human_gates_completed"].append("part6_final_decision_confirmed")
        state["human_decision_log"].append(
            {
                "gate_id": "part6_final_decision_confirmed",
                "stage_id": "part6",
                "confirmed_at": "2026-04-16T01:30:00+00:00",
                "notes": "伪造最终确认",
            }
        )
        self.write_json("runtime/state.json", state)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("submission_package_manifest" in issue for issue in issues))

    def test_manifest_submission_class_must_match_final_verdict(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["submission_class"] = "formal_submission_ready"
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("submission_class" in issue and "verdict" in issue for issue in issues))

    def test_final_decision_confirmation_is_invalidated_when_decision_changes(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["residual_risks"].append("确认后新增风险。")
        self.write_json("outputs/part6/final_readiness_decision.json", decision)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("part6_final_decision_confirmed" in issue and "artifact 已变化" in issue for issue in issues))

    def test_final_decision_confirmation_is_invalidated_when_manifest_changes(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["included_files"].append("outputs/part6/references_final.bib")
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("part6_final_decision_confirmed" in issue and "artifact 已变化" in issue for issue in issues))

    def test_human_decision_required_must_remain_true(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["human_decision_required"] = False
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("human_decision_required" in issue for issue in issues))

    def test_final_decision_confirmation_refreshes_pending_artifacts(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["residual_risks"].append("仍需用户确认 part6_final_decision_confirmed。")
        self.write_json("outputs/part6/final_readiness_decision.json", decision)
        self.write_text(
            "outputs/part6/submission_checklist.md",
            "# Submission Checklist\n\n"
            "- [ ] part6_final_decision_confirmed 仍需用户最终确认。\n"
            "- [ ] 人工确认最终状态。\n",
        )

        self.confirm_final_decision()

        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        self.assertNotIn(
            "仍需用户确认 part6_final_decision_confirmed。",
            decision["residual_risks"],
        )
        self.assertEqual("confirmed", decision.get("final_decision_status"))
        self.assertEqual(
            "part6_final_decision_confirmed",
            decision.get("final_decision_gate_id"),
        )
        checklist = (
            self.project_root / "outputs/part6/submission_checklist.md"
        ).read_text(encoding="utf-8")
        self.assertIn("- [x] part6_final_decision_confirmed 已由用户确认。", checklist)
        self.assertIn("- [x] 人工确认最终状态。", checklist)

        passed, issues = self.pipeline.validate_gate("part6")
        self.assertTrue(passed, issues)

    def test_final_readiness_must_require_final_human_decision(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["required_human_decisions"] = []
        self.write_json("outputs/part6/final_readiness_decision.json", decision)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("required_human_decisions" in issue for issue in issues))

    def test_unresolved_blocked_claim_risk_forces_blocked_by_evidence_debt(self):
        self.write_state()
        self.write_valid_part5_handoff(readiness_verdict="ready_for_part6")
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        claim_risk = self.read_json("outputs/part6/claim_risk_report.json")
        claim_risk["risk_items"] = [
            {
                "risk_id": "risk_blocked",
                "claim_id": "claim_001",
                "risk_level": "blocked",
                "risk_type": "source_sufficiency",
                "finding": "核心证据不足。",
                "source_ids": ["cnki_001"],
                "wiki_page_ids": ["wiki_001"],
                "recommended_action": "add_source",
                "applied_action": "defer_to_future_research",
                "status": "blocked",
                "residual_debt": "核心证据不足。",
            }
        ]
        self.write_json("outputs/part6/claim_risk_report.json", claim_risk)
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["verdict"] = "formal_submission_ready"
        decision["residual_risks"] = []
        decision["residual_research_debts"] = []
        self.write_json("outputs/part6/final_readiness_decision.json", decision)
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["submission_class"] = "formal_submission_ready"
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("blocked_by_evidence_debt" in issue for issue in issues))

    def test_get_next_action_recommends_part6_authorize_for_unauthorized_part6_state(self):
        state = {
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
                    "human_gates_completed": [],
                },
            }
        }

        action = self.pipeline.get_next_action(state)

        self.assertEqual("part6", action["stage_id"])
        self.assertIn("part6-authorize", action["command"])
        self.assertNotIn("confirm-gate", action["command"])
        self.assertNotIn("part6-confirm-final", action["command"])
        self.assertNotIn("validate part6", action["command"])
        self.assertIn("用户显式授权", action["reason"])

    def test_get_next_action_recommends_part6_authorize_when_state_has_no_part6_key(self):
        state = {
            "stages": {
                "part1": self.completed_stage(["intake_confirmed"]),
                "part2": self.completed_stage(),
                "part3": self.completed_stage(["argument_tree_selected"]),
                "part4": self.completed_stage(),
                "part5": self.completed_stage(),
            }
        }

        action = self.pipeline.get_next_action(state)

        self.assertEqual("part6", action["stage_id"])
        self.assertIn("part6-authorize", action["command"])
        self.assertNotIn("confirm-gate", action["command"])
        self.assertNotIn("validate part6", action["command"])
        self.assertIn("用户显式授权", action["reason"])

    def test_get_next_action_recommends_part6_finalize_after_authorization_with_incomplete_package(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()

        action = self.pipeline.get_next_action()

        self.assertEqual("part6", action["stage_id"])
        self.assertIn("part6-finalize", action["command"])
        self.assertIn("--step all", action["command"])
        self.assertNotIn("part6-authorize", action["command"])
        self.assertNotIn("part6-confirm-final", action["command"])
        self.assertNotIn("validate part6", action["command"])

    def test_get_next_action_recommends_part6_confirm_final_when_package_is_ready(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()

        action = self.pipeline.get_next_action()

        self.assertEqual("part6", action["stage_id"])
        self.assertIn("part6-confirm-final", action["command"])
        self.assertNotIn("part6-authorize", action["command"])
        self.assertNotIn("validate part6", action["command"])
        self.assertIn("最终决策", action["reason"])

    def test_manifest_decision_references_must_close(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        manifest = self.read_json("outputs/part6/submission_package_manifest.json")
        manifest["included_files"] = [
            item for item in manifest["included_files"]
            if item != "outputs/part6/final_readiness_decision.json"
        ]
        self.write_json("outputs/part6/submission_package_manifest.json", manifest)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("included_files" in issue for issue in issues))

    def test_does_not_advance_part7_must_be_true(self):
        self.write_state()
        self.write_valid_part5_handoff()
        self.authorize_part6()
        self.write_valid_part6_package()
        self.confirm_final_decision()
        decision = self.read_json("outputs/part6/final_readiness_decision.json")
        decision["does_not_advance_part7"] = False
        self.write_json("outputs/part6/final_readiness_decision.json", decision)

        passed, issues = self.pipeline.validate_gate("part6")

        self.assertFalse(passed)
        self.assertTrue(any("does_not_advance_part7" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
