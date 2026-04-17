from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.llm_agent_bridge import restore_if_protected_files_changed, snapshot_protected_files


WRITEAGENT_COMMAND_ENV = "RTM_WRITEAGENT_COMMAND"
WRITEAGENT_TIMEOUT_ENV = "RTM_WRITEAGENT_TIMEOUT"
ALLOW_DETERMINISTIC_WRITER_FALLBACK_ENV = "RTM_ALLOW_DETERMINISTIC_WRITER_FALLBACK"
DEFAULT_WRITEAGENT_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class LLMWriterResult:
    text: str
    abstract: str | None
    keywords: list[str]
    conclusion: str | None
    raw: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def configured_writeagent_command() -> str | None:
    command = os.environ.get(WRITEAGENT_COMMAND_ENV, "").strip()
    return command or None


def command_name(command: str | None) -> str | None:
    if not command:
        return None
    parts = shlex.split(command)
    if not parts:
        return None
    return Path(parts[0]).name


def deterministic_writer_fallback_allowed() -> bool:
    value = os.environ.get(ALLOW_DETERMINISTIC_WRITER_FALLBACK_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def missing_writeagent_command_message(task: str) -> str:
    return (
        f"{task} 需要真正的 writeagent，但未配置 {WRITEAGENT_COMMAND_ENV}。"
        " deterministic writer fallback 已默认停用；如需临时回退脚本，"
        f"显式设置 {ALLOW_DETERMINISTIC_WRITER_FALLBACK_ENV}=1。"
    )


def writeagent_timeout_seconds() -> int:
    raw_value = os.environ.get(WRITEAGENT_TIMEOUT_ENV, "").strip()
    if not raw_value:
        return DEFAULT_WRITEAGENT_TIMEOUT_SECONDS
    try:
        timeout = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{WRITEAGENT_TIMEOUT_ENV} 必须是整数秒数") from exc
    if timeout <= 0:
        raise RuntimeError(f"{WRITEAGENT_TIMEOUT_ENV} 必须大于 0")
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


def build_writeagent_request(
    project_root: Path,
    *,
    task: str,
    skill: str,
    output_ref: str,
    input_paths: list[str],
    instructions: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "agent_name": "writeagent",
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
            "accepted_text_fields": ["text", "body", "manuscript"],
            "optional_fields": ["abstract", "keywords", "conclusion"],
        },
        "hard_constraints": [
            "Do not invent research facts or sources.",
            "Do not confirm or bypass human gates.",
            "Do not write audit, readiness, manifest, or state artifacts.",
            "Keep writing-policy material separate from research evidence.",
            "Do not expose workflow artifacts, source_id, risk_level, review matrices, or evidence-chain plumbing in public manuscript prose.",
            "Use academic prose; keep evidence and citation checks in audit/report artifacts unless a citation is needed for the argument.",
            "Return JSON only.",
        ],
    }


def parse_writer_result(stdout: str) -> LLMWriterResult:
    text = stdout.strip()
    if not text:
        raise RuntimeError("writeagent command 没有输出")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("writeagent command 必须输出 JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("writeagent command 输出必须是 JSON object")

    raw_text = (
        payload.get("text")
        or payload.get("body")
        or payload.get("manuscript")
    )
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RuntimeError("writeagent command 输出缺少非空 text/body/manuscript")

    keywords = payload.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    clean_keywords = [
        item.strip()
        for item in keywords
        if isinstance(item, str) and item.strip()
    ]

    abstract = payload.get("abstract")
    conclusion = payload.get("conclusion")
    return LLMWriterResult(
        text=raw_text.strip() + "\n",
        abstract=abstract.strip() if isinstance(abstract, str) and abstract.strip() else None,
        keywords=clean_keywords,
        conclusion=conclusion.strip() if isinstance(conclusion, str) and conclusion.strip() else None,
        raw=payload,
    )


def request_writeagent(
    project_root: Path,
    *,
    task: str,
    skill: str,
    output_ref: str,
    input_paths: list[str],
    instructions: list[str],
) -> LLMWriterResult | None:
    command = configured_writeagent_command()
    if not command:
        return None

    request = build_writeagent_request(
        project_root,
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
            timeout=writeagent_timeout_seconds(),
            check=False,
        )
    finally:
        changed_protected_files = restore_if_protected_files_changed(project_root, protected_snapshot)
    if changed_protected_files:
        raise RuntimeError(
            "writeagent command attempted to modify protected workflow files: "
            + ", ".join(changed_protected_files)
        )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            "writeagent command 执行失败"
            + (f": {stderr}" if stderr else "")
        )
    return parse_writer_result(result.stdout)


def write_writer_provenance(
    project_root: Path,
    rel_path: str,
    *,
    task: str,
    skill: str,
    output_ref: str,
    mode: str,
    fallback_reason: str | None = None,
) -> None:
    command = configured_writeagent_command()
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "agent_name": "writeagent",
        "task": task,
        "skill": skill,
        "output_ref": output_ref,
        "mode": mode,
        "command_configured": command is not None,
        "command_name": command_name(command),
        "does_not_confirm_human_gate": True,
        "does_not_write_audit_or_decision_artifacts": True,
    }
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason

    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
