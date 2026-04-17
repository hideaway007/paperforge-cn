#!/usr/bin/env python3
"""
Part 5 MVP generator.

This script is deterministic by design: it turns the confirmed Part 4 outline
and locked Part 3 argument tree into auditable drafting artifacts. It does not
call an LLM and does not confirm any human gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.llm_writer_bridge import (  # noqa: E402
    deterministic_writer_fallback_allowed,
    missing_writeagent_command_message,
    request_writeagent,
    write_writer_provenance,
)
from runtime.writing_contract import (  # noqa: E402
    clean_claim_text,
    public_section_title,
    public_text_has_internal_markers,
    remove_internal_lines,
)

PREP_ARTIFACTS = [
    "outputs/part5/claim_evidence_matrix.json",
    "outputs/part5/citation_map.json",
    "outputs/part5/figure_plan.json",
    "outputs/part5/open_questions.json",
]

WRITEAGENT_STYLE_INPUTS = [
    "writing-policy/style_guides/author_style_profile.md",
    "writing-policy/style_guides/author_style_negative_patterns.md",
    "skills/author-style-profile-build/SKILL.md",
    "skills/academic-register-polish/SKILL.md",
    "skills/paper-manuscript-style-profile/SKILL.md",
    "skills/part5-formal-manuscript-authoring/SKILL.md",
    "skills/part5-draft-manuscript/SKILL.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_public_draft_text(text: str, *, artifact_name: str) -> str:
    raw_markers = public_text_has_internal_markers(text)
    if raw_markers:
        raise RuntimeError(
            f"{artifact_name} 包含内部工作标记，不能作为公开正文草稿: {raw_markers}"
        )
    cleaned = remove_internal_lines(text)
    markers = public_text_has_internal_markers(cleaned)
    if markers:
        raise RuntimeError(
            f"{artifact_name} 包含内部工作标记，不能作为公开正文草稿: {markers}"
        )
    return cleaned.strip() + "\n"


def load_required_json(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {rel_path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{rel_path} 必须是 JSON object")
    return data


def safe_project_path(project_root: Path, rel_path: str) -> Path:
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe project-relative path: {rel_path}")
    root = project_root.resolve()
    path = (root / rel).resolve()
    path.relative_to(root)
    return path


def safe_file_id(value: Any, fallback: str) -> str:
    cleaned = normalize_id(str(value or ""), fallback)
    if not cleaned or not all(ch.isalnum() or ch in {"_", "-"} for ch in cleaned):
        raise ValueError(f"Unsafe file id: {value!r}")
    return cleaned


def write_json(project_root: Path, rel_path: str, data: dict[str, Any]) -> None:
    path = safe_project_path(project_root, rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(project_root: Path, rel_path: str, text: str) -> None:
    path = safe_project_path(project_root, rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_state(project_root: Path) -> dict[str, Any]:
    return load_required_json(project_root, "runtime/state.json")


def stage_state(project_root: Path, stage_id: str) -> dict[str, Any]:
    state = load_state(project_root)
    stage = state.get("stages", {}).get(stage_id)
    if not isinstance(stage, dict):
        raise RuntimeError(f"runtime/state.json 缺少 stages.{stage_id}")
    return stage


def require_completed_stage(project_root: Path, stage_id: str) -> None:
    stage = stage_state(project_root, stage_id)
    if stage.get("status") != "completed" or stage.get("gate_passed") is not True:
        raise RuntimeError(f"{stage_id} gate 尚未通过，不能推进 Part 5")


def require_part5_entry(project_root: Path) -> None:
    for stage_id in ["part1", "part2", "part3", "part4"]:
        require_completed_stage(project_root, stage_id)


def require_files(project_root: Path, rel_paths: list[str]) -> None:
    missing = [rel_path for rel_path in rel_paths if not (project_root / rel_path).exists()]
    if missing:
        raise FileNotFoundError("缺少 Part 5 前置 artifact: " + ", ".join(missing))


def collect_argument_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: dict[str, Any]) -> None:
        nodes.append(node)
        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                visit(child)

    visit(root)
    return nodes


def source_title_map(raw_metadata: dict[str, Any]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for source in raw_metadata.get("sources", []) or []:
        if isinstance(source, dict) and isinstance(source.get("source_id"), str):
            titles[source["source_id"]] = source.get("title") or source["source_id"]
    return titles


def wiki_page_map(wiki_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pages: dict[str, dict[str, Any]] = {}
    for page in wiki_index.get("pages", []) or []:
        if isinstance(page, dict) and isinstance(page.get("page_id"), str):
            pages[page["page_id"]] = page
    return pages


def section_list(outline: dict[str, Any]) -> list[dict[str, Any]]:
    sections = outline.get("sections", [])
    if not isinstance(sections, list) or not sections:
        raise RuntimeError("paper_outline.sections 不能为空")
    return [section for section in sections if isinstance(section, dict)]


def normalize_id(value: str, fallback: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return cleaned or fallback


def risk_level_for_sources(source_ids: list[str], wiki_page_ids: list[str]) -> str:
    if not source_ids:
        return "critical"
    if not wiki_page_ids:
        return "medium"
    return "low"


def evidence_level_for_node(node: dict[str, Any]) -> str:
    source_ids = node.get("support_source_ids", []) or []
    if source_ids:
        return "hard_evidence"
    return "conceptual_framing"


def generate_prep_package(project_root: Path) -> dict[str, Any]:
    require_part5_entry(project_root)
    generated_at = now_iso()
    outline = load_required_json(project_root, "outputs/part4/paper_outline.json")
    argument_tree = load_required_json(project_root, "outputs/part3/argument_tree.json")
    wiki_index = load_required_json(project_root, "research-wiki/index.json")
    raw_metadata = load_required_json(project_root, "raw-library/metadata.json")
    policy = load_required_json(project_root, "writing-policy/source_index.json")

    nodes = collect_argument_nodes(argument_tree.get("root", {}))
    node_by_id = {
        node.get("node_id"): node
        for node in nodes
        if isinstance(node.get("node_id"), str)
    }
    titles = source_title_map(raw_metadata)
    pages = wiki_page_map(wiki_index)

    claims: list[dict[str, Any]] = []
    used_sources: set[str] = set()
    open_questions: list[dict[str, Any]] = []
    for node in nodes:
        claim_id = node.get("node_id") or f"claim_{len(claims) + 1}"
        source_ids = [
            source_id
            for source_id in node.get("support_source_ids", []) or []
            if isinstance(source_id, str)
        ]
        wiki_page_ids = [
            page_id
            for page_id in node.get("wiki_page_ids", []) or []
            if isinstance(page_id, str)
        ]
        used_sources.update(source_ids)
        risk_level = risk_level_for_sources(source_ids, wiki_page_ids)
        status = "mapped" if risk_level == "low" else "registered"
        claims.append({
            "claim_id": claim_id,
            "claim": clean_claim_text(node.get("claim", "")),
            "node_type": node.get("node_type", "argument"),
            "evidence_level": evidence_level_for_node(node),
            "source_ids": source_ids,
            "wiki_page_ids": wiki_page_ids,
            "risk_level": risk_level,
            "status": status,
        })
        if risk_level != "low":
            open_questions.append({
                "question_id": f"q_{len(open_questions) + 1:03d}",
                "type": "evidence_gap",
                "description": f"{claim_id} 缺少完整 source/wiki 映射，正文必须保守表述。",
                "claim_id": claim_id,
                "blocks_part6": risk_level == "critical",
            })

    out_dir = project_root / "outputs" / "part5"
    (out_dir / "chapter_briefs").mkdir(parents=True, exist_ok=True)
    (out_dir / "case_analysis_templates").mkdir(parents=True, exist_ok=True)

    for index, section in enumerate(section_list(outline), start=1):
        section_id = safe_file_id(section.get("section_id"), f"sec_{index}")
        title = section.get("title") or f"章节 {index}"
        argument_node_ids = [
            node_id
            for node_id in section.get("argument_node_ids", []) or []
            if isinstance(node_id, str)
        ]
        section_sources = [
            source_id
            for source_id in section.get("support_source_ids", []) or []
            if isinstance(source_id, str)
        ]
        node_claims = [
            node_by_id[node_id].get("claim", "")
            for node_id in argument_node_ids
            if node_id in node_by_id
        ]
        brief_lines = [
            f"# {title}",
            "",
            f"- section_id: {section_id}",
            f"- brief: {section.get('brief', '待扩写')}",
            f"- argument_node_ids: {', '.join(argument_node_ids) or '未指定'}",
            f"- source_ids: {', '.join(section_sources) or '未指定'}",
            "- writing_constraints:",
            "  - 不得新增未在 research-wiki 或 raw-library 中出现的引用。",
            "  - 案例事实证据不足时，降级为概念参照或研究债务。",
            "",
            "## Claims",
        ]
        brief_lines.extend(f"- {claim}" for claim in node_claims or ["待从 argument tree 补齐 claim"])
        write_text(project_root, f"outputs/part5/chapter_briefs/{section_id}.md", "\n".join(brief_lines) + "\n")

        if "案例" in title or "case" in title.lower():
            template_id = normalize_id(section_id, f"case_{index}")
            write_text(
                project_root,
                f"outputs/part5/case_analysis_templates/{template_id}.md",
                "\n".join([
                    f"# {title} 案例分析模板",
                    "",
                    "- 案例角色: 待用户确认为核心案例 / 辅助案例 / 概念参照",
                    "- 必须核验: 图纸、动线、视线、建筑师说明、建成信息",
                    "- 禁止: 将未核验案例写成硬建筑事实",
                    "- 可用写法: 作为空间组织方法的概念性参照",
                    "",
                ]),
            )

    if not list((out_dir / "case_analysis_templates").glob("*.md")):
        write_text(
            project_root,
            "outputs/part5/case_analysis_templates/conceptual_case_template.md",
            "# 概念参照案例模板\n\n- 当前 outline 未识别明确案例章节；如后续加入案例，需先补证据。\n",
        )

    citation_refs = [
        {
            "source_id": source_id,
            "title": titles.get(source_id, source_id),
            "claim_ids": [
                claim["claim_id"]
                for claim in claims
                if source_id in claim.get("source_ids", [])
            ],
            "citation_status": "accepted_source" if source_id in titles else "missing_metadata",
        }
        for source_id in sorted(used_sources)
    ]

    figure_items = []
    known_gaps = []
    for index, section in enumerate(section_list(outline), start=1):
        title = section.get("title") or f"章节 {index}"
        if "案例" in title or "空间" in title:
            figure_items.append({
                "figure_id": f"fig_{len(figure_items) + 1:03d}",
                "section_id": section.get("section_id", f"sec_{index}"),
                "purpose": f"支撑「{title}」的空间关系说明",
                "required_materials": ["图纸", "动线", "视线或界面关系说明"],
                "status": "needed",
            })
            known_gaps.append(f"{title} 需要图纸/动线/视线材料支撑，缺失时只能保守表述。")

    package = {
        "claim_evidence_matrix": {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "outline_ref": "outputs/part4/paper_outline.json",
            "argument_tree_ref": "outputs/part3/argument_tree.json",
            "wiki_ref": "research-wiki/index.json",
            "claims": claims,
        },
        "citation_map": {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "source_refs": citation_refs,
            "unmapped_sources": [
                source_id for source_id in used_sources if source_id not in titles
            ],
        },
        "figure_plan": {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "figures": figure_items,
            "known_gaps": known_gaps,
        },
        "open_questions": {
            "schema_version": "1.0.0",
            "generated_at": generated_at,
            "questions": open_questions,
        },
        "policy_snapshot": {
            "rules_count": len(policy.get("rules", []) or []),
            "style_guides_count": len(policy.get("style_guides", []) or []),
            "writing_policy_ref": "writing-policy/source_index.json",
            "policy_is_research_evidence": False,
        },
        "wiki_page_count": len(pages),
    }

    for artifact_name in PREP_ARTIFACTS:
        key = Path(artifact_name).stem
        write_json(project_root, artifact_name, package[key])

    return package


def generate_draft(project_root: Path) -> str:
    require_part5_entry(project_root)
    require_files(project_root, PREP_ARTIFACTS)

    llm_result = request_writeagent(
        project_root,
        task="part5_draft_manuscript",
        skill="part5-draft-manuscript",
        output_ref="outputs/part5/manuscript_v1.md",
        input_paths=[
            "outputs/part4/paper_outline.json",
            "outputs/part3/argument_tree.json",
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part5/citation_map.json",
            "outputs/part5/figure_plan.json",
            "outputs/part5/open_questions.json",
            "writing-policy/source_index.json",
        ] + WRITEAGENT_STYLE_INPUTS,
        instructions=[
            "Generate a continuous Chinese academic manuscript_v1 draft from paper_outline and argument_tree.",
            "Use author_style_profile if present, academic-register-polish rules, paper-manuscript-style-profile, and part5-formal-manuscript-authoring.",
            "Shape manuscript_v1 as a formal Chinese academic paper draft: standalone title, compliant abstract and keywords, consistent chapter hierarchy, writable subsections, chapter summaries, conclusion, and references section.",
            "Do not over-expose evidence-chain language in public prose; keep source/risk plumbing out of the manuscript body.",
            "Do not create a standalone '证据边界与研究不足' section unless the outline explicitly asks for it.",
            "Use citations and source names only where they serve the academic argument.",
            "Do not add new source ids, citations, case facts, figure facts, or uncited research facts.",
            "Keep manuscript_v1 as an intermediate draft, not a canonical final manuscript.",
        ],
    )
    if llm_result is not None:
        llm_text = ensure_public_draft_text(
            llm_result.text,
            artifact_name="writeagent part5 manuscript_v1",
        )
        write_text(project_root, "outputs/part5/manuscript_v1.md", llm_text)
        write_writer_provenance(
            project_root,
            "outputs/part5/writer_provenance.json",
            task="part5_draft_manuscript",
            skill="part5-draft-manuscript",
            output_ref="outputs/part5/manuscript_v1.md",
            mode="llm",
        )
        return llm_text

    if not deterministic_writer_fallback_allowed():
        raise RuntimeError(missing_writeagent_command_message("part5_draft_manuscript"))

    outline = load_required_json(project_root, "outputs/part4/paper_outline.json")
    matrix = load_required_json(project_root, "outputs/part5/claim_evidence_matrix.json")
    claims_by_id = {
        claim.get("claim_id"): claim
        for claim in matrix.get("claims", []) or []
        if isinstance(claim, dict)
    }

    lines = ["# 论文初稿 v1", ""]
    for section in section_list(outline):
        title = public_section_title(section.get("title", ""), section.get("title", "未命名章节"))
        lines.extend([f"## {title}", ""])
        brief = clean_claim_text(section.get("brief") or "本节围绕既有论证展开。")
        node_ids = section.get("argument_node_ids", []) or []
        section_claims = [claims_by_id.get(node_id) for node_id in node_ids if node_id in claims_by_id]
        claim_sentences = [
            clean_claim_text(claim.get("claim", ""))
            for claim in section_claims
            if isinstance(claim, dict) and claim.get("claim")
        ]
        if claim_sentences:
            primary_claim = claim_sentences[0].rstrip("。")
            secondary_claim = claim_sentences[1].rstrip("。") if len(claim_sentences) > 1 else ""
            lines.append(
                f"{brief} 在此基础上，论文首先说明{primary_claim}。"
                + (f"随后结合{secondary_claim}，进一步界定研究对象、材料范围与分析路径之间的关系。" if secondary_claim else "")
            )
        else:
            lines.append(
                f"{brief} 本节主要承担章节承接功能，交代研究背景、材料范围与后续论述顺序。"
            )
        lines.append("")
        if section_claims:
            lines.append(
                "论述范围限定在现有材料可以支持的边界内，避免把个案观察直接扩大为普遍结论。"
                "需要进一步补证的内容保留为研究边界，而不写成已经完成验证的事实。"
            )
            lines.append("")
        else:
            lines.append(
                "由于该部分不承担独立证据证明任务，正文保持概括性表述，避免替代核心论证章节。"
            )
            lines.append("")

    text = "\n".join(lines).strip() + "\n"
    write_text(project_root, "outputs/part5/manuscript_v1.md", text)
    write_writer_provenance(
        project_root,
        "outputs/part5/writer_provenance.json",
        task="part5_draft_manuscript",
        skill="part5-draft-manuscript",
        output_ref="outputs/part5/manuscript_v1.md",
        mode="deterministic_fallback",
        fallback_reason="RTM_WRITEAGENT_COMMAND not configured",
    )
    return text


def generate_review(project_root: Path) -> dict[str, Any]:
    require_part5_entry(project_root)
    require_files(project_root, PREP_ARTIFACTS + ["outputs/part5/manuscript_v1.md"])

    import part5_review_argument
    import part5_review_citation
    import part5_review_evidence
    import part5_review_integrator
    import part5_review_policy
    import part5_review_structure

    for review_agent in [
        part5_review_structure,
        part5_review_argument,
        part5_review_evidence,
        part5_review_citation,
        part5_review_policy,
    ]:
        review_agent.generate_review_fragment(project_root)

    review_package = part5_review_integrator.integrate_review_fragments(project_root)
    report_text = generate_user_review_report(project_root)
    review_package["review_report"] = report_text
    return review_package


def unresolved_critical_reviews(review_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    for review in review_matrix.get("reviews", []) or []:
        if not isinstance(review, dict):
            continue
        if review.get("severity") == "critical" and review.get("status") not in ("resolved", "mitigated", "downgraded"):
            unresolved.append(review)
    return unresolved


REVIEW_DIMENSION_LABELS = {
    "structure": "结构",
    "argument": "论证",
    "evidence": "证据",
    "citation": "引用",
    "writing_policy": "写作规范",
    "debt": "研究债务",
    "revision": "修订",
}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def claim_lookup_from_matrix(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        claim["claim_id"]: claim
        for claim in matrix.get("claims", []) or []
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    }


def review_revision_status(review: dict[str, Any]) -> str:
    if review.get("severity") == "critical":
        return "blocked"
    return "applied"


def claim_reference_text(claim_ids: list[str], claims_by_id: dict[str, dict[str, Any]]) -> str:
    if not claim_ids:
        return "全文层面的结构或规范问题"

    refs = []
    for claim_id in claim_ids:
        claim = claims_by_id.get(claim_id, {})
        claim_text = claim.get("claim")
        if isinstance(claim_text, str) and claim_text.strip():
            refs.append(f"{claim_id}「{claim_text}」")
        else:
            refs.append(claim_id)
    return "、".join(refs)


def revision_action_text(review: dict[str, Any], claims_by_id: dict[str, dict[str, Any]]) -> str:
    dimension = review.get("dimension")
    severity = review.get("severity", "medium")
    claim_ids = string_list(review.get("claim_ids"))
    claim_refs = claim_reference_text(claim_ids, claims_by_id)

    if severity == "critical":
        return (
            f"该项不写成正文硬结论；v2 仅保留 {claim_refs} 的问题登记，"
            "并把它交给 readiness/blocker 继续约束 Part 6。"
        )

    if dimension == "structure":
        return (
            "已在 v2 中新增审稿驱动修订段，把章节 scaffold 的问题转化为后续扩写约束；"
            "正文仍保留 outline 顺序，避免为了补写而改变 canonical structure。"
        )
    if dimension == "argument":
        return (
            f"已把 {claim_refs} 明确为论证落点，要求后续扩写围绕 argument tree 展开，"
            "不得把案例描述替代为论证本身。"
        )
    if dimension == "evidence":
        return (
            f"已将 {claim_refs} 调整为证据约束表达，明确 source/wiki 映射边界，"
            "并降低断言强度；未补足的图纸、动线或案例事实转入 residual risk。"
        )
    if dimension == "citation":
        return (
            f"已要求 {claim_refs} 只能使用 citation_map 中的 accepted_source，"
            "不得新增未进入 raw-library 和 research-wiki 的引用。"
        )
    if dimension == "writing_policy":
        return (
            "已把 writing-policy 固定为结构与表达约束层，不作为 research evidence；"
            "v2 的修订说明只引用其规范功能，不把它写成研究来源。"
        )
    return f"已登记并处理 {claim_refs}：{review.get('finding', 'review finding')}"


def build_revision_actions(
    review_matrix: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for index, review in enumerate(review_matrix.get("reviews", []) or [], start=1):
        if not isinstance(review, dict):
            continue
        review_id = review.get("review_id") or f"review_{index:03d}"
        dimension = review.get("dimension", "review")
        claim_ids = string_list(review.get("claim_ids"))
        applied_text = revision_action_text(review, claims_by_id)
        actions.append({
            "revision_id": f"rev_{index:03d}",
            "review_id": review_id,
            "action": f"处理 {dimension} review: {review.get('finding')}",
            "review_dimension": dimension,
            "status": review_revision_status(review),
            "claim_ids": claim_ids,
            "manuscript_anchor": f"Review 驱动修订 / {dimension}",
            "applied_text": applied_text,
            "severity": review.get("severity", "medium"),
            "finding": review.get("finding", ""),
        })
    return actions


def review_revision_lines(actions: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Review 驱动修订",
        "",
        "本节逐条吸收 `review_matrix.json` 的审稿意见；每一项都保留 review_id，便于从正文反查到结构化审稿记录。",
        "",
    ]

    for action in actions:
        dimension = action.get("review_dimension", "review")
        label = REVIEW_DIMENSION_LABELS.get(dimension, str(dimension))
        claim_ids = string_list(action.get("claim_ids"))
        claim_note = "、".join(claim_ids) if claim_ids else "全文层面"
        lines.extend([
            f"### {action.get('review_id')}",
            "",
            f"- 维度：{label}",
            f"- 级别：{action.get('severity')}",
            f"- 关联 claim：{claim_note}",
            f"- 审稿意见：{action.get('finding')}",
            f"- 修订处理：{action.get('applied_text')}",
            f"- 正文落点：{action.get('manuscript_anchor')}",
            "",
        ])
    return lines


def claim_revision_lines(
    actions: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    claim_ids = sorted({
        claim_id
        for action in actions
        for claim_id in string_list(action.get("claim_ids"))
    })

    lines = [
        "## Claim 级修订处理",
        "",
    ]
    if not claim_ids:
        lines.extend([
            "本轮 review 未指向单独 claim；v2 只保留全文层面的结构、引用和写作规范修订。",
            "",
        ])
        return lines

    for claim_id in claim_ids:
        claim = claims_by_id.get(claim_id, {})
        related_actions = [
            action
            for action in actions
            if claim_id in string_list(action.get("claim_ids"))
        ]
        source_ids = ", ".join(string_list(claim.get("source_ids"))) or "待补证据"
        wiki_page_ids = ", ".join(string_list(claim.get("wiki_page_ids"))) or "待补 wiki 映射"
        risk_level = claim.get("risk_level", "unknown")
        claim_text = claim.get("claim") or "未登记 claim 文本"
        needs_downgrade = any(
            action.get("review_dimension") == "evidence"
            or action.get("severity") in {"medium", "high", "critical"}
            for action in related_actions
        )
        if needs_downgrade:
            revised_statement = (
                "修订后只作为阶段性判断或方法参照使用；除非后续补齐来源、图纸、动线或案例材料，"
                "不得写成已被充分证明的事实结论。"
            )
        else:
            revised_statement = (
                "修订后可作为已映射论点继续扩写，但仍必须保留 source_id 与 wiki_page_id 的可追溯性。"
            )

        lines.extend([
            f"### {claim_id}",
            "",
            f"- 原论点：{claim_text}",
            f"- 证据状态：source_ids={source_ids}；wiki_page_ids={wiki_page_ids}；risk_level={risk_level}",
            f"- 修订后写法：{revised_statement}",
            "- 对应 review："
        ])
        lines.extend(
            f"  - {action.get('review_id')}：{action.get('applied_text')}"
            for action in related_actions
        )
        lines.append("")
    return lines


def generate_revision(project_root: Path) -> dict[str, Any]:
    require_part5_entry(project_root)
    require_files(project_root, [
        "outputs/part5/manuscript_v1.md",
        "outputs/part5/review_matrix.json",
        "outputs/part5/review_summary.md",
        "outputs/part5/review_report.md",
        "outputs/part5/claim_risk_report.json",
        "outputs/part5/citation_consistency_precheck.json",
    ])

    generated_at = now_iso()
    v1_text = (project_root / "outputs/part5/manuscript_v1.md").read_text(encoding="utf-8")
    review_matrix = load_required_json(project_root, "outputs/part5/review_matrix.json")
    citation_precheck = load_required_json(project_root, "outputs/part5/citation_consistency_precheck.json")
    if citation_precheck.get("status") == "blocked" or citation_precheck.get("errors"):
        raise RuntimeError("citation_consistency_precheck 为 blocked 或含 errors，不能生成 manuscript_v2")
    claim_matrix = load_required_json(project_root, "outputs/part5/claim_evidence_matrix.json")
    claims_by_id = claim_lookup_from_matrix(claim_matrix)
    figure_plan = load_required_json(project_root, "outputs/part5/figure_plan.json")
    critical = unresolved_critical_reviews(review_matrix)
    revisions = build_revision_actions(review_matrix, claims_by_id)

    public_v1 = remove_internal_lines(v1_text.replace("# 论文初稿 v1", "")).strip()
    revised_lines = [
        "# 论文修订稿 v2",
        "",
        public_v1,
        "",
        "## 证据边界与修订后表述",
        "",
        (
            "经结构、论证、证据、引用和写作规范复核后，本文只保留能够从既有材料回溯的阶段性判断。"
            "尚未获得充分材料支撑的内容不写成确定事实，而作为后续研究债务处理。"
        ),
        "",
        (
            "因此，修订稿的任务不是扩大论证范围，而是在既有论证树和大纲内形成连续正文，"
            "并为最终稿的语言收束、claim audit 和 citation audit 留出清晰边界。"
        ),
        "",
    ]
    write_text(project_root, "outputs/part5/manuscript_v2.md", "\n".join(revised_lines).strip() + "\n")

    residual_risks = [
        item
        for item in figure_plan.get("known_gaps", []) or []
        if isinstance(item, str)
    ]
    registered_blockers = [
        {
            "dimension": review.get("dimension"),
            "finding": review.get("finding"),
            "claim_ids": review.get("claim_ids", []),
        }
        for review in critical
    ]
    if critical:
        verdict = "blocked_by_evidence_debt"
    elif residual_risks:
        verdict = "ready_for_part6_with_research_debt"
    else:
        verdict = "ready_for_part6"

    revision_log = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "source_review_ref": "outputs/part5/review_matrix.json",
        "revisions": revisions,
        "residual_risks": residual_risks,
    }
    readiness = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "verdict": verdict,
        "registered_blockers": registered_blockers,
        "residual_risks": residual_risks,
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
    }

    write_json(project_root, "outputs/part5/revision_log.json", revision_log)
    write_json(project_root, "outputs/part5/part6_readiness_decision.json", readiness)
    return {"revision_log": revision_log, "part6_readiness_decision": readiness}


def _severity_counts(review_matrix: dict[str, Any]) -> dict[str, int]:
    return {
        severity: sum(
            1
            for review in review_matrix.get("reviews", []) or []
            if isinstance(review, dict) and review.get("severity") == severity
        )
        for severity in ["critical", "high", "medium", "low"]
    }


def generate_user_review_report(project_root: Path) -> str:
    require_files(project_root, [
        "outputs/part5/review_matrix.json",
        "outputs/part5/review_summary.md",
        "outputs/part5/claim_risk_report.json",
        "outputs/part5/citation_consistency_precheck.json",
    ])
    review_summary = (project_root / "outputs/part5/review_summary.md").read_text(encoding="utf-8").strip()
    review_matrix = load_required_json(project_root, "outputs/part5/review_matrix.json")
    risk_report = load_required_json(project_root, "outputs/part5/claim_risk_report.json")
    citation_precheck = load_required_json(project_root, "outputs/part5/citation_consistency_precheck.json")
    severity_counts = _severity_counts(review_matrix)
    reviews = [item for item in review_matrix.get("reviews", []) or [] if isinstance(item, dict)]
    risk_items = [item for item in risk_report.get("risk_items", []) or [] if isinstance(item, dict)]
    citation_errors = [
        item for item in citation_precheck.get("errors", []) or []
        if isinstance(item, str)
    ]
    citation_warnings = [
        item for item in citation_precheck.get("warnings", []) or []
        if isinstance(item, str)
    ]

    lines = [
        "# Part 5 Review Report",
        "",
        "## 结论",
        "",
        f"- review 项数: {len(reviews)}",
        f"- critical/high/medium/low: {severity_counts['critical']}/{severity_counts['high']}/{severity_counts['medium']}/{severity_counts['low']}",
        f"- claim 风险项: {len(risk_items)}",
        f"- citation precheck: {citation_precheck.get('status')}",
        "",
        "## 用户需要关注的风险",
    ]
    if risk_items:
        for item in risk_items[:12]:
            lines.append(
                f"- {item.get('claim_id', 'unknown')}: {item.get('risk_level', 'unknown')}；{item.get('reason', '')}"
            )
    else:
        lines.append("- 暂无 claim risk item。")

    lines.extend(["", "## 引文预检"])
    if citation_errors:
        lines.extend(f"- error: {error}" for error in citation_errors)
    if citation_warnings:
        lines.extend(f"- warning: {warning}" for warning in citation_warnings[:12])
    if not citation_errors and not citation_warnings:
        lines.append("- 未发现引文预检问题。")

    lines.extend(["", "## Review 明细"])
    for review in reviews[:20]:
        lines.append(
            f"- [{review.get('severity', 'unknown')}] {review.get('dimension', 'unknown')}: {review.get('finding', '')}"
        )

    lines.extend([
        "",
        "## 结构化摘要",
        "",
        review_summary,
        "",
    ])
    report_text = "\n".join(lines).strip() + "\n"
    write_text(project_root, "outputs/part5/review_report.md", report_text)
    return report_text


def run_step(project_root: Path, step: str) -> None:
    if step == "prep":
        generate_prep_package(project_root)
    elif step == "draft":
        generate_draft(project_root)
    elif step == "review":
        generate_review(project_root)
    elif step == "revise":
        generate_revision(project_root)
    elif step == "all":
        generate_prep_package(project_root)
        generate_draft(project_root)
        generate_review(project_root)
        generate_revision(project_root)
    else:
        raise ValueError(f"Unknown Part 5 step: {step}")


def print_summary(project_root: Path, step: str) -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Part 5 MVP step completed: {step}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for rel_path in [
        "outputs/part5/claim_evidence_matrix.json",
        "outputs/part5/citation_map.json",
        "outputs/part5/figure_plan.json",
        "outputs/part5/open_questions.json",
        "outputs/part5/manuscript_v1.md",
        "outputs/part5/review_matrix.json",
        "outputs/part5/review_summary.md",
        "outputs/part5/review_report.md",
        "outputs/part5/revision_log.json",
        "outputs/part5/manuscript_v2.md",
        "outputs/part5/part6_readiness_decision.json",
    ]:
        if (project_root / rel_path).exists():
            print(f"  ✓ {rel_path}")
    print("  Human gates are not auto-confirmed by this script.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate staged Part 5 MVP artifacts")
    parser.add_argument(
        "--step",
        choices=["prep", "draft", "review", "revise", "all"],
        default="prep",
        help="Part 5 step to run",
    )
    parser.add_argument(
        "--project-root",
        metavar="PATH",
        default=None,
        help="Project root; defaults to repository root",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT
    run_step(project_root, args.step)
    print_summary(project_root, args.step)


if __name__ == "__main__":
    main()
