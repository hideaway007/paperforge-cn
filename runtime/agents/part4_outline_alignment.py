#!/usr/bin/env python3
"""
Part 4 outline alignment helper.

职责：
  - 检查 paper_outline.json 中的 argument_node_ids 是否来自 canonical argument tree
  - 检查 thesis / main_argument 的最低覆盖
  - 检查 support_source_ids 与 argument tree / raw-library 的回溯关系
  - 记录 writing-policy 与 reference cases 的使用状态
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


CRITICAL_ARGUMENT_TYPES = {"thesis", "main_argument"}
SECONDARY_ARGUMENT_TYPES = {"sub_argument", "counterargument", "rebuttal"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def flatten_argument_nodes(root: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return node_id -> node for an argument tree root."""
    nodes: dict[str, dict[str, Any]] = {}

    def visit(node: dict[str, Any], parent_id: str | None = None) -> None:
        node_id = node.get("node_id")
        if isinstance(node_id, str) and node_id:
            next_node = dict(node)
            next_node["parent_id"] = parent_id
            nodes[node_id] = next_node
            next_parent = node_id
        else:
            next_parent = parent_id

        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                visit(child, next_parent)

    visit(root)
    return nodes


def flatten_outline_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    def visit(section: dict[str, Any]) -> None:
        flattened.append(section)
        for child in section.get("subsections", []) or []:
            if isinstance(child, dict):
                visit(child)

    for section in sections:
        if isinstance(section, dict):
            visit(section)
    return flattened


def collect_argument_source_ids(nodes: dict[str, dict[str, Any]]) -> set[str]:
    source_ids: set[str] = set()
    for node in nodes.values():
        for source_id in node.get("support_source_ids", []) or []:
            if isinstance(source_id, str) and source_id:
                source_ids.add(source_id)
    return source_ids


def collect_raw_source_ids(raw_metadata: dict[str, Any] | None) -> set[str]:
    if not raw_metadata:
        return set()
    sources = raw_metadata.get("sources", [])
    if not isinstance(sources, list):
        return set()
    return {
        source.get("source_id")
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }


def collect_wiki_page_ids(wiki_index: dict[str, Any]) -> set[str]:
    page_ids: set[str] = set()
    for key in ("pages", "entries", "items"):
        items = wiki_index.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for id_key in ("page_id", "id"):
                value = item.get(id_key)
                if isinstance(value, str) and value:
                    page_ids.add(value)
    return page_ids


