import importlib.util
import json
import shutil
import sys
from pathlib import Path

import jsonschema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_candidate_generator.py"
COMPARISON_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_comparison_generator.py"
SELECTION_LOCKER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_selection_locker.py"
SEED_MAP_GENERATOR_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_argument_seed_map_generator.py"
REFINER_PATH = PROJECT_ROOT / "runtime" / "agents" / "part3_argument_refiner.py"
PIPELINE_PATH = PROJECT_ROOT / "runtime" / "pipeline.py"
PART3_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part3_argument_tree.schema.json"
CANDIDATE_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part3_candidate_tree.schema.json"
COMPARISON_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part3_candidate_comparison.schema.json"
SEED_MAP_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part3_argument_seed_map.schema.json"
SELECTION_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "part3_human_selection_feedback.schema.json"
SELECTION_TABLE_REF = "outputs/part3/candidate_selection_table.md"
QUALITY_REPORT_REF = "outputs/part3/argument_quality_report.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_minimal_wiki(project_root):
    pages_dir = project_root / "research-wiki" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_specs = [
        {
            "page_id": "concept_current_topic_space",
            "title": "地域建筑空间概念",
            "page_type": "concept",
            "source_ids": ["cnki_001"],
            "file_path": "research-wiki/pages/concept_current_topic_space.md",
            "tags": ["传统建筑", "空间"],
        },
        {
            "page_id": "method_space_syntax",
            "title": "空间句法分析方法",
            "page_type": "method",
            "source_ids": ["cnki_002"],
            "file_path": "research-wiki/pages/method_space_syntax.md",
            "tags": ["方法", "结构"],
        },
        {
            "page_id": "topic_foshan_case",
            "title": "课程中的地域建筑符号案例",
            "page_type": "topic",
            "source_ids": ["cnki_003"],
            "file_path": "research-wiki/pages/topic_foshan_case.md",
            "tags": ["案例", "课程案例"],
        },
    ]
    for page in page_specs:
        page_path = project_root / page["file_path"]
        page_path.write_text(
            f"# {page['title']}\n\n"
            "## 摘要\n"
            f"{page['title']}说明地域建筑研究需要同时处理概念边界、方法路径与案例外推。\n\n"
            "## 可支撑论点\n"
            f"- {page['title']}可以支撑中文论文中的核心论点。\n"
            "- 该材料也提示案例外推边界，不能把单一材料扩展为全部地域建筑结论。\n\n"
            "## 潜在矛盾\n"
            "- 理论框架与案例材料之间可能存在解释尺度不一致。\n",
            encoding="utf-8",
        )
    write_json(
        project_root / "research-wiki" / "index.json",
        {
            "schema_version": "1.0.0",
            "generated_at": "2026-04-16T00:00:00+00:00",
            "source_bundle_ref": "raw-library/metadata.json",
            "source_mapping_complete": True,
            "pages": page_specs,
            "health_summary": {
                "total_pages": 3,
                "orphan_pages": 0,
                "unsourced_pages": 0,
                "contradiction_count": 0,
            },
        },
    )


def build_non_current_topic_wiki(project_root):
    pages_dir = project_root / "research-wiki" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_specs = [
        {
            "page_id": "concept_ancient_architecture_art_education",
            "title": "设计教育中的地域建筑符号转化",
            "page_type": "concept",
            "source_ids": ["cnki_edu_001"],
            "file_path": "research-wiki/pages/concept_ancient_architecture_art_education.md",
            "tags": ["地域建筑符号", "设计教育", "课程转化"],
        },
        {
            "page_id": "method_curriculum_application",
            "title": "课程转化与教学实践路径",
            "page_type": "method",
            "source_ids": ["cnki_edu_002"],
            "file_path": "research-wiki/pages/method_curriculum_application.md",
            "tags": ["教学实践", "实践教学", "课程体系"],
        },
        {
            "page_id": "topic_creative_transformation",
            "title": "设计创作与文创转化实践",
            "page_type": "topic",
            "source_ids": ["cnki_edu_003"],
            "file_path": "research-wiki/pages/topic_creative_transformation.md",
            "tags": ["设计创作", "文化传承", "成果转化"],
        },
    ]
    for page in page_specs:
        page_path = project_root / page["file_path"]
        page_path.write_text(
            f"# {page['title']}\n\n"
            "## 摘要\n"
            f"{page['title']}说明论文需要处理地域建筑符号、课程组织与学生创作能力之间的关系。\n\n"
            "## 可支撑论点\n"
            f"- {page['title']}可以支撑设计教育中的教学实践论点。\n"
            "- 该材料也提示成果转化需要限定在已登记课程与创作案例范围内。\n\n"
            "## 潜在矛盾\n"
            "- 地域建筑美学与课堂实践之间可能存在转化尺度不一致。\n",
            encoding="utf-8",
        )
    write_json(
        project_root / "research-wiki" / "index.json",
        {
            "schema_version": "1.0.0",
            "generated_at": "2026-04-16T00:00:00+00:00",
            "source_bundle_ref": "raw-library/metadata.json",
            "source_mapping_complete": True,
            "pages": page_specs,
            "health_summary": {
                "total_pages": 3,
                "orphan_pages": 0,
                "unsourced_pages": 0,
                "contradiction_count": 0,
            },
        },
    )


def build_minimal_raw_metadata(project_root):
    write_json(
        project_root / "raw-library" / "metadata.json",
        {
            "schema_version": "1.0.0",
            "generated_at": "2026-04-16T00:00:00+00:00",
            "intake_ref": "test_intake",
            "search_plan_ref": "outputs/part1/search_plan.json",
            "sources": [
                {"source_id": "cnki_001", "title": "source 1"},
                {"source_id": "cnki_002", "title": "source 2"},
                {"source_id": "cnki_003", "title": "source 3"},
            ],
            "summary": {"total_accepted": 3, "total_excluded": 0},
        },
    )


