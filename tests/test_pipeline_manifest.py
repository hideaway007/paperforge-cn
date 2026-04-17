import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_MANIFEST = PROJECT_ROOT / "manifests" / "pipeline-stages.json"


class PipelineManifestContractTests(unittest.TestCase):
    def load_manifest(self):
        with open(PIPELINE_MANIFEST, encoding="utf-8") as f:
            return json.load(f)

    def test_part6_is_active_stage_after_part5_not_deferred(self):
        manifest = self.load_manifest()
        stage_ids = [stage["id"] for stage in manifest["stages"]]

        self.assertIn("part6", stage_ids)
        self.assertEqual(stage_ids.index("part6"), stage_ids.index("part5") + 1)
        self.assertEqual(manifest["deferred_stages"], [])

    def test_part6_manifest_contract_matches_mvp_foundation(self):
        manifest = self.load_manifest()
        part6 = next(stage for stage in manifest["stages"] if stage["id"] == "part6")

        self.assertIn("runtime agent", part6["description"])
        self.assertIn("skill", part6["description"])
        self.assertIn("不声明", part6["description"])
        self.assertEqual(
            part6["implementation_boundary"],
            {
                "runtime_agent_declared": True,
                "skill_declared": True,
                "finalize_action_declared": True,
                "submission_action_declared": False,
            },
        )
        self.assertEqual(
            part6["automation_flow"],
            [
                "part6_finalize",
                "part6_audit_claim",
                "part6_audit_citation",
                "part6_package_draft",
                "part6_decide",
                "part6_package_final",
            ],
        )
        self.assertEqual(
            part6["canonical_artifacts"],
            [
                "outputs/part6/final_manuscript.md",
                "outputs/part6/claim_risk_report.json",
                "outputs/part6/citation_consistency_report.json",
                "outputs/part6/submission_package_manifest.json",
                "outputs/part6/final_readiness_decision.json",
            ],
        )
        self.assertEqual(
            [gate["id"] for gate in part6["human_gates"]],
            ["part6_finalization_authorized", "part6_final_decision_confirmed"],
        )
        required_checks = " ".join(part6["completion_gate"]["required_checks"])
        self.assertIn("Part 1-5 gates completed", required_checks)
        self.assertIn("Part 5 readiness verdict is not blocked", required_checks)
        self.assertIn("handoff fingerprint has not drifted", required_checks)
        self.assertIn("allowlist pass", required_checks)
        self.assertIn("manifest and final readiness verdict are consistent", required_checks)
        self.assertIn("final decision human confirmation", required_checks)
        self.assertIn("no submission action", required_checks)


if __name__ == "__main__":
    unittest.main()
