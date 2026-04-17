import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("pipeline_part5_test", PIPELINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part5PipelineTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = load_pipeline_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.pipeline.PROJECT_ROOT = self.project_root
        self.pipeline.STATE_FILE = self.project_root / "runtime" / "state.json"
        self.pipeline.PROCESS_MEMORY_DIR = self.project_root / "process-memory"
        self.pipeline.SCHEMA_MAP = {
            "outputs/part5/review_matrix.json": str(PROJECT_ROOT / "schemas" / "part5_review_matrix.schema.json"),
            "outputs/part5/revision_log.json": str(PROJECT_ROOT / "schemas" / "part5_revision_log.schema.json"),
            "outputs/part5/part6_readiness_decision.json": str(PROJECT_ROOT / "schemas" / "part5_readiness_decision.schema.json"),
        }

        for rel_dir in [
            "runtime",
            "raw-library",
            "research-wiki",
            "outputs/part5",
            "outputs/part5/chapter_briefs",
            "process-memory",
        ]:
            (self.project_root / rel_dir).mkdir(parents=True, exist_ok=True)

    def write_json(self, rel_path, data):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def write_text(self, rel_path, text):
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_json(self, rel_path):
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def write_state(self, *, part5_gates=None):
        def completed_stage(gates=None):
            return {
                "status": "completed",
                "started_at": "2026-04-16T00:00:00+00:00",
                "completed_at": "2026-04-16T00:10:00+00:00",
                "gate_passed": True,
                "human_gates_completed": gates or [],
            }

        self.write_json(
            "runtime/state.json",
            {
                "schema_version": "1.0.0",
                "pipeline_id": "research-to-manuscript-v1",
                "initialized_at": "2026-04-16T00:00:00+00:00",
                "current_stage": "part5",
                "stages": {
                    "part1": completed_stage(["intake_confirmed"]),
                    "part2": completed_stage(),
                    "part3": completed_stage(["argument_tree_selected"]),
                    "part4": completed_stage(),
                    "part5": {
                        "status": "in_progress",
                        "started_at": "2026-04-16T00:20:00+00:00",
                        "completed_at": None,
                        "gate_passed": False,
                        "human_gates_completed": part5_gates or [],
                    },
                },
                "last_failure": None,
                "repair_log": [],
                "human_decision_log": [],
            },
        )

    def write_valid_part5_artifacts(self, *, readiness_verdict="ready_for_part6_with_research_debt"):
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "sources": [
                    {
                        "source_id": "cnki_001",
                        "title": "地域建筑研究",
                        "authenticity_verdict": "pass",
                        "authenticity_status": "verified",
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
                        "page_id": "page_1",
                        "file_path": "research-wiki/pages/page_1.md",
                        "source_ids": ["cnki_001"],
                    }
                ],
                "source_mapping_complete": True,
            },
        )
        self.write_text(
            "outputs/part5/chapter_briefs/sec_1.md",
            "# 绪论\n\n- claim: thesis_001\n- evidence: cnki_001\n",
        )
        self.write_text(
            "outputs/part5/case_analysis_templates/case_001.md",
            "# 案例分析模板\n\n- 案例角色: 概念参照\n- 风险: 缺少图纸时保守表述\n",
        )
        self.write_json(
            "outputs/part5/claim_evidence_matrix.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "outline_ref": "outputs/part4/paper_outline.json",
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "claims": [
                    {
                        "claim_id": "thesis_001",
                        "claim": "地域建筑符号教学实践可作为当代设计方法的参照。",
                        "evidence_level": "hard_evidence",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["page_1"],
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
                        "title": "地域建筑研究",
                        "claim_ids": ["thesis_001"],
                        "citation_status": "accepted_source",
                    }
                ],
                "unmapped_sources": [],
            },
        )
        self.write_json(
            "outputs/part5/figure_plan.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "figures": [],
                "known_gaps": ["缺少图纸时不得写成硬建筑事实。"],
            },
        )
        self.write_json(
            "outputs/part5/claim_risk_report.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:35:00+00:00",
                "risk_items": [
                    {
                        "claim_id": "thesis_001",
                        "risk_level": "medium",
                        "reason": "案例图纸仍需补足。",
                        "mitigation": "正文中降级为概念参照。",
                    }
                ],
            },
        )
        self.write_json(
            "outputs/part5/citation_consistency_precheck.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:35:00+00:00",
                "status": "pass_with_warnings",
                "checked_claim_ids": ["thesis_001"],
                "warnings": ["案例图纸来源不足。"],
                "errors": [],
            },
        )
        self.write_json(
            "outputs/part5/open_questions.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "questions": [
                    {
                        "question_id": "q_001",
                        "type": "research_debt",
                        "description": "补足案例图纸或动线材料。",
                        "blocks_part6": False,
                    }
                ],
            },
        )
        self.write_text("outputs/part5/manuscript_v1.md", "# 论文初稿 v1\n\n## 绪论\n\n待扩写。\n")
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
                        "finding": "案例图纸证据仍不足。",
                        "claim_ids": ["thesis_001"],
                        "status": "registered",
                    }
                ],
            },
        )
        self.write_text("outputs/part5/review_summary.md", "# Review Summary\n\n证据债务已登记。\n")
        self.write_text(
            "outputs/part5/review_report.md",
            "# Part 5 Review Report\n\n证据债务已登记，修订前无需人工 gate。\n",
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
                        "action": "降低未核验案例断言强度",
                        "review_dimension": "evidence",
                        "status": "applied",
                    }
                ],
                "residual_risks": ["案例图纸仍需后续补足。"],
            },
        )
        self.write_text("outputs/part5/manuscript_v2.md", "# 论文修订稿 v2\n\n## 绪论\n\n保守表述。\n")
        self.write_json(
            "outputs/part5/part6_readiness_decision.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:55:00+00:00",
                "verdict": readiness_verdict,
                "registered_blockers": [],
                "residual_risks": ["案例图纸仍需后续补足。"],
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

    def confirm_part5_artifacts(self):
        self.pipeline.confirm_human_gate("part5_prep_confirmed", "确认 prep")
        self.pipeline.confirm_human_gate("part5_review_completed", "确认 review")
        self.pipeline.confirm_human_gate("manuscript_v2_accepted", "接受 v2")

    def test_part4_and_part5_no_longer_require_human_gates(self):
        self.assertIn("part5", self.pipeline.STAGE_ORDER)
        self.assertIn("part6", self.pipeline.STAGE_ORDER)
        self.assertLess(
            self.pipeline.STAGE_ORDER.index("part5"),
            self.pipeline.STAGE_ORDER.index("part6"),
        )
        self.assertEqual(self.pipeline.HUMAN_GATES["part4"], [])
        self.assertEqual(self.pipeline.HUMAN_GATES["part5"], [])

    def test_part5_gate_blocks_without_artifacts_but_not_human_decisions(self):
        self.write_state(part5_gates=[])

        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertFalse(any("writing_phase_authorized" in issue for issue in issues))
        self.assertFalse(any("part5_prep_confirmed" in issue for issue in issues))
        self.assertFalse(any("part5_review_completed" in issue for issue in issues))
        self.assertFalse(any("manuscript_v2_accepted" in issue for issue in issues))
        self.assertTrue(any("outputs/part5/manuscript_v2.md" in issue for issue in issues))

    def test_part5_gate_passes_with_minimal_mvp_artifacts_without_human_decisions(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()

        passed, issues = self.pipeline.validate_gate("part5")

        self.assertTrue(passed, issues)

    def test_part5_gate_requires_project_local_review_report(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        (self.project_root / "outputs/part5/review_report.md").unlink()

        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("outputs/part5/review_report.md" in issue for issue in issues))

    def test_part5_gate_requires_project_local_final_manuscript(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        (self.project_root / "outputs/part5/manuscript_v2.md").unlink()

        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("outputs/part5/manuscript_v2.md" in issue for issue in issues))

    def test_part5_gate_rejects_ready_verdict_when_critical_review_is_unresolved(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts(readiness_verdict="ready_for_part6")
        self.write_json(
            "outputs/part5/review_matrix.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:40:00+00:00",
                "manuscript_ref": "outputs/part5/manuscript_v1.md",
                "reviews": [
                    {
                        "review_id": "review_critical",
                        "dimension": "citation",
                        "severity": "critical",
                        "finding": "关键引文无法回溯。",
                        "claim_ids": ["thesis_001"],
                        "status": "unresolved",
                    }
                ],
            },
        )
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("critical blocker" in issue for issue in issues))

    def test_deprecated_part5_confirmation_commands_are_noops(self):
        self.write_state(part5_gates=[])

        self.pipeline.confirm_human_gate("writing_phase_authorized", "")
        self.pipeline.confirm_human_gate("part5_prep_confirmed", "")
        self.pipeline.confirm_human_gate("part5_review_completed", "")
        self.pipeline.confirm_human_gate("manuscript_v2_accepted", "")

        state = self.read_json("runtime/state.json")
        self.assertEqual(state["stages"]["part5"]["human_gates_completed"], [])
        self.assertEqual(
            [item["status"] for item in state["human_decision_log"]],
            ["deprecated_noop"] * 4,
        )

    def test_part5_gate_rejects_forged_source_id_even_when_marked_accepted(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        matrix = self.read_json("outputs/part5/claim_evidence_matrix.json")
        matrix["claims"][0]["source_ids"] = ["fake_001"]
        self.write_json("outputs/part5/claim_evidence_matrix.json", matrix)
        citation_map = self.read_json("outputs/part5/citation_map.json")
        citation_map["source_refs"][0]["source_id"] = "fake_001"
        citation_map["source_refs"][0]["citation_status"] = "accepted_source"
        self.write_json("outputs/part5/citation_map.json", citation_map)
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("不存在的 source_id" in issue for issue in issues))

    def test_part5_gate_rejects_source_missing_from_wiki_mapping(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        wiki = self.read_json("research-wiki/index.json")
        wiki["pages"] = [{"page_id": "page_1", "file_path": "research-wiki/pages/page_1.md", "source_ids": []}]
        self.write_json("research-wiki/index.json", wiki)
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("source_id 未出现在 research-wiki 映射中" in issue for issue in issues))

    def test_part5_gate_rejects_blocked_citation_precheck(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        precheck = self.read_json("outputs/part5/citation_consistency_precheck.json")
        precheck["status"] = "blocked"
        precheck["errors"] = ["fake_001 citation_status=missing_metadata"]
        self.write_json("outputs/part5/citation_consistency_precheck.json", precheck)
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("citation_consistency_precheck.status 为 blocked" in issue for issue in issues))

    def test_ready_for_part6_rejects_residual_risks(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts(readiness_verdict="ready_for_part6")
        readiness = self.read_json("outputs/part5/part6_readiness_decision.json")
        readiness["residual_risks"] = ["仍缺少案例图纸"]
        self.write_json("outputs/part5/part6_readiness_decision.json", readiness)
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("ready_for_part6 不得携带 residual_risks" in issue for issue in issues))

    def test_revision_log_must_cover_every_review_id(self):
        self.write_state(part5_gates=[])
        self.write_valid_part5_artifacts()
        review_matrix = self.read_json("outputs/part5/review_matrix.json")
        review_matrix["reviews"].append(
            {
                "review_id": "review_002",
                "dimension": "argument",
                "severity": "medium",
                "finding": "第二个 review 未被 revision_log 覆盖。",
                "claim_ids": ["thesis_001"],
                "status": "registered",
            }
        )
        self.write_json("outputs/part5/review_matrix.json", review_matrix)
        passed, issues = self.pipeline.validate_gate("part5")

        self.assertFalse(passed)
        self.assertTrue(any("revision_log 未覆盖 review_matrix 项" in issue for issue in issues))

    def test_validate_part5_ignores_stale_legacy_human_gate_fingerprints(self):
        self.write_state(part5_gates=[
            "writing_phase_authorized",
            "part5_prep_confirmed",
            "part5_review_completed",
            "manuscript_v2_accepted",
        ])
        self.write_valid_part5_artifacts()
        self.write_text("outputs/part5/manuscript_v2.md", "# 被覆盖的 v2\n")

        passed, issues = self.pipeline.validate_gate("part5")

        self.assertTrue(passed, issues)

    def test_next_action_does_not_prompt_removed_part4_or_part5_confirm_commands(self):
        state = {
            "stages": {
                stage_id: {
                    "status": "in_progress",
                    "gate_passed": False,
                    "human_gates_completed": [],
                    "started_at": None,
                    "completed_at": None,
                }
                for stage_id in self.pipeline.STAGE_ORDER
            }
        }

        issue_sets = {
            "part4": (False, ["人工节点未确认: outline_confirmed"]),
            "part5": (
                False,
                [
                    "人工节点未确认: writing_phase_authorized",
                    "人工节点未确认: part5_prep_confirmed",
                    "人工节点未确认: part5_review_completed",
                    "人工节点未确认: manuscript_v2_accepted",
                    "缺少 canonical artifact: outputs/part5/manuscript_v2.md",
                ],
            ),
        }

        def fake_validate(stage_id, state=None):
            return issue_sets.get(stage_id, (True, []))

        for earlier_stage in ["part1", "part2", "part3"]:
            state["stages"][earlier_stage]["status"] = "completed"
            state["stages"][earlier_stage]["gate_passed"] = True
        with patch.object(self.pipeline, "validate_gate", side_effect=fake_validate):
            part4_action = self.pipeline.get_next_action(state)
        self.assertNotIn("part4-confirm", part4_action["command"])

        state["stages"]["part4"]["status"] = "completed"
        state["stages"]["part4"]["gate_passed"] = True
        with patch.object(self.pipeline, "validate_gate", side_effect=fake_validate):
            part5_action = self.pipeline.get_next_action(state)
        for removed_command in [
            "part5-authorize",
            "part5-confirm-prep",
            "part5-confirm-review",
            "part5-accept",
        ]:
            self.assertNotIn(removed_command, part5_action["command"])


if __name__ == "__main__":
    unittest.main()