def build_non_current_topic_raw_metadata(project_root):
    write_json(
        project_root / "raw-library" / "metadata.json",
        {
            "schema_version": "1.0.0",
            "generated_at": "2026-04-16T00:00:00+00:00",
            "intake_ref": "test_intake",
            "search_plan_ref": "outputs/part1/search_plan.json",
            "sources": [
                {"source_id": "cnki_edu_001", "title": "地域建筑符号在设计教育中的课程转化"},
                {"source_id": "cnki_edu_002", "title": "地域建筑美学与高校艺术课程转化"},
                {"source_id": "cnki_edu_003", "title": "设计创作中的地域建筑文化传承实践"},
            ],
            "summary": {"total_accepted": 3, "total_excluded": 0},
        },
    )


def build_minimal_state(project_root, *, part2_completed=True, part3_gate=False):
    def stage(status, gate_passed, human_gates=None):
        return {
            "status": status,
            "started_at": "2026-04-16T00:00:00+00:00" if status != "not_started" else None,
            "completed_at": "2026-04-16T00:00:00+00:00" if status == "completed" else None,
            "gate_passed": gate_passed,
            "human_gates_completed": human_gates or [],
        }

    write_json(
        project_root / "runtime" / "state.json",
        {
            "schema_version": "1.0.0",
            "pipeline_id": "research-to-manuscript-v1",
            "initialized_at": "2026-04-16T00:00:00+00:00",
            "current_stage": "part3",
            "stages": {
                "part1": stage("completed", True, ["intake_confirmed"]),
                "part2": stage("completed", True) if part2_completed else stage("not_started", False),
                "part3": stage("in_progress", False, ["argument_tree_selected"] if part3_gate else []),
                "part4": stage("not_started", False),
            },
            "last_failure": None,
            "repair_log": [],
            "human_decision_log": [],
        },
    )


def configure_pipeline_for_tmp(pipeline, project_root):
    pipeline.PROJECT_ROOT = project_root
    pipeline.STATE_FILE = project_root / "runtime" / "state.json"
    pipeline.PROCESS_MEMORY_DIR = project_root / "process-memory"
    schema_dir = project_root / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    for schema_name in [
        "part3_argument_tree.schema.json",
        "part3_candidate_tree.schema.json",
        "part3_candidate_comparison.schema.json",
        "part3_human_selection_feedback.schema.json",
    ]:
        shutil.copy2(PROJECT_ROOT / "schemas" / schema_name, schema_dir / schema_name)


def collect_nodes(node):
    nodes = [node]
    for child in node.get("children", []) or []:
        if isinstance(child, dict):
            nodes.extend(collect_nodes(child))
    return nodes


def snapshot_force_relock_state(project_root):
    tracked_paths = [
        "outputs/part3/human_selection_feedback.json",
        "outputs/part3/argument_tree.json",
        "runtime/state.json",
        "outputs/part4/paper_outline.json",
        "outputs/part4/outline_rationale.json",
        "outputs/part4/reference_alignment_report.json",
    ]
    files = {}
    for rel_path in tracked_paths:
        path = project_root / rel_path
        files[rel_path] = path.read_text(encoding="utf-8") if path.exists() else None
    process_memory = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted((project_root / "process-memory").glob("*.json"))
    } if (project_root / "process-memory").exists() else {}
    part4_tree = {
        str(path.relative_to(project_root / "outputs" / "part4")): path.read_text(encoding="utf-8")
        for path in sorted((project_root / "outputs" / "part4").rglob("*"))
        if path.is_file()
    } if (project_root / "outputs" / "part4").exists() else {}
    return {"files": files, "process_memory": process_memory, "part4_tree": part4_tree}


def assert_force_relock_snapshot_restored(project_root, snapshot):
    for rel_path, expected in snapshot["files"].items():
        path = project_root / rel_path
        if expected is None:
            assert not path.exists()
        else:
            assert path.exists()
            assert path.read_text(encoding="utf-8") == expected
    process_memory_dir = project_root / "process-memory"
    current_memory = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(process_memory_dir.glob("*.json"))
    } if process_memory_dir.exists() else {}
    assert current_memory == snapshot["process_memory"]
    part4_root = project_root / "outputs" / "part4"
    current_part4_tree = {
        str(path.relative_to(part4_root)): path.read_text(encoding="utf-8")
        for path in sorted(part4_root.rglob("*"))
        if path.is_file()
    } if part4_root.exists() else {}
    assert current_part4_tree == snapshot["part4_tree"]


def prepare_force_relock_project(tmp_path):
    generator = load_module(f"part3_candidate_generator_force_{id(tmp_path)}", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module(f"part3_comparison_generator_force_{id(tmp_path)}", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module(f"part3_selection_locker_force_{id(tmp_path)}", SELECTION_LOCKER_PATH)
    prepare_part3_generation_inputs(tmp_path, part3_gate=False)
    generator.generate_candidates(project_root=tmp_path, generated_at="2026-04-16T01:00:00+00:00")
    comparison_generator.generate_comparison(project_root=tmp_path, generated_at="2026-04-16T02:00:00+00:00")
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )
    for rel_path in [
        "outputs/part4/paper_outline.json",
        "outputs/part4/outline_rationale.json",
        "outputs/part4/reference_alignment_report.json",
    ]:
        write_json(tmp_path / rel_path, {"schema_version": "1.0.0", "path": rel_path})
    state = json.load(open(tmp_path / "runtime" / "state.json", encoding="utf-8"))
    state["stages"]["part4"] = {
        "status": "completed",
        "started_at": "2026-04-16T04:00:00+00:00",
        "completed_at": "2026-04-16T05:00:00+00:00",
        "gate_passed": True,
        "human_gates_completed": ["outline_confirmed"],
    }
    state["current_stage"] = "part4"
    write_json(tmp_path / "runtime" / "state.json", state)
    return selection_locker


def prepare_part3_generation_inputs(tmp_path, *, part2_completed=True, part3_gate=False):
    seed_generator = load_module(
        f"part3_argument_seed_map_generator_{id(tmp_path)}",
        SEED_MAP_GENERATOR_PATH,
    )
    build_minimal_wiki(tmp_path)
    build_minimal_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=part2_completed, part3_gate=part3_gate)
    if part2_completed:
        seed_generator.generate_seed_map(
            project_root=tmp_path,
            generated_at="2026-04-16T00:30:00+00:00",
        )


