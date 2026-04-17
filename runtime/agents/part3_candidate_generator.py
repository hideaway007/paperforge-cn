#!/usr/bin/env python3
"""
runtime/agents/part3_candidate_generator.py

Deterministic MVP generator for Part 3 candidate argument trees.

用法：
  python3 runtime/agents/part3_candidate_generator.py
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402

SCHEMA_VERSION = "1.0.0"
WIKI_REF = "research-wiki/index.json"
CANDIDATE_DIR = "outputs/part3/candidate_argument_trees"
ARGUMENT_SEED_MAP_REF = "outputs/part3/argument_seed_map.json"
ARGUMENTAGENT_DESIGN_REF = "outputs/part3/argumentagent_candidate_design.json"
ARGUMENTAGENT_PROVENANCE_REF = "outputs/part3/argumentagent_provenance.json"
STRATEGIES = ("theory_first", "problem_solution", "case_application")
STATE_REF = "runtime/state.json"
SEED_TRACE_SECTIONS = (
    "candidate_claims",
    "evidence_points",
    "contradictions",
    "counterclaims",
    "method_paths",
    "case_boundaries",
    "evidence_gaps",
    "background_only_materials",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def assert_part2_gate_passed(project_root: Path) -> None:
    state_path = project_root / STATE_REF
    if not state_path.exists():
        raise FileNotFoundError(f"缺少 state 文件: {STATE_REF}；不能在无状态审计下启动 Part 3")
    state = load_json(state_path)
    part2 = state.get("stages", {}).get("part2", {})
    if part2.get("status") != "completed" or part2.get("gate_passed") is not True:
        raise RuntimeError("Part 2 gate 尚未通过，不能生成 Part 3 candidate argument trees")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_project_json(project_root: Path, rel_path: str, data: dict[str, Any]) -> None:
    write_json(project_root / rel_path, data)


def resolve_page_path(project_root: Path, file_path: str) -> Path:
    raw = Path(file_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([
            project_root / raw,
            project_root / "research-wiki" / raw,
            project_root / "research-wiki" / "pages" / raw.name,
        ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Wiki page file not found for file_path={file_path!r}")


def load_wiki_pages(project_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index_path = project_root / WIKI_REF
    if not index_path.exists():
        raise FileNotFoundError(f"缺少 Part 2 canonical wiki index: {WIKI_REF}")

    wiki_index = load_json(index_path)
    pages = wiki_index.get("pages", [])
    if not isinstance(pages, list) or not pages:
        raise ValueError("research-wiki/index.json pages must be a non-empty array")

    enriched_pages: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Each wiki page index entry must be an object")
        page_id = page.get("page_id")
        file_path = page.get("file_path")
        source_ids = page.get("source_ids")
        if not page_id or not file_path:
            raise ValueError("Each wiki page must include page_id and file_path")
        if not isinstance(source_ids, list) or not source_ids:
            raise ValueError(f"Wiki page {page_id} must preserve at least one source_id")

        resolved_path = resolve_page_path(project_root, file_path)
        content = resolved_path.read_text(encoding="utf-8")
        enriched_pages.append({
            **page,
            "content": content,
            "resolved_file_path": str(resolved_path),
        })

    return wiki_index, sorted(enriched_pages, key=lambda item: item.get("page_id", ""))


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def page_trace_sets(pages: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    source_trace: set[str] = set()
    page_trace: set[str] = set()
    for page in pages:
        page_id = page.get("page_id")
        if isinstance(page_id, str):
            page_trace.add(page_id)
        for source_id in page.get("source_ids", []) or []:
            if isinstance(source_id, str):
                source_trace.add(source_id)
    return source_trace, page_trace


def llm_candidate_payload(result: Any) -> list[dict[str, Any]] | None:
    containers = [result.artifacts, result.payload, result.raw]
    for container in containers:
        if isinstance(container, list):
            raw_candidates = container
        elif isinstance(container, dict):
            raw_candidates = (
                container.get("candidate_trees")
                or container.get("candidates")
                or container.get("argument_trees")
            )
        else:
            raw_candidates = None
        if isinstance(raw_candidates, list):
            candidates = [candidate for candidate in raw_candidates if isinstance(candidate, dict)]
            if len(candidates) == len(raw_candidates):
                return candidates
    return None


def seed_item_index(seed_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for section in SEED_TRACE_SECTIONS:
        for item in seed_items(seed_map, section):
            item_id = item.get("item_id")
            if isinstance(item_id, str) and item_id.strip():
                index[item_id] = item
    return index


def validate_llm_node_trace(
    node: dict[str, Any],
    *,
    source_trace: set[str],
    page_trace: set[str],
    seed_trace: dict[str, dict[str, Any]],
    path: str,
) -> None:
    if not isinstance(node.get("node_id"), str) or not node["node_id"].strip():
        raise RuntimeError(f"argumentagent candidate node 缺少 node_id: {path}")
    if not isinstance(node.get("claim"), str) or not node["claim"].strip():
        raise RuntimeError(f"argumentagent candidate node 缺少 claim: {path}")
    if not isinstance(node.get("node_type"), str) or not node["node_type"].strip():
        raise RuntimeError(f"argumentagent candidate node 缺少 node_type: {path}")

    support_source_ids = [
        source_id for source_id in node.get("support_source_ids", []) or []
        if isinstance(source_id, str) and source_id
    ]
    wiki_page_ids = [
        page_id for page_id in node.get("wiki_page_ids", []) or []
        if isinstance(page_id, str) and page_id
    ]
    if not support_source_ids:
        raise RuntimeError(f"argumentagent candidate node 缺少 support_source_ids: {path}")
    if not wiki_page_ids:
        raise RuntimeError(f"argumentagent candidate node 缺少 wiki_page_ids: {path}")

    unknown_sources = sorted(set(support_source_ids) - source_trace)
    unknown_pages = sorted(set(wiki_page_ids) - page_trace)
    if unknown_sources:
        raise RuntimeError(f"argumentagent candidate node 引用了未知 source_ids {unknown_sources}: {path}")
    if unknown_pages:
        raise RuntimeError(f"argumentagent candidate node 引用了未知 wiki_page_ids {unknown_pages}: {path}")

    seed_item_ids = [
        item_id for item_id in node.get("seed_item_ids", []) or []
        if isinstance(item_id, str) and item_id
    ]
    if not seed_item_ids:
        raise RuntimeError(f"argumentagent candidate node 缺少 seed_item_ids，无法证明来自 deterministic seed map: {path}")
    unknown_seed_items = sorted(set(seed_item_ids) - set(seed_trace))
    if unknown_seed_items:
        raise RuntimeError(f"argumentagent candidate node 引用了未知 seed_item_ids {unknown_seed_items}: {path}")

    allowed_sources: set[str] = set()
    allowed_pages: set[str] = set()
    for seed_item_id in seed_item_ids:
        seed_item = seed_trace[seed_item_id]
        allowed_sources.update(
            source_id
            for source_id in seed_item.get("source_ids", []) or []
            if isinstance(source_id, str)
        )
        allowed_pages.update(
            page_id
            for page_id in seed_item.get("wiki_page_ids", []) or []
            if isinstance(page_id, str)
        )
    outside_seed_sources = sorted(set(support_source_ids) - allowed_sources)
    outside_seed_pages = sorted(set(wiki_page_ids) - allowed_pages)
    if outside_seed_sources:
        raise RuntimeError(f"argumentagent candidate node 使用了 seed_item_ids 未覆盖的 source_ids {outside_seed_sources}: {path}")
    if outside_seed_pages:
        raise RuntimeError(f"argumentagent candidate node 使用了 seed_item_ids 未覆盖的 wiki_page_ids {outside_seed_pages}: {path}")

    for index, child in enumerate(node.get("children", []) or []):
        if not isinstance(child, dict):
            raise RuntimeError(f"argumentagent candidate node.children 必须是 object: {path}.{index}")
        validate_llm_node_trace(
            child,
            source_trace=source_trace,
            page_trace=page_trace,
            seed_trace=seed_trace,
            path=f"{path}.children[{index}]",
        )


def normalize_llm_candidates(
    raw_candidates: list[dict[str, Any]],
    *,
    pages: list[dict[str, Any]],
    seed_map: dict[str, Any],
    generated_at: str,
) -> list[dict[str, Any]]:
    if len(raw_candidates) != len(STRATEGIES):
        raise RuntimeError("argumentagent 必须返回 3 份候选 argument tree")

    by_strategy: dict[str, dict[str, Any]] = {}
    for candidate in raw_candidates:
        strategy = candidate.get("strategy")
        if strategy not in STRATEGIES:
            raise RuntimeError(f"argumentagent candidate strategy 非法: {strategy}")
        if strategy in by_strategy:
            raise RuntimeError(f"argumentagent candidate strategy 重复: {strategy}")
        by_strategy[strategy] = candidate
    if set(by_strategy) != set(STRATEGIES):
        raise RuntimeError("argumentagent candidate strategy 不完整")

    source_trace, page_trace = page_trace_sets(pages)
    seed_trace = seed_item_index(seed_map)
    if not seed_trace:
        raise RuntimeError("argumentagent 需要非空 argument_seed_map seed items")
    normalized: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        candidate = {**by_strategy[strategy]}
        candidate_id = f"candidate_{strategy}"
        if candidate.get("candidate_id") not in (None, candidate_id):
            raise RuntimeError(f"argumentagent candidate_id 与 strategy 不一致: {candidate.get('candidate_id')}")
        root = candidate.get("root")
        if not isinstance(root, dict):
            raise RuntimeError(f"argumentagent candidate 缺少 root: {candidate_id}")
        validate_llm_node_trace(
            root,
            source_trace=source_trace,
            page_trace=page_trace,
            seed_trace=seed_trace,
            path=f"{candidate_id}.root",
        )
        candidate.update({
            "schema_version": candidate.get("schema_version") or SCHEMA_VERSION,
            "candidate_id": candidate_id,
            "generated_at": candidate.get("generated_at") or generated_at,
            "strategy": strategy,
            "wiki_ref": candidate.get("wiki_ref") or WIKI_REF,
            "argument_seed_map_ref": candidate.get("argument_seed_map_ref") or ARGUMENT_SEED_MAP_REF,
            "root": root,
        })
        if candidate["wiki_ref"] != WIKI_REF:
            raise RuntimeError(f"argumentagent candidate wiki_ref 必须为 {WIKI_REF}")
        if candidate["argument_seed_map_ref"] != ARGUMENT_SEED_MAP_REF:
            raise RuntimeError(f"argumentagent candidate argument_seed_map_ref 必须为 {ARGUMENT_SEED_MAP_REF}")
        normalized.append(candidate)
    return normalized


def generate_candidates_with_argumentagent(
    project_root: Path,
    *,
    pages: list[dict[str, Any]],
    seed_map: dict[str, Any],
    generated_at: str,
) -> list[dict[str, Any]] | None:
    result = request_llm_agent(
        project_root,
        agent_name="argumentagent",
        task="part3_candidate_argument_design",
        skill="part3-argument-generate",
        output_ref=CANDIDATE_DIR,
        input_paths=[
            WIKI_REF,
            ARGUMENT_SEED_MAP_REF,
            "raw-library/metadata.json",
            "writing-policy/source_index.json",
        ],
        instructions=[
            "Read the existing deterministic argument_seed_map.json and design exactly three candidate argument trees.",
            "Return JSON with artifacts.candidate_trees as an array of candidate_theory_first, candidate_problem_solution, and candidate_case_application.",
            "Do not generate, rewrite, repair, or own argument_seed_map.json.",
            "Do not write canonical outputs/part3/argument_tree.json or human_selection_feedback.json.",
            "Every node must include support_source_ids and wiki_page_ids traceable to research-wiki/index.json.",
            "Every node must include seed_item_ids that reference existing argument_seed_map.json item_id values.",
            "A node's support_source_ids and wiki_page_ids must be covered by its referenced seed_item_ids.",
        ],
    )
    if result is None:
        return None

    raw_candidates = llm_candidate_payload(result)
    if raw_candidates is None:
        raise RuntimeError("argumentagent command 输出缺少 artifacts.candidate_trees")
    candidates = normalize_llm_candidates(
        raw_candidates,
        pages=pages,
        seed_map=seed_map,
        generated_at=generated_at,
    )
    write_project_json(project_root, ARGUMENTAGENT_DESIGN_REF, result.raw)
    write_llm_agent_provenance(
        project_root,
        ARGUMENTAGENT_PROVENANCE_REF,
        agent_name="argumentagent",
        task="part3_candidate_argument_design",
        skill="part3-argument-generate",
        output_ref=CANDIDATE_DIR,
        mode="llm",
    )
    return candidates


def flatten_sources(pages: list[dict[str, Any]]) -> list[str]:
    return unique_strings([
        source_id
        for page in pages
        for source_id in page.get("source_ids", [])
        if isinstance(source_id, str)
    ])


def group_pages(pages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "concept": [],
        "topic": [],
        "method": [],
        "contradiction": [],
        "evidence_aggregation": [],
        "case": [],
    }
    for page in pages:
        page_type = page.get("page_type", "")
        title = page.get("title", "")
        tags = " ".join(page.get("tags", [])) if isinstance(page.get("tags"), list) else ""
        text = f"{page.get('page_id', '')} {title} {tags} {page.get('content', '')}"
        if page_type in groups:
            groups[page_type].append(page)
        if any(term in text for term in ("案例", "个案", "课程", "创作", "实践", "应用", "博物馆")):
            groups["case"].append(page)
    groups["case"] = sorted({page["page_id"]: page for page in groups["case"]}.values(), key=lambda item: item["page_id"])
    return groups


def page_ids(pages: list[dict[str, Any]]) -> list[str]:
    return unique_strings([page.get("page_id", "") for page in pages])


def source_ids(pages: list[dict[str, Any]]) -> list[str]:
    return flatten_sources(pages)


def titles(pages: list[dict[str, Any]], fallback: str) -> str:
    selected = [page.get("title", page.get("page_id", "")) for page in pages[:3]]
    return "、".join([title for title in selected if title]) or fallback


def page_haystack(pages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for page in pages:
        parts.extend([
            str(page.get("title", "")),
            str(page.get("page_id", "")),
            str(page.get("content", "")),
        ])
        tags = page.get("tags", [])
        if isinstance(tags, list):
            parts.extend(str(tag) for tag in tags)
    return " ".join(parts)


def clean_topic_title(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value)
    cleaned = cleaned.replace("SourceEvidenceDigest", "")
    cleaned = cleaned.replace("Part2ResearchSynthesis", "")
    cleaned = cleaned.replace("Part2EvidenceSynthesis", "")
    cleaned = cleaned.strip(" :：-—")
    pieces = [piece.strip(" :：-—") for piece in re.split(r"[:：]", cleaned) if piece.strip(" :：-—")]
    if pieces:
        cleaned = pieces[-1]
    cleaned = re.sub(r"^《[^》]+》", "", cleaned).strip(" :：-—")
    return cleaned[:36]


def thesis_subject(pages: list[dict[str, Any]]) -> str:
    tagged_terms: list[str] = []
    for page in pages:
        tags = page.get("tags", [])
        if isinstance(tags, list):
            tagged_terms.extend(str(tag).strip() for tag in tags if str(tag).strip())
    hits = unique_strings(tagged_terms)
    if hits:
        return "、".join(hits[:3])

    for page in pages:
        title = clean_topic_title(str(page.get("title", "")))
        if title and title not in {"跨来源研究锚点"}:
            return title
    return "本研究对象"


def make_node(
    node_id: str,
    claim: str,
    node_type: str,
    pages: list[dict[str, Any]],
    children: list[dict[str, Any]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    source_refs = source_ids(pages)
    wiki_refs = page_ids(pages)
    node = {
        "node_id": node_id,
        "claim": claim,
        "node_type": node_type,
        "support_source_ids": source_refs,
        "wiki_page_ids": wiki_refs,
        "warrant": f"该节点的推理必须由 {len(wiki_refs)} 个 wiki 页面和 {len(source_refs)} 个 source_id 回溯支撑。",
        "evidence_summary": titles(pages, "相关 wiki 证据"),
        "assumptions": ["wiki 页面已经通过 Part 2 gate，且 source_id 可回溯到 raw-library/metadata.json"],
        "limitations": ["该节点不能扩展到未进入 Part 2 wiki 的材料"],
        "confidence": 0.72 if node_type != "evidence" else 0.78,
        "risk_flags": [],
    }
    if children:
        node["children"] = children
    if notes:
        node["notes"] = notes
    return node


def quality_fields_for_root(pages: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    strategy_limits = {
        "theory_first": "理论优先结构需要防止背景综述过重。",
        "problem_solution": "问题-解决结构需要防止把材料后置包装为单一问题。",
        "case_application": "案例应用结构需要防止由单一案例过度外推。",
    }
    return {
        "warrant": "根论点由 Part 2 wiki 的概念、方法、主题与证据聚合页面共同支撑。",
        "evidence_summary": titles(pages, "Part 2 Research Wiki"),
        "assumptions": ["Part 2 wiki 的来源映射完整", "候选树仍需人工选择后才能成为 canonical"],
        "limitations": [strategy_limits.get(strategy, "需要人工确认论证路径与论文目标匹配。")],
        "confidence": 0.74,
        "risk_flags": [f"strategy:{strategy}", "requires_human_selection"],
    }


def load_argument_seed_map(
    project_root: Path,
    pages: list[dict[str, Any]],
    *,
    allow_wiki_fallback: bool = False,
) -> dict[str, Any] | None:
    seed_path = project_root / ARGUMENT_SEED_MAP_REF
    if not seed_path.exists():
        if allow_wiki_fallback:
            return None
        raise FileNotFoundError(
            f"缺少 {ARGUMENT_SEED_MAP_REF}；请先运行 `python3 cli.py part3-seed-map`，"
            "或显式传入 --allow-wiki-fallback 使用保守 wiki fallback。"
        )
    seed_map = load_json(seed_path)
    if seed_map.get("wiki_ref") != WIKI_REF:
        raise ValueError(f"{ARGUMENT_SEED_MAP_REF} wiki_ref 必须指向 {WIKI_REF}")
    wiki_source_ids = set(source_ids(pages))
    wiki_page_ids = set(page_ids(pages))
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
        for item in seed_items(seed_map, section):
            item_id = item.get("item_id", "unknown")
            unknown_sources = set(item.get("source_ids", []) or []) - wiki_source_ids
            unknown_pages = set(item.get("wiki_page_ids", []) or []) - wiki_page_ids
            if unknown_sources:
                raise ValueError(f"{ARGUMENT_SEED_MAP_REF} {section}.{item_id} 引用了 wiki 中不存在的 source_id: {sorted(unknown_sources)}")
            if unknown_pages:
                raise ValueError(f"{ARGUMENT_SEED_MAP_REF} {section}.{item_id} 引用了不存在的 wiki page_id: {sorted(unknown_pages)}")
    return seed_map


def load_seed_map_optional(project_root: Path, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    seed_path = project_root / ARGUMENT_SEED_MAP_REF
    if not seed_path.exists():
        return None
    seed_map = load_json(seed_path)
    if seed_map.get("wiki_ref") != WIKI_REF:
        raise ValueError(f"{ARGUMENT_SEED_MAP_REF} wiki_ref 必须指向 {WIKI_REF}")
    wiki_source_ids = set(source_ids(pages))
    wiki_page_ids = set(page_ids(pages))
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
        for item in seed_items(seed_map, section):
            item_id = item.get("item_id", "unknown")
            unknown_sources = set(item.get("source_ids", []) or []) - wiki_source_ids
            unknown_pages = set(item.get("wiki_page_ids", []) or []) - wiki_page_ids
            if unknown_sources:
                raise ValueError(f"{ARGUMENT_SEED_MAP_REF} {section}.{item_id} 引用了 wiki 中不存在的 source_id: {sorted(unknown_sources)}")
            if unknown_pages:
                raise ValueError(f"{ARGUMENT_SEED_MAP_REF} {section}.{item_id} 引用了不存在的 wiki page_id: {sorted(unknown_pages)}")
    return seed_map


def seed_items(seed_map: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(seed_map, dict):
        return []
    return [
        item
        for item in seed_map.get(key, []) or []
        if isinstance(item, dict)
    ]


def seed_ref_node(
    node_id: str,
    node_type: str,
    seed_item: dict[str, Any],
    claim_prefix: str,
) -> dict[str, Any]:
    source_refs = [
        value
        for value in seed_item.get("source_ids", [])
        if isinstance(value, str)
    ]
    page_refs = [
        value
        for value in seed_item.get("wiki_page_ids", [])
        if isinstance(value, str)
    ]
    return {
        "node_id": node_id,
        "claim": f"{claim_prefix}{seed_item.get('text', '')}",
        "node_type": node_type,
        "support_source_ids": source_refs,
        "wiki_page_ids": page_refs,
        "seed_item_ids": [seed_item.get("item_id")] if isinstance(seed_item.get("item_id"), str) else [],
        "warrant": "该节点直接来自 argument_seed_map.json 的可追溯论证零件。",
        "evidence_summary": seed_item.get("text", ""),
        "assumptions": ["seed map 的 source_ids 已经由 raw-library/metadata.json 校验"],
        "limitations": ["不能使用 seed map 之外的材料扩展该节点"],
        "confidence": float(seed_item.get("confidence", 0.68) or 0.68),
        "risk_flags": ["seed_map_derived"],
    }


def counterargument_for_strategy(strategy: str, seed_map: dict[str, Any] | None) -> dict[str, Any] | None:
    counterclaims = seed_items(seed_map, "counterclaims")
    boundaries = seed_items(seed_map, "case_boundaries")
    gaps = seed_items(seed_map, "evidence_gaps")
    candidates = {
        "theory_first": gaps or counterclaims or boundaries,
        "problem_solution": counterclaims or gaps or boundaries,
        "case_application": boundaries or counterclaims or gaps,
    }.get(strategy, counterclaims)
    if not candidates:
        return None
    prefix = {
        "theory_first": "反方限制：理论框架不能替代证据链；",
        "problem_solution": "反方限制：问题意识不能后置包装材料；",
        "case_application": "反方限制：案例不能被过度外推；",
    }.get(strategy, "反方限制：")
    return seed_ref_node("counter_001", "counterargument", candidates[0], prefix)


def apply_seed_map(root: dict[str, Any], strategy: str, seed_map: dict[str, Any] | None) -> dict[str, Any]:
    if not seed_map:
        return root
    claims = seed_items(seed_map, "candidate_claims")
    strategy_claim = {
        "theory_first": claims[0] if len(claims) >= 1 else None,
        "problem_solution": claims[1] if len(claims) >= 2 else (claims[0] if claims else None),
        "case_application": claims[-1] if claims else None,
    }.get(strategy)
    children = list(root.get("children", []) or [])
    counter_node = counterargument_for_strategy(strategy, seed_map)
    if counter_node:
        children.append(counter_node)
    updated_root = {
        **root,
        "children": children,
        "risk_flags": unique_strings(list(root.get("risk_flags", [])) + ["seed_map_used"]),
    }
    if strategy_claim:
        updated_root["claim"] = f"{root.get('claim', '')} Seed map 侧重：{strategy_claim.get('text', '')}"
        updated_root["seed_item_ids"] = unique_strings(
            list(root.get("seed_item_ids", [])) + [strategy_claim.get("item_id", "")]
        )
        updated_root["support_source_ids"] = unique_strings(
            list(root.get("support_source_ids", [])) + list(strategy_claim.get("source_ids", []))
        )
        updated_root["wiki_page_ids"] = unique_strings(
            list(root.get("wiki_page_ids", [])) + list(strategy_claim.get("wiki_page_ids", []))
        )
    return updated_root


def evidence_node(node_id: str, pages: list[dict[str, Any]], focus: str) -> dict[str, Any]:
    return make_node(
        node_id=node_id,
        claim=f"证据层显示，{titles(pages, focus)}可以支撑“{focus}”这一判断。",
        node_type="evidence",
        pages=pages,
    )


def build_theory_first(pages: list[dict[str, Any]]) -> dict[str, Any]:
    groups = group_pages(pages)
    subject = thesis_subject(pages)
    concept_pages = groups["concept"] or pages[:2]
    method_pages = groups["method"] or groups["topic"] or pages[:2]
    topic_pages = groups["topic"] or pages[-2:]
    all_sources = flatten_sources(pages)
    all_page_ids = page_ids(pages)

    root_children = [
        make_node(
            "arg_001",
            f"首先需要以{titles(concept_pages, '核心概念')}界定论文的理论边界，避免把地域文化表征直接等同于空间机制。",
            "main_argument",
            concept_pages,
            [evidence_node("evidence_001_1", concept_pages, "理论边界需要由可回溯的概念页支撑")],
        ),
        make_node(
            "arg_002",
            f"其次应通过{titles(method_pages, '方法与结构分析')}解释{subject}从材料描述走向论证分析的路径。",
            "main_argument",
            method_pages,
            [evidence_node("evidence_002_1", method_pages, "方法页承担从材料到分析框架的转换")],
        ),
        make_node(
            "arg_003",
            f"最后将{titles(topic_pages, '主题证据')}转化为当代中文论文中的章节论证线索。",
            "main_argument",
            topic_pages,
            [evidence_node("evidence_003_1", topic_pages, "主题页提供论文主线的应用场景")],
        ),
    ]
    return {
        "node_id": "thesis_001",
        "claim": f"本文主张：应先建立{subject}的理论框架，再讨论其转化机制与应用路径。",
        "node_type": "thesis",
        "support_source_ids": all_sources,
        "wiki_page_ids": all_page_ids,
        "children": root_children,
        **quality_fields_for_root(pages, "theory_first"),
        "notes": "策略：theory_first。适合需要先稳固概念边界与理论定义的中文学术论文。",
    }


def build_problem_solution(pages: list[dict[str, Any]]) -> dict[str, Any]:
    groups = group_pages(pages)
    subject = thesis_subject(pages)
    contradiction_pages = groups["contradiction"] or groups["topic"] or pages[:2]
    concept_pages = groups["concept"] or pages[:2]
    method_pages = groups["method"] or groups["evidence_aggregation"] or pages[-2:]
    all_sources = flatten_sources(pages)
    all_page_ids = page_ids(pages)

    root_children = [
        make_node(
            "arg_001",
            f"现有讨论的主要问题在于{titles(contradiction_pages, '研究问题')}尚未被组织成清晰的论文矛盾。",
            "main_argument",
            contradiction_pages,
            [evidence_node("evidence_001_1", contradiction_pages, "问题诊断必须来自 wiki 中已有的主题或矛盾页")],
        ),
        make_node(
            "arg_002",
            f"解决路径应回到{titles(concept_pages, '核心概念')}，把对象、元素与应用机制拆分为可论证的层级。",
            "main_argument",
            concept_pages,
            [evidence_node("evidence_002_1", concept_pages, "概念页用于拆解问题而不是堆叠背景")],
        ),
        make_node(
            "arg_003",
            f"最终通过{titles(method_pages, '方法证据')}形成从问题诊断到设计启示的闭环。",
            "main_argument",
            method_pages,
            [evidence_node("evidence_003_1", method_pages, "方法或证据聚合页用于完成解决方案闭环")],
        ),
    ]
    return {
        "node_id": "thesis_001",
        "claim": f"本文主张：{subject}研究应从问题诊断出发，经过概念拆解与方法验证，形成可用于论文写作的解决路径。",
        "node_type": "thesis",
        "support_source_ids": all_sources,
        "wiki_page_ids": all_page_ids,
        "children": root_children,
        **quality_fields_for_root(pages, "problem_solution"),
        "notes": "策略：problem_solution。适合强调研究缺口、问题意识与解决路线的论文结构。",
    }


def build_case_application(pages: list[dict[str, Any]]) -> dict[str, Any]:
    groups = group_pages(pages)
    subject = thesis_subject(pages)
    case_pages = groups["case"] or groups["topic"] or pages[:2]
    method_pages = groups["method"] or groups["evidence_aggregation"] or pages[:2]
    concept_pages = groups["concept"] or pages[-2:]
    all_sources = flatten_sources(pages)
    all_page_ids = page_ids(pages)

    root_children = [
        make_node(
            "arg_001",
            f"以{titles(case_pages, '案例材料')}为起点，可以让论文先建立可观察的对象与实践场景。",
            "main_argument",
            case_pages,
            [evidence_node("evidence_001_1", case_pages, "案例页提供具体对象与经验材料")],
        ),
        make_node(
            "arg_002",
            f"案例分析需要借助{titles(method_pages, '分析方法')}提取组织方式、应用路径与转化关系。",
            "main_argument",
            method_pages,
            [evidence_node("evidence_002_1", method_pages, "方法页把案例观察转为可比较的分析指标")],
        ),
        make_node(
            "arg_003",
            f"应用层应回扣{titles(concept_pages, '概念依据')}，说明案例经验如何转化为论文结论。",
            "main_argument",
            concept_pages,
            [evidence_node("evidence_003_1", concept_pages, "概念页保证案例推论不会停留在描述层面")],
        ),
    ]
    return {
        "node_id": "thesis_001",
        "claim": f"本文主张：应从{subject}的案例与应用场景出发，经由方法分析提炼转化机制，再回到论文结论。",
        "node_type": "thesis",
        "support_source_ids": all_sources,
        "wiki_page_ids": all_page_ids,
        "children": root_children,
        **quality_fields_for_root(pages, "case_application"),
        "notes": "策略：case_application。适合以案例分析和设计应用为主线的论文结构。",
    }


def build_candidate(
    strategy: str,
    wiki_index: dict[str, Any],
    pages: list[dict[str, Any]],
    generated_at: str,
    seed_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    builders = {
        "theory_first": build_theory_first,
        "problem_solution": build_problem_solution,
        "case_application": build_case_application,
    }
    if strategy not in builders:
        raise ValueError(f"Unknown strategy: {strategy}")
    candidate_id = f"candidate_{strategy}"
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "generated_at": generated_at,
        "strategy": strategy,
        "wiki_ref": WIKI_REF,
        "wiki_generated_at": wiki_index.get("generated_at"),
        "root": apply_seed_map(builders[strategy](pages), strategy, seed_map),
    }
    if seed_map:
        candidate["argument_seed_map_ref"] = ARGUMENT_SEED_MAP_REF
        candidate["generation_notes"] = (
            "优先使用 argument_seed_map.json 生成候选；所有节点仍只引用 Part 2 wiki 与 raw-library 可回溯来源。"
        )
    else:
        candidate["generation_notes"] = (
            "未发现 argument_seed_map.json，已从 Part 2 wiki 保守 fallback 生成；"
            "建议先运行 `python3 cli.py part3-seed-map` 以获得更完整的论证零件。"
        )
    return candidate


def generate_candidates(
    project_root: Path = PROJECT_ROOT,
    generated_at: str | None = None,
    *,
    allow_wiki_fallback: bool = False,
) -> list[dict[str, Any]]:
    assert_part2_gate_passed(project_root)
    wiki_index, pages = load_wiki_pages(project_root)
    seed_map = load_argument_seed_map(project_root, pages, allow_wiki_fallback=allow_wiki_fallback)
    timestamp = generated_at or now_iso()
    output_dir = project_root / CANDIDATE_DIR
    candidates = None
    if seed_map is not None:
        candidates = generate_candidates_with_argumentagent(
            project_root,
            pages=pages,
            seed_map=seed_map,
            generated_at=timestamp,
        )
    if candidates is None:
        candidates = [
            build_candidate(strategy, wiki_index, pages, timestamp, seed_map=seed_map)
            for strategy in STRATEGIES
        ]
    for candidate in candidates:
        output_path = output_dir / f"{candidate['candidate_id']}.json"
        write_json(output_path, candidate)
    return candidates


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate three deterministic Part 3 argument tree candidates.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    parser.add_argument(
        "--allow-wiki-fallback",
        action="store_true",
        help="Allow conservative generation directly from Part 2 wiki when argument_seed_map.json is missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    try:
        candidates = generate_candidates(
            project_root=project_root,
            allow_wiki_fallback=args.allow_wiki_fallback,
        )
    except Exception as exc:
        print(f"[ERR] Part 3 candidate generation failed: {exc}", file=sys.stderr)
        return 1

    for candidate in candidates:
        print(f"[OK] {CANDIDATE_DIR}/{candidate['candidate_id']}.json")
    if not (project_root / ARGUMENT_SEED_MAP_REF).exists():
        print(f"[WARN] 缺少 {ARGUMENT_SEED_MAP_REF}；已使用 Part 2 wiki fallback。建议先运行 `python3 cli.py part3-seed-map`。")
    print("[INFO] 未写入 outputs/part3/argument_tree.json；canonical lock 必须由 human selection 脚本完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
