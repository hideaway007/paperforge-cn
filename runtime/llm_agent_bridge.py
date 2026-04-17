from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LLM_AGENT_TIMEOUT_SECONDS = 180
ACCEPTED_TEXT_FIELDS = ("text", "body", "report", "proposal")
ACCEPTED_OBJECT_FIELDS = ("artifacts", "payload")
PROTECTED_REL_PATHS = (
    "runtime/state.json",
    "manifests/source-policy.json",
    "outputs/part1/intake.json",
    "outputs/part1/search_plan.json",
    "outputs/part1/download_manifest.json",
    "outputs/part1/relevance_scores.json",
    "outputs/part1/accepted_sources.json",
    "outputs/part1/authenticity_report.json",
    "outputs/part1/excluded_sources_log.json",
    "raw-library/metadata.json",
    "research-wiki/index.json",
    "research-wiki/index.md",
    "research-wiki/log.md",
    "research-wiki/update_log.json",
    "research-wiki/contradictions_report.json",
    "outputs/part3/argument_seed_map.json",
    "outputs/part3/candidate_comparison.json",
    "outputs/part3/argument_tree.json",
    "outputs/part3/human_selection_feedback.json",
    "outputs/part4/paper_outline.json",
    "outputs/part4/outline_rationale.json",
    "outputs/part4/reference_alignment_report.json",
    "outputs/part5/manuscript_v1.md",
    "outputs/part5/manuscript_v2.md",
    "outputs/part5/review_matrix.json",
    "outputs/part5/review_report.md",
    "outputs/part5/revision_log.json",
    "outputs/part5/claim_evidence_matrix.json",
    "outputs/part5/citation_map.json",
    "outputs/part5/claim_risk_report.json",
    "outputs/part5/citation_consistency_precheck.json",
    "outputs/part5/part6_readiness_decision.json",
    "outputs/part6/final_manuscript.md",
    "outputs/part6/final_abstract.md",
    "outputs/part6/final_keywords.json",
    "outputs/part6/submission_checklist.md",
    "outputs/part6/claim_risk_report.json",
    "outputs/part6/citation_consistency_report.json",
    "outputs/part6/submission_package_manifest.json",
    "outputs/part6/final_readiness_decision.json",
)
PROTECTED_DIRS = (
    "runtime",
    "manifests",
    "outputs",
    "outputs/part1",
    "outputs/part2",
    "outputs/part3",
    "outputs/part3/candidate_argument_trees",
    "outputs/part4",
    "outputs/part5",
    "outputs/part5/chapter_briefs",
    "outputs/part5/llm_agent_reviews",
    "outputs/part6",
    "outputs/part6/llm_agent_audits",
    "process-memory",
    "raw-library",
    "raw-library/papers",
    "raw-library/normalized",
    "raw-library/provenance",
    "research-wiki",
    "research-wiki/pages",
    "writing-policy",
    "skills",
)
PROTECTED_GLOBS = (
    "outputs/part*/**/*",
    "process-memory/**/*",
    "manifests/**/*",
    "raw-library/**/*",
    "research-wiki/**/*",
    "skills/**/*",
    "writing-policy/**/*",
)


@dataclass(frozen=True)
class LLMAgentResult:
    agent_name: str
    text: str | None
    body: str | None
    report: str | None
    proposal: str | None
    artifacts: Any | None
    payload: Any | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class ProtectedFileSnapshot:
    rel_path: str
    kind: str
    content: bytes | None
    symlink_target: str | None = None