def prepare_non_current_topic_part3_generation_inputs(tmp_path):
    seed_generator = load_module(
        f"part3_argument_seed_map_generator_non_current_topic_{id(tmp_path)}",
        SEED_MAP_GENERATOR_PATH,
    )
    build_non_current_topic_wiki(tmp_path)
    build_non_current_topic_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=True)
    seed_generator.generate_seed_map(
        project_root=tmp_path,
        generated_at="2026-04-16T00:30:00+00:00",
    )


def test_seed_map_generator_writes_traceable_argument_parts(tmp_path):
    seed_generator = load_module("part3_argument_seed_map_generator", SEED_MAP_GENERATOR_PATH)
    build_minimal_wiki(tmp_path)
    build_minimal_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=True)

    seed_map = seed_generator.generate_seed_map(
        project_root=tmp_path,
        generated_at="2026-04-16T00:30:00+00:00",
    )

    seed_path = tmp_path / "outputs" / "part3" / "argument_seed_map.json"
    assert seed_path.exists()
    assert seed_map["wiki_ref"] == "research-wiki/index.json"
    assert seed_map["raw_metadata_ref"] == "raw-library/metadata.json"
    assert seed_map["research_question"]
    assert seed_map["candidate_claims"]
    assert seed_map["evidence_points"]
    assert seed_map["counterclaims"]
    assert seed_map["evidence_gaps"]
    assert seed_map["background_only_materials"]
    with open(SEED_MAP_SCHEMA_PATH, encoding="utf-8") as f:
        seed_schema = json.load(f)
    jsonschema.validate(instance=seed_map, schema=seed_schema)

    raw_source_ids = {"cnki_001", "cnki_002", "cnki_003"}
    wiki_page_ids = {"concept_current_topic_space", "method_space_syntax", "topic_foshan_case"}
    for section in [
        "candidate_claims",
        "evidence_points",
        "contradictions",
        "counterclaims",
        "method_paths",
        "case_boundaries",
        "evidence_gaps",
        "background_only_materials",
    ]:
        for item in seed_map[section]:
            assert set(item["source_ids"]) <= raw_source_ids
            assert set(item["wiki_page_ids"]) <= wiki_page_ids
            assert item["source_ids"]
            assert item["wiki_page_ids"]


def test_seed_map_and_candidates_follow_non_current_topic_topic_without_stale_current_topic(tmp_path):
    seed_generator = load_module(
        "part3_argument_seed_map_generator_non_current_topic",
        SEED_MAP_GENERATOR_PATH,
    )
    generator = load_module("part3_candidate_generator_non_current_topic", CANDIDATE_GENERATOR_PATH)
    build_non_current_topic_wiki(tmp_path)
    build_non_current_topic_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=True)

    seed_map = seed_generator.generate_seed_map(
        project_root=tmp_path,
        generated_at="2026-04-16T00:30:00+00:00",
    )
    candidates = generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )

    serialized_seed = json.dumps(seed_map, ensure_ascii=False)
    serialized_candidates = json.dumps(candidates, ensure_ascii=False)
    assert "地域建筑符号" in seed_map["research_question"] or "设计教育" in seed_map["research_question"]
    assert "庭院案例" not in serialized_candidates
    assert "固定案例模板" not in serialized_seed
    assert "固定案例模板" not in serialized_candidates
    assert any(
        "地域建筑符号" in candidate["root"]["claim"] or "设计教育" in candidate["root"]["claim"]
        for candidate in candidates
    )


def test_seed_map_generator_blocks_when_part2_gate_has_not_passed(tmp_path):
    seed_generator = load_module("part3_argument_seed_map_generator_blocked", SEED_MAP_GENERATOR_PATH)
    build_minimal_wiki(tmp_path)
    build_minimal_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=False)

    try:
        seed_generator.generate_seed_map(project_root=tmp_path)
    except RuntimeError as exc:
        assert "Part 2 gate" in str(exc)
    else:
        raise AssertionError("seed map generation must require completed Part 2 gate")


def test_candidate_generator_writes_three_candidates_without_canonical_tree(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    prepare_part3_generation_inputs(tmp_path)

    candidates = generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )

    assert [candidate["strategy"] for candidate in candidates] == [
        "theory_first",
        "problem_solution",
        "case_application",
    ]
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()

    for candidate in candidates:
        candidate_path = (
            tmp_path
            / "outputs"
            / "part3"
            / "candidate_argument_trees"
            / f"{candidate['candidate_id']}.json"
        )
        assert candidate_path.exists()
        assert candidate["schema_version"] == "1.0.0"
        assert candidate["wiki_ref"] == "research-wiki/index.json"
        assert candidate["root"]["support_source_ids"]
        assert candidate["root"]["wiki_page_ids"]
        assert "传统建筑" in candidate["root"]["claim"]
        assert "本研究对象" not in candidate["root"]["claim"]
        assert candidate.get("argument_seed_map_ref") == "outputs/part3/argument_seed_map.json"
        assert "seed_map_ref" not in candidate
        with open(CANDIDATE_SCHEMA_PATH, encoding="utf-8") as f:
            candidate_schema = json.load(f)
        jsonschema.validate(instance=candidate, schema=candidate_schema)
        for node in collect_nodes(candidate["root"]):
            assert node["warrant"]
            assert node["evidence_summary"]
            assert isinstance(node["assumptions"], list)
            assert isinstance(node["limitations"], list)
            assert 0 <= node["confidence"] <= 1
            assert isinstance(node["risk_flags"], list)


