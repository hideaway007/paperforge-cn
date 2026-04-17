import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = PROJECT_ROOT / "runtime" / "agents"
GENERATOR_PATH = AGENTS_DIR / "part5_mvp_generator.py"
FRAGMENT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part5_review_fragment.schema.json"


def load_agent_module(module_name):
    module_dir = str(AGENTS_DIR)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(
        f"{module_name}_test",
        AGENTS_DIR / f"{module_name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator_module():
    module_dir = str(AGENTS_DIR)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location("part5_mvp_generator_fragments_test", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part5ReviewFragmentTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.original_env = {
            "RTM_CLAIMAUDITOR_COMMAND": os.environ.get("RTM_CLAIMAUDITOR_COMMAND"),
            "RTM_CLAIMAUDITOR_TIMEOUT": os.environ.get("RTM_CLAIMAUDITOR_TIMEOUT"),
            "RTM_CITATIONAUDITOR_COMMAND": os.environ.get("RTM_CITATIONAUDITOR_COMMAND"),
            "RTM_CITATIONAUDITOR_TIMEOUT": os.environ.get("RTM_CITATIONAUDITOR_TIMEOUT"),
        }
        self.addCleanup(self.restore_env)
        for key in self.original_env:
            os.environ.pop(key, None)
        self.write_fixture_project()

    def restore_env(self):
        for key, value in self.original_env.items():
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

    def write_state(self, gates=None):
        def completed(completed_gates=None):
            return {
                "status": "completed",
                "gate_passed": True,
                "started_at": "2026-04-16T00:00:00+00:00",
                "completed_at": "2026-04-16T00:10:00+00:00",
                "human_gates_completed": completed_gates or [],
            }

        self.write_json(
            "runtime/state.json",
            {
                "schema_version": "1.0.0",
                "stages": {
                    "part1": completed(["intake_confirmed"]),
                    "part2": completed(),
                    "part3": completed(["argument_tree_selected"]),
                    "part4": completed(),
                    "part5": {
                        "status": "in_progress",
                        "gate_passed": False,
                        "started_at": "2026-04-16T00:20:00+00:00",
                        "completed_at": None,
                        "human_gates_completed": gates or [],
                    },
                },
                "human_decision_log": [],
            },
        )

    def write_fixture_project(self):
        for rel_dir in [
            "runtime",
            "outputs/part3",
            "outputs/part4",
            "outputs/part5",
            "research-wiki/pages",
            "raw-library",
            "writing-policy/rules",
            "writing-policy/style_guides",
        ]:
            (self.project_root / rel_dir).mkdir(parents=True, exist_ok=True)

        self.write_state()
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
                        "page_id": "page_current_topic",
                        "file_path": "research-wiki/pages/page_current_topic.md",
                        "source_ids": ["cnki_001"],
                    }
                ],
                "source_mapping_complete": True,
            },
        )
        self.write_text("research-wiki/pages/page_current_topic.md", "# 地域建筑\n\n空间场景。\n")
        self.write_json(
            "writing-policy/source_index.json",
            {
                "schema_version": "1.0.0",
                "rules": [
                    {
                        "id": "rule_conservative_claims",
                        "path": "writing-policy/rules/rule.md",
                        "usage": "structure_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "style_guides": [
                    {
                        "id": "guide_academic_chinese",
                        "path": "writing-policy/style_guides/guide.md",
                        "usage": "expression_constraint_only",
                        "may_be_used_as_research_evidence": False,
                    }
                ],
                "coverage": {"structure": True, "expression": True},
            },
        )
        self.write_text("writing-policy/rules/rule.md", "# 规则\n")
        self.write_text("writing-policy/style_guides/guide.md", "# 表达\n")
        self.write_json(
            "outputs/part3/argument_tree.json",
            {
                "schema_version": "1.0.0",
                "locked_at": "2026-04-16T00:00:00+00:00",
                "wiki_ref": "research-wiki/index.json",
                "root": {
                    "node_id": "thesis_001",
                    "node_type": "thesis",
                    "claim": "地域建筑符号教学实践可作为当代设计方法参照。",
                    "support_source_ids": ["cnki_001"],
                    "wiki_page_ids": ["page_current_topic"],
                },
            },
        )
        self.write_json(
            "outputs/part4/paper_outline.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "confirmed_at": None,
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "wiki_ref": "research-wiki/index.json",
                "writing_policy_ref": "writing-policy/source_index.json",
                "sections": [
                    {
                        "section_id": "sec_1",
                        "title": "绪论",
                        "level": 1,
                        "brief": "说明研究缘起。",
                        "argument_node_ids": ["thesis_001"],
                        "support_source_ids": ["cnki_001"],
                    }
                ],
            },
        )
        self.write_json(
            "outputs/part5/claim_evidence_matrix.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:30:00+00:00",
                "outline_ref": "outputs/part4/paper_outline.json",
                "argument_tree_ref": "outputs/part3/argument_tree.json",
                "wiki_ref": "research-wiki/index.json",
                "claims": [
                    {
                        "claim_id": "thesis_001",
                        "claim": "地域建筑符号教学实践可作为当代设计方法参照。",
                        "evidence_level": "hard_evidence",
                        "source_ids": ["cnki_001"],
                        "wiki_page_ids": ["page_current_topic"],
                        "risk_level": "low",
                        "status": "mapped",
                    },
                    {
                        "claim_id": "arg_gap",
                        "claim": "案例空间关系仍需图纸支撑。",
                        "evidence_level": "conceptual_framing",
                        "source_ids": [],
                        "wiki_page_ids": [],
                        "risk_level": "critical",
                        "status": "registered",
                    },
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
                "known_gaps": ["案例图纸缺口必须保守处理。"],
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
                        "type": "evidence_gap",
                        "description": "补充案例图纸。",
                        "claim_id": "arg_gap",
                        "blocks_part6": True,
                    }
                ],
            },
        )
        self.write_text(
            "outputs/part5/manuscript_v1.md",
            "# 论文初稿 v1\n\n## 绪论\n\n地域建筑符号教学实践可作为当代设计方法参照。\n",
        )

    def validate_fragment_schema(self, artifact):
        with open(FRAGMENT_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=artifact, schema=schema)

    def test_individual_review_agents_only_write_fragment_artifacts(self):
        modules = [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]

        for module_name in modules:
            artifact = load_agent_module(module_name).generate_review_fragment(self.project_root)
            self.validate_fragment_schema(artifact)

        fragment_dir = self.project_root / "outputs" / "part5" / "review_fragments"
        self.assertTrue((fragment_dir / "structure_review.json").exists())
        self.assertTrue((fragment_dir / "argument_review.json").exists())
        self.assertTrue((fragment_dir / "evidence_review.json").exists())
        self.assertTrue((fragment_dir / "citation_review.json").exists())
        self.assertTrue((fragment_dir / "writing_policy_review.json").exists())

        self.assertFalse((self.project_root / "outputs/part5/review_matrix.json").exists())
        self.assertFalse((self.project_root / "outputs/part5/review_summary.md").exists())
        self.assertFalse((self.project_root / "outputs/part5/claim_risk_report.json").exists())
        self.assertFalse((self.project_root / "outputs/part5/citation_consistency_precheck.json").exists())

    def test_evidence_review_runs_claimauditor_sidecar_when_configured(self):
        fake_agent = self.project_root / "fake_claimauditor.py"
        fake_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'claimauditor'\n"
                "assert request['task'] == 'part5_claim_evidence_review'\n"
                "assert request['skill'] == 'part5-review-manuscript'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "assert 'outputs/part5/claim_evidence_matrix.json' in paths\n"
                "assert 'outputs/part5/manuscript_v1.md' in paths\n"
                "print(json.dumps({'report': 'claim auditor reviewed part5 evidence'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_CLAIMAUDITOR_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_CLAIMAUDITOR_TIMEOUT"] = "5"

        artifact = load_agent_module("part5_review_evidence").generate_review_fragment(self.project_root)

        self.validate_fragment_schema(artifact)
        sidecar = self.read_json("outputs/part5/llm_agent_reviews/claimauditor_evidence_review.json")
        self.assertEqual("claim auditor reviewed part5 evidence", sidecar["report"])
        provenance = self.read_json("outputs/part5/claimauditor_provenance.json")
        self.assertEqual("claimauditor", provenance["agent_name"])
        self.assertEqual("llm", provenance["mode"])
        self.assertTrue(provenance["does_not_confirm_human_gate"])

    def test_citation_review_runs_citationauditor_sidecar_when_configured(self):
        fake_agent = self.project_root / "fake_citationauditor.py"
        fake_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'citationauditor'\n"
                "assert request['task'] == 'part5_citation_consistency_review'\n"
                "assert request['skill'] == 'part5-review-manuscript'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "assert 'outputs/part5/citation_map.json' in paths\n"
                "assert 'raw-library/metadata.json' in paths\n"
                "print(json.dumps({'report': 'citation auditor reviewed part5 citations'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_CITATIONAUDITOR_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_CITATIONAUDITOR_TIMEOUT"] = "5"

        artifact = load_agent_module("part5_review_citation").generate_review_fragment(self.project_root)

        self.validate_fragment_schema(artifact)
        sidecar = self.read_json("outputs/part5/llm_agent_reviews/citationauditor_citation_review.json")
        self.assertEqual("citation auditor reviewed part5 citations", sidecar["report"])
        provenance = self.read_json("outputs/part5/citationauditor_provenance.json")
        self.assertEqual("citationauditor", provenance["agent_name"])
        self.assertEqual("llm", provenance["mode"])
        self.assertTrue(provenance["does_not_confirm_human_gate"])

    def test_generator_review_step_integrates_fragments_without_confirming_human_gate(self):
        generator = load_generator_module()

        generator.run_step(self.project_root, "review")

        review_matrix = self.read_json("outputs/part5/review_matrix.json")
        dimensions = {item["dimension"] for item in review_matrix["reviews"]}
        self.assertTrue(
            {"structure", "argument", "evidence", "citation", "writing_policy"}.issubset(dimensions)
        )
        self.assertTrue((self.project_root / "outputs/part5/review_summary.md").exists())
        self.assertTrue((self.project_root / "outputs/part5/review_report.md").exists())
        self.assertTrue((self.project_root / "outputs/part5/claim_risk_report.json").exists())
        self.assertTrue((self.project_root / "outputs/part5/citation_consistency_precheck.json").exists())

        state = self.read_json("runtime/state.json")
        self.assertNotIn(
            "part5_review_completed",
            state["stages"]["part5"]["human_gates_completed"],
        )

    def test_citation_review_blocks_non_accepted_and_untraceable_sources(self):
        citation_map = self.read_json("outputs/part5/citation_map.json")
        citation_map["source_refs"].extend(
            [
                {
                    "source_id": "fake_001",
                    "title": "不存在的来源",
                    "claim_ids": ["fake_claim"],
                    "citation_status": "accepted_source",
                },
                {
                    "source_id": "draft_only_001",
                    "title": "草稿临时来源",
                    "claim_ids": ["thesis_001"],
                    "citation_status": "missing_metadata",
                },
            ]
        )
        self.write_json("outputs/part5/citation_map.json", citation_map)

        generator = load_generator_module()
        generator.run_step(self.project_root, "review")

        citation_fragment = self.read_json("outputs/part5/review_fragments/citation_review.json")
        critical_source_ids = {
            ref["source_id"]
            for review in citation_fragment["reviews"]
            if review["severity"] == "critical"
            for ref in review.get("source_refs", [])
        }
        self.assertIn("fake_001", critical_source_ids)
        self.assertIn("draft_only_001", critical_source_ids)

        precheck = self.read_json("outputs/part5/citation_consistency_precheck.json")
        self.assertEqual(precheck["status"], "blocked")
        self.assertTrue(any("fake_001" in error for error in precheck["errors"]))
        self.assertTrue(any("draft_only_001" in error for error in precheck["errors"]))

        review_matrix = self.read_json("outputs/part5/review_matrix.json")
        self.assertTrue(
            any(
                item["dimension"] == "citation" and item["severity"] == "critical"
                for item in review_matrix["reviews"]
            )
        )

    def test_citation_review_requires_source_id_in_wiki_page_source_ids(self):
        wiki_index = self.read_json("research-wiki/index.json")
        wiki_index["pages"][0]["source_ids"] = []
        self.write_json("research-wiki/index.json", wiki_index)

        generator = load_generator_module()
        generator.run_step(self.project_root, "review")

        citation_fragment = self.read_json("outputs/part5/review_fragments/citation_review.json")
        critical_source_ids = {
            ref["source_id"]
            for review in citation_fragment["reviews"]
            if review["severity"] == "critical"
            for ref in review.get("source_refs", [])
        }
        self.assertIn("cnki_001", critical_source_ids)

        precheck = self.read_json("outputs/part5/citation_consistency_precheck.json")
        self.assertEqual(precheck["status"], "blocked")
        self.assertTrue(any("cnki_001" in error for error in precheck["errors"]))

    def test_direct_review_agents_and_integrator_require_prep_artifacts(self):
        (self.project_root / "outputs/part5/claim_evidence_matrix.json").unlink()

        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            with self.subTest(module_name=module_name):
                with self.assertRaisesRegex(FileNotFoundError, "claim_evidence_matrix"):
                    load_agent_module(module_name).generate_review_fragment(self.project_root)

        integrator = load_agent_module("part5_review_integrator")
        with self.assertRaisesRegex(FileNotFoundError, "claim_evidence_matrix"):
            integrator.integrate_review_fragments(self.project_root)

    def test_direct_review_agents_and_integrator_require_full_part5_entry(self):
        state = self.read_json("runtime/state.json")
        state["stages"]["part4"]["gate_passed"] = False
        self.write_json("runtime/state.json", state)

        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            with self.subTest(module_name=module_name):
                with self.assertRaisesRegex(RuntimeError, "part4 gate"):
                    load_agent_module(module_name).generate_review_fragment(self.project_root)

        integrator = load_agent_module("part5_review_integrator")
        with self.assertRaisesRegex(RuntimeError, "part4 gate"):
            integrator.integrate_review_fragments(self.project_root)

    def test_integrator_rejects_review_item_dimension_mismatch(self):
        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            load_agent_module(module_name).generate_review_fragment(self.project_root)

        structure_fragment = self.read_json("outputs/part5/review_fragments/structure_review.json")
        structure_fragment["reviews"][0]["dimension"] = "citation"
        self.write_json("outputs/part5/review_fragments/structure_review.json", structure_fragment)

        integrator = load_agent_module("part5_review_integrator")
        with self.assertRaisesRegex(RuntimeError, "review item dimension"):
            integrator.integrate_review_fragments(self.project_root)

    def test_integrator_rejects_malformed_fragment_schema(self):
        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            load_agent_module(module_name).generate_review_fragment(self.project_root)

        structure_fragment = self.read_json("outputs/part5/review_fragments/structure_review.json")
        structure_fragment.pop("reviews")
        self.write_json("outputs/part5/review_fragments/structure_review.json", structure_fragment)

        integrator = load_agent_module("part5_review_integrator")
        with self.assertRaisesRegex(RuntimeError, "schema validation failed"):
            integrator.integrate_review_fragments(self.project_root)

    def test_integrator_rejects_fragment_ref_mismatch(self):
        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            load_agent_module(module_name).generate_review_fragment(self.project_root)

        structure_fragment = self.read_json("outputs/part5/review_fragments/structure_review.json")
        structure_fragment["fragment_ref"] = "outputs/part5/review_fragments/argument_review.json"
        self.write_json("outputs/part5/review_fragments/structure_review.json", structure_fragment)

        integrator = load_agent_module("part5_review_integrator")
        with self.assertRaisesRegex(RuntimeError, "fragment_ref 不一致"):
            integrator.integrate_review_fragments(self.project_root)

    def test_direct_review_agents_require_existing_non_empty_manuscript_v1(self):
        (self.project_root / "outputs/part5/manuscript_v1.md").unlink()

        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            with self.subTest(module_name=module_name):
                with self.assertRaisesRegex(FileNotFoundError, "outputs/part5/manuscript_v1.md"):
                    load_agent_module(module_name).generate_review_fragment(self.project_root)

        self.write_text("outputs/part5/manuscript_v1.md", " \n\t\n")
        for module_name in [
            "part5_review_structure",
            "part5_review_argument",
            "part5_review_evidence",
            "part5_review_citation",
            "part5_review_policy",
        ]:
            with self.subTest(module_name=f"{module_name}_empty"):
                with self.assertRaisesRegex(RuntimeError, "manuscript_v1.md 不能为空"):
                    load_agent_module(module_name).generate_review_fragment(self.project_root)

    def test_review_step_requires_prep_artifacts(self):
        (self.project_root / "outputs/part5/claim_evidence_matrix.json").unlink()
        generator = load_generator_module()

        with self.assertRaisesRegex(FileNotFoundError, "claim_evidence_matrix"):
            generator.run_step(self.project_root, "review")


if __name__ == "__main__":
    unittest.main()