def add_ancestors(rel_paths: set[str], rel_path: str) -> None:
    path = Path(rel_path)
    for parent in path.parents:
        parent_text = parent.as_posix()
        if parent_text in {"", "."}:
            break
        rel_paths.add(parent_text)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def agent_env_prefix(agent_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", agent_name).strip("_").upper()
    if not normalized:
        raise RuntimeError("agent_name 不能为空")
    return f"RTM_{normalized}"


def command_env_name(agent_name: str) -> str:
    return f"{agent_env_prefix(agent_name)}_COMMAND"


def timeout_env_name(agent_name: str) -> str:
    return f"{agent_env_prefix(agent_name)}_TIMEOUT"


def configured_agent_command(agent_name: str) -> str | None:
    command = os.environ.get(command_env_name(agent_name), "").strip()
    return command or None


def command_name(command: str | None) -> str | None:
    if not command:
        return None
    parts = shlex.split(command)
    if not parts:
        return None
    return Path(parts[0]).name


def protected_rel_paths(project_root: Path) -> list[str]:
    rel_paths = set(PROTECTED_REL_PATHS) | set(PROTECTED_DIRS)
    for rel_path in list(rel_paths):
        add_ancestors(rel_paths, rel_path)
    for pattern in PROTECTED_GLOBS:
        for path in project_root.glob(pattern):
            if path.is_file() or path.is_symlink() or path.is_dir():
                rel_path = path.relative_to(project_root).as_posix()
                rel_paths.add(rel_path)
                add_ancestors(rel_paths, rel_path)
    return sorted(rel_paths)


def snapshot_one_protected_file(project_root: Path, rel_path: str) -> ProtectedFileSnapshot:
    path = project_root / rel_path
    if path.is_symlink():
        return ProtectedFileSnapshot(
            rel_path=rel_path,
            kind="symlink",
            content=None,
            symlink_target=os.readlink(path),
        )
    if path.is_dir():
        return ProtectedFileSnapshot(
            rel_path=rel_path,
            kind="directory",
            content=None,
        )
    if path.is_file():
        return ProtectedFileSnapshot(
            rel_path=rel_path,
            kind="file",
            content=path.read_bytes(),
        )
    if path.exists():
        return ProtectedFileSnapshot(
            rel_path=rel_path,
            kind="other",
            content=None,
        )
    return ProtectedFileSnapshot(rel_path=rel_path, kind="missing", content=None)


def snapshot_protected_files(project_root: Path) -> dict[str, ProtectedFileSnapshot]:
    snapshots: dict[str, ProtectedFileSnapshot] = {}
    for rel_path in protected_rel_paths(project_root):
        snapshots[rel_path] = snapshot_one_protected_file(project_root, rel_path)
    return snapshots


def remove_current_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def restore_protected_snapshot(project_root: Path, snapshot: ProtectedFileSnapshot) -> None:
    path = project_root / snapshot.rel_path
    remove_current_path(path)
    if snapshot.kind == "missing":
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if snapshot.kind == "file":
        path.write_bytes(snapshot.content or b"")
    elif snapshot.kind == "symlink":
        if not snapshot.symlink_target:
            raise RuntimeError(f"protected symlink snapshot 缺少 target: {snapshot.rel_path}")
        os.symlink(snapshot.symlink_target, path)
    elif snapshot.kind == "directory":
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.touch()


def restore_if_protected_files_changed(
    project_root: Path,
    before: dict[str, ProtectedFileSnapshot],
) -> list[str]:
    rel_paths = set(before) | set(protected_rel_paths(project_root))
    changed: list[str] = []
    ordered_rel_paths = sorted(rel_paths, key=lambda value: (len(Path(value).parts), value))
    for rel_path in ordered_rel_paths:
        previous = before.get(rel_path) or ProtectedFileSnapshot(
            rel_path=rel_path,
            kind="missing",
            content=None,
        )
        current = snapshot_one_protected_file(project_root, rel_path)
        if previous == current:
            continue
        changed.append(rel_path)
        restore_protected_snapshot(project_root, previous)
    return changed


def agent_timeout_seconds(agent_name: str) -> int:
    env_name = timeout_env_name(agent_name)
    raw_value = os.environ.get(env_name, "").strip()
    if not raw_value:
        return DEFAULT_LLM_AGENT_TIMEOUT_SECONDS
    try:
        timeout = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} 必须是整数秒数") from exc
    if timeout <= 0:
        raise RuntimeError(f"{env_name} 必须大于 0")
    return timeout


