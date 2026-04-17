#!/usr/bin/env python3
"""
runtime/agents/part3_selection_locker.py

Lock one human-selected Part 3 candidate as canonical argument_tree.json.

用法：
  python3 runtime/agents/part3_selection_locker.py --candidate-id candidate_theory_first --notes "选择理由"
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.writing_contract import clean_claim_text  # noqa: E402

SCHEMA_VERSION = "1.0.0"
CANDIDATE_DIR = "outputs/part3/candidate_argument_trees"
REFINED_CANDIDATE_DIR = "outputs/part3/refined_candidate_argument_trees"
COMPARISON_REF = "outputs/part3/candidate_comparison.json"
FEEDBACK_REF = "outputs/part3/human_selection_feedback.json"
ARGUMENT_TREE_REF = "outputs/part3/argument_tree.json"
WIKI_REF = "research-wiki/index.json"
PROCESS_MEMORY_DIR = "process-memory"
STATE_REF = "runtime/state.json"
PART4_ARTIFACT_REFS = [
    "outputs/part4/paper_outline.json",
    "outputs/part4/outline_rationale.json",
    "outputs/part4/reference_alignment_report.json",
]
CANDIDATE_SOURCES = ("original", "refined")


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


def restore_or_remove(path: Path, backup_path: Path | None) -> None:
    if backup_path and backup_path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.replace(path)
    elif path.exists():
        path.unlink()


def cleanup_path(path: Path) -> None:
    if path.exists():
        path.unlink()


def read_file_snapshot(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() and path.is_file() else None


def snapshot_tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def restore_file_snapshot(path: Path, content: bytes | None) -> None:
    if content is None:
        cleanup_path(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def restore_tree_snapshot(root: Path, snapshot: dict[str, bytes]) -> None:
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file() and str(path.relative_to(root)) not in snapshot:
                path.unlink()
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir() and path != root:
                try:
                    path.rmdir()
                except OSError:
                    pass
    for rel_path, content in snapshot.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def snapshot_process_memory(project_root: Path) -> dict[str, bytes]:
    memory_dir = project_root / PROCESS_MEMORY_DIR
    if not memory_dir.exists():
        return {}
    return {
        path.name: path.read_bytes()
        for path in sorted(memory_dir.glob("*.json"))
        if path.is_file()
    }


def restore_process_memory(project_root: Path, snapshot: dict[str, bytes]) -> None:
    memory_dir = project_root / PROCESS_MEMORY_DIR
    if memory_dir.exists():
        for path in sorted(memory_dir.glob("*.json")):
            if path.name not in snapshot:
                path.unlink()
    for filename, content in snapshot.items():
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / filename).write_bytes(content)


def snapshot_relock_transaction(project_root: Path) -> dict[str, Any]:
    tracked_files = [
        FEEDBACK_REF,
        ARGUMENT_TREE_REF,
        STATE_REF,
        *PART4_ARTIFACT_REFS,
    ]
    return {
        "files": {
            rel_path: read_file_snapshot(project_root / rel_path)
            for rel_path in tracked_files
        },
        "part4_tree": snapshot_tree(project_root / "outputs" / "part4"),
        "process_memory": snapshot_process_memory(project_root),
    }


def restore_relock_transaction(project_root: Path, snapshot: dict[str, Any]) -> None:
    restore_tree_snapshot(project_root / "outputs" / "part4", snapshot["part4_tree"])
    for rel_path, content in snapshot["files"].items():
        restore_file_snapshot(project_root / rel_path, content)
    restore_process_memory(project_root, snapshot["process_memory"])


def assert_selection_state_ready(project_root: Path) -> dict[str, Any]:
    state_path = project_root / STATE_REF
    if not state_path.exists():
        raise FileNotFoundError(
            f"缺少 state 文件: {STATE_REF}；不能在无审计状态下锁定 canonical argument tree"
        )

    try:
        state = load_json(state_path)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"State file is corrupted; cannot lock Part 3 canonical artifact: {exc}") from exc

    stages = state.get("stages", {})
    part2 = stages.get("part2", {})
    if part2.get("status") != "completed" or part2.get("gate_passed") is not True:
        raise RuntimeError("Part 2 gate 尚未通过，不能锁定 Part 3 canonical argument tree")
    part3 = stages.get("part3")
    if not isinstance(part3, dict):
        raise RuntimeError("runtime/state.json 缺少 stages.part3，不能记录 argument_tree_selected gate")
    return state


def record_human_gate(project_root: Path, notes: str, confirmed_at: str) -> None:
    state_path = project_root / STATE_REF
    state = assert_selection_state_ready(project_root)
    part3 = state["stages"]["part3"]

    completed_gates = part3.setdefault("human_gates_completed", [])
    if "argument_tree_selected" not in completed_gates:
        completed_gates.append("argument_tree_selected")

    record = {
        "gate_id": "argument_tree_selected",
        "stage_id": "part3",
        "confirmed_at": confirmed_at,
        "notes": notes,
    }
    state.setdefault("human_decision_log", []).append(record)
    shutil.copy2(state_path, str(state_path) + ".bak")
    write_json(state_path, state)

    memory_dir = project_root / PROCESS_MEMORY_DIR
    memory_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    write_json(
        memory_dir / f"{ts}_human_gate_confirmed.json",
        {"event": "human_gate_confirmed", "timestamp": confirmed_at, **record},
    )


def invalidate_part4_after_part3_relock(project_root: Path, invalidated_at: str) -> None:
    """Remove stale Part 4 artifacts/state after a forced Part 3 canonical relock."""
    existing_artifacts = [
        project_root / rel_path
        for rel_path in PART4_ARTIFACT_REFS
        if (project_root / rel_path).exists()
    ]
    state_path = project_root / STATE_REF
    state = load_json(state_path) if state_path.exists() else {}
    part4 = state.get("stages", {}).get("part4", {}) if isinstance(state, dict) else {}
    completed_gates = part4.get("human_gates_completed", []) if isinstance(part4, dict) else []
    has_outline_gate = isinstance(completed_gates, list) and "outline_confirmed" in completed_gates
    if not existing_artifacts and not has_outline_gate:
        return

    safe_ts = invalidated_at.replace(":", "").replace("-", "")
    backup_dir = project_root / "outputs" / "part4" / f"invalidated_by_part3_relock_{safe_ts}"
    for artifact_path in existing_artifacts:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(artifact_path), str(backup_dir / artifact_path.name))

    if state_path.exists() and isinstance(part4, dict):
        if isinstance(completed_gates, list):
            part4["human_gates_completed"] = [
                gate for gate in completed_gates if gate != "outline_confirmed"
            ]
        part4["gate_passed"] = False
        if part4.get("status") == "completed":
            part4["status"] = "in_progress"
            part4["completed_at"] = None
        state["current_stage"] = "part3"
        state.setdefault("human_decision_log", []).append(
            {
                "event": "part4_invalidated",
                "stage_id": "part4",
                "invalidated_at": invalidated_at,
                "reason": "Part 3 canonical argument tree was force-relocked; Part 4 artifacts must be regenerated and reconfirmed.",
                "backup_dir": str(backup_dir.relative_to(project_root)) if backup_dir.exists() else None,
            }
        )
        shutil.copy2(state_path, str(state_path) + ".bak")
        write_json(state_path, state)

    memory_dir = project_root / PROCESS_MEMORY_DIR
    memory_dir.mkdir(exist_ok=True)
    write_json(
        memory_dir / f"{safe_ts}_part4_invalidated.json",
        {
            "event": "part4_invalidated",
            "timestamp": invalidated_at,
            "stage_id": "part4",
            "reason": "Part 3 canonical argument tree was force-relocked; Part 4 artifacts must be regenerated and reconfirmed.",
            "backup_dir": str(backup_dir.relative_to(project_root)) if backup_dir.exists() else None,
        },
    )


def validate_notes(notes: str) -> str:
    normalized = notes.strip()
    if not normalized:
        raise ValueError("--notes 不能为空；Part 3 canonical lock 必须保留人工选择依据")
    return normalized


def candidate_dir_for_source(candidate_source: str) -> str:
    if candidate_source not in CANDIDATE_SOURCES:
        raise ValueError("--candidate-source must be original or refined")
    return REFINED_CANDIDATE_DIR if candidate_source == "refined" else CANDIDATE_DIR


def candidate_path(project_root: Path, candidate_id: str, candidate_source: str = "original") -> Path:
    safe_id = candidate_id.strip()
    if not safe_id or "/" in safe_id or "\\" in safe_id or safe_id in (".", ".."):
        raise ValueError("--candidate-id must be a candidate file stem, e.g. candidate_theory_first")
    return project_root / candidate_dir_for_source(candidate_source) / f"{safe_id}.json"


def load_required_inputs(
    project_root: Path,
    candidate_id: str,
    candidate_source: str = "original",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    candidate_file = candidate_path(project_root, candidate_id, candidate_source)
    if not candidate_file.exists():
        raise FileNotFoundError(f"候选不存在: {candidate_file.relative_to(project_root)}")
    comparison_file = project_root / COMPARISON_REF
    if not comparison_file.exists():
        raise FileNotFoundError(f"缺少候选比较: {COMPARISON_REF}")
    wiki_file = project_root / WIKI_REF
    if not wiki_file.exists():
        raise FileNotFoundError(f"缺少 wiki index: {WIKI_REF}")

    candidate = load_json(candidate_file)
    comparison = load_json(comparison_file)
    if candidate.get("candidate_id") != candidate_id:
        raise ValueError("candidate_id 与候选文件名不一致")

    compared_ids = {
        item.get("candidate_id")
        for item in comparison.get("candidates", [])
        if isinstance(item, dict)
    }
    compared_id = candidate_id
    if candidate_source == "refined":
        based_on_ref = candidate.get("based_on_candidate_ref")
        if not isinstance(based_on_ref, str) or not based_on_ref.startswith(f"{CANDIDATE_DIR}/"):
            raise ValueError("refined candidate 必须保留 based_on_candidate_ref")
        compared_id = Path(based_on_ref).stem
    if compared_id not in compared_ids:
        raise ValueError(f"{candidate_id} 未出现在 candidate_comparison.json 中，不能锁定")
    return candidate, comparison, str(candidate_file.relative_to(project_root))


def build_feedback(
    candidate: dict[str, Any],
    notes: str,
    selected_at: str,
    *,
    candidate_source: str,
    candidate_tree_ref: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "selected_at": selected_at,
        "selected_candidate_id": candidate["candidate_id"],
        "selected_strategy": candidate.get("strategy"),
        "selection_notes": notes,
        "selector": "human",
        "candidate_source": candidate_source,
        "candidate_tree_ref": candidate_tree_ref,
        "candidate_comparison_ref": COMPARISON_REF,
        "wiki_ref": candidate.get("wiki_ref", WIKI_REF),
        "locked_artifact": ARGUMENT_TREE_REF,
        "feedback": [],
    }


def build_canonical_argument_tree(
    candidate: dict[str, Any],
    locked_at: str,
    *,
    candidate_source: str,
    candidate_tree_ref: str,
) -> dict[str, Any]:
    root = candidate.get("root")
    if not isinstance(root, dict):
        raise ValueError("Selected candidate must contain root object")
    root = clean_argument_node_for_canonical(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "locked_at": locked_at,
        "selected_candidate_id": candidate["candidate_id"],
        "candidate_source": candidate_source,
        "candidate_tree_ref": candidate_tree_ref,
        "human_selection_ref": FEEDBACK_REF,
        "candidate_comparison_ref": COMPARISON_REF,
        "wiki_ref": candidate.get("wiki_ref", WIKI_REF),
        "root": root,
    }


def clean_argument_node_for_canonical(node: dict[str, Any]) -> dict[str, Any]:
    clean_node = dict(node)
    original_claim = node.get("claim")
    clean_claim = clean_claim_text(original_claim)
    clean_node["claim"] = clean_claim
    if clean_claim != original_claim:
        clean_node.setdefault("derivation_notes", {})
        if isinstance(clean_node["derivation_notes"], dict):
            clean_node["derivation_notes"]["original_claim"] = original_claim
            clean_node["derivation_notes"]["claim_sanitized_for_public_writing"] = True
    children = [
        clean_argument_node_for_canonical(child)
        for child in node.get("children", []) or []
        if isinstance(child, dict)
    ]
    if children:
        clean_node["children"] = children
    return clean_node


def lock_selection(
    candidate_id: str,
    notes: str,
    project_root: Path = PROJECT_ROOT,
    selected_at: str | None = None,
    force: bool = False,
    candidate_source: str = "original",
) -> dict[str, Any]:
    normalized_notes = validate_notes(notes)
    assert_selection_state_ready(project_root)
    timestamp = selected_at or now_iso()
    argument_tree_path = project_root / ARGUMENT_TREE_REF
    feedback_path = project_root / FEEDBACK_REF
    if not force and (argument_tree_path.exists() or feedback_path.exists()):
        raise FileExistsError(
            "Part 3 canonical selection already exists. "
            "Use --force only after the user explicitly requests re-locking."
        )
    candidate, _comparison, candidate_tree_ref = load_required_inputs(
        project_root,
        candidate_id,
        candidate_source,
    )

    feedback = build_feedback(
        candidate,
        normalized_notes,
        timestamp,
        candidate_source=candidate_source,
        candidate_tree_ref=candidate_tree_ref,
    )
    canonical = build_canonical_argument_tree(
        candidate,
        timestamp,
        candidate_source=candidate_source,
        candidate_tree_ref=candidate_tree_ref,
    )
    transaction_snapshot = snapshot_relock_transaction(project_root)
    feedback_tmp = feedback_path.with_name(feedback_path.name + ".tmp")
    argument_tree_tmp = argument_tree_path.with_name(argument_tree_path.name + ".tmp")
    feedback_backup = feedback_path.with_name(feedback_path.name + ".txn.bak") if feedback_path.exists() else None
    argument_tree_backup = argument_tree_path.with_name(argument_tree_path.name + ".txn.bak") if argument_tree_path.exists() else None
    try:
        if feedback_backup:
            shutil.copy2(feedback_path, feedback_backup)
        if argument_tree_backup:
            shutil.copy2(argument_tree_path, argument_tree_backup)
        write_json(feedback_tmp, feedback)
        write_json(argument_tree_tmp, canonical)
        feedback_tmp.replace(feedback_path)
        argument_tree_tmp.replace(argument_tree_path)
        record_human_gate(project_root, normalized_notes, timestamp)
        if force:
            invalidate_part4_after_part3_relock(project_root, timestamp)
    except Exception:
        cleanup_path(feedback_tmp)
        cleanup_path(argument_tree_tmp)
        restore_or_remove(feedback_path, feedback_backup)
        restore_or_remove(argument_tree_path, argument_tree_backup)
        restore_relock_transaction(project_root, transaction_snapshot)
        raise
    finally:
        if feedback_backup and feedback_backup.exists():
            feedback_backup.unlink()
        if argument_tree_backup and argument_tree_backup.exists():
            argument_tree_backup.unlink()
    return canonical


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lock a human-selected Part 3 candidate as canonical argument_tree.json.")
    parser.add_argument("--candidate-id", required=True, help="Selected candidate ID, e.g. candidate_theory_first.")
    parser.add_argument("--notes", required=True, help="Human selection notes; must be non-empty.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing Part 3 canonical lock.")
    parser.add_argument(
        "--candidate-source",
        choices=CANDIDATE_SOURCES,
        default="original",
        help="Select from original candidates or refined candidates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    try:
        lock_selection(
            args.candidate_id,
            args.notes,
            project_root=project_root,
            force=args.force,
            candidate_source=args.candidate_source,
        )
    except Exception as exc:
        print(f"[ERR] Part 3 selection lock failed: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] {FEEDBACK_REF}")
    print(f"[OK] {ARGUMENT_TREE_REF}")
    print("[INFO] 已生成 canonical artifact，但未自动 advance part3；stage gate 仍需由项目流程显式处理。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
