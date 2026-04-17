#!/usr/bin/env python3
"""
runtime/agents/part3_comparison_generator.py

Deterministic comparison generator for the three Part 3 argument tree candidates.

用法：
  python3 runtime/agents/part3_comparison_generator.py
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SCHEMA_VERSION = "1.0.0"
CANDIDATE_DIR = "outputs/part3/candidate_argument_trees"
COMPARISON_REF = "outputs/part3/candidate_comparison.json"
QUALITY_REPORT_REF = "outputs/part3/argument_quality_report.json"
SELECTION_TABLE_REF = "outputs/part3/candidate_selection_table.md"
WIKI_REF = "research-wiki/index.json"
EXPECTED_STRATEGIES = ("theory_first", "problem_solution", "case_application")
STATE_REF = "runtime/state.json"
QUALITY_DIMENSIONS = [
    "thesis_clarity",
    "warrant_strength",
    "evidence_fit",
    "counterargument_handling",
    "outline_viability",
    "risk_level",
]


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
        raise FileNotFoundError(f"缺少 state 文件: {STATE_REF}；不能在无状态审计下执行 Part 3 comparison")
    state = load_json(state_path)
    part2 = state.get("stages", {}).get("part2", {})
    if part2.get("status") != "completed" or part2.get("gate_passed") is not True:
        raise RuntimeError("Part 2 gate 尚未通过，不能生成 Part 3 candidate comparison")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def collect_node_refs(node: dict[str, Any]) -> tuple[list[str], list[str], int]:
    source_ids = [
        value
        for value in node.get("support_source_ids", [])
        if isinstance(value, str)
    ]
    page_ids = [
        value
        for value in node.get("wiki_page_ids", [])
        if isinstance(value, str)
    ]
    node_count = 1
    for child in node.get("children", []) or []:
        if not isinstance(child, dict):
            continue
        child_sources, child_pages, child_count = collect_node_refs(child)
        source_ids.extend(child_sources)
        page_ids.extend(child_pages)
        node_count += child_count
    return unique_strings(source_ids), unique_strings(page_ids), node_count


def collect_quality_signals(node: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    def walk(current: dict[str, Any]) -> None:
        nodes.append(current)
        for child in current.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    walk(node)
    node_count = max(len(nodes), 1)
    warrant_count = sum(1 for item in nodes if item.get("warrant"))
    evidence_summary_count = sum(1 for item in nodes if item.get("evidence_summary"))
    counter_count = sum(1 for item in nodes if item.get("node_type") in ("counterargument", "rebuttal"))
    limitation_count = sum(1 for item in nodes if item.get("limitations"))
    confidence_values = [
        float(item.get("confidence"))
        for item in nodes
        if isinstance(item.get("confidence"), (int, float))
    ]
    average_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.55
    risk_flags = unique_strings([
        flag
        for item in nodes
        for flag in item.get("risk_flags", []) or []
        if isinstance(flag, str)
    ])
    risk_level = "low"
    if any(flag in {"requires_human_selection", "seed_map_used"} for flag in risk_flags) or limitation_count >= 3:
        risk_level = "medium"
    if average_confidence < 0.55:
        risk_level = "high"
    return {
        "thesis_clarity": round(1.0 if node.get("node_type") == "thesis" and len(node.get("claim", "")) >= 20 else 0.65, 4),
        "warrant_strength": round(warrant_count / node_count, 4),
        "evidence_fit": round((evidence_summary_count / node_count + average_confidence) / 2, 4),
        "counterargument_handling": round(min(counter_count / 1, 1.0), 4),
        "outline_viability": round(min((node_count / 7) * 0.6 + average_confidence * 0.4, 1.0), 4),
        "risk_level": risk_level,
        "risk_flags": risk_flags,
    }


def summarize_argument_nodes(root: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for child in root.get("children", []) or []:
        if not isinstance(child, dict):
            continue
        summaries.append({
            "node_id": child.get("node_id", ""),
            "node_type": child.get("node_type", ""),
            "claim": child.get("claim", ""),
            "warrant": child.get("warrant", ""),
            "evidence_summary": child.get("evidence_summary", ""),
            "limitations": child.get("limitations", []) or [],
            "source_count": len(child.get("support_source_ids", []) or []),
            "wiki_page_count": len(child.get("wiki_page_ids", []) or []),
        })

    return summaries


def load_wiki_index(project_root: Path) -> dict[str, Any]:
    path = project_root / WIKI_REF
    if not path.exists():
        raise FileNotFoundError(f"缺少 wiki index: {WIKI_REF}")
    return load_json(path)


def all_wiki_refs(wiki_index: dict[str, Any]) -> tuple[list[str], list[str]]:
    pages = wiki_index.get("pages", [])
    if not isinstance(pages, list) or not pages:
        raise ValueError("research-wiki/index.json pages must be a non-empty array")
    page_ids = []
    source_ids = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id")
        if isinstance(page_id, str):
            page_ids.append(page_id)
        source_ids.extend([
            source_id
            for source_id in page.get("source_ids", [])
            if isinstance(source_id, str)
        ])
    return unique_strings(page_ids), unique_strings(source_ids)


def load_candidates(project_root: Path) -> list[dict[str, Any]]:
    candidate_dir = project_root / CANDIDATE_DIR
    if not candidate_dir.exists():
        raise FileNotFoundError(f"缺少候选目录: {CANDIDATE_DIR}")
    candidate_paths = sorted(candidate_dir.glob("*.json"))
    candidates = [load_json(path) for path in candidate_paths]
    strategies = sorted(candidate.get("strategy") for candidate in candidates)
    if len(candidates) != 3 or strategies != sorted(EXPECTED_STRATEGIES):
        raise ValueError(
            "Part 3 comparison requires exactly three candidates with strategies: "
            + ", ".join(EXPECTED_STRATEGIES)
        )
    return sorted(candidates, key=lambda item: item.get("candidate_id", ""))


def strengths_for(strategy: str) -> list[str]:
    mapping = {
        "theory_first": [
            "概念边界清晰，适合先建立中文论文的理论定义。",
            "论证顺序从概念到方法再到主题，章节承接稳定。",
        ],
        "problem_solution": [
            "问题意识突出，便于回应研究缺口和论文创新性。",
            "从诊断到解决路径的逻辑更适合形成摘要和引言主线。",
        ],
        "case_application": [
            "案例抓手明确，适合建筑设计背景下的空间分析写作。",
            "从对象观察到方法提炼再到应用结论，读者进入成本低。",
        ],
    }
    return mapping.get(strategy, ["结构完整，保留了 wiki 与来源回溯。"])


def weaknesses_for(strategy: str) -> list[str]:
    mapping = {
        "theory_first": [
            "如果后续证据不足，容易显得理论先行而案例支撑偏弱。",
            "需要在大纲阶段补足具体案例与应用章节。",
        ],
        "problem_solution": [
            "对 research gap 的表达要求较高，否则问题链会显得人为。",
            "需要避免把所有材料都压成单一问题叙事。",
        ],
        "case_application": [
            "如果案例页覆盖不足，论文可能偏案例描述而非理论论证。",
            "需要在大纲阶段明确案例外推的边界。",
        ],
    }
    return mapping.get(strategy, ["需要人工检查论点是否与研究主题完全贴合。"])


def risks_for(strategy: str, evidence_ratio: float, wiki_ratio: float) -> list[str]:
    risks = []
    if evidence_ratio < 0.8:
        risks.append("evidence coverage 未覆盖全部 source_id，锁定前需检查遗漏文献是否关键。")
    if wiki_ratio < 0.8:
        risks.append("wiki coverage 未覆盖全部 page_id，锁定前需检查遗漏页面是否影响论证完整性。")
    if strategy == "theory_first":
        risks.append("理论优先结构需要防止背景综述过重。")
    elif strategy == "problem_solution":
        risks.append("问题-解决结构需要人工确认研究问题不是后置包装。")
    elif strategy == "case_application":
        risks.append("案例应用结构需要人工确认案例推论可以回溯到来源证据。")
    return risks


def score_candidate(strategy: str, evidence_ratio: float, wiki_ratio: float, node_count: int) -> float:
    strategy_bonus = {
        "theory_first": 0.03,
        "problem_solution": 0.05,
        "case_application": 0.04,
    }.get(strategy, 0.0)
    structure_bonus = min(node_count / 10, 1.0) * 0.1
    return round(evidence_ratio * 0.45 + wiki_ratio * 0.4 + structure_bonus + strategy_bonus, 4)


def quality_score(quality: dict[str, Any]) -> float:
    numeric_dimensions = [
        "thesis_clarity",
        "warrant_strength",
        "evidence_fit",
        "counterargument_handling",
        "outline_viability",
    ]
    return sum(float(quality.get(key, 0) or 0) for key in numeric_dimensions) / len(numeric_dimensions)


def markdown_cell(value: Any) -> str:
    if isinstance(value, list):
        text = "<br>".join(str(item) for item in value if str(item).strip())
    else:
        text = str(value or "")
    return text.replace("|", "\\|").replace("\n", "<br>")


def ratio_label(coverage: dict[str, Any] | None) -> str:
    if not isinstance(coverage, dict):
        return "—"
    count = coverage.get("source_count", coverage.get("page_count", 0))
    total = coverage.get("total_wiki_source_count", coverage.get("total_wiki_page_count", 0))
    ratio = coverage.get("coverage_ratio", 0)
    try:
        percent = f"{float(ratio) * 100:.0f}%"
    except (TypeError, ValueError):
        percent = "—"
    return f"{count}/{total} ({percent})"


def percent_label(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


def quality_label(quality: dict[str, Any] | None) -> str:
    if not isinstance(quality, dict):
        return "—"
    return (
        f"thesis {percent_label(quality.get('thesis_clarity'))}, "
        f"warrant {percent_label(quality.get('warrant_strength'))}, "
        f"evidence {percent_label(quality.get('evidence_fit'))}, "
        f"counter {percent_label(quality.get('counterargument_handling'))}, "
        f"outline {percent_label(quality.get('outline_viability'))}, "
        f"risk {quality.get('risk_level', '—')}"
    )


def compact_text(value: Any, *, limit: int) -> str:
    text = str(value or "—")
    text = " ".join(text.replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；;、 ") + "…"


def thesis_brief(thesis: str) -> str:
    if " Seed map 侧重：" in thesis:
        thesis = thesis.split(" Seed map 侧重：", 1)[0]
    return compact_text(thesis, limit=50)


def argument_claims_cell(nodes: list[dict[str, Any]]) -> str:
    claims = [
        compact_text(node.get("claim", ""), limit=46)
        for node in nodes
        if isinstance(node, dict) and str(node.get("claim", "")).strip()
    ]
    if not claims:
        return "—"
    return "<br>".join(f"{index}. {claim}" for index, claim in enumerate(claims[:4], start=1))


def recommendation_reason(item: dict[str, Any], recommended_id: str | None) -> str:
    candidate_id = item.get("candidate_id", "")
    strengths = item.get("strengths") or []
    weaknesses = item.get("weaknesses") or []
    if candidate_id == recommended_id:
        reason = strengths[0] if strengths else "综合分数最高，适合作为优先方案。"
        return f"推荐：{compact_text(reason, limit=42)}"
    reason = strengths[0] if strengths else "可作为备选主线。"
    caveat = weaknesses[0] if weaknesses else ""
    if caveat:
        return f"备选：{compact_text(reason, limit=30)}；注意{compact_text(caveat, limit=24)}"
    return f"备选：{compact_text(reason, limit=42)}"


def strategy_label(strategy: str) -> str:
    labels = {
        "theory_first": "理论优先",
        "problem_solution": "问题-解决",
        "case_application": "案例应用",
    }
    return labels.get(strategy, strategy)


def selection_focus(strategy: str) -> str:
    mapping = {
        "theory_first": "适合先定义概念边界，再展开方法和材料。",
        "problem_solution": "适合突出研究缺口，并形成摘要、引言和章节主线。",
        "case_application": "适合以建筑案例和设计转译为抓手展开。",
    }
    return mapping.get(strategy, "需结合论文目标人工判断。")


def selection_tradeoff(strategy: str) -> str:
    mapping = {
        "theory_first": "可能让论文前半部分偏理论综述，需要后续大纲补足案例和应用。",
        "problem_solution": "对研究问题表述要求最高，需要避免把材料硬压成单一问题。",
        "case_application": "可能让论文偏案例描述，需要明确案例如何外推为论证。",
    }
    return mapping.get(strategy, "需要人工检查与论文目标的匹配度。")


def candidate_command(candidate_id: str) -> str:
    return f'python3 cli.py part3-select --candidate-id {candidate_id} --notes "选择理由"'


def render_selection_table(comparison: dict[str, Any]) -> str:
    candidates = [
        item
        for item in comparison.get("candidates", [])
        if isinstance(item, dict)
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (-float(item.get("score", 0) or 0), item.get("candidate_id", "")),
    )
    recommendation = comparison.get("recommendation", {})
    recommended_id = recommendation.get("recommended_candidate_id")

    lines = [
        "# Part 3 人工选择表",
        "",
        "这张表只用于人工选择。系统推荐只是排序参考，不会自动锁定。",
        "",
        f"- generated_at: {comparison.get('generated_at', 'unknown')}",
        f"- comparison_ref: {COMPARISON_REF}",
        "- human_decision_required: true",
        "",
        "## 可视化对比",
        "",
        "| 选项 | 推荐 | 候选 ID | 主线 | 分数 | 推荐理由 | 核心主张（约50字） | 论点 | 适合选择情况 | 代价 |",
        "|---:|---|---|---|---:|---|---|---|---|---|",
    ]

    for index, item in enumerate(ranked, start=1):
        candidate_id = item.get("candidate_id", "")
        strategy = item.get("strategy", "")
        marker = "推荐" if candidate_id == recommended_id else "备选"
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(index),
                    markdown_cell(marker),
                    markdown_cell(candidate_id),
                    markdown_cell(strategy_label(strategy)),
                    markdown_cell(item.get("score", "—")),
                    markdown_cell(recommendation_reason(item, recommended_id)),
                    markdown_cell(thesis_brief(item.get("thesis", ""))),
                    markdown_cell(argument_claims_cell(item.get("argument_nodes", []) or [])),
                    markdown_cell(selection_focus(strategy)),
                    markdown_cell(selection_tradeoff(strategy)),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            f"- recommended_candidate_id: {recommended_id or 'unknown'}",
            "- note: 最终仍需用户明确选择 candidate_id 和选择理由。",
            "",
        ]
    )
    return "\n".join(lines)


def build_comparison(project_root: Path = PROJECT_ROOT, generated_at: str | None = None) -> dict[str, Any]:
    assert_part2_gate_passed(project_root)
    wiki_index = load_wiki_index(project_root)
    all_page_ids, all_source_ids = all_wiki_refs(wiki_index)
    candidates = load_candidates(project_root)
    timestamp = generated_at or now_iso()
    candidate_tree_refs = [
        f"{CANDIDATE_DIR}/{candidate['candidate_id']}.json"
        for candidate in candidates
    ]

    comparison_items = []
    for candidate in candidates:
        strategy = candidate.get("strategy", "unknown")
        source_ids, page_ids, node_count = collect_node_refs(candidate.get("root", {}))
        evidence_ratio = round(len(set(source_ids)) / max(len(set(all_source_ids)), 1), 4)
        wiki_ratio = round(len(set(page_ids)) / max(len(set(all_page_ids)), 1), 4)
        quality = collect_quality_signals(candidate.get("root", {}))
        score = round(
            score_candidate(strategy, evidence_ratio, wiki_ratio, node_count) * 0.7
            + quality_score(quality) * 0.3,
            4,
        )
        comparison_items.append({
            "candidate_id": candidate.get("candidate_id"),
            "strategy": strategy,
            "thesis": candidate.get("root", {}).get("claim", ""),
            "argument_nodes": summarize_argument_nodes(candidate.get("root", {})),
            "strengths": strengths_for(strategy),
            "weaknesses": weaknesses_for(strategy),
            "evidence_coverage": {
                "source_ids": source_ids,
                "source_count": len(source_ids),
                "total_wiki_source_count": len(all_source_ids),
                "coverage_ratio": evidence_ratio,
            },
            "wiki_coverage": {
                "page_ids": page_ids,
                "page_count": len(page_ids),
                "total_wiki_page_count": len(all_page_ids),
                "coverage_ratio": wiki_ratio,
            },
            "quality": {
                "thesis_clarity": quality["thesis_clarity"],
                "warrant_strength": quality["warrant_strength"],
                "evidence_fit": quality["evidence_fit"],
                "counterargument_handling": quality["counterargument_handling"],
                "outline_viability": quality["outline_viability"],
                "risk_level": quality["risk_level"],
            },
            "risks": risks_for(strategy, evidence_ratio, wiki_ratio),
            "score": score,
        })

    ranked = sorted(comparison_items, key=lambda item: (-item["score"], item["candidate_id"]))
    recommendation = {
        "recommended_candidate_id": ranked[0]["candidate_id"],
        "reason": (
            f"{ranked[0]['candidate_id']} 在 evidence coverage、wiki coverage 与结构完整度上综合得分最高；"
            "仍需用户结合论文写作目标进行最终人工选择。"
        ),
        "selection_cautions": [
            "recommendation 不是 human selection，不能据此自动锁定 canonical argument_tree.json。",
            "锁定前需要人工确认 candidate_id 与选择理由。",
        ],
        "human_decision_required": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "wiki_ref": WIKI_REF,
        "candidate_dir": CANDIDATE_DIR,
        "candidate_tree_refs": candidate_tree_refs,
        "quality_dimensions": QUALITY_DIMENSIONS,
        "candidates": comparison_items,
        "recommendation": recommendation,
    }


def build_quality_report(comparison: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        item
        for item in comparison.get("candidates", []) or []
        if isinstance(item, dict)
    ]
    findings = []
    for item in candidates:
        quality = item.get("quality", {}) if isinstance(item.get("quality"), dict) else {}
        low_dimensions = [
            key
            for key in QUALITY_DIMENSIONS
            if key != "risk_level" and float(quality.get(key, 0) or 0) < 0.75
        ]
        findings.append({
            "candidate_id": item.get("candidate_id"),
            "strategy": item.get("strategy"),
            "quality": quality,
            "strengths": item.get("strengths", []),
            "weaknesses": item.get("weaknesses", []),
            "risks": item.get("risks", []),
            "refinement_targets": low_dimensions,
        })

    ready_count = sum(
        1
        for item in candidates
        if item.get("quality", {}).get("risk_level") in ("low", "medium")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": comparison.get("generated_at"),
        "wiki_ref": comparison.get("wiki_ref", WIKI_REF),
        "candidate_comparison_ref": COMPARISON_REF,
        "quality_dimensions": list(QUALITY_DIMENSIONS),
        "candidate_findings": findings,
        "outline_readiness": {
            "status": "ready_for_human_selection" if ready_count else "blocked_for_refinement",
            "ready_candidate_count": ready_count,
            "human_decision_required": True,
            "notes": "quality report 只辅助人工选择或 refine，不得自动锁定 canonical argument_tree.json。",
        },
    }


def generate_comparison(project_root: Path = PROJECT_ROOT, generated_at: str | None = None) -> dict[str, Any]:
    comparison = build_comparison(project_root=project_root, generated_at=generated_at)
    quality_report = build_quality_report(comparison)
    write_json(project_root / COMPARISON_REF, comparison)
    write_json(project_root / QUALITY_REPORT_REF, quality_report)
    write_text(project_root / SELECTION_TABLE_REF, render_selection_table(comparison))
    return comparison


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Part 3 candidate comparison.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    try:
        comparison = generate_comparison(project_root=project_root)
    except Exception as exc:
        print(f"[ERR] Part 3 comparison generation failed: {exc}", file=sys.stderr)
        return 1

    recommended = comparison["recommendation"]["recommended_candidate_id"]
    print(f"[OK] {COMPARISON_REF}")
    print(f"[OK] {QUALITY_REPORT_REF}")
    print(f"[OK] {SELECTION_TABLE_REF}")
    print(f"[INFO] 推荐候选: {recommended}；仍需 human selection/locking 后才能生成 canonical argument_tree.json。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
