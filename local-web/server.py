#!/usr/bin/env python3
"""Local web console for the research-to-manuscript workflow.

Run:
  python3 local-web/server.py --port 8765
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4


LOCAL_WEB_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = LOCAL_WEB_ROOT.parent
STATIC_ROOT = LOCAL_WEB_ROOT / "static"
STAGE_IDS = {"part1", "part2", "part3", "part4", "part5", "part6"}
SAFE_ARTIFACT_PREFIXES = (
    "outputs/",
    "research-wiki/",
    "writing-policy/",
    "manifests/",
    "process-memory/",
    "runtime/state.json",
    "workspace_manifest.json",
    "raw-library/metadata.json",
)
MAX_PREVIEW_BYTES = 160_000
JOB_TIMEOUT_SECONDS = 60 * 60


@dataclass
class Job:
    job_id: str
    action_id: str
    context_id: str
    context_path: str
    commands: list[list[str]]
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    output: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "action_id": self.action_id,
            "context_id": self.context_id,
            "context_path": self.context_path,
            "commands": self.commands,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error,
        }


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()


ACTION_SPECS: list[dict[str, str]] = [
    {"id": "doctor", "label": "运行诊断", "group": "global"},
    {"id": "start-stage", "label": "标记阶段开始", "group": "stage"},
    {"id": "validate-stage", "label": "校验阶段 gate", "group": "stage"},
    {"id": "advance-stage", "label": "推进阶段", "group": "stage"},
    {"id": "part1-intake", "label": "生成 Part 1 intake 请求", "group": "part1"},
    {"id": "save-intake", "label": "保存网页 intake", "group": "part1"},
    {"id": "save-intake-run", "label": "保存 intake 并运行 Part 1", "group": "part1"},
    {"id": "confirm-intake", "label": "确认 intake 并运行 Part 1", "group": "part1"},
    {"id": "part1-runner", "label": "运行 Part 1 检索流程", "group": "part1"},
    {"id": "part1-export-table", "label": "导出已下载论文表", "group": "part1"},
    {"id": "part2-generate", "label": "生成 Research Wiki", "group": "part2"},
    {"id": "part2-health", "label": "检查 Wiki health", "group": "part2"},
    {"id": "part3-seed-map", "label": "生成论证 seed map", "group": "part3"},
    {"id": "part3-generate", "label": "生成 3 份候选论证树", "group": "part3"},
    {"id": "part3-compare", "label": "生成候选比较表", "group": "part3"},
    {"id": "part3-refine", "label": "细化候选论证树", "group": "part3"},
    {"id": "part3-review", "label": "查看候选选择表", "group": "part3"},
    {"id": "part3-select", "label": "选择并锁定论证树", "group": "part3"},
    {"id": "part4-generate", "label": "生成论文大纲", "group": "part4"},
    {"id": "part4-check", "label": "检查大纲 gate", "group": "part4"},
    {"id": "part5-prep", "label": "生成写作输入包", "group": "part5"},
    {"id": "part5-draft", "label": "生成初稿 v1", "group": "part5"},
    {"id": "part5-review", "label": "生成结构化 review", "group": "part5"},
    {"id": "part5-revise", "label": "生成修订稿 v2", "group": "part5"},
    {"id": "part5-all", "label": "自动运行 Part 5 MVP", "group": "part5"},
    {"id": "part5-check", "label": "检查 Part 5 gate", "group": "part5"},
    {"id": "part6-precheck", "label": "只读检查 Part 6", "group": "part6"},
    {"id": "part6-authorize", "label": "授权进入 Part 6", "group": "part6"},
    {"id": "part6-finalize", "label": "运行 Part 6 finalizer", "group": "part6"},
    {"id": "part6-check", "label": "检查 Part 6 package", "group": "part6"},
    {"id": "part6-confirm-final", "label": "确认 Part 6 最终决策", "group": "part6"},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any | None:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def discover_contexts() -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = [
        {
            "id": "root",
            "label": "root 项目控制面",
            "kind": "root",
            "path": str(PROJECT_ROOT),
            "is_latest": False,
        }
    ]

    latest_workspace_path = None
    root_workspace_manifest = load_json(PROJECT_ROOT / "outputs" / "part1" / "workspace_manifest.json")
    if isinstance(root_workspace_manifest, dict):
        latest = root_workspace_manifest.get("latest_workspace") or {}
        if isinstance(latest, dict):
            latest_workspace_path = latest.get("workspace_path")

    workspaces_root = PROJECT_ROOT / "workspaces"
    for manifest_path in sorted(workspaces_root.glob("ws_*/workspace_manifest.json")):
        manifest = load_json(manifest_path)
        workspace_root = manifest_path.parent
        workspace_id = workspace_root.name
        intake_id = ""
        if isinstance(manifest, dict):
            workspace_id = str(manifest.get("workspace_id") or workspace_id)
            intake_id = str(manifest.get("intake_id") or "")
        label_suffix = f" · {intake_id}" if intake_id else ""
        contexts.append(
            {
                "id": workspace_id,
                "label": f"{workspace_id}{label_suffix}",
                "kind": "workspace",
                "path": str(workspace_root),
                "is_latest": str(workspace_root) == str(latest_workspace_path),
            }
        )

    return contexts


def default_context_id() -> str:
    for context in discover_contexts():
        if context.get("is_latest"):
            return str(context["id"])
    return "root"


def resolve_context(context_id: str | None) -> tuple[str, Path]:
    selected_id = context_id or default_context_id()
    if selected_id == "root":
        return "root", PROJECT_ROOT

    if not re.fullmatch(r"ws_\d{3}", selected_id):
        raise ValueError(f"Unknown context_id: {selected_id}")

    workspace_root = (PROJECT_ROOT / "workspaces" / selected_id).resolve()
    if not workspace_root.is_dir():
        raise ValueError(f"Workspace not found: {selected_id}")
    if not str(workspace_root).startswith(str((PROJECT_ROOT / "workspaces").resolve())):
        raise ValueError(f"Invalid workspace path: {selected_id}")
    return selected_id, workspace_root


def call_pipeline(root: Path, function_name: str, *args: Any) -> Any:
    pipeline_path = root / "runtime" / "pipeline.py"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"Missing runtime/pipeline.py in {root}")

    module_name = f"_local_web_pipeline_{abs(hash(str(root)))}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, pipeline_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load pipeline module: {pipeline_path}")

    old_path = list(sys.path)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "runtime"))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, function_name)(*args)
    finally:
        sys.path = old_path


def recent_process_memory(root: Path, limit: int = 8) -> list[dict[str, Any]]:
    memory_dir = root / "process-memory"
    records: list[dict[str, Any]] = []
    for path in sorted(memory_dir.glob("*.json"))[-limit:]:
        data = load_json(path)
        records.append(
            {
                "file": str(path.relative_to(root)),
                "data": data if isinstance(data, dict) else {"event": "unreadable"},
            }
        )
    return records


def research_summary(root: Path) -> dict[str, Any]:
    metadata = load_json(root / "raw-library" / "metadata.json")
    wiki = load_json(root / "research-wiki" / "index.json")
    readiness = load_json(root / "outputs" / "part5" / "part6_readiness_decision.json")

    source_count = 0
    if isinstance(metadata, dict):
        sources = metadata.get("sources")
        if isinstance(sources, list):
            source_count = len(sources)

    wiki_pages = 0
    if isinstance(wiki, dict):
        pages = wiki.get("pages")
        if isinstance(pages, list):
            wiki_pages = len(pages)

    return {
        "source_count": source_count,
        "wiki_pages": wiki_pages,
        "part5_readiness": readiness.get("verdict") if isinstance(readiness, dict) else None,
        "user_outputs": {
            "part1_table": str(root / "outputs" / "part1" / "downloaded_papers_table.md"),
            "part5_review": str(root / "outputs" / "part5" / "review_report.md"),
            "manuscript_v2": str(root / "outputs" / "part5" / "manuscript_v2.md"),
        },
    }


def part1_reference_snapshot(root: Path) -> dict[str, Any]:
    table_path = root / "outputs" / "part1" / "downloaded_papers_table.csv"
    references: list[dict[str, Any]] = []

    if table_path.exists():
        with table_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                local_path = (row.get("local_path") or "").strip()
                file_name = Path(local_path).name if local_path else f"{row.get('source_id', 'unknown')}.pdf"
                references.append(
                    {
                        "source_id": (row.get("source_id") or "").strip(),
                        "file_name": file_name,
                        "title": (row.get("title") or "").strip(),
                        "authors": (row.get("authors") or "").strip(),
                        "year": (row.get("year") or "").strip(),
                        "journal": (row.get("journal") or "").strip(),
                        "source_name": (row.get("source_name") or "").strip(),
                        "query_id": (row.get("query_id") or "").strip(),
                        "download_status": (row.get("download_status") or "").strip(),
                        "library_status": (row.get("library_status") or "").strip(),
                        "relevance_tier": (row.get("relevance_tier") or "").strip(),
                        "relevance_score": (row.get("relevance_score") or "").strip(),
                        "local_path": local_path,
                        "local_exists": bool(local_path and (root / local_path).exists()),
                    }
                )
    else:
        metadata = load_json(root / "raw-library" / "metadata.json")
        if isinstance(metadata, dict):
            for source in metadata.get("sources", []) or []:
                if not isinstance(source, dict):
                    continue
                local_path = str(source.get("local_path") or "").strip()
                file_name = Path(local_path).name if local_path else f"{source.get('source_id', 'unknown')}.pdf"
                references.append(
                    {
                        "source_id": source.get("source_id"),
                        "file_name": file_name,
                        "title": source.get("title"),
                        "authors": "；".join(source.get("authors", [])) if isinstance(source.get("authors"), list) else source.get("authors"),
                        "year": source.get("year"),
                        "journal": source.get("journal"),
                        "source_name": source.get("source_name"),
                        "query_id": "",
                        "download_status": "success" if local_path else "",
                        "library_status": "accepted",
                        "relevance_tier": source.get("relevance_tier"),
                        "relevance_score": source.get("relevance_score"),
                        "local_path": local_path,
                        "local_exists": bool(local_path and (root / local_path).exists()),
                    }
                )

    known_paths = {item.get("local_path") for item in references}
    for pdf_path in sorted((root / "raw-library" / "papers").glob("*.pdf")):
        rel_path = str(pdf_path.relative_to(root))
        if rel_path in known_paths:
            continue
        references.append(
            {
                "source_id": pdf_path.stem,
                "file_name": pdf_path.name,
                "title": "",
                "authors": "",
                "year": "",
                "journal": "",
                "source_name": "",
                "query_id": "",
                "download_status": "success",
                "library_status": "",
                "relevance_tier": "",
                "relevance_score": "",
                "local_path": rel_path,
                "local_exists": True,
            }
        )

    return {
        "table_path": "outputs/part1/downloaded_papers_table.csv" if table_path.exists() else None,
        "total": len(references),
        "accepted_count": sum(1 for item in references if item.get("library_status") == "accepted"),
        "references": references,
    }


def intake_snapshot() -> dict[str, Any]:
    return {
        "template": load_json(PROJECT_ROOT / "outputs" / "part1" / "intake_template.json"),
        "current": load_json(PROJECT_ROOT / "outputs" / "part1" / "intake.json"),
        "target_path": "outputs/part1/intake.json",
        "write_context": "root",
    }


def part3_candidate_snapshot(root: Path) -> dict[str, Any]:
    comparison = load_json(root / "outputs" / "part3" / "candidate_comparison.json")
    selection = load_json(root / "outputs" / "part3" / "human_selection_feedback.json")
    candidates: list[dict[str, Any]] = []
    recommendation: dict[str, Any] = {}

    if isinstance(comparison, dict):
        recommendation = comparison.get("recommendation") if isinstance(comparison.get("recommendation"), dict) else {}
        for candidate in comparison.get("candidates", []) or []:
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "strategy": candidate.get("strategy"),
                    "thesis": candidate.get("thesis"),
                    "score": candidate.get("score"),
                    "strengths": candidate.get("strengths", []),
                    "weaknesses": candidate.get("weaknesses", []),
                    "risks": candidate.get("risks", []),
                    "quality": candidate.get("quality", {}),
                    "argument_nodes": candidate.get("argument_nodes", []),
                    "evidence_coverage": candidate.get("evidence_coverage", {}),
                    "wiki_coverage": candidate.get("wiki_coverage", {}),
                }
            )
    else:
        candidate_dir = root / "outputs" / "part3" / "candidate_argument_trees"
        for path in sorted(candidate_dir.glob("*.json")):
            candidate = load_json(path)
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                {
                    "candidate_id": candidate.get("candidate_id") or path.stem,
                    "strategy": candidate.get("strategy"),
                    "thesis": candidate.get("thesis"),
                    "score": None,
                    "strengths": [],
                    "weaknesses": [],
                    "risks": [],
                    "quality": {},
                    "argument_nodes": [],
                    "evidence_coverage": {},
                    "wiki_coverage": {},
                }
            )

    return {
        "seed_map_exists": (root / "outputs" / "part3" / "argument_seed_map.json").exists(),
        "comparison_exists": isinstance(comparison, dict),
        "candidates": candidates,
        "recommendation": recommendation,
        "selection": selection if isinstance(selection, dict) else None,
    }


def page_status(context_id: str | None) -> dict[str, Any]:
    selected_id, root = resolve_context(context_id)
    response: dict[str, Any] = {
        "contexts": discover_contexts(),
        "default_context_id": default_context_id(),
        "active_context": {
            "id": selected_id,
            "path": str(root),
        },
        "actions": ACTION_SPECS,
        "summary": research_summary(root),
        "part1_references": part1_reference_snapshot(root),
        "process_memory": recent_process_memory(root),
        "part1_intake": intake_snapshot(),
        "part3": part3_candidate_snapshot(root),
    }

    manifest = load_json(root / "manifests" / "pipeline-stages.json")
    if isinstance(manifest, dict):
        response["manifest"] = manifest

    workspace_manifest = load_json(root / "workspace_manifest.json")
    if isinstance(workspace_manifest, dict):
        response["workspace_manifest"] = workspace_manifest

    try:
        status = call_pipeline(root, "get_status")
        state = call_pipeline(root, "load_state")
        if isinstance(status, dict) and isinstance(state, dict):
            for stage_id, stage_status in (status.get("stages") or {}).items():
                stage_state = (state.get("stages") or {}).get(stage_id) or {}
                if isinstance(stage_status, dict):
                    stage_status["human_gates_completed"] = stage_state.get("human_gates_completed", [])
            status["state"] = {
                "schema_version": state.get("schema_version"),
                "pipeline_id": state.get("pipeline_id"),
                "human_decision_log": state.get("human_decision_log", []),
            }
        response["status"] = status
    except Exception as exc:  # noqa: BLE001 - local diagnostic endpoint should surface root cause.
        response["status_error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(limit=4),
        }

    return response


def validate_stage_param(params: dict[str, Any]) -> str:
    stage = str(params.get("stage") or "")
    if stage not in STAGE_IDS:
        raise ValueError(f"Invalid stage: {stage}")
    return stage


def required_note(params: dict[str, Any], field_name: str = "notes") -> str:
    note = str(params.get(field_name) or "").strip()
    if not note:
        raise ValueError(f"{field_name} cannot be empty")
    return note


def bool_param(params: dict[str, Any], field_name: str) -> bool:
    return params.get(field_name) is True


def text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def slug_for_intake(value: str) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if ascii_slug:
        return ascii_slug[:64]
    return "topic"


def normalize_intake_from_params(params: dict[str, Any]) -> dict[str, Any]:
    raw = params.get("intake")
    if not isinstance(raw, dict):
        raise ValueError("intake must be an object")

    research_topic = str(raw.get("research_topic") or "").strip()
    research_question = str(raw.get("research_question") or "").strip()
    scope_notes = str(raw.get("scope_notes") or "").strip()
    keywords_required = text_list(raw.get("keywords_required"))
    if not research_topic:
        raise ValueError("research_topic cannot be empty")
    if not research_question:
        raise ValueError("research_question cannot be empty")
    if not keywords_required:
        raise ValueError("keywords_required must include at least one keyword")
    if not scope_notes:
        raise ValueError("scope_notes cannot be empty")

    time_range = raw.get("time_range") if isinstance(raw.get("time_range"), dict) else {}
    start_year = int(time_range.get("start_year") or 2015)
    end_year = int(time_range.get("end_year") or datetime.now().year)
    if start_year > end_year:
        raise ValueError("time_range.start_year cannot be greater than end_year")

    intake_id = str(raw.get("intake_id") or "").strip()
    if not intake_id:
        intake_id = f"intake_{datetime.now().strftime('%Y%m%d')}_{slug_for_intake(research_topic)}"

    source_preference = raw.get("source_preference") if isinstance(raw.get("source_preference"), dict) else {}
    priority_sources = text_list(source_preference.get("priority_sources")) or text_list(source_preference.get("databases")) or ["cnki", "wanfang", "vip"]
    document_types = text_list(source_preference.get("document_types")) or ["期刊论文", "硕士论文", "博士论文"]

    return {
        "schema_version": "1.0.0",
        "intake_id": intake_id,
        "research_topic": research_topic,
        "research_question": research_question,
        "core_research_questions": text_list(raw.get("core_research_questions")),
        "discipline_fields": text_list(raw.get("discipline_fields")),
        "time_range": {
            "start_year": start_year,
            "end_year": end_year,
        },
        "keywords_required": keywords_required,
        "keywords_suggested": text_list(raw.get("keywords_suggested")),
        "exclusions": text_list(raw.get("exclusions") or raw.get("exclusion_rules")),
        "language_preference": raw.get("language_preference") if isinstance(raw.get("language_preference"), dict) else {
            "primary": "中文文献",
            "supplementary": "英文文献只作方法、背景与比较研究补充",
        },
        "source_preference": {
            "priority_sources": priority_sources,
            "databases": priority_sources,
            "document_types": document_types,
            "priority": "CNKI first",
            "source_requirements": text_list(source_preference.get("source_requirements")),
        },
        "expected_research_types": text_list(raw.get("expected_research_types")),
        "scope_notes": scope_notes,
        "human_confirmation": {
            "confirmed": False,
            "confirmed_gate": None,
            "confirmed_at": None,
            "notes": "",
        },
    }


def write_intake_file(intake: dict[str, Any]) -> Path:
    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    intake_path.parent.mkdir(parents=True, exist_ok=True)
    if intake_path.exists():
        backup_path = intake_path.with_suffix(".json.bak")
        shutil.copy2(intake_path, backup_path)
    with intake_path.open("w", encoding="utf-8") as handle:
        json.dump(intake, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return intake_path


def latest_workspace_from_registry() -> Path:
    registry = load_json(PROJECT_ROOT / "outputs" / "part1" / "workspace_manifest.json")
    if not isinstance(registry, dict):
        raise RuntimeError("outputs/part1/workspace_manifest.json was not created")
    latest = registry.get("latest_workspace")
    if not isinstance(latest, dict) or not latest.get("workspace_path"):
        raise RuntimeError("workspace registry does not contain latest_workspace.workspace_path")
    workspace_path = Path(str(latest["workspace_path"])).resolve()
    if not workspace_path.exists():
        raise RuntimeError(f"latest workspace does not exist: {workspace_path}")
    return workspace_path


def cli_command(root: Path, *args: str) -> list[str]:
    return [sys.executable, str(root / "cli.py"), *args]


def build_commands(root: Path, action_id: str, params: dict[str, Any]) -> list[list[str]]:
    if action_id == "doctor":
        return [cli_command(root, "doctor")]

    if action_id == "start-stage":
        return [cli_command(root, "start", validate_stage_param(params))]
    if action_id == "validate-stage":
        return [cli_command(root, "validate", validate_stage_param(params))]
    if action_id == "advance-stage":
        return [cli_command(root, "advance", validate_stage_param(params))]

    if action_id == "part1-intake":
        command = cli_command(root, "part1-intake")
        if bool_param(params, "force"):
            command.append("--force")
        return [command]
    if action_id == "confirm-intake":
        return [cli_command(root, "confirm-gate", "intake_confirmed", "--notes", required_note(params))]
    if action_id == "part1-runner":
        script = root / "runtime" / "agents" / "part1_runner.py"
        if not script.exists():
            raise FileNotFoundError(f"Missing {script}")
        return [[sys.executable, str(script)]]
    if action_id == "part1-export-table":
        return [cli_command(root, "part1-export-table")]

    simple_cli: dict[str, list[str]] = {
        "part2-health": ["part2-health"],
        "part3-seed-map": ["part3-seed-map"],
        "part3-generate": ["part3-generate"],
        "part3-compare": ["part3-compare"],
        "part3-review": ["part3-review"],
        "part4-check": ["part4-check"],
        "part5-prep": ["part5-prep"],
        "part5-draft": ["part5-draft"],
        "part5-review": ["part5-review"],
        "part5-revise": ["part5-revise"],
        "part5-check": ["part5-check"],
        "part6-precheck": ["part6-precheck"],
        "part6-check": ["part6-check"],
    }
    if action_id in simple_cli:
        return [cli_command(root, *simple_cli[action_id])]

    if action_id == "part2-generate":
        command = cli_command(root, "part2-generate")
        if bool_param(params, "force"):
            command.append("--force")
        return [command]
    if action_id == "part3-refine":
        command = cli_command(root, "part3-refine")
        if bool_param(params, "force"):
            command.append("--force")
        return [command]
    if action_id == "part3-select":
        candidate_id = str(params.get("candidate_id") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", candidate_id):
            raise ValueError("candidate_id is required")
        candidate_source = str(params.get("candidate_source") or "original")
        if candidate_source not in {"original", "refined"}:
            raise ValueError("candidate_source must be original or refined")
        return [
            cli_command(
                root,
                "part3-select",
                "--candidate-id",
                candidate_id,
                "--notes",
                required_note(params),
                "--candidate-source",
                candidate_source,
            )
        ]
    if action_id == "part4-generate":
        command = cli_command(root, "part4-generate")
        if bool_param(params, "force"):
            command.append("--force")
        return [command]
    if action_id == "part5-all":
        return [
            cli_command(root, "part5-prep"),
            cli_command(root, "part5-draft"),
            cli_command(root, "part5-review"),
            cli_command(root, "part5-revise"),
            cli_command(root, "part5-check"),
        ]
    if action_id == "part6-authorize":
        return [cli_command(root, "part6-authorize", "--notes", required_note(params))]
    if action_id == "part6-finalize":
        step = str(params.get("step") or "all")
        if step not in {"precheck", "finalize", "audit-claim", "audit-citation", "package-draft", "decide", "package-final", "all"}:
            raise ValueError(f"Invalid Part 6 step: {step}")
        return [cli_command(root, "part6-finalize", "--step", step)]
    if action_id == "part6-confirm-final":
        return [cli_command(root, "part6-confirm-final", "--notes", required_note(params))]

    raise ValueError(f"Unknown action_id: {action_id}")


def append_job_output(job: Job, text: str) -> None:
    job.output = (job.output + text)[-120_000:]


def run_command_for_job(job: Job, command: list[str], cwd: Path, index: int) -> int:
    append_job_output(job, f"$ {' '.join(command)}\n")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert process.stdout is not None
    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    while True:
        line = process.stdout.readline()
        if line:
            append_job_output(job, line)
        if process.poll() is not None:
            remainder = process.stdout.read()
            if remainder:
                append_job_output(job, remainder)
            break
        if time.monotonic() > deadline:
            process.kill()
            raise subprocess.TimeoutExpired(command, JOB_TIMEOUT_SECONDS)
        time.sleep(0.05)

    exit_code = process.returncode or 0
    job.exit_code = exit_code
    if exit_code != 0:
        append_job_output(job, f"\nCommand {index} failed with exit code {exit_code}.\n")
    return exit_code


def run_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.status = "running"
        job.started_at = now_iso()

    try:
        cwd = Path(job.context_path)
        for index, command in enumerate(job.commands, start=1):
            exit_code = run_command_for_job(job, command, cwd, index)
            if exit_code != 0:
                job.status = "failed"
                break
        else:
            job.status = "completed"
    except subprocess.TimeoutExpired:
        job.status = "failed"
        job.error = f"Action timed out after {JOB_TIMEOUT_SECONDS} seconds"
    except Exception as exc:  # noqa: BLE001 - keep local job failure inspectable.
        job.status = "failed"
        job.error = str(exc)
        append_job_output(job, traceback.format_exc(limit=4))
    finally:
        job.finished_at = now_iso()


def run_intake_job(job_id: str, params: dict[str, Any], run_after_save: bool) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.status = "running"
        job.started_at = now_iso()

    try:
        intake = normalize_intake_from_params(params)
        intake_path = write_intake_file(intake)
        append_job_output(job, f"saved {intake_path.relative_to(PROJECT_ROOT)}\n")
        if not run_after_save:
            job.status = "completed"
            return

        notes = str(params.get("notes") or "").strip() or f"网页确认 intake 并启动 Part 1：{intake['research_topic']}"
        confirm_command = cli_command(
            PROJECT_ROOT,
            "confirm-gate",
            "intake_confirmed",
            "--notes",
            notes,
            "--no-auto-run-part1",
        )
        if run_command_for_job(job, confirm_command, PROJECT_ROOT, 1) != 0:
            job.status = "failed"
            return

        workspace_path = latest_workspace_from_registry()
        runner = workspace_path / "runtime" / "agents" / "part1_runner.py"
        if not runner.exists():
            raise FileNotFoundError(f"Missing workspace Part 1 runner: {runner}")
        append_job_output(job, f"\nworkspace: {workspace_path}\n")
        if run_command_for_job(job, [sys.executable, str(runner)], workspace_path, 2) != 0:
            job.status = "failed"
            return
        job.status = "completed"
    except subprocess.TimeoutExpired:
        job.status = "failed"
        job.error = f"Action timed out after {JOB_TIMEOUT_SECONDS} seconds"
    except Exception as exc:  # noqa: BLE001 - keep local job failure inspectable.
        job.status = "failed"
        job.error = str(exc)
        append_job_output(job, traceback.format_exc(limit=4))
    finally:
        job.finished_at = now_iso()


def start_job(context_id: str, root: Path, action_id: str, params: dict[str, Any]) -> dict[str, Any]:
    if action_id in {"save-intake", "save-intake-run"}:
        job = Job(
            job_id=uuid4().hex,
            action_id=action_id,
            context_id="root",
            context_path=str(PROJECT_ROOT),
            commands=[["internal", action_id]],
        )
        with JOBS_LOCK:
            JOBS[job.job_id] = job
        thread = threading.Thread(
            target=run_intake_job,
            args=(job.job_id, params, action_id == "save-intake-run"),
            daemon=True,
        )
        thread.start()
        return job.to_dict()

    commands = build_commands(root, action_id, params)
    job = Job(
        job_id=uuid4().hex,
        action_id=action_id,
        context_id=context_id,
        context_path=str(root),
        commands=commands,
    )
    with JOBS_LOCK:
        JOBS[job.job_id] = job
    thread = threading.Thread(target=run_job, args=(job.job_id,), daemon=True)
    thread.start()
    return job.to_dict()


def safe_artifact_path(root: Path, rel_path: str) -> Path:
    rel_path = rel_path.strip().replace("\\", "/")
    if rel_path.startswith("/") or ".." in Path(rel_path).parts:
        raise ValueError("Invalid artifact path")
    if not any(rel_path == prefix or rel_path.startswith(prefix) for prefix in SAFE_ARTIFACT_PREFIXES):
        raise ValueError("Path is outside readable workflow artifact prefixes")
    path = (root / rel_path).resolve()
    if not str(path).startswith(str(root.resolve())):
        raise ValueError("Invalid artifact path")
    return path


def artifact_preview(context_id: str | None, rel_path: str) -> dict[str, Any]:
    selected_id, root = resolve_context(context_id)
    path = safe_artifact_path(root, rel_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(rel_path)
    if path.suffix.lower() == ".pdf":
        raise ValueError("PDF preview is not exposed through this console")

    raw = path.read_bytes()
    truncated = len(raw) > MAX_PREVIEW_BYTES
    text = raw[:MAX_PREVIEW_BYTES].decode("utf-8", errors="replace")
    return {
        "context_id": selected_id,
        "path": rel_path,
        "size": len(raw),
        "truncated": truncated,
        "content": text,
    }


class LocalWebHandler(BaseHTTPRequestHandler):
    server_version = "ResearchLocalWeb/1.0"

    def log_message(self, format_string: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format_string % args))

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text_error(self, message: str, status: int = 400) -> None:
        self.send_json({"error": message}, status=status)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def serve_static(self, request_path: str) -> None:
        if request_path in {"", "/"}:
            path = STATIC_ROOT / "index.html"
        else:
            static_rel = request_path.removeprefix("/static/")
            if request_path.startswith("/static/"):
                path = (STATIC_ROOT / static_rel).resolve()
            else:
                path = (STATIC_ROOT / request_path.lstrip("/")).resolve()
        if not str(path).startswith(str(STATIC_ROOT.resolve())) or not path.exists() or not path.is_file():
            self.send_text_error("Not found", status=404)
            return
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(path.name)
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/status":
                self.send_json(page_status((query.get("context_id") or [None])[0]))
                return
            if parsed.path == "/api/actions":
                self.send_json({"actions": ACTION_SPECS})
                return
            if parsed.path.startswith("/api/jobs/"):
                job_id = parsed.path.rsplit("/", 1)[-1]
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                    payload = job.to_dict() if job else None
                if payload is None:
                    self.send_text_error("Job not found", status=404)
                    return
                self.send_json(payload)
                return
            if parsed.path == "/api/artifact":
                rel_path = (query.get("path") or [""])[0]
                self.send_json(artifact_preview((query.get("context_id") or [None])[0], rel_path))
                return
            self.serve_static(parsed.path)
        except Exception as exc:  # noqa: BLE001 - return local diagnostic.
            self.send_text_error(str(exc), status=400)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        try:
            if self.path != "/api/actions":
                self.send_text_error("Not found", status=404)
                return
            body = self.read_json_body()
            action_id = str(body.get("action_id") or "")
            if action_id in {"save-intake", "save-intake-run"}:
                context_id, root = "root", PROJECT_ROOT
            else:
                context_id, root = resolve_context(str(body.get("context_id") or default_context_id()))
            params = body.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("params must be an object")
            self.send_json(start_job(context_id, root, action_id, params), status=202)
        except Exception as exc:  # noqa: BLE001 - return local diagnostic.
            self.send_text_error(str(exc), status=400)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local research workflow web console.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Defaults to 127.0.0.1.")
    parser.add_argument("--port", type=int, default=8765, help="Bind port. Defaults to 8765.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), LocalWebHandler)
    print(f"Local web console: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local web console.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
