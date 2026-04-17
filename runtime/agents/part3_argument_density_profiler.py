#!/usr/bin/env python3
"""
runtime/agents/part3_argument_density_profiler.py

Profile Part 3 argument density without modifying canonical artifacts.

用法：
  python3 runtime/agents/part3_argument_density_profiler.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEFAULT_OUTPUT_REF = "outputs/part3/argument_density_profile.json"
VIEWPOINT_TYPES = {"thesis", "main_argument", "sub_argument", "counterargument", "rebuttal"}
TARGETS = {
    "total_nodes": {"min": 12, "max": 18},
    "viewpoint_nodes": {"min": 9, "max": 13},
    "main_argument_nodes": {"min": 3, "max": 5},
    "sub_argument_nodes": {"min": 6, "max": 8},
    "counterargument_nodes": {"min": 1, "max": None},
}
REFERENCE_CASES = [
    "writing-policy/reference_cases/case_chinese_architecture_outline.md",
    "writing-policy/rubrics/chapter_argument_alignment.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def collect_nodes(node: dict[str, Any], depth: int = 0) -> list[tuple[dict[str, Any], int]]:
    nodes = [(node, depth)]
    for child in node.get("children", []) or []:
        if isinstance(child, dict):
            nodes.extend(collect_nodes(child, depth + 1))
    return nodes


def string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value]


def range_status(value: int, minimum: int, maximum: int | None) -> str:
    if value < minimum:
        return "low"
    if maximum is not None and value > maximum:
        return "high"
    return "pass"


def candidate_density(candidate: dict[str, Any], rel_path: str) -> dict[str, Any]:
    root = candidate.get("root")
    nodes = collect_nodes(root) if isinstance(root, dict) else []
    node_types = [str(node.get("node_type", "")) for node, _depth in nodes]
    innovation_flags: list[str] = []
    weak_flags: list[str] = []
    for node, _depth in nodes:
        for flag in string_list(node.get("risk_flags")):
            if flag.startswith("innovation_type:"):
                innovation_flags.append(flag.split(":", 1)[1])
            if flag in {"innovation_hypothesis", "requires_evidence_followup"}:
                weak_flags.append(flag)

    counts = {
        "total_nodes": len(nodes),
        "viewpoint_nodes": sum(1 for node_type in node_types if node_type in VIEWPOINT_TYPES),
        "main_argument_nodes": node_types.count("main_argument"),
        "sub_argument_nodes": node_types.count("sub_argument"),
        "evidence_nodes": node_types.count("evidence"),
        "counterargument_nodes": node_types.count("counterargument"),
        "rebuttal_nodes": node_types.count("rebuttal"),
        "max_depth": max((depth for _node, depth in nodes), default=0),
    }
    checks = {
        key: range_status(counts[key], target["min"], target["max"])
        for key, target in TARGETS.items()
    }
    return {
        "candidate_id": candidate.get("candidate_id"),
        "strategy": candidate.get("strategy"),
        "path": rel_path,
        "counts": counts,
        "checks": checks,
        "innovation_types": sorted(set(innovation_flags)),
        "weak_or_hypothesis_flags": sorted(set(weak_flags)),
        "status": "pass" if all(value == "pass" for value in checks.values()) else "needs_expansion",
    }


def candidate_paths(project_root: Path) -> list[Path]:
    roots = [
        project_root / "outputs" / "part3" / "candidate_argument_trees",
        project_root / "outputs" / "part3" / "refined_candidate_argument_trees",
    ]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        paths.extend(
            path
            for path in sorted(root.glob("*.json"))
            if path.name != "refinement_summary.json"
        )
    argument_tree = project_root / "outputs" / "part3" / "argument_tree.json"
    if argument_tree.exists():
        paths.append(argument_tree)
    return paths


def analyze_reference_case(path: Path, project_root: Path) -> dict[str, Any]:
    rel_path = path.relative_to(project_root).as_posix()
    if not path.exists():
        return {"path": rel_path, "exists": False}
    text = path.read_text(encoding="utf-8")
    numbered_sections = re.findall(r"(?m)^\s*\d+[.、]\s+", text)
    heading_count = len(re.findall(r"(?m)^#{1,4}\s+", text))
    argument_terms = {
        term: text.count(term)
        for term in ["论点", "观点", "论证", "主张", "thesis", "main_argument"]
    }
    return {
        "path": rel_path,
        "exists": True,
        "numbered_section_count": len(numbered_sections),
        "heading_count": heading_count,
        "argument_term_counts": argument_terms,
    }


def summarize_candidate_densities(densities: list[dict[str, Any]]) -> dict[str, Any]:
    if not densities:
        return {
            "candidate_count": 0,
            "status": "no_candidate_outputs",
            "recommendation": "当前 workspace 没有 Part 3 候选树；运行 part3-generate 后再统计真实候选密度。",
        }
    total_values = [item["counts"]["total_nodes"] for item in densities]
    viewpoint_values = [item["counts"]["viewpoint_nodes"] for item in densities]
    innovation_types = sorted({
        innovation_type
        for item in densities
        for innovation_type in item.get("innovation_types", [])
    })
    statuses = [item["status"] for item in densities]
    return {
        "candidate_count": len(densities),
        "total_nodes_range": [min(total_values), max(total_values)],
        "viewpoint_nodes_range": [min(viewpoint_values), max(viewpoint_values)],
        "innovation_type_count": len(innovation_types),
        "innovation_types": innovation_types,
        "status": "pass" if all(status == "pass" for status in statuses) else "needs_expansion",
        "recommendation": (
            "候选树密度达到 Part 3 发散生成目标。"
            if all(status == "pass" for status in statuses)
            else "至少一份候选树低于目标密度；应用 part3-argument-divergent-generate 扩展 sub_argument、counterargument 与创新假说。"
        ),
    }


def build_profile(project_root: Path, generated_at: str | None = None) -> dict[str, Any]:
    densities = []
    for path in candidate_paths(project_root):
        candidate = load_json(path)
        densities.append(candidate_density(candidate, path.relative_to(project_root).as_posix()))
    reference_cases = [
        analyze_reference_case(project_root / rel_path, project_root)
        for rel_path in REFERENCE_CASES
    ]
    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at or now_iso(),
        "scope_note": (
            "This profile reads local repository artifacts only. Clean root raw-library/research-wiki may be empty; "
            "reference cases are structure calibration, not research evidence."
        ),
        "targets": TARGETS,
        "reference_cases": reference_cases,
        "candidate_densities": densities,
        "summary": summarize_candidate_densities(densities),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile Part 3 argument density.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_REF, help=f"Output JSON path, default {DEFAULT_OUTPUT_REF}.")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without writing the report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    profile = build_profile(project_root)
    if args.dry_run:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    else:
        output_path = project_root / args.output
        write_json(output_path, profile)
        print(f"[OK] {args.output}")
        print(f"[INFO] {profile['summary']['status']}: {profile['summary']['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
