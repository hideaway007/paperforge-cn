import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part2_wiki_generator.py"
PART2_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part2_wiki_bundle.schema.json"


def load_generator_module():
    module_dir = str(GENERATOR_PATH.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location("part2_wiki_generator_test", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Part2WikiGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = load_generator_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name)
        self.original_env = {
            "RTM_WIKISYNTHESISAGENT_COMMAND": os.environ.get("RTM_WIKISYNTHESISAGENT_COMMAND"),
            "RTM_WIKISYNTHESISAGENT_TIMEOUT": os.environ.get("RTM_WIKISYNTHESISAGENT_TIMEOUT"),
        }
        self.addCleanup(self.restore_env)
        for key in self.original_env:
            os.environ.pop(key, None)
        (self.project_root / "raw-library").mkdir(parents=True)
        (self.project_root / "writing-policy" / "reference_cases").mkdir(parents=True)
        (self.project_root / "writing-policy" / "rules").mkdir(parents=True)
        (self.project_root / "writing-policy" / "reference_cases" / "case_001.md").write_text(
            "# 禁止混入 Research Wiki 的写作案例\n\nWRITING_POLICY_SENTINEL\n",
            encoding="utf-8",
        )
        (self.project_root / "writing-policy" / "rules" / "rule_001.md").write_text(
            "# 写作规则\n\nWRITING_POLICY_RULE_SENTINEL\n",
            encoding="utf-8",
        )

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
            f.write("\n")

    def read_json(self, rel_path):
        with open(self.project_root / rel_path, encoding="utf-8") as f:
            return json.load(f)

    def read_text(self, rel_path):
        return (self.project_root / rel_path).read_text(encoding="utf-8")

    def write_metadata(self, sources=None):
        self.write_json(
            "raw-library/metadata.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "intake_ref": "outputs/part1/intake.json",
                "sources": sources if sources is not None else self.accepted_sources(),
                "summary": {
                    "total_accepted": len(sources if sources is not None else self.accepted_sources()),
                    "total_excluded": 0,
                    "tier1_count": 2,
                    "tier2_count": 0,
                },
            },
        )

    def accepted_sources(self):
        return [
            {
                "source_id": "cnki_2024_001",
                "title": "地域建筑符号教学实践类型研究",
                "authors": ["张三"],
                "year": 2024,
                "journal": "建筑学报",
                "doi": None,
                "abstract": "讨论地域建筑符号教学实践、地域性与现代建筑转译。",
                "keywords": ["地域建筑", "空间场景", "地域性"],
                "source_tier": "tier1_chinese_primary",
                "source_name": "cnki",
                "language": "zh",
                "authenticity_status": "verified",
                "relevance_score": 0.91,
                "local_path": "raw-library/papers/cnki_2024_001.pdf",
                "normalized_path": "raw-library/normalized/cnki_2024_001.txt",
                "provenance_path": "raw-library/provenance/cnki_2024_001.json",
                "added_at": "2026-04-16T00:00:00+00:00",
            },
            {
                "source_id": "cnki_2023_002",
                "title": "空间句法视角下的传统聚落路径研究",
                "authors": ["李四"],
                "year": 2023,
                "journal": "南方建筑",
                "doi": None,
                "abstract": "以空间句法分析传统聚落的路径组织和界面关系。",
                "keywords": ["空间句法", "传统聚落", "路径组织"],
                "source_tier": "tier1_chinese_primary",
                "source_name": "cnki",
                "language": "zh",
                "authenticity_status": "verified",
                "relevance_score": 0.86,
                "local_path": "raw-library/papers/cnki_2023_002.pdf",
                "normalized_path": "raw-library/normalized/cnki_2023_002.txt",
                "provenance_path": "raw-library/provenance/cnki_2023_002.json",
                "added_at": "2026-04-16T00:00:00+00:00",
            },
        ]

    def run_generator(self, *, dry_run=False, force=False):
        if hasattr(self.generator, "run_wiki_generation"):
            return self.generator.run_wiki_generation(
                self.project_root,
                dry_run=dry_run,
                force=force,
            )

        package = self.generator.generate_wiki_bundle(self.project_root)
        if not dry_run:
            self.generator.write_wiki_bundle(self.project_root, package, force=force)
        return package

    def assert_no_canonical_index(self):
        self.assertFalse((self.project_root / "research-wiki" / "index.json").exists())

    def assert_text_artifact_exists(self, rel_path):
        path = self.project_root / rel_path
        self.assertTrue(path.exists(), f"{rel_path} must be generated")

    def assert_markdown_link_to_page(self, markdown_text, page):
        file_path = page["file_path"]
        relative_from_wiki_root = file_path.removeprefix("research-wiki/")
        link_pattern = rf"\[[^\]]+\]\(({re.escape(file_path)}|{re.escape(relative_from_wiki_root)})\)"
        self.assertRegex(
            markdown_text,
            link_pattern,
            f"index.md must include a markdown link to {file_path}",
        )

    def colliding_slug_sources(self):
        return [
            {
                **self.accepted_sources()[0],
                "source_id": "a/b",
                "title": "普通研究一",
                "abstract": "普通材料。",
                "keywords": ["场地"],
            },
            {
                **self.accepted_sources()[1],
                "source_id": "a?b",
                "title": "普通研究二",
                "abstract": "普通材料。",
                "keywords": ["场地"],
            },
        ]

    def test_missing_raw_metadata_fails_without_creating_canonical_index(self):
        with self.assertRaisesRegex((FileNotFoundError, RuntimeError), "raw-library/metadata.json"):
            self.run_generator()

        self.assert_no_canonical_index()

    def test_empty_metadata_sources_fails_without_creating_canonical_index(self):
        self.write_metadata(sources=[])

        with self.assertRaisesRegex(RuntimeError, "sources"):
            self.run_generator()

        self.assert_no_canonical_index()

    def test_generates_schema_valid_wiki_index_and_required_side_artifacts(self):
        self.write_metadata()

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        with open(PART2_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=index, schema=schema)

        self.assertEqual(index["source_bundle_ref"], "raw-library/metadata.json")
        self.assertTrue(index["source_mapping_complete"])
        self.assertGreaterEqual(len(index["pages"]), 1)
        for rel_path in ("research-wiki/index.md", "research-wiki/log.md"):
            with self.subTest(rel_path=rel_path):
                self.assert_text_artifact_exists(rel_path)
        self.assertTrue((self.project_root / "research-wiki" / "update_log.json").exists())
        self.assertTrue((self.project_root / "research-wiki" / "contradictions_report.json").exists())

        expected_page_type_enum = [
            "concept",
            "topic",
            "method",
            "contradiction",
            "evidence_aggregation",
        ]
        self.assertEqual(
            schema["$defs"]["WikiPageIndex"]["properties"]["page_type"]["enum"],
            expected_page_type_enum,
        )
        allowed_page_types = set(expected_page_type_enum)
        for page in index["pages"]:
            self.assertIn(page["page_type"], allowed_page_types)

    def test_wikisynthesisagent_sidecar_runs_when_configured(self):
        self.write_metadata()
        fake_agent = self.project_root / "fake_wikisynthesisagent.py"
        fake_agent.write_text(
            (
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "assert request['agent_name'] == 'wikisynthesisagent'\n"
                "assert request['task'] == 'part2_research_wiki_synthesis_review'\n"
                "paths = [item['path'] for item in request['inputs']]\n"
                "assert 'research-wiki/index.json' in paths\n"
                "assert 'raw-library/metadata.json' in paths\n"
                "print(json.dumps({'report': 'wikisynthesisagent reviewed research wiki'}, ensure_ascii=False))\n"
            ),
            encoding="utf-8",
        )
        os.environ["RTM_WIKISYNTHESISAGENT_COMMAND"] = f"{sys.executable} {fake_agent}"
        os.environ["RTM_WIKISYNTHESISAGENT_TIMEOUT"] = "5"

        self.run_generator(force=True)

        review = self.read_json("research-wiki/wikisynthesisagent_review.json")
        self.assertEqual("wikisynthesisagent reviewed research wiki", review["report"])
        provenance = self.read_json("research-wiki/wikisynthesisagent_provenance.json")
        self.assertEqual("wikisynthesisagent", provenance["agent_name"])
        self.assertEqual("llm", provenance["mode"])

    def test_generates_cumulative_research_wiki_not_one_card_per_source(self):
        sources = self.accepted_sources()
        self.write_metadata(sources=sources)

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        source_ids = {source["source_id"] for source in sources}
        pages = index["pages"]
        page_types = {page["page_type"] for page in pages}

        self.assertGreaterEqual(
            len(pages),
            len(sources) + 2,
            "Part 2 wiki must be more than one thin metadata card per source.",
        )
        self.assertTrue(
            page_types & {"concept", "topic"},
            "Generated wiki should include concept/topic pages built from source themes.",
        )
        self.assertIn(
            "evidence_aggregation",
            page_types,
            "Generated wiki should include evidence aggregation pages.",
        )
        digest_pages = [
            page
            for page in pages
            if page["page_id"].startswith("source_digest_")
            and "source_digest" in page.get("tags", [])
        ]
        digest_source_ids = {
            source_id
            for page in digest_pages
            for source_id in page["source_ids"]
        }
        self.assertEqual(
            digest_source_ids,
            source_ids,
            "Every accepted source must have an explicit source_digest page.",
        )
        for page in digest_pages:
            self.assertEqual(
                len(page["source_ids"]),
                1,
                f"{page['page_id']} should digest exactly one accepted source.",
            )
            self.assertEqual(page["page_type"], "evidence_aggregation")
            self.assertRegex(
                page["file_path"],
                r"^research-wiki/pages/source-digest/source_digest_[^/]+\.md$",
            )

        aggregation_pages = [
            page
            for page in pages
            if page["page_type"] == "evidence_aggregation"
            and page["page_id"] == "evidence_aggregation_all_sources"
            and source_ids.issubset(set(page["source_ids"]))
        ]
        self.assertTrue(
            aggregation_pages,
            "At least one evidence aggregation page should accumulate all ingested sources.",
        )

        synthesis_pages = [
            page
            for page in pages
            if page["page_id"] == "synthesis_all_sources"
            and "synthesis" in page.get("tags", [])
            and source_ids.issubset(set(page["source_ids"]))
        ]
        self.assertTrue(
            synthesis_pages,
            "At least one synthesis page should accumulate all ingested sources.",
        )
        for page in synthesis_pages:
            self.assertEqual(page["page_type"], "evidence_aggregation")
            self.assertEqual(
                page["file_path"],
                "research-wiki/pages/synthesis/synthesis_all_sources.md",
            )

    def test_page_bodies_include_source_ids_and_related_page_links(self):
        self.write_metadata()

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        page_ids = {page["page_id"] for page in index["pages"]}
        for page in index["pages"]:
            body = self.read_text(page["file_path"])
            self.assertIn(
                "source_ids",
                body,
                f"{page['file_path']} must expose source_ids in the page body.",
            )
            for source_id in page["source_ids"]:
                self.assertIn(source_id, body)

            self.assertRegex(
                body,
                r"(related_pages|links|\[[^\]]+\]\([^)]+\.md\))",
                f"{page['file_path']} must expose links/related pages in the page body.",
            )
            for related_page_id in page.get("related_pages", []):
                self.assertIn(related_page_id, page_ids)
                self.assertIn(related_page_id, body)

    def test_index_markdown_is_content_directory_with_sections_and_page_links(self):
        self.write_metadata()

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        self.assert_text_artifact_exists("research-wiki/index.md")
        index_markdown = self.read_text("research-wiki/index.md")
        digest_pages = [
            page
            for page in index["pages"]
            if page["page_id"].startswith("source_digest_")
            and "source_digest" in page.get("tags", [])
        ]
        synthesis_pages = [
            page
            for page in index["pages"]
            if page["page_id"] == "synthesis_all_sources"
            and "synthesis" in page.get("tags", [])
        ]

        self.assertRegex(index_markdown, r"(?m)^# .*(Research Wiki|研究 Wiki|研究维基)")
        self.assertRegex(
            index_markdown,
            r"(?m)^## .*Source Digest",
            "index.md should keep a Source Digest section based on tags/page_id.",
        )
        self.assertRegex(
            index_markdown,
            r"(?m)^## .*(概念|主题|Concept|Topic|concept|topic)",
            "index.md should group concept/topic pages under content sections.",
        )
        self.assertRegex(
            index_markdown,
            r"(?m)^## .*(综合|合成|证据|Synthesis|Evidence|synthesis|evidence)",
            "index.md should group synthesis/evidence pages under content sections.",
        )
        for page in [*digest_pages, *synthesis_pages]:
            self.assertIn(page["title"], index_markdown)
            self.assert_markdown_link_to_page(index_markdown, page)
        for page in index["pages"]:
            self.assertIn(page["title"], index_markdown)
            self.assert_markdown_link_to_page(index_markdown, page)

    def test_log_markdown_appends_generation_context_across_runs(self):
        self.write_metadata()

        self.run_generator()
        self.assert_text_artifact_exists("research-wiki/log.md")
        first_log = self.read_text("research-wiki/log.md")

        self.assertIn("raw-library/metadata.json", first_log)
        self.assertIn("cnki_2024_001", first_log)
        self.assertIn("cnki_2023_002", first_log)
        self.assertRegex(first_log, r"(ingest|generation|生成|追加)")
        self.assertRegex(first_log, r"(source_count|来源数|sources)")
        self.assertRegex(first_log, r"(page_count|页面数|pages)")
        self.assertGreaterEqual(len(first_log.strip().splitlines()), 6)

        self.run_generator(force=True)
        second_log = self.read_text("research-wiki/log.md")

        self.assertIn(first_log.strip(), second_log)
        self.assertGreater(len(second_log), len(first_log))
        self.assertGreaterEqual(second_log.count("raw-library/metadata.json"), 2)

    def test_page_source_ids_are_accepted_metadata_source_ids(self):
        self.write_metadata()
        accepted_source_ids = {source["source_id"] for source in self.accepted_sources()}

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        for page in index["pages"]:
            self.assertTrue(page["source_ids"], f"{page['page_id']} must keep source traceability")
            self.assertTrue(set(page["source_ids"]).issubset(accepted_source_ids))

    def test_page_file_paths_exist_under_research_wiki_pages(self):
        self.write_metadata()

        self.run_generator()

        pages_root = (self.project_root / "research-wiki" / "pages").resolve()
        index = self.read_json("research-wiki/index.json")
        for page in index["pages"]:
            file_path = page["file_path"]
            self.assertTrue(file_path.startswith("research-wiki/pages/"))
            absolute_path = (self.project_root / file_path).resolve()
            absolute_path.relative_to(pages_root)
            self.assertTrue(absolute_path.exists(), file_path)

    def test_health_summary_is_complete_for_generated_pages(self):
        self.write_metadata()

        self.run_generator()

        index = self.read_json("research-wiki/index.json")
        self.assertEqual(index["health_summary"]["total_pages"], len(index["pages"]))
        self.assertEqual(index["health_summary"]["unsourced_pages"], 0)
        self.assertEqual(index["health_summary"]["orphan_pages"], 0)
        self.assertEqual(index["health_summary"]["isolated_pages"], 0)
        self.assertTrue(index["source_mapping_complete"])

    def test_does_not_mix_writing_policy_content_into_research_wiki(self):
        self.write_metadata()

        self.run_generator()

        research_wiki_root = self.project_root / "research-wiki"
        combined_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in research_wiki_root.rglob("*")
            if path.is_file()
        )
        self.assertNotIn("WRITING_POLICY_SENTINEL", combined_text)
        self.assertNotIn("WRITING_POLICY_RULE_SENTINEL", combined_text)
        self.assertNotIn("writing-policy/", combined_text)

    def test_dry_run_does_not_write_wiki_artifacts_when_cli_entry_is_available(self):
        if not hasattr(self.generator, "main"):
            self.skipTest("part2_wiki_generator.main is not available")
        self.write_metadata()

        with mock.patch.object(
            sys,
            "argv",
            [
                "part2_wiki_generator.py",
                "--project-root",
                str(self.project_root),
                "--dry-run",
            ],
        ):
            self.generator.main()

        self.assert_no_canonical_index()
        self.assertFalse((self.project_root / "research-wiki" / "index.md").exists())
        self.assertFalse((self.project_root / "research-wiki" / "log.md").exists())
        self.assertFalse((self.project_root / "research-wiki" / "update_log.json").exists())
        self.assertFalse((self.project_root / "research-wiki" / "contradictions_report.json").exists())

    def test_existing_canonical_index_requires_force_and_preserves_original_index(self):
        self.write_metadata()
        existing_index = {
            "schema_version": "1.0.0",
            "sentinel": "do-not-overwrite",
        }
        self.write_json("research-wiki/index.json", existing_index)

        try:
            with self.assertRaisesRegex(RuntimeError, "force|already exists"):
                self.run_generator(force=False)
        finally:
            self.assertEqual(self.read_json("research-wiki/index.json"), existing_index)

    def test_force_allows_existing_canonical_index_to_be_rewritten(self):
        self.write_metadata()
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "sentinel": "replace-me",
            },
        )

        self.run_generator(force=True)

        index = self.read_json("research-wiki/index.json")
        self.assertEqual(index["source_bundle_ref"], "raw-library/metadata.json")
        self.assertNotIn("sentinel", index)
        self.assertGreaterEqual(len(index["pages"]), 1)

    def test_force_removes_previously_indexed_stale_page_files(self):
        self.write_metadata()
        stale_page_path = self.project_root / "research-wiki" / "pages" / "stale_old_page.md"
        stale_page_path.parent.mkdir(parents=True, exist_ok=True)
        stale_page_path.write_text("# stale\n", encoding="utf-8")
        unindexed_page_path = self.project_root / "research-wiki" / "pages" / "manual_note.md"
        unindexed_page_path.write_text("# keep\n", encoding="utf-8")
        gitkeep_path = self.project_root / "research-wiki" / "pages" / ".gitkeep"
        gitkeep_path.write_text("", encoding="utf-8")
        self.write_json(
            "research-wiki/index.json",
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "source_bundle_ref": "raw-library/metadata.json",
                "source_mapping_complete": True,
                "pages": [
                    {
                        "page_id": "stale_old_page",
                        "title": "stale",
                        "page_type": "topic",
                        "source_ids": ["cnki_2024_001"],
                        "file_path": "research-wiki/pages/stale_old_page.md",
                        "created_at": "2026-04-16T00:00:00+00:00",
                    },
                    {
                        "page_id": "placeholder_gitkeep",
                        "title": "placeholder",
                        "page_type": "topic",
                        "source_ids": ["cnki_2024_001"],
                        "file_path": "research-wiki/pages/.gitkeep",
                        "created_at": "2026-04-16T00:00:00+00:00",
                    }
                ],
                "health_summary": {
                    "total_pages": 2,
                    "orphan_pages": 0,
                    "unsourced_pages": 0,
                    "contradiction_count": 0,
                },
            },
        )

        self.run_generator(force=True)

        self.assertFalse(stale_page_path.exists())
        self.assertTrue(unindexed_page_path.exists())
        self.assertTrue(gitkeep_path.exists())

    def test_slug_collision_fails_without_generating_canonical_index(self):
        self.write_metadata(sources=self.colliding_slug_sources())

        with self.assertRaisesRegex(RuntimeError, "duplicate|page_id"):
            self.run_generator()

        self.assert_no_canonical_index()

    def test_write_wiki_bundle_rejects_page_path_traversal_without_writing_outside_wiki(self):
        package = {
            "index": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "last_updated": "2026-04-16T00:00:00+00:00",
                "source_bundle_ref": "raw-library/metadata.json",
                "source_mapping_complete": True,
                "pages": [],
                "health_summary": {},
            },
            "page_files": {
                "research-wiki/pages/../../escape.md": "escape",
            },
            "update_log": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "source_bundle_ref": "raw-library/metadata.json",
                "events": [],
            },
            "contradictions_report": {
                "schema_version": "1.0.0",
                "generated_at": "2026-04-16T00:00:00+00:00",
                "source_bundle_ref": "raw-library/metadata.json",
                "contradiction_count": 0,
                "pages": [],
            },
        }

        with self.assertRaisesRegex(RuntimeError, "Invalid|path|traversal"):
            self.generator.write_wiki_bundle(self.project_root, package, force=True)

        self.assertFalse((self.project_root / "escape.md").exists())


if __name__ == "__main__":
    unittest.main()