def evaluate_outline_alignment(
    outline: dict[str, Any],
    argument_tree: dict[str, Any],
    wiki_index: dict[str, Any],
    *,
    raw_metadata: dict[str, Any] | None = None,
    writing_policy_ref_exists: bool = False,
    reference_cases_used: list[str] | None = None,
    rubrics_used: list[str] | None = None,
) -> dict[str, Any]:
    """Build a reference_alignment_report-compatible dict."""
    argument_nodes = flatten_argument_nodes(argument_tree.get("root", {}))
    sections = flatten_outline_sections(outline.get("sections", []) or [])
    reference_cases_used = reference_cases_used or []
    rubrics_used = rubrics_used or []

    errors: list[str] = []
    warnings: list[str] = []

    used_node_ids: set[str] = set()
    sections_without_argument_nodes: list[str] = []
    for section in sections:
        node_ids = section.get("argument_node_ids", [])
        if not node_ids:
            sections_without_argument_nodes.append(section.get("section_id", "unknown"))
            continue
        for node_id in node_ids:
            if isinstance(node_id, str) and node_id:
                used_node_ids.add(node_id)

    all_node_ids = set(argument_nodes)
    invalid_node_ids = sorted(used_node_ids - all_node_ids)
    if invalid_node_ids:
        errors.append(
            "outline 引用了 argument tree 中不存在的 node_id: "
            + ", ".join(invalid_node_ids)
        )

    critical_node_ids = {
        node_id
        for node_id, node in argument_nodes.items()
        if node.get("node_type") in CRITICAL_ARGUMENT_TYPES
    }
    uncovered_critical = sorted(critical_node_ids - used_node_ids)
    if uncovered_critical:
        errors.append(
            "outline 未覆盖 thesis/main_argument 节点: "
            + ", ".join(uncovered_critical)
        )

    secondary_node_ids = {
        node_id
        for node_id, node in argument_nodes.items()
        if node.get("node_type") in SECONDARY_ARGUMENT_TYPES
    }
    uncovered_secondary = sorted(secondary_node_ids - used_node_ids)
    if uncovered_secondary:
        warnings.append(
            "outline 未显式覆盖部分 sub/counter/rebuttal 节点: "
            + ", ".join(uncovered_secondary)
        )

    if sections_without_argument_nodes:
        warnings.append(
            "部分章节缺少 argument_node_ids: "
            + ", ".join(sections_without_argument_nodes)
        )

    outline_source_ids: set[str] = set()
    for section in sections:
        for source_id in section.get("support_source_ids", []) or []:
            if isinstance(source_id, str) and source_id:
                outline_source_ids.add(source_id)

    argument_source_ids = collect_argument_source_ids(argument_nodes)
    raw_source_ids = collect_raw_source_ids(raw_metadata)
    known_source_ids = argument_source_ids | raw_source_ids
    unknown_source_ids = sorted(outline_source_ids - known_source_ids)
    if unknown_source_ids:
        errors.append(
            "outline 引用了无法回溯到 argument tree 或 raw-library 的 source_id: "
            + ", ".join(unknown_source_ids)
        )

    source_ids_not_in_argument_tree = sorted(outline_source_ids - argument_source_ids)
    if source_ids_not_in_argument_tree and raw_source_ids:
        warnings.append(
            "部分 source_id 仅能回溯到 raw-library，未在 argument tree 中出现: "
            + ", ".join(source_ids_not_in_argument_tree)
        )

    wiki_page_ids = collect_wiki_page_ids(wiki_index)
    tree_wiki_page_ids: set[str] = set()
    for node in argument_nodes.values():
        for page_id in node.get("wiki_page_ids", []) or []:
            if isinstance(page_id, str) and page_id:
                tree_wiki_page_ids.add(page_id)
    missing_wiki_pages = sorted(tree_wiki_page_ids - wiki_page_ids)
    if tree_wiki_page_ids and not wiki_page_ids:
        errors.append("research-wiki/index.json 未提供可校验的 page_id 列表")
    if missing_wiki_pages:
        errors.append(
            "argument tree 中部分 wiki_page_ids 未在 research-wiki/index.json 中登记: "
            + ", ".join(missing_wiki_pages)
        )

    section_wiki_traceability: list[dict[str, Any]] = []
    sections_without_wiki_trace: list[str] = []
    for section in sections:
        section_id = section.get("section_id", "unknown")
        node_ids = [
            node_id
            for node_id in section.get("argument_node_ids", []) or []
            if isinstance(node_id, str) and node_id in argument_nodes
        ]
        section_page_ids: set[str] = set()
        for node_id in node_ids:
            node = argument_nodes[node_id]
            for page_id in node.get("wiki_page_ids", []) or []:
                if isinstance(page_id, str) and page_id:
                    section_page_ids.add(page_id)

        missing_section_pages = sorted(section_page_ids - wiki_page_ids)
        has_trace = bool(section_page_ids) and not missing_section_pages
        if not has_trace:
            sections_without_wiki_trace.append(section_id)
        section_wiki_traceability.append(
            {
                "section_id": section_id,
                "argument_node_ids": node_ids,
                "wiki_page_ids": sorted(section_page_ids),
                "missing_wiki_page_ids": missing_section_pages,
                "status": "pass" if has_trace else "fail",
            }
        )

    if sections_without_wiki_trace:
        errors.append(
            "部分 outline section 缺少可校验的 research-wiki 回溯: "
            + ", ".join(sections_without_wiki_trace)
        )

    if not writing_policy_ref_exists:
        errors.append(
            "未发现 writing-policy/source_index.json；outline 已保留 writing_policy_ref，"
            "但写作规范来源无法完整审计，不能通过 Part 4 completion gate"
        )

    if not reference_cases_used:
        warnings.append(
            "未发现 reference cases；Part 4 仍可生成草稿，但参考案例对齐为空"
        )
    if not rubrics_used:
        warnings.append(
            "未发现章节结构 rubric；Part 4 仍可生成草稿，但 rubric 检查为空"
        )

    status = "pass" if not errors else "fail"
    covered_critical = sorted(critical_node_ids & used_node_ids)

    return {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "status": status,
        "inputs": {
            "argument_tree_ref": outline.get("argument_tree_ref"),
            "wiki_ref": outline.get("wiki_ref"),
            "writing_policy_ref": outline.get("writing_policy_ref"),
            "reference_cases_used": reference_cases_used,
            "rubrics_used": rubrics_used,
        },
        "coverage": {
            "total_argument_nodes": len(argument_nodes),
            "critical_argument_node_ids": sorted(critical_node_ids),
            "covered_critical_argument_node_ids": covered_critical,
            "uncovered_critical_argument_node_ids": uncovered_critical,
            "uncovered_secondary_argument_node_ids": uncovered_secondary,
            "outline_section_count": len(sections),
            "outline_source_ids": sorted(outline_source_ids),
        },
        "checks": [
            {
                "id": "argument_node_ids_valid",
                "status": "fail" if invalid_node_ids else "pass",
                "invalid_node_ids": invalid_node_ids,
            },
            {
                "id": "critical_argument_coverage",
                "status": "fail" if uncovered_critical else "pass",
                "uncovered_node_ids": uncovered_critical,
            },
            {
                "id": "source_traceability",
                "status": "fail" if unknown_source_ids else "pass",
                "unknown_source_ids": unknown_source_ids,
            },
            {
                "id": "writing_policy_layer",
                "status": "pass" if writing_policy_ref_exists else "fail",
            },
            {
                "id": "reference_cases",
                "status": "pass" if reference_cases_used else "warning",
            },
            {
                "id": "rubrics",
                "status": "pass" if rubrics_used else "warning",
            },
            {
                "id": "wiki_traceability",
                "status": "fail" if sections_without_wiki_trace or missing_wiki_pages else "pass",
                "sections_without_wiki_trace": sections_without_wiki_trace,
                "missing_wiki_page_ids": missing_wiki_pages,
            },
        ],
        "wiki_traceability": section_wiki_traceability,
        "reference_case_alignment": [
            {
                "reference_case": case_path,
                "influence_dimensions": [
                    "章节顺序参考",
                    "结构密度参考",
                    "表达规范参考",
                    "论证展开方式参考",
                ],
                "status": "referenced",
            }
            for case_path in reference_cases_used
        ],
        "rubric_alignment": [
            {
                "rubric": rubric_path,
                "status": "referenced_for_manual_review",
            }
            for rubric_path in rubrics_used
        ],
        "errors": errors,
        "warnings": warnings,
    }
