#!/usr/bin/env python3
"""
runtime/agents/part4_outline_generator.py

Part 4 outline 生成 agent。

输入：
  - outputs/part3/argument_tree.json
  - research-wiki/index.json
  - writing-policy/source_index.json（缺失时生成 warning，不伪造）
  - writing-policy/reference_cases/ 与 writing-policy/rubrics/（可选）

输出：
  - outputs/part4/paper_outline.json
  - outputs/part4/outline_rationale.json
  - outputs/part4/reference_alignment_report.json

用法：
  python3 runtime/agents/part4_outline_generator.py
  python3 runtime/agents/part4_outline_generator.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from part4_outline_alignment import (
        evaluate_outline_alignment,
        flatten_argument_nodes,
    )
except ImportError:
    from runtime.agents.part4_outline_alignment import (  # type: ignore
        evaluate_outline_alignment,
        flatten_argument_nodes,
    )


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.writing_contract import clean_claim_text, public_section_title  # noqa: E402
from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402

ARGUMENT_TREE_REF = "outputs/part3/argument_tree.json"
WIKI_REF = "research-wiki/index.json"
WRITING_POLICY_REF = "writing-policy/source_index.json"
RAW_METADATA_REF = "raw-library/metadata.json"
HUMAN_SELECTION_REF = "outputs/part3/human_selection_feedback.json"
CANDIDATE_COMPARISON_REF = "outputs/part3/candidate_comparison.json"
REFINED_CANDIDATE_DIR = "outputs/part3/refined_candidate_argument_trees"
OUTLINEAGENT_REVIEW_REF = "outputs/part4/outlineagent_review.json"
OUTLINEAGENT_PROVENANCE_REF = "outputs/part4/outlineagent_provenance.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_required_json(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需输入: {rel_path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{rel_path} 无法解析: {e}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"{rel_path} 必须是 JSON object")
    return data


def load_optional_json(project_root: Path, rel_path: str) -> dict[str, Any] | None:
    path = project_root / rel_path
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def discover_reference_inputs(project_root: Path) -> dict[str, list[str]]:
    """Return optional reference case and rubric paths relative to project root."""
    groups = {
        "reference_cases": project_root / "writing-policy" / "reference_cases",
        "rubrics": project_root / "writing-policy" / "rubrics",
    }
    discovered: dict[str, list[str]] = {"reference_cases": [], "rubrics": []}
    for key, root in groups.items():
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                discovered[key].append(str(path.relative_to(project_root)))
    return discovered


def validate_argument_tree_for_outline(argument_tree: dict[str, Any]) -> None:
    if not argument_tree.get("locked_at"):
        raise RuntimeError(
            "outputs/part3/argument_tree.json 缺少 locked_at；"
            "Part 4 只能基于已人工选定并锁定的 argument tree 生成"
        )
    root = argument_tree.get("root")
    if not isinstance(root, dict) or not root.get("node_id"):
        raise RuntimeError("argument_tree.root 缺失或无 node_id")


def validate_part3_gate_for_outline(project_root: Path, argument_tree: dict[str, Any]) -> None:
    """Require state and Part 3 decision artifacts before Part 4 generation."""
    state = load_required_json(project_root, "runtime/state.json")
    part3_state = state.get("stages", {}).get("part3", {})
    issues: list[str] = []
    completed_gates = part3_state.get("human_gates_completed", [])
    if "argument_tree_selected" not in completed_gates:
        issues.append("argument_tree_selected gate 尚未完成")
    if part3_state.get("gate_passed") is not True:
        issues.append("Part 3 gate 尚未通过")
    if issues:
        raise RuntimeError("；".join(issues) + "，不能生成 Part 4 outline")

    selection = load_required_json(project_root, HUMAN_SELECTION_REF)
    comparison = load_required_json(project_root, CANDIDATE_COMPARISON_REF)

    selected_candidate_id = selection.get("selected_candidate_id")
    if not selected_candidate_id:
        raise RuntimeError("human_selection_feedback.selected_candidate_id 为空")
    if argument_tree.get("selected_candidate_id") != selected_candidate_id:
        raise RuntimeError("argument_tree.selected_candidate_id 与 human_selection_feedback 不一致")
    candidate_source = selection.get("candidate_source", "original")
    if candidate_source not in ("original", "refined"):
        raise RuntimeError("human_selection_feedback.candidate_source 必须为 original 或 refined")
    if argument_tree.get("candidate_source", "original") != candidate_source:
        raise RuntimeError("argument_tree.candidate_source 与 human_selection_feedback 不一致")
    if argument_tree.get("human_selection_ref") != HUMAN_SELECTION_REF:
        raise RuntimeError("argument_tree.human_selection_ref 未指向 human_selection_feedback.json")
    if argument_tree.get("candidate_comparison_ref") != CANDIDATE_COMPARISON_REF:
        raise RuntimeError("argument_tree.candidate_comparison_ref 未指向 candidate_comparison.json")
    selection_comparison_ref = selection.get("candidate_comparison_ref", CANDIDATE_COMPARISON_REF)
    if selection_comparison_ref != CANDIDATE_COMPARISON_REF:
        raise RuntimeError("human_selection_feedback.candidate_comparison_ref 未指向 candidate_comparison.json")

    compared_ids = {
        item.get("candidate_id")
        for item in comparison.get("candidates", [])
        if isinstance(item, dict)
    }
    candidate_tree_ref = selection.get("candidate_tree_ref")
    if argument_tree.get("candidate_tree_ref") != candidate_tree_ref:
        raise RuntimeError("argument_tree.candidate_tree_ref 与 human_selection_feedback 不一致")

    if candidate_source == "original":
        if selected_candidate_id not in compared_ids:
            raise RuntimeError("human_selection_feedback 选择了 candidate_comparison 中不存在的候选")
        return

    if not isinstance(candidate_tree_ref, str) or not candidate_tree_ref.startswith(f"{REFINED_CANDIDATE_DIR}/"):
        raise RuntimeError("refined selection 的 candidate_tree_ref 必须指向 refined_candidate_argument_trees")
    refined_candidate = load_required_json(project_root, candidate_tree_ref)
    if refined_candidate.get("candidate_id") != selected_candidate_id:
        raise RuntimeError("refined candidate_id 与 human_selection_feedback 不一致")
    based_on_ref = refined_candidate.get("based_on_candidate_ref")
    if not isinstance(based_on_ref, str) or not based_on_ref.startswith("outputs/part3/candidate_argument_trees/"):
        raise RuntimeError("refined candidate 缺少有效 based_on_candidate_ref")
    based_on_id = Path(based_on_ref).stem
    if based_on_id not in compared_ids:
        raise RuntimeError("refined candidate 依赖的原始候选不在 candidate_comparison 中")
    if refined_candidate.get("candidate_comparison_ref") not in (None, CANDIDATE_COMPARISON_REF):
        raise RuntimeError("refined candidate.candidate_comparison_ref 与 canonical comparison 不一致")


def collect_node_source_ids(node: dict[str, Any]) -> list[str]:
    source_ids: list[str] = []

    def visit(next_node: dict[str, Any]) -> None:
        for source_id in next_node.get("support_source_ids", []) or []:
            if isinstance(source_id, str) and source_id not in source_ids:
                source_ids.append(source_id)
        for child in next_node.get("children", []) or []:
            if isinstance(child, dict):
                visit(child)

    visit(node)
    return source_ids


def build_writing_constraints(
    writing_policy: dict[str, Any] | None,
    *,
    reference_cases_used: list[str],
    rubrics_used: list[str],
) -> list[str]:
    constraints: list[str] = []
    if writing_policy:
        for key in ("rules", "style_guides", "constraints"):
            items = writing_policy.get(key, [])
            if isinstance(items, list):
                for item in items[:3]:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("id") or item.get("path")
                        if title:
                            constraints.append(f"遵守写作规范：{title}")
                    elif isinstance(item, str):
                        constraints.append(f"遵守写作规范：{item}")
    else:
        constraints.append("待补充 writing-policy/source_index.json 后复核写作规范")

    if reference_cases_used:
        constraints.append("章节顺序与结构密度需参考 reference_alignment_report.json")
    else:
        constraints.append("未提供 reference cases 时，不得伪造范文来源")
    if rubrics_used:
        constraints.append("章节层级与比例需对照 rubric_alignment 复核")
    else:
        constraints.append("未提供 rubrics 时，不得伪造章节结构评分")

    return unique_nonempty(constraints)


def build_section_title(claim: str, fallback: str) -> str:
    return public_section_title(claim, fallback)


def unique_nonempty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        clean = value.strip()
        if clean and clean not in seen:
            result.append(clean)
            seen.add(clean)
    return result


def child_argument_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    children = [
        child
        for child in root.get("children", []) or []
        if isinstance(child, dict)
        and child.get("node_type") in {"main_argument", "sub_argument", "counterargument", "rebuttal"}
    ]
    if children:
        return children
    return [root]


def build_subsections_for_node(
    node: dict[str, Any],
    *,
    parent_section_id: str,
    constraints: list[str],
) -> list[dict[str, Any]]:
    subsections: list[dict[str, Any]] = []
    children = [
        child
        for child in node.get("children", []) or []
        if isinstance(child, dict)
        and child.get("node_type") in {"sub_argument", "evidence", "counterargument", "rebuttal"}
    ]

    for index, child in enumerate(children, start=1):
        child_id = child.get("node_id")
        claim = clean_claim_text(child.get("claim", ""))
        section_id = f"{parent_section_id}_{index}"
        subsections.append(
            {
                "section_id": section_id,
                "title": build_section_title(claim, f"论证展开 {index}"),
                "level": 2,
                "brief": f"围绕该层论点展开：{claim}",
                "argument_node_ids": unique_nonempty([child_id]),
                "support_source_ids": collect_node_source_ids(child),
                "writing_constraints": constraints,
                "subsections": [],
            }
        )

    return subsections


def build_outline(
    argument_tree: dict[str, Any],
    wiki_index: dict[str, Any],
    writing_policy: dict[str, Any] | None,
    *,
    reference_cases_used: list[str],
    rubrics_used: list[str],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or now_iso()
    root = argument_tree["root"]
    root_id = root.get("node_id")
    root_claim = clean_claim_text(root.get("claim", ""))
    body_nodes = child_argument_nodes(root)
    constraints = build_writing_constraints(
        writing_policy,
        reference_cases_used=reference_cases_used,
        rubrics_used=rubrics_used,
    )

    sections: list[dict[str, Any]] = [
        {
            "section_id": "sec_1",
            "title": "绪论",
            "level": 1,
            "brief": f"提出研究背景、问题意识、研究对象与主论题：{root_claim}",
            "argument_node_ids": unique_nonempty([root_id]),
            "support_source_ids": collect_node_source_ids(root)[:5],
            "writing_constraints": constraints,
            "subsections": [
                {
                    "section_id": "sec_1_1",
                    "title": "研究背景与问题提出",
                    "level": 2,
                    "brief": "说明研究缘起、现实问题与中文学术写作场景中的研究必要性。",
                    "argument_node_ids": unique_nonempty([root_id]),
                    "support_source_ids": collect_node_source_ids(root)[:3],
                    "writing_constraints": constraints,
                    "subsections": [],
                },
                {
                    "section_id": "sec_1_2",
                    "title": "研究对象、范围与方法",
                    "level": 2,
                    "brief": "界定研究对象、材料范围、方法路径与后续章节的论证顺序。",
                    "argument_node_ids": unique_nonempty([root_id]),
                    "support_source_ids": collect_node_source_ids(root)[:3],
                    "writing_constraints": constraints,
                    "subsections": [],
                },
            ],
        },
        {
            "section_id": "sec_2",
            "title": "文献综述与理论基础",
            "level": 1,
            "brief": "基于已整理研究材料梳理核心概念、研究现状、方法基础与争议缺口。",
            "argument_node_ids": unique_nonempty([root_id]),
            "support_source_ids": collect_node_source_ids(root),
            "writing_constraints": constraints,
            "subsections": [],
        },
    ]

    for offset, node in enumerate(body_nodes, start=3):
        node_id = node.get("node_id")
        claim = clean_claim_text(node.get("claim", ""))
        section_id = f"sec_{offset}"
        sections.append(
            {
                "section_id": section_id,
                "title": build_section_title(claim, f"核心论证 {offset - 2}"),
                "level": 1,
                "brief": f"围绕该章节论点展开：{claim}",
                "argument_node_ids": unique_nonempty([node_id]),
                "support_source_ids": collect_node_source_ids(node),
                "writing_constraints": constraints,
                "subsections": build_subsections_for_node(
                    node,
                    parent_section_id=section_id,
                    constraints=constraints,
                ),
            }
        )

    conclusion_id = f"sec_{len(sections) + 1}"
    sections.append(
        {
            "section_id": conclusion_id,
            "title": "结论与写作准备",
            "level": 1,
            "brief": "回收主论题，明确研究结论、论证边界与后续研究债务。",
            "argument_node_ids": unique_nonempty([root_id] + [node.get("node_id", "") for node in body_nodes]),
            "support_source_ids": collect_node_source_ids(root),
            "writing_constraints": constraints,
            "subsections": [],
        }
    )

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "confirmed_at": None,
        "argument_tree_ref": ARGUMENT_TREE_REF,
        "wiki_ref": WIKI_REF,
        "writing_policy_ref": WRITING_POLICY_REF,
        "reference_cases_used": reference_cases_used,
        "sections": sections,
    }


def build_outline_rationale(
    outline: dict[str, Any],
    argument_tree: dict[str, Any],
    wiki_index: dict[str, Any],
    *,
    reference_cases_used: list[str],
    rubrics_used: list[str],
) -> dict[str, Any]:
    nodes = flatten_argument_nodes(argument_tree["root"])
    section_mappings: list[dict[str, Any]] = []
    for section in outline.get("sections", []) or []:
        node_ids = section.get("argument_node_ids", []) or []
        section_mappings.append(
            {
                "section_id": section.get("section_id"),
                "title": section.get("title"),
                "argument_node_ids": node_ids,
                "claims": [
                    nodes[node_id].get("claim")
                    for node_id in node_ids
                    if node_id in nodes
                ],
                "rationale": "章节由 argument tree 节点映射生成，source_id 与 wiki_ref 保留回溯入口。",
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "strategy": "argument_tree + research_wiki + writing_policy + reference_cases",
        "training_dependency": False,
        "inputs": {
            "argument_tree_ref": ARGUMENT_TREE_REF,
            "wiki_ref": WIKI_REF,
            "writing_policy_ref": WRITING_POLICY_REF,
            "reference_cases_used": reference_cases_used,
            "rubrics_used": rubrics_used,
            "wiki_page_count": len(wiki_index.get("pages", []) or []),
        },
        "section_mappings": section_mappings,
        "workflow_gate": {
            "id": "part4_artifact_alignment",
            "required_before_writing": True,
            "status": "checked_by_reference_alignment_report",
        },
    }


def generate_outline_package(project_root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any]]:
    if not (project_root / "research-wiki" / "pages").exists():
        raise FileNotFoundError("缺少必需输入目录: research-wiki/pages/")
    if not (project_root / "writing-policy").exists():
        raise FileNotFoundError("缺少必需输入目录: writing-policy/")

    argument_tree = load_required_json(project_root, ARGUMENT_TREE_REF)
    validate_argument_tree_for_outline(argument_tree)
    validate_part3_gate_for_outline(project_root, argument_tree)

    wiki_index = load_required_json(project_root, WIKI_REF)
    writing_policy = load_optional_json(project_root, WRITING_POLICY_REF)
    raw_metadata = load_optional_json(project_root, RAW_METADATA_REF)
    reference_inputs = discover_reference_inputs(project_root)
    reference_cases_used = reference_inputs["reference_cases"]
    rubrics_used = reference_inputs["rubrics"]

    outline = build_outline(
        argument_tree,
        wiki_index,
        writing_policy,
        reference_cases_used=reference_cases_used,
        rubrics_used=rubrics_used,
    )
    rationale = build_outline_rationale(
        outline,
        argument_tree,
        wiki_index,
        reference_cases_used=reference_cases_used,
        rubrics_used=rubrics_used,
    )
    alignment_report = evaluate_outline_alignment(
        outline,
        argument_tree,
        wiki_index,
        raw_metadata=raw_metadata,
        writing_policy_ref_exists=(project_root / WRITING_POLICY_REF).exists(),
        reference_cases_used=reference_cases_used,
        rubrics_used=rubrics_used,
    )

    return {
        "paper_outline": outline,
        "outline_rationale": rationale,
        "reference_alignment_report": alignment_report,
    }


def assert_outline_overwrite_allowed(project_root: Path, *, force: bool = False) -> None:
    outline_path = project_root / "outputs" / "part4" / "paper_outline.json"
    if force or not outline_path.exists():
        return

    try:
        with open(outline_path, encoding="utf-8") as f:
            existing_outline = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"paper_outline.json 无法解析，不能安全覆盖: {e}") from e

    if not isinstance(existing_outline, dict):
        raise RuntimeError("paper_outline.json 必须是 JSON object，不能安全覆盖")


def write_package(
    project_root: Path,
    package: dict[str, dict[str, Any]],
    *,
    force: bool = False,
) -> None:
    assert_outline_overwrite_allowed(project_root, force=force)
    out_dir = project_root / "outputs" / "part4"
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "paper_outline": out_dir / "paper_outline.json",
        "outline_rationale": out_dir / "outline_rationale.json",
        "reference_alignment_report": out_dir / "reference_alignment_report.json",
    }
    for key, path in targets.items():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(package[key], f, ensure_ascii=False, indent=2)
    write_outlineagent_review(project_root)


def write_outlineagent_review(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="outlineagent",
        task="part4_outline_alignment_review",
        skill="outline-alignment",
        output_ref=OUTLINEAGENT_REVIEW_REF,
        input_paths=[
            ARGUMENT_TREE_REF,
            WIKI_REF,
            WRITING_POLICY_REF,
            "outputs/part4/paper_outline.json",
            "outputs/part4/outline_rationale.json",
            "outputs/part4/reference_alignment_report.json",
        ],
        instructions=[
            "Review the generated Part 4 outline for argument coverage, section responsibility, transition logic, and alignment risk.",
            "Return JSON with report or payload. Do not rewrite paper_outline.json.",
            "Do not modify Part 3 argument_tree.json, runtime state, or gate status.",
            "Keep writing-policy constraints separate from research evidence.",
        ],
    )
    if result is None:
        return

    path = project_root / OUTLINEAGENT_REVIEW_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.raw, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_llm_agent_provenance(
        project_root,
        OUTLINEAGENT_PROVENANCE_REF,
        agent_name="outlineagent",
        task="part4_outline_alignment_review",
        skill="outline-alignment",
        output_ref=OUTLINEAGENT_REVIEW_REF,
        mode="llm",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Part 4 paper outline artifacts")
    parser.add_argument("--dry-run", action="store_true", help="打印产物但不写文件")
    parser.add_argument(
        "--force",
        action="store_true",
        help="允许覆盖已生成的 Part 4 outline；Part 4 不再需要 outline_confirmed",
    )
    parser.add_argument(
        "--project-root",
        default=str(PROJECT_ROOT),
        help="项目根目录，默认自动从脚本位置推断",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    try:
        package = generate_outline_package(project_root)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(package, ensure_ascii=False, indent=2))
    else:
        write_package(project_root, package, force=args.force)
        print("Part 4 outline artifacts 写入完成")
        print("  outputs/part4/paper_outline.json")
        print("  outputs/part4/outline_rationale.json")
        print("  outputs/part4/reference_alignment_report.json")

    status = package["reference_alignment_report"].get("status")
    if status != "pass":
        print("reference_alignment_report.status != pass", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