def read_input_artifact(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        return {"path": rel_path, "exists": False}
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            return {
                "path": rel_path,
                "exists": True,
                "kind": "json",
                "content": json.load(f),
            }
    return {
        "path": rel_path,
        "exists": True,
        "kind": "text",
        "content": path.read_text(encoding="utf-8"),
    }


def build_llm_agent_request(
    project_root: Path,
    *,
    agent_name: str,
    task: str,
    skill: str,
    output_ref: str,
    input_paths: list[str],
    instructions: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "agent_name": agent_name,
        "task": task,
        "skill": skill,
        "project_root": str(project_root),
        "output_ref": output_ref,
        "inputs": [
            read_input_artifact(project_root, rel_path)
            for rel_path in input_paths
        ],
        "instructions": instructions,
        "output_contract": {
            "format": "json",
            "accepted_fields": [*ACCEPTED_TEXT_FIELDS, *ACCEPTED_OBJECT_FIELDS],
        },
        "hard_constraints": [
            "Do not confirm or bypass human gates.",
            "Do not write runtime state, canonical locks, audit decisions, or readiness decisions unless the deterministic runtime explicitly owns that artifact.",
            "Do not invent source_id, citation, case fact, data, or research conclusion.",
            "Keep writing-policy material separate from research evidence.",
            "Return JSON only.",
        ],
    }


def _clean_text_field(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_llm_agent_result(agent_name: str, stdout: str) -> LLMAgentResult:
    text = stdout.strip()
    if not text:
        raise RuntimeError(f"{agent_name} command 没有输出")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{agent_name} command 必须输出 JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{agent_name} command 输出必须是 JSON object")

    cleaned_text_fields = {
        field: _clean_text_field(payload, field)
        for field in ACCEPTED_TEXT_FIELDS
    }
    has_text_field = any(value is not None for value in cleaned_text_fields.values())
    has_artifacts = "artifacts" in payload and payload.get("artifacts") is not None
    has_payload = "payload" in payload and payload.get("payload") is not None
    if not (has_text_field or has_artifacts or has_payload):
        accepted = "/".join((*ACCEPTED_TEXT_FIELDS, *ACCEPTED_OBJECT_FIELDS))
        raise RuntimeError(f"{agent_name} command 输出缺少 {accepted}")

    return LLMAgentResult(
        agent_name=agent_name,
        text=cleaned_text_fields["text"],
        body=cleaned_text_fields["body"],
        report=cleaned_text_fields["report"],
        proposal=cleaned_text_fields["proposal"],
        artifacts=payload.get("artifacts") if has_artifacts else None,
        payload=payload.get("payload") if has_payload else None,
        raw=payload,
    )


def request_llm_agent(
    project_root: Path,
    *,
    agent_name: str,
    task: str,
    skill: str,
    output_ref: str,
    input_paths: list[str],
    instructions: list[str],
) -> LLMAgentResult | None:
    command = configured_agent_command(agent_name)
    if not command:
        return None

    request = build_llm_agent_request(
        project_root,
        agent_name=agent_name,
        task=task,
        skill=skill,
        output_ref=output_ref,
        input_paths=input_paths,
        instructions=instructions,
    )
    protected_snapshot = snapshot_protected_files(project_root)
    try:
        result = subprocess.run(
            shlex.split(command),
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=agent_timeout_seconds(agent_name),
            check=False,
        )
    finally:
        changed_protected_files = restore_if_protected_files_changed(project_root, protected_snapshot)
    if changed_protected_files:
        raise RuntimeError(
            f"{agent_name} command attempted to modify protected workflow files: "
            + ", ".join(changed_protected_files)
        )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"{agent_name} command 执行失败"
            + (f": {stderr}" if stderr else "")
        )
    return parse_llm_agent_result(agent_name, result.stdout)


def write_llm_agent_provenance(
    project_root: Path,
    rel_path: str,
    *,
    agent_name: str,
    task: str,
    skill: str,
    output_ref: str,
    mode: str,
    fallback_reason: str | None = None,
) -> None:
    command = configured_agent_command(agent_name)
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "agent_name": agent_name,
        "task": task,
        "skill": skill,
        "output_ref": output_ref,
        "mode": mode,
        "command_configured": command is not None,
        "command_name": command_name(command),
        "does_not_confirm_human_gate": True,
    }
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason

    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
