import copy
import json
import unittest
from pathlib import Path

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "schemas"


def load_schema(name):
    with open(SCHEMA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class Part6SchemaContractTests(unittest.TestCase):
    def setUp(self):
        self.schemas = {
            "claim_risk": load_schema("part6_claim_risk_report.schema.json"),
            "citation": load_schema("part6_citation_consistency_report.schema.json"),
            "manifest": load_schema("part6_submission_package_manifest.schema.json"),
            "readiness": load_schema("part6_final_readiness_decision.schema.json"),
        }
        self.samples = {
            "claim_risk": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+08:00",
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
                        "finding": "案例证据仍需保守表达。",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["page_current_topic"],
                        "recommended_action": "add_source",
                        "applied_action": "downgrade_claim",
                        "status": "mitigated",
                        "residual_debt": "后续正式投稿前可补充案例图源。"
                    }
                ],
                "summary": {"total": 1, "blocked": 0}
            },
            "citation": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+08:00",
                "manuscript_ref": "outputs/part6/final_manuscript.md",
                "citation_map_ref": "outputs/part5/citation_map.json",
                "raw_metadata_ref": "raw-library/metadata.json",
                "wiki_index_ref": "research-wiki/index.json",
                "accepted_sources_ref": "outputs/part1/accepted_sources.json",
                "authenticity_report_ref": "outputs/part1/authenticity_report.json",
                "status": "pass_with_warnings",
                "checked_claim_ids": ["claim_001"],
                "checked_source_ids": ["cnki_001"],
                "citation_items": [
                    {
                        "source_id": "cnki_001",
                        "claim_ids": ["claim_001"],
                        "citation_status": "accepted",
                        "raw_metadata_present": True,
                        "wiki_mapped": True,
                        "authenticity_status": "passed",
                        "reference_entry_status": "present",
                        "drift_detected": False,
                        "issues": [],
                        "action": "keep"
                    }
                ],
                "warnings": ["仍需人工核对最终参考文献格式。"],
                "errors": []
            },
            "manifest": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+08:00",
                "package_id": "part6_package_001",
                "status": "complete",
                "submission_class": "internal_review_only",
                "included_files": [
                    "outputs/part6/final_manuscript.md",
                    "outputs/part6/final_abstract.md",
                    "outputs/part6/final_keywords.json",
                    "outputs/part6/submission_checklist.md",
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json",
                    "outputs/part6/final_readiness_decision.json"
                ],
                "required_files": [
                    "outputs/part6/final_manuscript.md",
                    "outputs/part6/final_abstract.md",
                    "outputs/part6/final_keywords.json",
                    "outputs/part6/submission_checklist.md",
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json",
                    "outputs/part6/final_readiness_decision.json"
                ],
                "missing_files": [],
                "audit_refs": [
                    "outputs/part6/claim_risk_report.json",
                    "outputs/part6/citation_consistency_report.json"
                ],
                "policy_refs": ["writing-policy/source_index.json"],
                "evidence_refs": [
                    "raw-library/metadata.json",
                    "research-wiki/index.json",
                    "outputs/part5/claim_evidence_matrix.json",
                    "outputs/part5/citation_map.json"
                ],
                "human_decision_required": True
            },
            "readiness": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+08:00",
                "verdict": "internal_review_only",
                "manifest_ref": "outputs/part6/submission_package_manifest.json",
                "claim_risk_report_ref": "outputs/part6/claim_risk_report.json",
                "citation_consistency_report_ref": "outputs/part6/citation_consistency_report.json",
                "blocking_issues": [],
                "residual_risks": ["正式投稿前仍需人工确认图源与格式。"],
                "residual_research_debts": [],
                "required_human_decisions": ["part6_final_decision_confirmed"],
                "does_not_advance_part7": True
            }
        }

    def validate_sample(self, key, sample=None):
        jsonschema.validate(
            instance=sample or self.samples[key],
            schema=self.schemas[key],
        )

    def test_minimal_valid_samples_pass(self):
        for key in self.schemas:
            with self.subTest(schema=key):
                self.validate_sample(key)

    def test_missing_required_field_fails(self):
        for key, schema in self.schemas.items():
            for field in schema["required"]:
                sample = copy.deepcopy(self.samples[key])
                sample.pop(field)
                with self.subTest(schema=key, missing=field):
                    with self.assertRaises(jsonschema.ValidationError):
                        self.validate_sample(key, sample)

    def test_final_readiness_does_not_advance_part7_must_be_true(self):
        sample = copy.deepcopy(self.samples["readiness"])
        sample["does_not_advance_part7"] = False

        with self.assertRaises(jsonschema.ValidationError):
            self.validate_sample("readiness", sample)

    def test_manifest_human_decision_required_must_be_true(self):
        sample = copy.deepcopy(self.samples["manifest"])
        sample["human_decision_required"] = False

        with self.assertRaises(jsonschema.ValidationError):
            self.validate_sample("manifest", sample)

    def test_final_readiness_requires_final_decision_human_gate(self):
        sample = copy.deepcopy(self.samples["readiness"])
        sample["required_human_decisions"] = ["part6_finalization_authorized"]

        with self.assertRaises(jsonschema.ValidationError):
            self.validate_sample("readiness", sample)

    def test_part6_claim_risk_applied_action_cannot_add_source(self):
        sample = copy.deepcopy(self.samples["claim_risk"])
        sample["risk_items"][0]["applied_action"] = "add_source"

        with self.assertRaises(jsonschema.ValidationError):
            self.validate_sample("claim_risk", sample)


if __name__ == "__main__":
    unittest.main()