def test_candidate_generator_uses_argumentagent_when_command_is_configured(tmp_path, monkeypatch):
    generator = load_module("part3_candidate_generator_llm", CANDIDATE_GENERATOR_PATH)
    prepare_part3_generation_inputs(tmp_path)
    fake_agent = tmp_path / "fake_argumentagent.py"
    fake_agent.write_text(
        (
            "import json, sys\n"
            "request = json.load(sys.stdin)\n"
            "assert request['agent_name'] == 'argumentagent'\n"
            "assert request['task'] == 'part3_candidate_argument_design'\n"
            "assert request['skill'] == 'part3-argument-generate'\n"
            "paths = [item['path'] for item in request['inputs']]\n"
            "assert 'outputs/part3/argument_seed_map.json' in paths\n"
            "assert 'research-wiki/index.json' in paths\n"
            "def candidate(strategy):\n"
            "    return {\n"
            "        'candidate_id': 'candidate_' + strategy,\n"
            "        'strategy': strategy,\n"
            "        'root': {\n"
            "            'node_id': 'thesis_' + strategy,\n"
            "            'claim': 'LLM 设计的' + strategy + '候选论证路线。',\n"
            "            'node_type': 'thesis',\n"
            "            'support_source_ids': ['cnki_001'],\n"
            "            'wiki_page_ids': ['concept_current_topic_space'],\n"
            "            'seed_item_ids': ['claim_001'],\n"
            "            'children': []\n"
            "        }\n"
            "    }\n"
            "print(json.dumps({'artifacts': {'candidate_trees': [\n"
            "    candidate('theory_first'),\n"
            "    candidate('problem_solution'),\n"
            "    candidate('case_application'),\n"
            "]}}, ensure_ascii=False))\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("RTM_ARGUMENTAGENT_COMMAND", f"{sys.executable} {fake_agent}")
    monkeypatch.setenv("RTM_ARGUMENTAGENT_TIMEOUT", "5")

    candidates = generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )

    assert [candidate["strategy"] for candidate in candidates] == [
        "theory_first",
        "problem_solution",
        "case_application",
    ]
    assert all(candidate["root"]["claim"].startswith("LLM 设计的") for candidate in candidates)
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()
    assert (tmp_path / "outputs" / "part3" / "argumentagent_candidate_design.json").exists()
    provenance = json.load(open(tmp_path / "outputs" / "part3" / "argumentagent_provenance.json", encoding="utf-8"))
    assert provenance["agent_name"] == "argumentagent"
    assert provenance["mode"] == "llm"
    assert provenance["output_ref"] == "outputs/part3/candidate_argument_trees"
    for candidate in candidates:
        assert (
            tmp_path
            / "outputs"
            / "part3"
            / "candidate_argument_trees"
            / f"{candidate['candidate_id']}.json"
        ).exists()


def test_candidate_generator_rejects_argumentagent_candidates_without_seed_item_ids(tmp_path, monkeypatch):
    generator = load_module("part3_candidate_generator_llm_seed_required", CANDIDATE_GENERATOR_PATH)
    prepare_part3_generation_inputs(tmp_path)
    fake_agent = tmp_path / "fake_argumentagent_without_seed.py"
    fake_agent.write_text(
        (
            "import json, sys\n"
            "json.load(sys.stdin)\n"
            "def candidate(strategy):\n"
            "    return {\n"
            "        'candidate_id': 'candidate_' + strategy,\n"
            "        'strategy': strategy,\n"
            "        'root': {\n"
            "            'node_id': 'thesis_' + strategy,\n"
            "            'claim': '缺少 seed_item_ids 的候选论证路线。',\n"
            "            'node_type': 'thesis',\n"
            "            'support_source_ids': ['cnki_001'],\n"
            "            'wiki_page_ids': ['concept_current_topic_space'],\n"
            "            'children': []\n"
            "        }\n"
            "    }\n"
            "print(json.dumps({'artifacts': {'candidate_trees': [\n"
            "    candidate('theory_first'),\n"
            "    candidate('problem_solution'),\n"
            "    candidate('case_application'),\n"
            "]}}, ensure_ascii=False))\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("RTM_ARGUMENTAGENT_COMMAND", f"{sys.executable} {fake_agent}")
    monkeypatch.setenv("RTM_ARGUMENTAGENT_TIMEOUT", "5")

    try:
        generator.generate_candidates(
            project_root=tmp_path,
            generated_at="2026-04-16T01:00:00+00:00",
        )
    except RuntimeError as exc:
        assert "seed_item_ids" in str(exc)
    else:
        raise AssertionError("argumentagent candidates must cite deterministic seed_item_ids")


def test_candidate_generator_rejects_argumentagent_nodes_outside_seed_trace(tmp_path, monkeypatch):
    generator = load_module("part3_candidate_generator_llm_seed_trace", CANDIDATE_GENERATOR_PATH)
    prepare_part3_generation_inputs(tmp_path)
    fake_agent = tmp_path / "fake_argumentagent_bad_seed_trace.py"
    fake_agent.write_text(
        (
            "import json, sys\n"
            "json.load(sys.stdin)\n"
            "def candidate(strategy):\n"
            "    return {\n"
            "        'candidate_id': 'candidate_' + strategy,\n"
            "        'strategy': strategy,\n"
            "        'root': {\n"
            "            'node_id': 'thesis_' + strategy,\n"
            "            'claim': 'seed item 与来源不一致的候选论证路线。',\n"
            "            'node_type': 'thesis',\n"
            "            'support_source_ids': ['cnki_002'],\n"
            "            'wiki_page_ids': ['method_space_syntax'],\n"
            "            'seed_item_ids': ['claim_001'],\n"
            "            'children': []\n"
            "        }\n"
            "    }\n"
            "print(json.dumps({'artifacts': {'candidate_trees': [\n"
            "    candidate('theory_first'),\n"
            "    candidate('problem_solution'),\n"
            "    candidate('case_application'),\n"
            "]}}, ensure_ascii=False))\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("RTM_ARGUMENTAGENT_COMMAND", f"{sys.executable} {fake_agent}")
    monkeypatch.setenv("RTM_ARGUMENTAGENT_TIMEOUT", "5")

    try:
        generator.generate_candidates(
            project_root=tmp_path,
            generated_at="2026-04-16T01:00:00+00:00",
        )
    except RuntimeError as exc:
        assert "seed_item_ids 未覆盖" in str(exc)
    else:
        raise AssertionError("argumentagent node trace must be covered by referenced seed items")


def test_candidate_generator_requires_seed_map_by_default(tmp_path):
    generator = load_module("part3_candidate_generator_requires_seed_map", CANDIDATE_GENERATOR_PATH)
    build_minimal_wiki(tmp_path)
    build_minimal_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=True)

    try:
        generator.generate_candidates(project_root=tmp_path)
    except FileNotFoundError as exc:
        assert "part3-seed-map" in str(exc)
    else:
        raise AssertionError("candidate generation must require argument_seed_map.json by default")


def test_candidate_generator_allows_explicit_wiki_fallback(tmp_path):
    generator = load_module("part3_candidate_generator_allows_fallback", CANDIDATE_GENERATOR_PATH)
    build_minimal_wiki(tmp_path)
    build_minimal_raw_metadata(tmp_path)
    build_minimal_state(tmp_path, part2_completed=True)

    candidates = generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
        allow_wiki_fallback=True,
    )

    assert len(candidates) == 3
    assert all("argument_seed_map_ref" not in candidate for candidate in candidates)


def test_comparison_generator_summarizes_three_candidates(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )

    comparison = comparison_generator.generate_comparison(
        project_root=tmp_path,
        generated_at="2026-04-16T02:00:00+00:00",
    )

    comparison_path = tmp_path / "outputs" / "part3" / "candidate_comparison.json"
    quality_report_path = tmp_path / QUALITY_REPORT_REF
    table_path = tmp_path / SELECTION_TABLE_REF
    assert comparison_path.exists()
    assert quality_report_path.exists()
    assert table_path.exists()
    assert len(comparison["candidates"]) == 3
    assert len(comparison["candidate_tree_refs"]) == 3
    assert comparison["recommendation"]["human_decision_required"] is True
    assert comparison["quality_dimensions"] == [
        "thesis_clarity",
        "warrant_strength",
        "evidence_fit",
        "counterargument_handling",
        "outline_viability",
        "risk_level",
    ]
    with open(COMPARISON_SCHEMA_PATH, encoding="utf-8") as f:
        comparison_schema = json.load(f)
    jsonschema.validate(instance=comparison, schema=comparison_schema)
    quality_report = json.load(open(quality_report_path, encoding="utf-8"))
    assert quality_report["candidate_comparison_ref"] == "outputs/part3/candidate_comparison.json"
    assert quality_report["quality_dimensions"] == comparison["quality_dimensions"]
    assert len(quality_report["candidate_findings"]) == 3
    assert quality_report["outline_readiness"]["human_decision_required"] is True
    for item in comparison["candidates"]:
        assert item["thesis"]
        assert item["argument_nodes"]
        assert item["strengths"]
        assert item["weaknesses"]
        assert item["risks"]
        assert item["evidence_coverage"]["coverage_ratio"] > 0
        assert item["evidence_coverage"]["source_count"] > 0
        assert item["wiki_coverage"]["coverage_ratio"] > 0
        assert item["wiki_coverage"]["page_count"] > 0
        quality = item["quality"]
        assert set(comparison["quality_dimensions"]) <= set(quality)
        assert quality["risk_level"] in ("low", "medium", "high")
        for dimension in [
            "thesis_clarity",
            "warrant_strength",
            "evidence_fit",
            "counterargument_handling",
            "outline_viability",
        ]:
            assert 0 <= quality[dimension] <= 1
        for node in item["argument_nodes"]:
            assert node["node_id"]
            assert node["claim"]
            assert node["warrant"]
            assert node["evidence_summary"]
            assert node["source_count"] >= 0
            assert node["wiki_page_count"] >= 0
    table = table_path.read_text(encoding="utf-8")
    assert "## 可视化对比" in table
    assert "| 选项 | 推荐 | 候选 ID | 主线 | 分数 | 推荐理由 | 核心主张（约50字） | 论点 | 适合选择情况 | 代价 |" in table
    assert "质量信号:" not in table
    assert "证据覆盖" not in table
    assert "Wiki 覆盖" not in table
    assert "  - 边界:" not in table
    assert "candidate_problem_solution" in table
    assert "candidate_case_application" in table
    assert "candidate_theory_first" in table
    assert "推荐：" in table
    assert "备选：" in table
    assert "human_decision_required: true" in table


def test_refiner_writes_refined_candidates_without_overwriting_originals_or_canonical(tmp_path):
    generator = load_module("part3_candidate_generator_for_refine", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_for_refine", COMPARISON_GENERATOR_PATH)
    refiner = load_module("part3_argument_refiner", REFINER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )
    comparison_generator.generate_comparison(
        project_root=tmp_path,
        generated_at="2026-04-16T02:00:00+00:00",
    )
    original_dir = tmp_path / "outputs" / "part3" / "candidate_argument_trees"
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(original_dir.glob("*.json"))
    }

    refined = refiner.refine_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T02:30:00+00:00",
    )

    refined_dir = tmp_path / "outputs" / "part3" / "refined_candidate_argument_trees"
    refinement_summary_path = refined_dir / "refinement_summary.json"
    assert refined_dir.exists()
    assert len(refined) == 3
    assert len([path for path in refined_dir.glob("*.json") if path.name != "refinement_summary.json"]) == 3
    assert refinement_summary_path.exists()
    refinement_summary = json.load(open(refinement_summary_path, encoding="utf-8"))
    assert refinement_summary["argument_seed_map_ref"] == "outputs/part3/argument_seed_map.json"
    assert refinement_summary["argument_quality_report_ref"] == "outputs/part3/argument_quality_report.json"
    assert len(refinement_summary["refined_candidate_refs"]) == 3
    assert {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(original_dir.glob("*.json"))
    } == before
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()
    for candidate in refined:
        assert candidate["candidate_id"].startswith("candidate_")
        assert candidate["candidate_id"].endswith("_refined")
        assert candidate["based_on_candidate_ref"].startswith("outputs/part3/candidate_argument_trees/")
        assert candidate["argument_seed_map_ref"] == "outputs/part3/argument_seed_map.json"
        assert candidate["argument_quality_report_ref"] == "outputs/part3/argument_quality_report.json"
        assert candidate["candidate_comparison_ref"] == "outputs/part3/candidate_comparison.json"
        assert "source_candidate_ref" not in candidate
        assert "seed_map_ref" not in candidate
        assert "refined" in candidate["generation_notes"]


def test_refiner_refuses_after_human_selection_by_default(tmp_path):
    generator = load_module("part3_candidate_generator_refine_selected", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_refine_selected", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker_refine_selected", SELECTION_LOCKER_PATH)
    refiner = load_module("part3_argument_refiner_selected", REFINER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(project_root=tmp_path)
    comparison_generator.generate_comparison(project_root=tmp_path)
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
    )

    try:
        refiner.refine_candidates(project_root=tmp_path)
    except RuntimeError as exc:
        assert "human selection" in str(exc)
    else:
        raise AssertionError("refiner must refuse after human selection unless explicitly allowed")


def test_refined_candidate_id_uses_original_id_suffix(tmp_path):
    generator = load_module("part3_candidate_generator_refined_id", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_refined_id", COMPARISON_GENERATOR_PATH)
    refiner = load_module("part3_argument_refiner_id", REFINER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(project_root=tmp_path)
    comparison_generator.generate_comparison(project_root=tmp_path)

    refined = refiner.refine_candidates(project_root=tmp_path)

    refined_ids = {candidate["candidate_id"] for candidate in refined}
    assert refined_ids == {
        "candidate_theory_first_refined",
        "candidate_problem_solution_refined",
        "candidate_case_application_refined",
    }
    for candidate_id in refined_ids:
        assert (
            tmp_path
            / "outputs"
            / "part3"
            / "refined_candidate_argument_trees"
            / f"{candidate_id}.json"
        ).exists()


def test_selection_locker_can_lock_refined_candidate_after_human_selection(tmp_path):
    generator = load_module("part3_candidate_generator_refined_lock", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_refined_lock", COMPARISON_GENERATOR_PATH)
    refiner = load_module("part3_argument_refiner_lock", REFINER_PATH)
    selection_locker = load_module("part3_selection_locker_refined_lock", SELECTION_LOCKER_PATH)
    pipeline = load_module("pipeline_for_part3_refined_lock", PIPELINE_PATH)
    configure_pipeline_for_tmp(pipeline, tmp_path)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )
    comparison_generator.generate_comparison(
        project_root=tmp_path,
        generated_at="2026-04-16T02:00:00+00:00",
    )
    refined = refiner.refine_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T02:30:00+00:00",
    )
    selected_id = refined[0]["candidate_id"]
    assert selected_id.endswith("_refined")

    canonical = selection_locker.lock_selection(
        selected_id,
        "人工确认：选择 refine 后候选。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
        candidate_source="refined",
    )

    feedback = json.load(open(tmp_path / "outputs" / "part3" / "human_selection_feedback.json", encoding="utf-8"))
    assert canonical["candidate_source"] == "refined"
    assert feedback["candidate_source"] == "refined"
    assert canonical["candidate_tree_ref"] == f"outputs/part3/refined_candidate_argument_trees/{selected_id}.json"
    assert feedback["candidate_tree_ref"] == canonical["candidate_tree_ref"]
    assert canonical["root"]["claim"] != refined[0]["root"]["claim"]
    assert "Refine 补充" not in canonical["root"]["claim"]
    assert "Seed map" not in canonical["root"]["claim"]
    assert canonical["root"]["derivation_notes"]["claim_sanitized_for_public_writing"] is True
    state = json.load(open(tmp_path / "runtime" / "state.json", encoding="utf-8"))
    assert "argument_tree_selected" in state["stages"]["part3"]["human_gates_completed"]
    passed, issues = pipeline.validate_gate("part3")
    assert passed is True
    assert issues == []


def test_selection_locker_requires_notes_and_writes_schema_valid_canonical(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker", SELECTION_LOCKER_PATH)
    prepare_part3_generation_inputs(tmp_path, part3_gate=False)
    generator.generate_candidates(
        project_root=tmp_path,
        generated_at="2026-04-16T01:00:00+00:00",
    )
    comparison_generator.generate_comparison(
        project_root=tmp_path,
        generated_at="2026-04-16T02:00:00+00:00",
    )

    try:
        selection_locker.lock_selection("candidate_theory_first", "  ", project_root=tmp_path)
    except ValueError as exc:
        assert "--notes" in str(exc)
    else:
        raise AssertionError("empty notes should block canonical lock")

    canonical = selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )

    feedback_path = tmp_path / "outputs" / "part3" / "human_selection_feedback.json"
    argument_tree_path = tmp_path / "outputs" / "part3" / "argument_tree.json"
    assert feedback_path.exists()
    assert argument_tree_path.exists()

    with open(PART3_SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=canonical, schema=schema)
    with open(SELECTION_SCHEMA_PATH, encoding="utf-8") as f:
        selection_schema = json.load(f)
    feedback = json.load(open(feedback_path, encoding="utf-8"))
    jsonschema.validate(instance=feedback, schema=selection_schema)
    assert canonical["locked_at"] == "2026-04-16T03:00:00+00:00"
    assert canonical["selected_candidate_id"] == "candidate_theory_first"
    assert canonical["candidate_source"] == "original"
    assert canonical["human_selection_ref"] == "outputs/part3/human_selection_feedback.json"
    assert canonical["candidate_comparison_ref"] == "outputs/part3/candidate_comparison.json"
    assert canonical["wiki_ref"] == "research-wiki/index.json"
    assert canonical["candidate_tree_ref"] == "outputs/part3/candidate_argument_trees/candidate_theory_first.json"
    assert feedback["candidate_source"] == "original"
    state = json.load(open(tmp_path / "runtime" / "state.json", encoding="utf-8"))
    assert "argument_tree_selected" in state["stages"]["part3"]["human_gates_completed"]

    try:
        selection_locker.lock_selection(
            "candidate_problem_solution",
            "人工确认：尝试重锁定。",
            project_root=tmp_path,
        )
    except FileExistsError as exc:
        assert "--force" in str(exc)
    else:
        raise AssertionError("existing canonical lock should require force")


def test_selection_locker_does_not_write_artifacts_without_state(tmp_path):
    generator = load_module("part3_candidate_generator_no_state", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_no_state", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker_no_state", SELECTION_LOCKER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(project_root=tmp_path)
    comparison_generator.generate_comparison(project_root=tmp_path)
    (tmp_path / "runtime" / "state.json").unlink()

    try:
        selection_locker.lock_selection(
            "candidate_theory_first",
            "人工确认：理论优先结构更适合本论文。",
            project_root=tmp_path,
        )
    except FileNotFoundError as exc:
        assert "state" in str(exc)
    else:
        raise AssertionError("missing state must block selection lock")

    assert not (tmp_path / "outputs" / "part3" / "human_selection_feedback.json").exists()
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()


def test_selection_locker_does_not_write_artifacts_when_part2_gate_fails(tmp_path):
    generator = load_module("part3_candidate_generator_part2_fails", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_part2_fails", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker_part2_fails", SELECTION_LOCKER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(project_root=tmp_path)
    comparison_generator.generate_comparison(project_root=tmp_path)
    state = json.load(open(tmp_path / "runtime" / "state.json", encoding="utf-8"))
    state["stages"]["part2"] = {
        "status": "in_progress",
        "started_at": "2026-04-16T00:00:00+00:00",
        "completed_at": None,
        "gate_passed": False,
        "human_gates_completed": [],
    }
    write_json(tmp_path / "runtime" / "state.json", state)

    try:
        selection_locker.lock_selection(
            "candidate_theory_first",
            "人工确认：理论优先结构更适合本论文。",
            project_root=tmp_path,
        )
    except RuntimeError as exc:
        assert "Part 2 gate" in str(exc)
    else:
        raise AssertionError("failed Part 2 gate must block selection lock")

    assert not (tmp_path / "outputs" / "part3" / "human_selection_feedback.json").exists()
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()


def test_selection_locker_cleans_up_artifacts_when_gate_recording_fails(tmp_path, monkeypatch):
    generator = load_module("part3_candidate_generator_record_fails", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator_record_fails", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker_record_fails", SELECTION_LOCKER_PATH)
    prepare_part3_generation_inputs(tmp_path)
    generator.generate_candidates(project_root=tmp_path)
    comparison_generator.generate_comparison(project_root=tmp_path)

    def fail_record(*_args, **_kwargs):
        raise RuntimeError("simulated record failure")

    monkeypatch.setattr(selection_locker, "record_human_gate", fail_record)

    try:
        selection_locker.lock_selection(
            "candidate_theory_first",
            "人工确认：理论优先结构更适合本论文。",
            project_root=tmp_path,
        )
    except RuntimeError as exc:
        assert "simulated record failure" in str(exc)
    else:
        raise AssertionError("record_human_gate failure must abort selection lock")

    assert not (tmp_path / "outputs" / "part3" / "human_selection_feedback.json").exists()
    assert not (tmp_path / "outputs" / "part3" / "argument_tree.json").exists()


def test_part3_gate_blocks_when_previous_stage_is_not_completed(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker", SELECTION_LOCKER_PATH)
    pipeline = load_module("pipeline_for_part3_previous_stage", PIPELINE_PATH)
    configure_pipeline_for_tmp(pipeline, tmp_path)

    prepare_part3_generation_inputs(tmp_path, part3_gate=True)
    generator.generate_candidates(project_root=tmp_path, generated_at="2026-04-16T01:00:00+00:00")
    comparison_generator.generate_comparison(project_root=tmp_path, generated_at="2026-04-16T02:00:00+00:00")
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )
    build_minimal_state(tmp_path, part2_completed=False, part3_gate=True)

    passed, issues = pipeline.validate_gate("part3")

    assert passed is False
    assert any("前序阶段未完成或 gate 未通过: part2" in issue for issue in issues)


def test_part3_gate_rejects_unknown_wiki_and_source_refs(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker", SELECTION_LOCKER_PATH)
    pipeline = load_module("pipeline_for_part3_ref_check", PIPELINE_PATH)
    configure_pipeline_for_tmp(pipeline, tmp_path)

    prepare_part3_generation_inputs(tmp_path, part3_gate=True)
    generator.generate_candidates(project_root=tmp_path, generated_at="2026-04-16T01:00:00+00:00")
    comparison_generator.generate_comparison(project_root=tmp_path, generated_at="2026-04-16T02:00:00+00:00")
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )
    argument_tree_path = tmp_path / "outputs" / "part3" / "argument_tree.json"
    argument_tree = json.load(open(argument_tree_path, encoding="utf-8"))
    argument_tree["root"]["support_source_ids"] = ["missing_source"]
    argument_tree["root"]["wiki_page_ids"] = ["missing_page"]
    write_json(argument_tree_path, argument_tree)

    passed, issues = pipeline.validate_gate("part3")

    assert passed is False
    assert any("argument_tree.json 引用了 wiki 中不存在的 source_id" in issue for issue in issues)
    assert any("argument_tree.json 引用了 raw-library 中不存在的 source_id" in issue for issue in issues)
    assert any("argument_tree.json 引用了不存在的 wiki page_id" in issue for issue in issues)


def test_part3_gate_passes_with_valid_artifacts(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker", SELECTION_LOCKER_PATH)
    pipeline = load_module("pipeline_for_part3_happy_path", PIPELINE_PATH)
    configure_pipeline_for_tmp(pipeline, tmp_path)

    prepare_part3_generation_inputs(tmp_path, part3_gate=False)
    generator.generate_candidates(project_root=tmp_path, generated_at="2026-04-16T01:00:00+00:00")
    comparison_generator.generate_comparison(project_root=tmp_path, generated_at="2026-04-16T02:00:00+00:00")
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )

    passed, issues = pipeline.validate_gate("part3")

    assert passed is True
    assert issues == []


def test_part3_force_relock_invalidates_existing_part4_artifacts(tmp_path):
    selection_locker = prepare_force_relock_project(tmp_path)

    selection_locker.lock_selection(
        "candidate_problem_solution",
        "人工确认：改选问题-解决结构。",
        project_root=tmp_path,
        selected_at="2026-04-16T06:00:00+00:00",
        force=True,
    )

    for rel_path in [
        "outputs/part4/paper_outline.json",
        "outputs/part4/outline_rationale.json",
        "outputs/part4/reference_alignment_report.json",
    ]:
        assert not (tmp_path / rel_path).exists()
    backup_dirs = list((tmp_path / "outputs" / "part4").glob("invalidated_by_part3_relock_*"))
    assert backup_dirs
    state = json.load(open(tmp_path / "runtime" / "state.json", encoding="utf-8"))
    assert "outline_confirmed" not in state["stages"]["part4"]["human_gates_completed"]
    assert state["stages"]["part4"]["gate_passed"] is False
    assert state["current_stage"] == "part3"
    assert list((tmp_path / "process-memory").glob("*part4_invalidated.json"))


def test_force_relock_restores_part3_part4_state_when_gate_recording_fails(tmp_path, monkeypatch):
    selection_locker = prepare_force_relock_project(tmp_path)
    snapshot = snapshot_force_relock_state(tmp_path)

    def fail_record(*_args, **_kwargs):
        raise RuntimeError("simulated force record failure")

    monkeypatch.setattr(selection_locker, "record_human_gate", fail_record)

    try:
        selection_locker.lock_selection(
            "candidate_problem_solution",
            "人工确认：改选问题-解决结构。",
            project_root=tmp_path,
            selected_at="2026-04-16T06:00:00+00:00",
            force=True,
        )
    except RuntimeError as exc:
        assert "simulated force record failure" in str(exc)
    else:
        raise AssertionError("force relock must fail when record_human_gate fails")

    assert_force_relock_snapshot_restored(tmp_path, snapshot)
    assert not list((tmp_path / "process-memory").glob("*part4_invalidated.json"))


def test_force_relock_restores_part3_part4_state_when_invalidation_fails(tmp_path, monkeypatch):
    selection_locker = prepare_force_relock_project(tmp_path)
    snapshot = snapshot_force_relock_state(tmp_path)

    def fail_invalidation(project_root, invalidated_at):
        write_json(
            project_root / "process-memory" / "99999999_part4_invalidated.json",
            {
                "event": "part4_invalidated",
                "timestamp": invalidated_at,
                "stage_id": "part4",
                "reason": "simulated misleading invalidation",
            },
        )
        for rel_path in [
            "outputs/part4/paper_outline.json",
            "outputs/part4/outline_rationale.json",
            "outputs/part4/reference_alignment_report.json",
        ]:
            path = project_root / rel_path
            if path.exists():
                path.unlink()
        state = json.load(open(project_root / "runtime" / "state.json", encoding="utf-8"))
        state["stages"]["part4"]["gate_passed"] = False
        write_json(project_root / "runtime" / "state.json", state)
        raise RuntimeError("simulated invalidation failure")

    monkeypatch.setattr(selection_locker, "invalidate_part4_after_part3_relock", fail_invalidation)

    try:
        selection_locker.lock_selection(
            "candidate_problem_solution",
            "人工确认：改选问题-解决结构。",
            project_root=tmp_path,
            selected_at="2026-04-16T06:00:00+00:00",
            force=True,
        )
    except RuntimeError as exc:
        assert "simulated invalidation failure" in str(exc)
    else:
        raise AssertionError("force relock must fail when Part 4 invalidation fails")

    assert_force_relock_snapshot_restored(tmp_path, snapshot)
    assert not (tmp_path / "process-memory" / "99999999_part4_invalidated.json").exists()


def test_part3_gate_rejects_source_refs_missing_from_raw_metadata(tmp_path):
    generator = load_module("part3_candidate_generator", CANDIDATE_GENERATOR_PATH)
    comparison_generator = load_module("part3_comparison_generator", COMPARISON_GENERATOR_PATH)
    selection_locker = load_module("part3_selection_locker", SELECTION_LOCKER_PATH)
    pipeline = load_module("pipeline_for_part3_empty_raw_metadata", PIPELINE_PATH)
    configure_pipeline_for_tmp(pipeline, tmp_path)

    prepare_part3_generation_inputs(tmp_path, part3_gate=False)
    generator.generate_candidates(project_root=tmp_path, generated_at="2026-04-16T01:00:00+00:00")
    comparison_generator.generate_comparison(project_root=tmp_path, generated_at="2026-04-16T02:00:00+00:00")
    selection_locker.lock_selection(
        "candidate_theory_first",
        "人工确认：理论优先结构更适合本论文。",
        project_root=tmp_path,
        selected_at="2026-04-16T03:00:00+00:00",
    )

    metadata_path = tmp_path / "raw-library" / "metadata.json"
    metadata = json.load(open(metadata_path, encoding="utf-8"))
    metadata["sources"] = []
    metadata["summary"] = {"total_accepted": 0, "total_excluded": 0}
    write_json(metadata_path, metadata)

    passed, issues = pipeline.validate_gate("part3")

    assert passed is False
    assert any("raw-library 中不存在的 source_id" in issue for issue in issues)
