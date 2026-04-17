#!/usr/bin/env python3
"""Part 5 writing-policy review fragment generator."""

from __future__ import annotations

from pathlib import Path

from part5_review_integrator import (
    load_required_json,
    require_manuscript_v1,
    require_part5_prep_confirmed,
    review_item,
    write_review_fragment,
)


DIMENSION = "writing_policy"


def policy_issues(source_index: dict) -> list[str]:
    issues: list[str] = []
    rules = source_index.get("rules")
    style_guides = source_index.get("style_guides")
    if not isinstance(rules, list) or not rules:
        issues.append("writing-policy/source_index.json 缺少 rules")
    if not isinstance(style_guides, list) or not style_guides:
        issues.append("writing-policy/source_index.json 缺少 style_guides")

    for group_name in ["rules", "style_guides", "reference_cases", "rubrics"]:
        items = source_index.get(group_name, [])
        if items is None:
            continue
        if not isinstance(items, list):
            issues.append(f"writing-policy/source_index.json {group_name} 必须是 list")
            continue
        for item in items:
            if not isinstance(item, dict):
                issues.append(f"writing-policy/source_index.json {group_name} 包含非 object 项")
                continue
            path = item.get("path")
            usage = item.get("usage", "")
            may_be_evidence = item.get("may_be_used_as_research_evidence")
            if not isinstance(path, str) or not path.startswith("writing-policy/"):
                issues.append(f"writing-policy 索引路径非法: {path}")
            usage_is_constraint = (
                isinstance(usage, str)
                and usage.endswith("_only")
                and "research_evidence" not in usage
            )
            if may_be_evidence is not False and not usage_is_constraint:
                issues.append(f"writing-policy 索引项未声明不可作为 research evidence: {path}")

    coverage = source_index.get("coverage", {})
    if isinstance(coverage, dict):
        if coverage.get("structure") is not True:
            issues.append("writing-policy coverage.structure 必须为 true")
        if coverage.get("expression") is not True:
            issues.append("writing-policy coverage.expression 必须为 true")
    return issues


def generate_review_fragment(project_root: Path) -> dict:
    require_part5_prep_confirmed(project_root)
    require_manuscript_v1(project_root)
    source_index = load_required_json(project_root, "writing-policy/source_index.json")
    issues = policy_issues(source_index)

    if issues:
        reviews = [
            review_item(
                review_id=f"writing_policy_review_{index:03d}",
                dimension=DIMENSION,
                severity="high",
                finding=issue,
                claim_ids=[],
                evidence_refs=[{"artifact": "writing-policy/source_index.json"}],
            )
            for index, issue in enumerate(issues, start=1)
        ]
    else:
        reviews = [
            review_item(
                review_id="writing_policy_review_001",
                dimension=DIMENSION,
                severity="low",
                finding="writing-policy 仅作为结构与表达约束层使用，未混入 research evidence。",
                status="resolved",
                claim_ids=[],
                evidence_refs=[{"artifact": "writing-policy/source_index.json"}],
            )
        ]

    return write_review_fragment(project_root, DIMENSION, reviews)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Part 5 writing-policy review fragment")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    generate_review_fragment(Path(args.project_root).resolve())
