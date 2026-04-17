#!/usr/bin/env python3
"""
runtime/agents/part3_argument_refiner.py

Refine Part 3 candidate argument trees without touching the original candidates
or the canonical argument_tree.json.

用法：
  python3 runtime/agents/part3_argument_refiner.py
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SCHEMA_VERSION = "1.0.0"
STATE_REF = "runtime/state.json"
ARGUMENT_SEED_MAP_REF = "outputs/part3/argument_seed_map.json"
ARGUMENT_QUALITY_REPORT_REF = "outputs/part3/argument_quality_report.json"
COMPARISON_REF = "outputs/part3/candidate_comparison.json"
CANDIDATE_DIR = "outputs/part3/candidate_argument_trees"
REFINED_CANDIDATE_DIR = "outputs/part3/refined_candidate_argument_trees"
ARGUMENT_TREE_REF = "outputs/part3/argument_tree.json"
FEEDBACK_REF = "outputs/part3/human_selection_feedback.json"
EXPECTED_STRATEGIES = ("theory_first", "problem_solution", "case_application")
REFINEMENT_SUMMARY_NAME = "refinement_summary.json"


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


def assert_part2_gate_passed(project_root: Path) -> None:
    state_path = project_root / STATE_REF
    if not state_path.exists():
        raise FileNotFoundError(f"缺少 state 文件: {STATE_REF}；不能在无状态审计下 refine Part 3 candidates")
    state = load_json(state_path)
    part2 = state.get("stages", {}).get("part2", {})
    if part2.get("status") != "completed" or part2.get("gate_passed") is not True:
        raise RuntimeError("Part 2 gate 尚未通过，不能 refine Part 3 candidate argument trees")


def load_required_inputs(project_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    seed_path = project_root / ARGUMENT_SEED_MAP_REF
    quality_report_path = project_root / ARGUMENT_QUALITY_REPORT_REF
    comparison_path = project_root / COMPARISON_REF
    candidate_dir = project_root / CANDIDATE_DIR
    if not seed_path.exists():
        raise FileNotFoundError(f"缺少 argument seed map: {ARGUMENT_SEED_MAP_REF}；先运行 `python3 cli.py part3-seed-map`")
    if not quality_report_path.exists():
        raise FileNotFoundError(f"缺少 argument quality report: {ARGUMENT_QUALITY_REPORT_REF}；先运行 `python3 cli.py part3-compare`")
    if not comparison_path.exists():
        raise FileNotFoundError(f"缺少 candidate comparison: {COMPARISON_REF}；先运行 `python3 cli.py part3-compare`")
    if not candidate_dir.exists():
        raise FileNotFoundError(f"缺少候选目录: {CANDIDATE_DIR}")

    candidates = [load_json(path) for path in sorted(candidate_dir.glob("*.json"))]
    strategies = sorted(candidate.get("strategy") for candidate in candidates)
    if len(candidates) != 3 or strategies != sorted(EXPECTED_STRATEGIES):
        raise ValueError(
            "Part 3 refine requires exactly three original candidates with strategies: "
            + ", ".join(EXPECTED_STRATEGIES)
        )
    return load_json(seed_path), load_json(quality_report_path), load_json(comparison_path), candidates


def selection_exists(project_root: Path) -> bool:
    return (project_root / ARGUMENT_TREE_REF).exists() or (project_root / FEEDBACK_REF).exists()


def find_quality(comparison: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for item in comparison.get("candidates", []) or []:
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            quality = item.get("quality", {})
            return quality if isinstance(quality, dict) else {}
    return {}


def find_quality_from_report(quality_report: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for item in quality_report.get("candidate_findings", []) or []:
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            quality = item.get("quality", {})
            return quality if isinstance(quality, dict) else {}
    return {}


def first_seed_text(seed_map: dict[str, Any], key: str, fallback: str) -> str:
    values = seed_map.get(key, []) or []
    for value in values:
        if isinstance(value, dict) and isinstance(value.get("text"), str) and value["text"].strip():
            return value["text"].strip()
    return fallback


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def refine_node(node: dict[str, Any], quality: dict[str, Any], seed_map: dict[str, Any], *, is_root: bool = False) -> dict[str, Any]:
    children = [
        refine_node(child, quality, seed_map, is_root=False)
        for child in node.get("children", []) or []
        if isinstance(child, dict)
    ]
    limitations = list(node.get("limitations", []) or [])
    assumptions = list(node.get("assumptions", []) or [])
    risk_flags = list(node.get("risk_flags", []) or [])
    if quality.get("counterargument_handling", 0) < 1:
        limitations.append("需要在大纲阶段继续显式处理反方观点。")
        risk_flags.append("counterargument_needs_outline_followup")
    if quality.get("evidence_fit", 0) < 0.8:
        assumptions.append("证据适配度需要在 Part 4 reference alignment 中复核。")
        risk_flags.append("evidence_fit_needs_recheck")

    refined = {
        **node,
        "children": children,
        "warrant": node.get("warrant") or "该节点已在 refine 阶段补充推理依据，但仍需人工选择后才能进入 canonical。",
        "evidence_summary": node.get("evidence_summary") or first_seed_text(seed_map, "evidence_points", "Part 2 wiki evidence"),
        "assumptions": unique_strings(assumptions + ["refine 结果不能绕过 argument_tree_selected human gate"]),
        "limitations": unique_strings(limitations + ["refined candidate 不是 canonical artifact"]),
        "risk_flags": unique_strings(risk_flags + ["refined"]),
        "confidence": min(float(node.get("confidence", 0.68) or 0.68) + 0.04, 0.92),
    }
    if is_root:
        refined["claim"] = (
            f"{node.get('claim', '')} Refine 补充："
            f"{first_seed_text(seed_map, 'method_paths', '论证路径需要由 seed map 与 comparison 共同约束。')}"
        )
    return refined


def build_refined_candidate(
    candidate: dict[str, Any],
    seed_map: dict[str, Any],
    quality_report: dict[str, Any],
    comparison: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("candidate must include candidate_id")
    quality = find_quality_from_report(quality_report, candidate_id) or find_quality(comparison, candidate_id)
    refined_id = f"{candidate_id}_refined"
    return {
        **candidate,
        "schema_version": SCHEMA_VERSION,
        "candidate_id": refined_id,
        "generated_at": generated_at,
        "based_on_candidate_ref": f"{CANDIDATE_DIR}/{candidate_id}.json",
        "argument_seed_map_ref": ARGUMENT_SEED_MAP_REF,
        "argument_quality_report_ref": ARGUMENT_QUALITY_REPORT_REF,
        "candidate_comparison_ref": COMPARISON_REF,
        "root": refine_node(candidate.get("root", {}), quality, seed_map, is_root=True),
        "generation_notes": (
            "refined candidate generated from original candidate, argument_seed_map.json, "
            "and candidate_comparison.json; original candidates and canonical argument_tree.json were not modified."
        ),
    }


def refine_candidates(
    project_root: Path = PROJECT_ROOT,
    generated_at: str | None = None,
    *,
    force: bool = False,
    allow_after_selection: bool = False,
) -> list[dict[str, Any]]:
    assert_part2_gate_passed(project_root)
    if selection_exists(project_root) and not allow_after_selection:
        raise RuntimeError(
            "Part 3 human selection or canonical argument_tree already exists; "
            "refine is blocked after human selection unless an explicit safety parameter is used."
        )

    output_dir = project_root / REFINED_CANDIDATE_DIR
    existing_refined = sorted(output_dir.glob("*.json")) if output_dir.exists() else []
    if existing_refined and not force:
        raise FileExistsError(
            f"{REFINED_CANDIDATE_DIR} already contains refined candidates. Use --force to overwrite refined outputs only."
        )

    seed_map, quality_report, comparison, candidates = load_required_inputs(project_root)
    timestamp = generated_at or now_iso()
    refined = [
        build_refined_candidate(candidate, seed_map, quality_report, comparison, timestamp)
        for candidate in candidates
    ]
    for candidate in refined:
        write_json(output_dir / f"{candidate['candidate_id']}.json", candidate)
    write_json(
        output_dir / REFINEMENT_SUMMARY_NAME,
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": timestamp,
            "argument_seed_map_ref": ARGUMENT_SEED_MAP_REF,
            "argument_quality_report_ref": ARGUMENT_QUALITY_REPORT_REF,
            "candidate_comparison_ref": COMPARISON_REF,
            "source_candidate_dir": CANDIDATE_DIR,
            "refined_candidate_dir": REFINED_CANDIDATE_DIR,
            "refined_candidate_refs": [
                f"{REFINED_CANDIDATE_DIR}/{candidate['candidate_id']}.json"
                for candidate in refined
            ],
            "human_decision_required": True,
            "notes": "refinement_summary 只记录 refine 结果；canonical lock 仍必须通过 part3-select human selection。",
        },
    )
    return refined


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refine Part 3 candidates without writing canonical argument_tree.json.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing refined candidates only; original candidates are never overwritten.")
    parser.add_argument(
        "--allow-after-selection",
        action="store_true",
        help="Allow refine after human_selection_feedback or canonical argument_tree exists; does not modify canonical.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    try:
        refined = refine_candidates(
            project_root=project_root,
            force=args.force,
            allow_after_selection=args.allow_after_selection,
        )
    except Exception as exc:
        print(f"[ERR] Part 3 refine failed: {exc}", file=sys.stderr)
        return 1
    for candidate in refined:
        print(f"[OK] {REFINED_CANDIDATE_DIR}/{candidate['candidate_id']}.json")
    print("[INFO] 未覆盖原始候选；未写入 outputs/part3/argument_tree.json。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
