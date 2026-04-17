import importlib.util
import json
import sys
from pathlib import Path

import pytest


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"


def load_server_module():
    spec = importlib.util.spec_from_file_location("local_web_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_discover_contexts_includes_root():
    server = load_server_module()
    contexts = server.discover_contexts()
    ids = {context["id"] for context in contexts}
    assert "root" in ids


def test_resolve_context_rejects_path_traversal():
    server = load_server_module()
    with pytest.raises(ValueError):
        server.resolve_context("../runtime")


def test_build_commands_uses_allowlisted_cli_without_shell():
    server = load_server_module()
    context_id, root = server.resolve_context("root")
    commands = server.build_commands(root, "validate-stage", {"stage": "part1"})
    assert context_id == "root"
    assert len(commands) == 1
    assert commands[0][1].endswith("cli.py")
    assert commands[0][2:] == ["validate", "part1"]


def test_part3_select_requires_explicit_notes():
    server = load_server_module()
    _, root = server.resolve_context("root")
    with pytest.raises(ValueError):
        server.build_commands(
            root,
            "part3-select",
            {"candidate_id": "candidate_theory_first", "notes": ""},
        )


def test_artifact_preview_blocks_non_artifact_paths():
    server = load_server_module()
    with pytest.raises(ValueError):
        server.artifact_preview("root", "cli.py")


def test_normalize_intake_requires_core_fields():
    server = load_server_module()
    with pytest.raises(ValueError):
        server.normalize_intake_from_params({"intake": {"research_topic": "x"}})


def test_normalize_intake_builds_cnki_first_source_preference():
    server = load_server_module()
    intake = server.normalize_intake_from_params(
        {
            "intake": {
                "research_topic": "测试题目",
                "research_question": "测试问题",
                "keywords_required": ["关键词一"],
                "scope_notes": "测试范围",
                "time_range": {"start_year": 2020, "end_year": 2026},
            }
        }
    )
    assert intake["source_preference"]["priority"] == "CNKI first"
    assert "cnki" in intake["source_preference"]["priority_sources"]


def test_part3_candidate_snapshot_has_expected_shape(tmp_path):
    server = load_server_module()
    comparison_path = tmp_path / "outputs" / "part3" / "candidate_comparison.json"
    comparison_path.parent.mkdir(parents=True)
    comparison_path.write_text(
        json.dumps(
            {
                "recommendation": {"recommended_candidate_id": "candidate_a"},
                "candidates": [
                    {
                        "candidate_id": "candidate_a",
                        "strategy": "baseline",
                        "thesis": "测试 thesis",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    snapshot = server.part3_candidate_snapshot(tmp_path)
    assert "candidates" in snapshot
    assert isinstance(snapshot["candidates"], list)
    assert snapshot["candidates"][0]["candidate_id"] == "candidate_a"


def test_part1_reference_snapshot_reads_downloaded_files(tmp_path):
    server = load_server_module()
    table_path = tmp_path / "outputs" / "part1" / "downloaded_papers_table.csv"
    table_path.parent.mkdir(parents=True)
    table_path.write_text(
        "source_id,local_path,title,authors,year,journal,source_name,query_id,download_status,library_status,relevance_tier,relevance_score\n"
        "cnki_2026_001,raw-library/papers/cnki_2026_001.pdf,测试论文,作者,2026,测试期刊,CNKI,cnki_q1_1,success,accepted,tier_A,0.9\n",
        encoding="utf-8-sig",
    )
    paper_path = tmp_path / "raw-library" / "papers" / "cnki_2026_001.pdf"
    paper_path.parent.mkdir(parents=True)
    paper_path.write_bytes(b"%PDF-1.4\n")
    snapshot = server.part1_reference_snapshot(tmp_path)
    assert snapshot["total"] >= 1
    first = snapshot["references"][0]
    assert first["file_name"].endswith(".pdf")
    assert first["local_path"].startswith("raw-library/papers/")
