"""
Research-to-Manuscript Pipeline — Core Runtime

职责：
  - 状态文件读写（含备份）
  - Canonical artifact 存在性与 schema 校验
  - Stage gate 校验（artifact + human gates + wiki health）
  - Stage 推进逻辑
  - Process memory 写入
"""

import json
import re
import shutil
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from runtime.writing_contract import public_text_has_internal_markers
    from runtime.source_quota import build_source_quota_report
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    runtime_dir = Path(__file__).resolve().parent
    if str(runtime_dir) not in sys.path:
        sys.path.insert(0, str(runtime_dir))
    from writing_contract import public_text_has_internal_markers
    from source_quota import build_source_quota_report

PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / "runtime" / "state.json"
PROCESS_MEMORY_DIR = PROJECT_ROOT / "process-memory"

# ── Canonical artifacts per stage ─────────────────────────────────────────────

CANONICAL_ARTIFACTS: dict[str, list[str]] = {
    "part1": [
        "raw-library/metadata.json",
        "outputs/part1/authenticity_report.json",
    ],
    "part2": [
        "research-wiki/index.json",
    ],
    "part3": [
        "outputs/part3/argument_tree.json",
        "outputs/part3/candidate_comparison.json",
        "outputs/part3/human_selection_feedback.json",
    ],
    "part4": [
        "outputs/part4/paper_outline.json",
        "outputs/part4/outline_rationale.json",
        "outputs/part4/reference_alignment_report.json",
    ],
    "part5": [
        "outputs/part5/manuscript_v2.md",
        "outputs/part5/review_matrix.json",
        "outputs/part5/review_report.md",
        "outputs/part5/revision_log.json",
        "outputs/part5/part6_readiness_decision.json",
    ],
    "part6": [
        "outputs/part6/final_manuscript.md",
        "outputs/part6/claim_risk_report.json",
        "outputs/part6/citation_consistency_report.json",
        "outputs/part6/submission_package_manifest.json",
        "outputs/part6/final_readiness_decision.json",
    ],
}

# Which artifacts have a JSON Schema to validate against
SCHEMA_MAP: dict[str, str] = {
    "raw-library/metadata.json":             "schemas/part1_source_bundle.schema.json",
    "research-wiki/index.json":              "schemas/part2_wiki_bundle.schema.json",
    "outputs/part3/argument_tree.json":      "schemas/part3_argument_tree.schema.json",
    "outputs/part3/candidate_comparison.json": "schemas/part3_candidate_comparison.schema.json",
    "outputs/part3/human_selection_feedback.json": "schemas/part3_human_selection_feedback.schema.json",
    "outputs/part4/paper_outline.json":      "schemas/part4_outline.schema.json",
    "outputs/part5/review_matrix.json":      "schemas/part5_review_matrix.schema.json",
    "outputs/part5/revision_log.json":       "schemas/part5_revision_log.schema.json",
    "outputs/part5/part6_readiness_decision.json": "schemas/part5_readiness_decision.schema.json",
    "outputs/part6/claim_risk_report.json": "schemas/part6_claim_risk_report.schema.json",
    "outputs/part6/citation_consistency_report.json": "schemas/part6_citation_consistency_report.schema.json",
    "outputs/part6/submission_package_manifest.json": "schemas/part6_submission_package_manifest.schema.json",
    "outputs/part6/final_readiness_decision.json": "schemas/part6_final_readiness_decision.schema.json",
}

# Human gates required before a stage can be marked complete
HUMAN_GATES: dict[str, list[str]] = {
    "part1": ["intake_confirmed"],
    "part2": [],
    "part3": ["argument_tree_selected"],
    "part4": [],
    "part5": [],
    "part6": ["part6_finalization_authorized", "part6_final_decision_confirmed"],
}
DEPRECATED_HUMAN_GATES: dict[str, str] = {
    "outline_confirmed": "part4",
    "writing_phase_authorized": "part5",
    "part5_prep_confirmed": "part5",
    "part5_review_completed": "part5",
    "manuscript_v2_accepted": "part5",
}

STAGE_ORDER = ["part1", "part2", "part3", "part4", "part5", "part6"]
PART3_EXPECTED_STRATEGIES = {"theory_first", "problem_solution", "case_application"}
PART3_EXPECTED_CANDIDATE_IDS = {f"candidate_{strategy}" for strategy in PART3_EXPECTED_STRATEGIES}
PART3_REFINED_CANDIDATE_DIR = "outputs/part3/refined_candidate_argument_trees"
PART5_READINESS_VERDICTS = {
    "ready_for_part6",
    "ready_for_part6_with_research_debt",
    "blocked_by_evidence_debt",
}
PART5_HUMAN_GATE_ORDER = [
    "writing_phase_authorized",
    "part5_prep_confirmed",
    "part5_review_completed",
    "manuscript_v2_accepted",
]
PART5_HANDOFF_ARTIFACTS = [
    "outputs/part5/manuscript_v2.md",
    "outputs/part5/review_matrix.json",
    "outputs/part5/review_report.md",
    "outputs/part5/revision_log.json",
    "outputs/part5/part6_readiness_decision.json",
    "outputs/part5/claim_evidence_matrix.json",
    "outputs/part5/citation_map.json",
    "outputs/part5/figure_plan.json",
    "outputs/part5/claim_risk_report.json",
    "outputs/part5/citation_consistency_precheck.json",
]
PART1_ACCEPTED_SOURCES = "outputs/part1/accepted_sources.json"
PART1_AUTHENTICITY_REPORT = "outputs/part1/authenticity_report.json"
RAW_LIBRARY_METADATA = "raw-library/metadata.json"
RESEARCH_WIKI_INDEX = "research-wiki/index.json"
PART5_CITATION_MAP = "outputs/part5/citation_map.json"
PART6_FINAL_READINESS_DECISION = "outputs/part6/final_readiness_decision.json"
PART6_SUBMISSION_PACKAGE_MANIFEST = "outputs/part6/submission_package_manifest.json"
PART6_CLAIM_RISK_REPORT = "outputs/part6/claim_risk_report.json"
PART6_CITATION_CONSISTENCY_REPORT = "outputs/part6/citation_consistency_report.json"
PART6_FINAL_MANUSCRIPT = "outputs/part6/final_manuscript.md"
PART6_FINAL_ABSTRACT = "outputs/part6/final_abstract.md"
PART6_FINAL_KEYWORDS = "outputs/part6/final_keywords.json"
PART6_SUBMISSION_CHECKLIST = "outputs/part6/submission_checklist.md"
PART6_FINAL_MANUSCRIPT_DOCX = "outputs/part6/final_manuscript.docx"
PART6_DOCX_FORMAT_REPORT = "outputs/part6/docx_format_report.json"
PART6_REQUIRED_PACKAGE_FILES = {
    PART6_FINAL_MANUSCRIPT,
    PART6_FINAL_ABSTRACT,
    PART6_FINAL_KEYWORDS,
    PART6_SUBMISSION_CHECKLIST,
    PART6_FINAL_MANUSCRIPT_DOCX,
    PART6_DOCX_FORMAT_REPORT,
    PART6_CLAIM_RISK_REPORT,
    PART6_CITATION_CONSISTENCY_REPORT,
    PART6_FINAL_READINESS_DECISION,
}
PART6_COMPLETION_FINGERPRINT_FILES = sorted(
    set(CANONICAL_ARTIFACTS["part6"]) | PART6_REQUIRED_PACKAGE_FILES
)
PART6_READINESS_VERDICTS = {
    "formal_submission_ready",
    "internal_review_only",
    "blocked_by_evidence_debt",
}
PART6_FINAL_DECISION_PENDING_RISK = "仍需用户确认 part6_final_decision_confirmed。"
ACCEPTED_AUTHENTICITY_VERDICTS = {"pass", "warning"}


# ── Utilities ──────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authenticity_verdict_is_accepted(verdict) -> bool:
    return verdict is None or verdict in ACCEPTED_AUTHENTICITY_VERDICTS


def _default_stage_state() -> dict:
    return {
        "status": "not_started",
        "started_at": None,
        "completed_at": None,
        "gate_passed": False,
        "human_gates_completed": [],
    }


def _stage_state(state: dict, stage_id: str) -> dict:
    return state.get("stages", {}).get(stage_id, _default_stage_state())


def _ensure_stage_state(state: dict, stage_id: str) -> dict:
    stages = state.setdefault("stages", {})
    if stage_id not in stages:
        stages[stage_id] = _default_stage_state()
    return stages[stage_id]


# ── State I/O ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if not STATE_FILE.exists():
        raise FileNotFoundError(
            f"State file not found: {STATE_FILE}\n"
            "Run `python cli.py init` to initialize the project."
        )
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"State file is corrupted (invalid JSON): {e}\n"
            f"Backup may exist at {STATE_FILE}.bak — do NOT silently reset.\n"
            "Investigate root cause before repair."
        )


def save_state(state: dict) -> None:
    """Write state. Always backs up the previous file before overwriting."""
    if STATE_FILE.exists():
        shutil.copy2(STATE_FILE, str(STATE_FILE) + ".bak")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def init_state() -> dict:
    if STATE_FILE.exists():
        raise RuntimeError(
            "State file already exists at runtime/state.json.\n"
            "Use `python cli.py doctor` to diagnose current state."
        )
    state = {
        "schema_version": "1.0.0",
        "pipeline_id": "research-to-manuscript-v1",
        "initialized_at": now_iso(),
        "current_stage": None,
        "stages": {
            stage: {
                "status": "not_started",   # not_started | in_progress | completed | failed
                "started_at": None,
                "completed_at": None,
                "gate_passed": False,
                "human_gates_completed": [],
            }
            for stage in STAGE_ORDER
        },
        "last_failure": None,
        "repair_log": [],
        "human_decision_log": [],
    }
    save_state(state)
    return state


# ── Artifact checks ───────────────────────────────────────────────────────────

def check_artifacts(stage_id: str) -> list[dict]:
    """Return existence + schema validation results for all canonical artifacts of a stage."""
    results = []
    for rel_path in CANONICAL_ARTIFACTS.get(stage_id, []):
        full_path = PROJECT_ROOT / rel_path
        exists = full_path.exists()
        schema_valid: Optional[bool] = None
        issues: list[str] = []

        if exists and rel_path in SCHEMA_MAP:
            schema_path = PROJECT_ROOT / SCHEMA_MAP[rel_path]
            schema_valid, issues = _validate_schema(full_path, schema_path)

        results.append({
            "path": rel_path,
            "exists": exists,
            "schema_valid": schema_valid,
            "issues": issues,
        })
    return results


def _validate_schema(artifact_path: Path, schema_path: Path) -> tuple[Optional[bool], list[str]]:
    try:
        import jsonschema
    except ImportError:
        return None, ["jsonschema not installed — run: pip install jsonschema"]

    if not schema_path.exists():
        return None, [f"Schema file not found: {schema_path.relative_to(PROJECT_ROOT)}"]

    try:
        with open(artifact_path, encoding="utf-8") as f:
            data = json.load(f)
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [e.message]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in artifact: {e}"]


def _load_json_artifact(rel_path: str) -> tuple[Optional[dict], Optional[str]]:
    path = PROJECT_ROOT / rel_path
    if not path.exists():
        return None, f"缺少 artifact: {rel_path}"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"{rel_path} 无法解析: {e}"
    if not isinstance(data, dict):
        return None, f"{rel_path} 必须是 JSON object"
    return data, None


def _write_json_artifact(rel_path: str, data: dict) -> None:
    path = PROJECT_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _has_non_empty_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_non_empty_list(value) -> bool:
    return isinstance(value, list) and any(_has_non_empty_text(item) for item in value)


def _safe_part1_metadata_path(
    rel_path: object,
    required_prefix: str,
    required_suffix: str,
    field_name: str,
) -> tuple[Path | None, str | None]:
    if not isinstance(rel_path, str) or not rel_path.strip():
        return None, f"{field_name} 不能为空"
    rel = Path(rel_path.strip())
    if rel.is_absolute() or ".." in rel.parts:
        return None, f"{field_name} 必须是项目内相对路径"
    normalized = rel.as_posix()
    if not normalized.startswith(required_prefix) or not normalized.endswith(required_suffix):
        return None, f"{field_name} 必须位于 {required_prefix} 且以 {required_suffix} 结尾"
    root = PROJECT_ROOT.resolve()
    candidate = PROJECT_ROOT / rel
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None, f"{field_name} 解析后越过项目根目录"
    return candidate, None


def _safe_part1_local_artifact_path(rel_path: object, field_name: str) -> tuple[Path | None, str | None]:
    if isinstance(rel_path, str):
        normalized = Path(rel_path.strip()).as_posix()
        if normalized.startswith("raw-library/web-archives/") and normalized.endswith(".md"):
            return _safe_part1_metadata_path(
                rel_path,
                "raw-library/web-archives/",
                ".md",
                field_name,
            )
    return _safe_part1_metadata_path(
        rel_path,
        "raw-library/papers/",
        ".pdf",
        field_name,
    )


def _part1_intake_gate_issues() -> list[str]:
    path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    if not path.exists():
        return [f"outputs/part1/intake.json 不存在: {path}"]
    try:
        with open(path, encoding="utf-8") as f:
            intake = json.load(f)
    except json.JSONDecodeError as e:
        return [f"outputs/part1/intake.json 无法解析: {e}"]
    if not isinstance(intake, dict):
        return ["outputs/part1/intake.json 必须是 JSON object"]

    issues: list[str] = []
    if not _has_non_empty_text(intake.get("intake_id")):
        issues.append("intake_id 不能为空")
    if not _has_non_empty_text(intake.get("research_topic")):
        issues.append("research_topic 不能为空")
    if not _has_non_empty_text(intake.get("research_question")):
        issues.append("research_question 不能为空")
    if not _has_non_empty_list(intake.get("keywords_required")):
        issues.append("keywords_required 必须至少包含一个检索锚点")
    if not isinstance(intake.get("time_range"), dict):
        issues.append("time_range 必须是 object")
    if not isinstance(intake.get("source_preference"), dict):
        issues.append("source_preference 必须是 object")
    if not _has_non_empty_text(intake.get("scope_notes")):
        issues.append("scope_notes 不能为空")
    return issues


def check_part1_contract_gate() -> list[str]:
    """Validate Part 1 workflow artifacts beyond canonical presence."""
    issues: list[str] = []

    for rel_path in [
        "outputs/part1/search_plan.json",
        "outputs/part1/download_manifest.json",
        "outputs/part1/relevance_scores.json",
        "outputs/part1/accepted_sources.json",
        "outputs/part1/source_quota_report.json",
        "outputs/part1/downloaded_papers_table.csv",
        "outputs/part1/downloaded_papers_table.md",
    ]:
        if not (PROJECT_ROOT / rel_path).exists():
            issues.append(f"缺少 Part 1 workflow artifact: {rel_path}")

    manifest, err = _load_json_artifact("outputs/part1/download_manifest.json")
    if err:
        issues.append(err)
    elif manifest:
        if manifest.get("task_type") != "cnki_search_download":
            issues.append("download_manifest.task_type 不是 cnki_search_download")
        if manifest.get("dry_run") is True:
            issues.append("download_manifest 是 dry_run 产物")
        if manifest.get("run_status") in ("failed", "fatal"):
            issues.append(f"CNKI 下载失败: {manifest.get('fatal_error', 'unknown')}")
        if int(manifest.get("total_downloaded") or 0) <= 0:
            issues.append("download_manifest.total_downloaded 必须大于 0")
        if "cnki_q1_1" not in set(manifest.get("queries_executed", [])):
            issues.append("download_manifest 缺少 CNKI 主查询 cnki_q1_1")

    metadata, err = _load_json_artifact("raw-library/metadata.json")
    if err:
        issues.append(err)
    elif metadata:
        sources = metadata.get("sources", [])
        if not sources:
            issues.append("raw-library/metadata.json sources 为空")
        summary = metadata.get("summary", {})
        if summary.get("total_accepted") != len(sources):
            issues.append("metadata.summary.total_accepted 与 sources 数量不一致")

        for source in sources:
            source_id = source.get("source_id", "unknown")
            pdf_rel = source.get("local_path", f"raw-library/papers/{source_id}.pdf")
            prov_rel = source.get("provenance_path", f"raw-library/provenance/{source_id}.json")
            pdf_path, pdf_path_issue = _safe_part1_local_artifact_path(pdf_rel, "local_path")
            if pdf_path_issue:
                issues.append(f"metadata source {source_id} local_path 非法: {pdf_path_issue}")
                continue
            prov_path, prov_path_issue = _safe_part1_metadata_path(
                prov_rel,
                "raw-library/provenance/",
                ".json",
                "provenance_path",
            )
            if prov_path_issue:
                issues.append(f"metadata source {source_id} provenance_path 非法: {prov_path_issue}")
                continue
            if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                issues.append(f"metadata source 缺少本地文件: {source_id}")
            if not prov_path.exists():
                issues.append(f"metadata source 缺少 provenance: {source_id}")
                continue
            try:
                with open(prov_path, encoding="utf-8") as f:
                    provenance = json.load(f)
            except json.JSONDecodeError as e:
                issues.append(f"provenance 无法解析 [{source_id}]: {e}")
                continue
            if provenance.get("download_status") != "success":
                issues.append(f"provenance download_status 非 success: {source_id}")

        quota_report = build_source_quota_report(metadata)
        if not quota_report["passed"]:
            issues.extend(quota_report["issues"])

        recorded_quota, quota_err = _load_json_artifact("outputs/part1/source_quota_report.json")
        if quota_err:
            issues.append(quota_err)
        elif recorded_quota:
            if recorded_quota.get("counts") != quota_report["counts"]:
                issues.append("source_quota_report.counts 与 raw-library/metadata.json 不一致")
            if recorded_quota.get("passed") is not True:
                issues.append("source_quota_report.passed 不是 true")

    relevance, err = _load_json_artifact("outputs/part1/relevance_scores.json")
    if err:
        issues.append(err)
    elif relevance and int(relevance.get("total_scored") or 0) <= 0:
        issues.append("relevance_scores.total_scored 必须大于 0")

    return issues


# ── Wiki health check ─────────────────────────────────────────────────────────

def check_wiki_health_gate(wiki_index: dict) -> list[str]:
    """
    Validate the wiki health_summary against acceptable thresholds.

    Thresholds (user-defined):
      - source_mapping_complete must be True (hard block)
      - isolated / orphan pages <= 2
      - unresolved / contradiction pages <= 3
    """
    summary = wiki_index.get("health_summary", {})
    pages = wiki_index.get("pages", [])
    issues: list[str] = []

    # 1. source_mapping_complete — hard block
    if not wiki_index.get("source_mapping_complete", False):
        issues.append(
            "source_mapping_complete = false：存在无来源映射的 wiki 页面，"
            "gate 要求所有页面至少关联一个 source_id"
        )

    if not isinstance(pages, list) or not pages:
        issues.append("research-wiki/index.json pages 不能为空")
        pages = []

    if isinstance(summary, dict) and summary.get("total_pages") not in (None, len(pages)):
        issues.append(
            f"health_summary.total_pages = {summary.get('total_pages')}，"
            f"但 pages 实际数量为 {len(pages)}"
        )

    page_ids = {
        page.get("page_id")
        for page in pages
        if isinstance(page, dict) and isinstance(page.get("page_id"), str)
    }
    for page in pages:
        if not isinstance(page, dict):
            issues.append("research-wiki/index.json pages 包含非 object 项")
            continue
        page_id = page.get("page_id", "unknown")
        source_ids = page.get("source_ids", [])
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(f"wiki 页面缺少 source_ids: {page_id}")
        file_path = page.get("file_path")
        if not isinstance(file_path, str) or not file_path:
            issues.append(f"wiki 页面缺少 file_path: {page_id}")
        elif not (PROJECT_ROOT / file_path).exists():
            issues.append(f"wiki 页面 file_path 不存在 [{page_id}]: {file_path}")
        for related_page_id in page.get("related_pages", []) or []:
            if isinstance(related_page_id, str) and related_page_id not in page_ids:
                issues.append(f"wiki related_pages 指向不存在的 page_id [{page_id}]: {related_page_id}")

    unresolved_items = wiki_index.get("unresolved_references", [])
    unresolved_count = summary.get("unresolved_references")
    if unresolved_count is None:
        unresolved_count = len(unresolved_items) if isinstance(unresolved_items, list) else 0
    if unresolved_count:
        examples: list[str] = []
        if isinstance(unresolved_items, list):
            for item in unresolved_items[:3]:
                if isinstance(item, dict):
                    examples.append(
                        f"{item.get('page_id', 'unknown')} -> {item.get('unresolved_title', 'unknown')}"
                    )
        suffix = f"；示例: {'; '.join(examples)}" if examples else ""
        issues.append(
            f"unresolved_references = {unresolved_count}，存在未解析 wiki 引用{suffix}"
        )

    # 2. Isolated / orphan pages <= 2
    isolated = summary.get("isolated_pages", summary.get("orphan_pages", 0))
    if isolated > 2:
        issues.append(
            f"孤立页面（isolated_pages）= {isolated}，超过阈值 2；"
            "请为这些页面建立交叉引用或合并"
        )

    # 3. Unresolved contradiction pages <= 3
    contradictions = summary.get(
        "unresolved_contradiction_pages",
        summary.get("contradiction_pages",
            summary.get("contradiction_count", 0))
    )
    if contradictions > 3:
        issues.append(
            f"未解决矛盾页面（contradiction_pages）= {contradictions}，超过阈值 3；"
            "请先 reconcile 或标注处理方式"
        )

    return issues


def check_writing_policy_gate() -> list[str]:
    """Validate the Part 2 writing-policy layer required by the architecture."""
    issues: list[str] = []
    policy_root = PROJECT_ROOT / "writing-policy"
    source_index_path = policy_root / "source_index.json"

    if not policy_root.exists():
        return ["writing-policy/ 目录缺失 — Part 2 要求研究证据层与写作规范层物理分离"]
    if not source_index_path.exists():
        return ["缺少 writing-policy/source_index.json — Part 2 gate 要求写作规范层已建立"]

    try:
        with open(source_index_path, encoding="utf-8") as f:
            source_index = json.load(f)
    except json.JSONDecodeError as e:
        return [f"writing-policy/source_index.json 无法解析: {e}"]

    if not isinstance(source_index, dict):
        return ["writing-policy/source_index.json 必须是 JSON object"]

    rules = source_index.get("rules", [])
    style_guides = source_index.get("style_guides", [])
    if not isinstance(rules, list) or not rules:
        issues.append("writing-policy/source_index.json 缺少 rules")
    if not isinstance(style_guides, list) or not style_guides:
        issues.append("writing-policy/source_index.json 缺少 style_guides")

    for item_type, items in [
        ("rules", rules),
        ("style_guides", style_guides),
        ("reference_cases", source_index.get("reference_cases", [])),
        ("rubrics", source_index.get("rubrics", [])),
    ]:
        if not isinstance(items, list):
            issues.append(f"writing-policy/source_index.json {item_type} 必须是 list")
            continue
        for item in items:
            if not isinstance(item, dict):
                issues.append(f"writing-policy/source_index.json {item_type} 包含非 object 项")
                continue
            path = item.get("path")
            if not isinstance(path, str) or not path:
                issues.append(f"writing-policy/source_index.json {item_type} 缺少 path")
                continue
            if not (PROJECT_ROOT / path).exists():
                issues.append(f"writing-policy/source_index.json 指向不存在的文件: {path}")
            if isinstance(path, str) and not path.startswith("writing-policy/"):
                issues.append(f"writing-policy/source_index.json 不应索引 writing-policy/ 外部文件: {path}")
            usage = item.get("usage")
            may_be_evidence = item.get("may_be_used_as_research_evidence")
            usage_is_constraint = (
                isinstance(usage, str)
                and usage.endswith("_only")
                and "research_evidence" not in usage
            )
            if may_be_evidence is not False and not usage_is_constraint:
                issues.append(
                    "writing-policy/source_index.json 索引项必须声明不可作为 research evidence: "
                    f"{path}"
                )

    coverage = source_index.get("coverage", {})
    if isinstance(coverage, dict):
        if coverage.get("structure") is not True:
            issues.append("writing-policy coverage.structure 必须为 true")
        if coverage.get("expression") is not True:
            issues.append("writing-policy coverage.expression 必须为 true")

    return issues


def check_wiki_source_traceability(wiki_index: dict) -> list[str]:
    """Ensure wiki source_ids resolve to accepted, verified raw-library sources."""
    issues: list[str] = []
    metadata, err = _load_json_artifact("raw-library/metadata.json")
    if err:
        return [err]

    accepted_sources: dict[str, dict] = {}
    for source in metadata.get("sources", []) or []:
        if isinstance(source, dict) and isinstance(source.get("source_id"), str):
            accepted_sources[source["source_id"]] = source

    if not accepted_sources:
        return ["raw-library/metadata.json 没有可回溯 source；Part 2 wiki 不能通过"]

    for page in wiki_index.get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id", "unknown")
        for source_id in page.get("source_ids", []) or []:
            if source_id not in accepted_sources:
                issues.append(f"wiki 页面 source_id 不存在于 raw-library [{page_id}]: {source_id}")
                continue
            source = accepted_sources[source_id]
            verdict = source.get("authenticity_verdict")
            status = source.get("authenticity_status")
            if not _authenticity_verdict_is_accepted(verdict) or status not in (None, "verified"):
                issues.append(
                    f"wiki 页面引用了未通过真实性校验的 source [{page_id}]: {source_id}"
                )

    return issues


def _collect_argument_refs(node: dict) -> tuple[set[str], set[str]]:
    source_ids = set(node.get("support_source_ids", []) or [])
    page_ids = set(node.get("wiki_page_ids", []) or [])
    for child in node.get("children", []) or []:
        if isinstance(child, dict):
            child_sources, child_pages = _collect_argument_refs(child)
            source_ids.update(child_sources)
            page_ids.update(child_pages)
    return source_ids, page_ids


def check_part3_contract_gate() -> list[str]:
    """Validate Part 3 workflow artifacts beyond canonical presence."""
    issues: list[str] = []

    wiki_index, err = _load_json_artifact("research-wiki/index.json")
    wiki_page_ids: set[str] = set()
    wiki_source_ids: set[str] = set()
    if err:
        issues.append(err)
    elif wiki_index:
        for page in wiki_index.get("pages", []) or []:
            if not isinstance(page, dict):
                continue
            page_id = page.get("page_id")
            if isinstance(page_id, str):
                wiki_page_ids.add(page_id)
            wiki_source_ids.update(
                source_id
                for source_id in page.get("source_ids", []) or []
                if isinstance(source_id, str)
            )

    metadata, err = _load_json_artifact("raw-library/metadata.json")
    raw_source_ids: set[str] = set()
    if err:
        issues.append(err)
    elif metadata:
        raw_source_ids = {
            source.get("source_id")
            for source in metadata.get("sources", []) or []
            if isinstance(source, dict) and isinstance(source.get("source_id"), str)
        }

    seed_map, err = _load_json_artifact("outputs/part3/argument_seed_map.json")
    if err:
        issues.append(err)
    elif seed_map:
        if seed_map.get("wiki_ref") != "research-wiki/index.json":
            issues.append("argument_seed_map.json.wiki_ref 必须指向 research-wiki/index.json")
        for section in [
            "candidate_claims",
            "evidence_points",
            "contradictions",
            "counterclaims",
            "method_paths",
            "case_boundaries",
            "evidence_gaps",
            "background_only_materials",
        ]:
            for item in seed_map.get(section, []) or []:
                if not isinstance(item, dict):
                    issues.append(f"argument_seed_map.json {section} 包含非 object 项")
                    continue
                item_id = item.get("item_id", "unknown")
                for source_id in item.get("source_ids", []) or []:
                    if source_id not in wiki_source_ids:
                        issues.append(f"argument_seed_map.json 引用了 wiki 中不存在的 source_id [{item_id}]: {source_id}")
                    if source_id not in raw_source_ids:
                        issues.append(f"argument_seed_map.json 引用了 raw-library 中不存在的 source_id [{item_id}]: {source_id}")
                for page_id in item.get("wiki_page_ids", []) or []:
                    if page_id not in wiki_page_ids:
                        issues.append(f"argument_seed_map.json 引用了不存在的 wiki page_id [{item_id}]: {page_id}")

    candidate_dir = PROJECT_ROOT / "outputs" / "part3" / "candidate_argument_trees"
    candidate_files = sorted(candidate_dir.glob("*.json")) if candidate_dir.exists() else []
    if len(candidate_files) != 3:
        issues.append(f"Part 3 候选 argument tree 必须正好 3 份，当前为 {len(candidate_files)} 份")

    candidate_ids: set[str] = set()
    candidate_strategies: set[str] = set()
    for candidate_file in candidate_files:
        schema_valid, schema_issues = _validate_schema(
            candidate_file,
            PROJECT_ROOT / "schemas" / "part3_candidate_tree.schema.json",
        )
        if schema_valid is False:
            rel = candidate_file.relative_to(PROJECT_ROOT)
            issues.append(f"候选 argument tree schema 校验失败 [{rel}]: {'; '.join(schema_issues)}")
            continue
        if schema_issues:
            rel = candidate_file.relative_to(PROJECT_ROOT)
            issues.append(f"候选 argument tree schema 校验跳过 [{rel}]: {'; '.join(schema_issues)}")
            continue
        candidate, err = _load_json_artifact(str(candidate_file.relative_to(PROJECT_ROOT)))
        if err:
            issues.append(err)
            continue
        candidate_id = candidate.get("candidate_id")
        if candidate_id:
            candidate_ids.add(candidate_id)
        strategy = candidate.get("strategy")
        if isinstance(strategy, str):
            candidate_strategies.add(strategy)
        root = candidate.get("root", {})
        source_ids, page_ids = _collect_argument_refs(root if isinstance(root, dict) else {})
        if not source_ids:
            issues.append(f"候选 argument tree 缺少 support_source_ids: {candidate_file.name}")
        if not page_ids:
            issues.append(f"候选 argument tree 缺少 wiki_page_ids: {candidate_file.name}")
        unknown_sources = source_ids - wiki_source_ids
        if unknown_sources:
            issues.append(f"候选 argument tree 引用了 wiki 中不存在的 source_id [{candidate_file.name}]: {sorted(unknown_sources)}")
        unknown_raw_sources = source_ids - raw_source_ids
        if unknown_raw_sources:
            issues.append(f"候选 argument tree 引用了 raw-library 中不存在的 source_id [{candidate_file.name}]: {sorted(unknown_raw_sources)}")
        unknown_pages = page_ids - wiki_page_ids
        if unknown_pages:
            issues.append(f"候选 argument tree 引用了不存在的 wiki page_id [{candidate_file.name}]: {sorted(unknown_pages)}")

    if candidate_ids and candidate_ids != PART3_EXPECTED_CANDIDATE_IDS:
        issues.append(f"Part 3 候选 ID 必须为 {sorted(PART3_EXPECTED_CANDIDATE_IDS)}，当前为 {sorted(candidate_ids)}")
    if candidate_strategies and candidate_strategies != PART3_EXPECTED_STRATEGIES:
        issues.append(f"Part 3 候选策略必须为 {sorted(PART3_EXPECTED_STRATEGIES)}，当前为 {sorted(candidate_strategies)}")

    comparison, err = _load_json_artifact("outputs/part3/candidate_comparison.json")
    compared_ids: set[str] = set()
    if err:
        issues.append(err)
    elif comparison:
        compared_ids = {item.get("candidate_id") for item in comparison.get("candidates", [])}
        if compared_ids != candidate_ids:
            issues.append(f"candidate_comparison.json 候选集合与候选文件不一致: compared={sorted(compared_ids)}, files={sorted(candidate_ids)}")
        recommended = comparison.get("recommendation", {}).get("recommended_candidate_id")
        if recommended and recommended not in candidate_ids:
            issues.append(f"comparison 推荐了不存在的候选: {recommended}")
        if comparison.get("recommendation", {}).get("human_decision_required") is not True:
            issues.append("candidate_comparison.json 必须声明 human_decision_required = true")

    selection, err = _load_json_artifact("outputs/part3/human_selection_feedback.json")
    selected_candidate_id = None
    selected_candidate_source = "original"
    selected_candidate_ref = None
    if err:
        issues.append(err)
    elif selection:
        selected_candidate_id = selection.get("selected_candidate_id")
        selected_candidate_source = selection.get("candidate_source", "original")
        selected_candidate_ref = selection.get("candidate_tree_ref")
        if selected_candidate_source not in ("original", "refined"):
            issues.append(f"human_selection_feedback.candidate_source 非法: {selected_candidate_source}")
        if selected_candidate_source == "original" and selected_candidate_id not in candidate_ids:
            issues.append(f"human_selection_feedback 选择了不存在的候选: {selected_candidate_id}")
        if selected_candidate_source == "refined":
            if not isinstance(selected_candidate_ref, str) or not selected_candidate_ref.startswith(f"{PART3_REFINED_CANDIDATE_DIR}/"):
                issues.append("human_selection_feedback refined candidate_tree_ref 必须指向 refined_candidate_argument_trees/")
            elif not (PROJECT_ROOT / selected_candidate_ref).exists():
                issues.append(f"human_selection_feedback 选择了不存在的 refined candidate: {selected_candidate_ref}")
            else:
                refined_candidate, refined_err = _load_json_artifact(selected_candidate_ref)
                if refined_err:
                    issues.append(refined_err)
                elif refined_candidate:
                    based_on_ref = refined_candidate.get("based_on_candidate_ref")
                    based_on_id = Path(based_on_ref).stem if isinstance(based_on_ref, str) else None
                    if based_on_id not in candidate_ids:
                        issues.append(f"refined candidate based_on_candidate_ref 不存在于原始候选: {based_on_ref}")
                    if compared_ids and based_on_id not in compared_ids:
                        issues.append(f"refined candidate 依赖了未比较的原始候选: {based_on_id}")
        if compared_ids and selected_candidate_source == "original" and selected_candidate_id not in compared_ids:
            issues.append(f"human_selection_feedback 选择了未比较的候选: {selected_candidate_id}")
        if not (selection.get("selection_notes") or "").strip():
            issues.append("human_selection_feedback.selection_notes 为空")

    argument_tree, err = _load_json_artifact("outputs/part3/argument_tree.json")
    if err:
        issues.append(err)
    elif argument_tree:
        if not argument_tree.get("locked_at"):
            issues.append("argument_tree.json 缺少 locked_at，尚未锁定")
        if selected_candidate_id and argument_tree.get("selected_candidate_id") != selected_candidate_id:
            issues.append("argument_tree.json.selected_candidate_id 与 human_selection_feedback 不一致")
        if argument_tree.get("candidate_source", "original") != selected_candidate_source:
            issues.append("argument_tree.json.candidate_source 与 human_selection_feedback 不一致")
        if selected_candidate_ref and argument_tree.get("candidate_tree_ref") != selected_candidate_ref:
            issues.append("argument_tree.json.candidate_tree_ref 与 human_selection_feedback 不一致")
        if argument_tree.get("human_selection_ref") != "outputs/part3/human_selection_feedback.json":
            issues.append("argument_tree.json.human_selection_ref 未指向 human_selection_feedback.json")
        if argument_tree.get("candidate_comparison_ref") != "outputs/part3/candidate_comparison.json":
            issues.append("argument_tree.json.candidate_comparison_ref 未指向 candidate_comparison.json")
        source_ids, page_ids = _collect_argument_refs(argument_tree.get("root", {}))
        unknown_sources = source_ids - wiki_source_ids
        if unknown_sources:
            issues.append(f"argument_tree.json 引用了 wiki 中不存在的 source_id: {sorted(unknown_sources)}")
        unknown_raw_sources = source_ids - raw_source_ids
        if unknown_raw_sources:
            issues.append(f"argument_tree.json 引用了 raw-library 中不存在的 source_id: {sorted(unknown_raw_sources)}")
        unknown_pages = page_ids - wiki_page_ids
        if unknown_pages:
            issues.append(f"argument_tree.json 引用了不存在的 wiki page_id: {sorted(unknown_pages)}")

    return issues


def check_previous_stage_gates(stage_id: str, state: dict) -> list[str]:
    issues: list[str] = []
    if stage_id not in STAGE_ORDER:
        if stage_id not in CANONICAL_ARTIFACTS:
            return [f"未知 stage: {stage_id}"]
        previous_stage_ids = STAGE_ORDER
    else:
        previous_stage_ids = STAGE_ORDER[:STAGE_ORDER.index(stage_id)]
    for previous_stage_id in previous_stage_ids:
        previous = state["stages"].get(previous_stage_id, {})
        if previous.get("status") != "completed" or previous.get("gate_passed") is not True:
            issues.append(f"前序阶段未完成或 gate 未通过: {previous_stage_id}")
    return issues


def _human_gate_completed(state: dict, stage_id: str, gate_id: str) -> bool:
    gates = _stage_state(state, stage_id).get("human_gates_completed", [])
    return isinstance(gates, list) and gate_id in gates


def _part5_entry_prerequisite_issues(state: dict) -> list[str]:
    issues: list[str] = []
    for stage_id in ["part1", "part2", "part3", "part4"]:
        stage = _stage_state(state, stage_id)
        if stage.get("status") != "completed" or stage.get("gate_passed") is not True:
            issues.append(f"{stage_id} gate 尚未通过")
    return issues


def _part5_gate_sequence_issues(gate_id: str, state: dict) -> list[str]:
    if gate_id not in PART5_HUMAN_GATE_ORDER:
        return []

    issues = _part5_entry_prerequisite_issues(state)
    gate_index = PART5_HUMAN_GATE_ORDER.index(gate_id)
    for required_gate in PART5_HUMAN_GATE_ORDER[:gate_index]:
        if not _human_gate_completed(state, "part5", required_gate):
            issues.append(f"{required_gate} gate 尚未完成")
    return issues


def check_part5_human_gate_prerequisites(state: dict) -> list[str]:
    issues: list[str] = []
    completed = set(_stage_state(state, "part5").get("human_gates_completed", []) or [])
    for gate_id in PART5_HUMAN_GATE_ORDER:
        if gate_id not in completed:
            continue
        for issue in _part5_gate_sequence_issues(gate_id, state):
            issues.append(f"{gate_id} 前置条件无效: {issue}")
    return issues


def check_part4_alignment_gate() -> list[str]:
    """Validate Part 4 workflow artifacts beyond canonical presence."""
    issues: list[str] = []

    outline, err = _load_json_artifact("outputs/part4/paper_outline.json")
    if err:
        issues.append(err)
        outline = None

    argument_tree, err = _load_json_artifact("outputs/part3/argument_tree.json")
    if err:
        issues.append(err)
        argument_tree = None

    report, err = _load_json_artifact("outputs/part4/reference_alignment_report.json")
    if err:
        issues.append(err)
        report = None

    rationale, err = _load_json_artifact("outputs/part4/outline_rationale.json")
    if err:
        issues.append(err)
        rationale = None

    wiki_index, err = _load_json_artifact("research-wiki/index.json")
    if err:
        issues.append(err)
        wiki_index = None

    raw_metadata, _raw_err = _load_json_artifact("raw-library/metadata.json")

    for issue in check_writing_policy_gate():
        issues.append(f"Part 4 writing-policy 校验失败: {issue}")

    if outline:
        if outline.get("argument_tree_ref") != "outputs/part3/argument_tree.json":
            issues.append(
                "paper_outline.argument_tree_ref 必须指向 outputs/part3/argument_tree.json"
            )
        if outline.get("wiki_ref") != "research-wiki/index.json":
            issues.append("paper_outline.wiki_ref 必须指向 research-wiki/index.json")
        if outline.get("writing_policy_ref") != "writing-policy/source_index.json":
            issues.append(
                "paper_outline.writing_policy_ref 必须指向 writing-policy/source_index.json"
            )
        if not outline.get("sections"):
            issues.append("paper_outline.sections 不能为空")

    if outline and argument_tree:
        tree_wiki_ref = argument_tree.get("wiki_ref")
        if tree_wiki_ref and tree_wiki_ref != outline.get("wiki_ref"):
            issues.append(
                "paper_outline.wiki_ref 与 argument_tree.wiki_ref 不一致: "
                f"{outline.get('wiki_ref')} != {tree_wiki_ref}"
            )

    if rationale:
        inputs = rationale.get("inputs", {})
        if not isinstance(inputs, dict):
            issues.append("outline_rationale.inputs 必须是 object")
        else:
            if inputs.get("argument_tree_ref") != "outputs/part3/argument_tree.json":
                issues.append("outline_rationale.inputs.argument_tree_ref 必须指向 outputs/part3/argument_tree.json")
            if inputs.get("wiki_ref") != "research-wiki/index.json":
                issues.append("outline_rationale.inputs.wiki_ref 必须指向 research-wiki/index.json")
            if inputs.get("writing_policy_ref") != "writing-policy/source_index.json":
                issues.append("outline_rationale.inputs.writing_policy_ref 必须指向 writing-policy/source_index.json")
        if not rationale.get("section_mappings"):
            issues.append("outline_rationale.section_mappings 不能为空")
    if report:
        inputs = report.get("inputs", {})
        if outline and isinstance(inputs, dict):
            for key in ("argument_tree_ref", "wiki_ref", "writing_policy_ref"):
                if inputs.get(key) != outline.get(key):
                    issues.append(f"reference_alignment_report.inputs.{key} 与 paper_outline 不一致")
        if report.get("status") != "pass":
            issues.append(
                "reference_alignment_report.status 必须为 pass；"
                f"当前为 {report.get('status', 'missing')}"
            )
        coverage = report.get("coverage", {})
        if coverage.get("uncovered_critical_argument_node_ids"):
            issues.append(
                "reference_alignment_report 存在未覆盖的 thesis/main_argument 节点: "
                + ", ".join(coverage["uncovered_critical_argument_node_ids"])
            )
        if report.get("errors"):
            issues.append(
                "reference_alignment_report.errors 非空: "
                + "; ".join(str(item) for item in report["errors"])
            )

    if outline and argument_tree and wiki_index:
        try:
            computed_report = _compute_part4_alignment_report(
                outline,
                argument_tree,
                wiki_index,
                raw_metadata=raw_metadata,
            )
        except Exception as e:
            issues.append(f"Part 4 实时 alignment 复算失败: {e}")
        else:
            if computed_report.get("status") != "pass":
                realtime_errors = computed_report.get("errors", [])
                detail = "; ".join(str(item) for item in realtime_errors) or "unknown"
                issues.append(f"Part 4 实时 alignment 未通过: {detail}")
            if report:
                stored_coverage = report.get("coverage", {})
                computed_coverage = computed_report.get("coverage", {})
                for key in (
                    "critical_argument_node_ids",
                    "covered_critical_argument_node_ids",
                    "uncovered_critical_argument_node_ids",
                    "outline_source_ids",
                ):
                    if stored_coverage.get(key) != computed_coverage.get(key):
                        issues.append(f"reference_alignment_report.coverage.{key} 与实时复算结果不一致")

    return issues


def _discover_policy_files(group_name: str) -> list[str]:
    root = PROJECT_ROOT / "writing-policy" / group_name
    if not root.exists():
        return []
    return [
        str(path.relative_to(PROJECT_ROOT))
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != ".gitkeep"
    ]


def _compute_part4_alignment_report(
    outline: dict,
    argument_tree: dict,
    wiki_index: dict,
    *,
    raw_metadata: Optional[dict],
) -> dict:
    try:
        from runtime.agents.part4_outline_alignment import evaluate_outline_alignment
    except ImportError:
        from agents.part4_outline_alignment import evaluate_outline_alignment  # type: ignore

    return evaluate_outline_alignment(
        outline,
        argument_tree,
        wiki_index,
        raw_metadata=raw_metadata,
        writing_policy_ref_exists=(PROJECT_ROOT / "writing-policy" / "source_index.json").exists(),
        reference_cases_used=_discover_policy_files("reference_cases"),
        rubrics_used=_discover_policy_files("rubrics"),
    )


def _json_list(data: Optional[dict], key: str) -> list:
    if not isinstance(data, dict):
        return []
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def _nonempty_text_file(rel_path: str) -> bool:
    path = PROJECT_ROOT / rel_path
    return path.exists() and path.is_file() and bool(path.read_text(encoding="utf-8").strip())


def _part5_step_artifacts_present() -> list[str]:
    required_paths = [
        "outputs/part5/claim_evidence_matrix.json",
        "outputs/part5/citation_map.json",
        "outputs/part5/figure_plan.json",
        "outputs/part5/open_questions.json",
        "outputs/part5/manuscript_v1.md",
        "outputs/part5/review_summary.md",
        "outputs/part5/review_report.md",
        "outputs/part5/claim_risk_report.json",
        "outputs/part5/citation_consistency_precheck.json",
    ]
    issues: list[str] = []
    for rel_path in required_paths:
        if not (PROJECT_ROOT / rel_path).exists():
            issues.append(f"缺少 Part 5 workflow artifact: {rel_path}")

    chapter_briefs_dir = PROJECT_ROOT / "outputs" / "part5" / "chapter_briefs"
    if not chapter_briefs_dir.exists() or not list(chapter_briefs_dir.glob("*.md")):
        issues.append("缺少 Part 5 chapter briefs: outputs/part5/chapter_briefs/*.md")

    case_templates_dir = PROJECT_ROOT / "outputs" / "part5" / "case_analysis_templates"
    if not case_templates_dir.exists() or not list(case_templates_dir.glob("*.md")):
        issues.append("缺少 Part 5 case analysis templates: outputs/part5/case_analysis_templates/*.md")

    for rel_path in [
        "outputs/part5/manuscript_v1.md",
        "outputs/part5/manuscript_v2.md",
        "outputs/part5/review_summary.md",
        "outputs/part5/review_report.md",
    ]:
        if (PROJECT_ROOT / rel_path).exists() and not _nonempty_text_file(rel_path):
            issues.append(f"{rel_path} 不能为空")

    return issues


def _missing_paths(rel_paths: list[str]) -> list[str]:
    return [rel_path for rel_path in rel_paths if not (PROJECT_ROOT / rel_path).exists()]


def _sha256_file(rel_path: str) -> Optional[str]:
    path = PROJECT_ROOT / rel_path
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _part5_gate_artifact_paths(gate_id: str) -> list[str]:
    if gate_id == "part5_prep_confirmed":
        return [
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part5/citation_map.json",
            "outputs/part5/figure_plan.json",
            "outputs/part5/open_questions.json",
        ] + [
            str(path.relative_to(PROJECT_ROOT))
            for path in sorted((PROJECT_ROOT / "outputs" / "part5" / "chapter_briefs").glob("*.md"))
        ] + [
            str(path.relative_to(PROJECT_ROOT))
            for path in sorted((PROJECT_ROOT / "outputs" / "part5" / "case_analysis_templates").glob("*.md"))
        ]
    if gate_id == "part5_review_completed":
        return [
            "outputs/part5/manuscript_v1.md",
            "outputs/part5/review_matrix.json",
            "outputs/part5/review_summary.md",
            "outputs/part5/claim_risk_report.json",
            "outputs/part5/citation_consistency_precheck.json",
        ]
    if gate_id == "manuscript_v2_accepted":
        return [
            "outputs/part5/manuscript_v2.md",
            "outputs/part5/revision_log.json",
            "outputs/part5/part6_readiness_decision.json",
        ]
    return []


def _part5_artifact_fingerprints(gate_id: str) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rel_path in _part5_gate_artifact_paths(gate_id):
        digest = _sha256_file(rel_path)
        if digest:
            fingerprints[rel_path] = digest
    return fingerprints


def _part6_handoff_artifact_fingerprints() -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rel_path in PART5_HANDOFF_ARTIFACTS:
        digest = _sha256_file(rel_path)
        if digest:
            fingerprints[rel_path] = digest
    return fingerprints


def _part6_completion_artifact_fingerprints() -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for rel_path in PART6_COMPLETION_FINGERPRINT_FILES:
        digest = _sha256_file(rel_path)
        if digest:
            fingerprints[rel_path] = digest
    return fingerprints


def _latest_human_decision(state: dict, gate_id: str) -> Optional[dict]:
    decisions = state.get("human_decision_log", [])
    if not isinstance(decisions, list):
        return None
    for record in reversed(decisions):
        if isinstance(record, dict) and record.get("gate_id") == gate_id:
            return record
    return None


def check_part5_human_gate_fingerprints(state: dict) -> list[str]:
    issues: list[str] = []
    part5 = _stage_state(state, "part5")
    completed = set(part5.get("human_gates_completed", []) or [])
    for gate_id in [
        "part5_prep_confirmed",
        "part5_review_completed",
        "manuscript_v2_accepted",
    ]:
        if gate_id not in completed:
            continue
        record = _latest_human_decision(state, gate_id)
        if not record:
            issues.append(f"{gate_id} 缺少 human_decision_log 记录，必须重新确认")
            continue
        expected = record.get("artifact_fingerprints")
        if not isinstance(expected, dict) or not expected:
            issues.append(f"{gate_id} 缺少 artifact fingerprint，必须重新确认当前产物")
            continue
        current = _part5_artifact_fingerprints(gate_id)
        if expected != current:
            issues.append(f"{gate_id} 对应 artifact 已变化，必须重新人工确认")
    return issues


def _part6_final_decision_fingerprint_issues(state: dict) -> list[str]:
    if not _human_gate_completed(state, "part6", "part6_final_decision_confirmed"):
        return []

    record = _latest_human_decision(state, "part6_final_decision_confirmed")
    if not record:
        return ["part6_final_decision_confirmed 缺少 human_decision_log 记录，必须重新确认"]

    expected = record.get("artifact_fingerprints")
    if not isinstance(expected, dict) or not expected:
        return ["part6_final_decision_confirmed 缺少 Part 6 package fingerprint，必须重新确认"]

    current = _part6_completion_artifact_fingerprints()
    if expected == current:
        return []

    changed_paths = sorted(
        {
            rel_path
            for rel_path in set(expected) | set(current)
            if expected.get(rel_path) != current.get(rel_path)
        }
    )
    return [
        "part6_final_decision_confirmed 对应 artifact 已变化，必须重新人工确认: "
        f"{changed_paths}"
    ]


def _mark_part6_final_decision_confirmed(confirmed_at: str, notes: str) -> None:
    decision, decision_err = _load_json_artifact(PART6_FINAL_READINESS_DECISION)
    if decision_err:
        raise RuntimeError(
            "part6_final_decision_confirmed 不能刷新 final readiness: "
            + decision_err
        )
    assert decision is not None

    residual_risks = _json_list(decision, "residual_risks")
    decision["residual_risks"] = [
        risk for risk in residual_risks
        if not (
            isinstance(risk, str)
            and risk.strip() == PART6_FINAL_DECISION_PENDING_RISK
        )
    ]
    decision["final_decision_status"] = "confirmed"
    decision["final_decision_gate_id"] = "part6_final_decision_confirmed"
    decision["final_decision_confirmed_at"] = confirmed_at
    if notes.strip():
        decision["final_decision_notes"] = notes.strip()
    _write_json_artifact(PART6_FINAL_READINESS_DECISION, decision)

    checklist_path = PROJECT_ROOT / PART6_SUBMISSION_CHECKLIST
    if checklist_path.exists():
        checklist = checklist_path.read_text(encoding="utf-8")
        replacements = {
            "- [ ] part6_final_decision_confirmed 仍需用户最终确认。":
                "- [x] part6_final_decision_confirmed 已由用户确认。",
            "- [ ] 人工确认最终状态。": "- [x] 人工确认最终状态。",
        }
        for before, after in replacements.items():
            checklist = checklist.replace(before, after)
        checklist_path.write_text(checklist, encoding="utf-8")


def _ref_matches(value: object, target_rel_path: str) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().lstrip("./")
    return normalized == target_rel_path


def _collect_ref_values(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.add(value.strip().lstrip("./"))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_ref_values(item))
    elif isinstance(value, dict):
        for dict_value in value.values():
            refs.update(_collect_ref_values(dict_value))
    return refs


def _collect_text_values(value: object) -> list[str]:
    values: list[str] = []
    if isinstance(value, str):
        if value.strip():
            values.append(value.strip())
    elif isinstance(value, list):
        for item in value:
            values.extend(_collect_text_values(item))
    elif isinstance(value, dict):
        for dict_value in value.values():
            values.extend(_collect_text_values(dict_value))
    return values


def _normalized_content(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(value.split())


def _text_file_content(rel_path: str) -> tuple[Optional[str], Optional[str]]:
    path = PROJECT_ROOT / rel_path
    if not path.exists():
        return None, f"缺少 artifact: {rel_path}"
    if not path.is_file():
        return None, f"{rel_path} 不是文件"
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None, f"{rel_path} 不能为空"
    return text, None


def _content_without_markdown_headings(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return "\n".join(lines).strip()


def _extract_keywords_from_part6_json(value: object) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not isinstance(value, dict):
        return []
    for key in ["keywords", "final_keywords", "items"]:
        keywords = _extract_keywords_from_part6_json(value.get(key))
        if keywords:
            return keywords
    return [
        item
        for item in _collect_text_values(value)
        if item not in {"keywords", "final_keywords", "items"}
    ]


def _part6_stage_prerequisite_issues(state: dict) -> list[str]:
    issues: list[str] = []
    for stage_id in ["part1", "part2", "part3", "part4", "part5"]:
        stage = _stage_state(state, stage_id)
        if stage.get("status") != "completed" or stage.get("gate_passed") is not True:
            issues.append(f"{stage_id} gate 尚未通过")
    return issues


def _part6_entry_precondition_issues(state: dict, *, require_authorization: bool) -> list[str]:
    issues = _part6_stage_prerequisite_issues(state)

    missing_handoff = _missing_paths(PART5_HANDOFF_ARTIFACTS)
    for rel_path in missing_handoff:
        issues.append(f"缺少 Part 5 handoff artifact: {rel_path}")

    part5_passed, part5_issues = validate_gate("part5", state)
    if not part5_passed:
        for issue in part5_issues:
            issues.append(f"Part 5 handoff 当前无效: {issue}")

    readiness, err = _load_json_artifact("outputs/part5/part6_readiness_decision.json")
    if err:
        issues.append(err)
    elif readiness and readiness.get("verdict") == "blocked_by_evidence_debt":
        issues.append("Part 5 readiness verdict 为 blocked_by_evidence_debt，不能进入 Part 6")

    if not require_authorization:
        return issues

    if not _human_gate_completed(state, "part6", "part6_finalization_authorized"):
        issues.append("人工节点未确认: part6_finalization_authorized")
        return issues

    record = _latest_human_decision(state, "part6_finalization_authorized")
    if not record:
        issues.append("part6_finalization_authorized 缺少 human_decision_log 记录，必须重新授权")
        return issues

    expected = record.get("artifact_fingerprints")
    if not isinstance(expected, dict) or not expected:
        issues.append("part6_finalization_authorized 缺少 Part 5 handoff fingerprint，必须重新授权")
        return issues

    current = _part6_handoff_artifact_fingerprints()
    if expected != current:
        issues.append("Part 5 handoff artifact 已变化，必须重新确认 part6_finalization_authorized")

    return issues


def _part6_final_manuscript_issues() -> list[str]:
    issues: list[str] = []
    manuscript, manuscript_err = _text_file_content(PART6_FINAL_MANUSCRIPT)
    if manuscript_err:
        return [manuscript_err]
    assert manuscript is not None

    if "摘要" not in manuscript:
        issues.append("final_manuscript.md 缺少摘要")
    if "关键词" not in manuscript and "关键字" not in manuscript:
        issues.append("final_manuscript.md 缺少关键词")
    if "结论" not in manuscript and "总结" not in manuscript:
        issues.append("final_manuscript.md 缺少结论")
    matched_scaffold_markers = public_text_has_internal_markers(manuscript)
    if matched_scaffold_markers:
        issues.append(f"final_manuscript.md 包含 scaffold/骨架标记: {matched_scaffold_markers}")

    headings = [
        line.lstrip("#").strip()
        for line in manuscript.splitlines()
        if line.lstrip().startswith("#")
    ]
    non_body_markers = ("摘要", "关键词", "关键字", "结论", "总结", "风险", "残余", "最终稿")
    has_body_heading = any(
        heading and not any(marker in heading for marker in non_body_markers)
        for heading in headings
    )
    if not has_body_heading:
        issues.append("final_manuscript.md 缺少正文章节")

    abstract, abstract_err = _text_file_content(PART6_FINAL_ABSTRACT)
    if abstract_err:
        issues.append(abstract_err)
    elif abstract:
        abstract_body = _content_without_markdown_headings(abstract)
        if abstract_body and _normalized_content(abstract_body) not in _normalized_content(manuscript):
            issues.append("final_manuscript.md 摘要与 final_abstract.md 不一致")

    keywords, keywords_err = _load_json_artifact(PART6_FINAL_KEYWORDS)
    if keywords_err:
        issues.append(keywords_err)
    else:
        keyword_values = _extract_keywords_from_part6_json(keywords)
        if not keyword_values:
            issues.append("final_keywords.json 必须包含 keywords")
        manuscript_normalized = _normalized_content(manuscript)
        missing_keywords = [
            keyword
            for keyword in keyword_values
            if _normalized_content(keyword) not in manuscript_normalized
        ]
        if missing_keywords:
            issues.append(f"final_manuscript.md 关键词与 final_keywords.json 不一致: {missing_keywords}")

    return issues


def _part6_public_residual_risk_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("Part 2 Evidence Synthesis", "证据综合")
    text = text.replace("Part 2 Evidence", "证据综合")
    text = text.replace("manuscript_v1", "初稿正文")
    text = text.replace("...", "")
    text = re.sub(r"evidence_\d+_\d+", "部分证据", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("案例分析需要借助证据综合需要", "案例分析需要借助证据综合；相关判断需要")
    text = text.replace("案例材料只能承担对需要", "案例材料只能承担辅助论证功能，相关判断需要")
    return text


def _part6_residual_risk_issues(decision: dict, claim_risk: dict) -> list[str]:
    readiness, err = _load_json_artifact("outputs/part5/part6_readiness_decision.json")
    if err:
        return [err]
    if not readiness:
        return []

    if readiness.get("verdict") != "ready_for_part6_with_research_debt":
        return []

    residual_risks = [
        item.strip()
        for item in _json_list(readiness, "residual_risks")
        if isinstance(item, str) and item.strip()
    ]
    if not residual_risks:
        return []

    claim_text = _normalized_content(_part6_public_residual_risk_text(" ".join(_collect_text_values(claim_risk))))
    decision_text = _normalized_content(_part6_public_residual_risk_text(" ".join(_collect_text_values(decision))))
    issues: list[str] = []
    for residual_risk in residual_risks:
        normalized_risk = _normalized_content(_part6_public_residual_risk_text(residual_risk))
        if normalized_risk not in claim_text and normalized_risk not in decision_text:
            issues.append(
                "Part 5 residual_risks 未延续到 Part 6 claim_risk_report 或 "
                f"final_readiness_decision: {residual_risk}"
            )
    return issues


def _part6_verdict_consistency_issues(
    decision: dict,
    manifest: dict,
    claim_risk: dict,
    citation_report: dict,
) -> list[str]:
    issues: list[str] = []
    verdict = decision.get("verdict")

    if manifest.get("submission_class") != verdict:
        issues.append(
            "submission_package_manifest.submission_class 必须与 "
            f"final_readiness_decision.verdict 一致: {manifest.get('submission_class')} != {verdict}"
        )

    if manifest.get("human_decision_required") is not True:
        issues.append("submission_package_manifest.human_decision_required 必须为 true")

    required_human_decisions = _json_list(decision, "required_human_decisions")
    if "part6_final_decision_confirmed" not in required_human_decisions:
        issues.append(
            "final_readiness_decision.required_human_decisions 必须包含 "
            "part6_final_decision_confirmed"
        )

    citation_blocked = (
        citation_report.get("status") == "blocked"
        or bool(_json_list(citation_report, "errors"))
    )
    if citation_blocked and verdict != "blocked_by_evidence_debt":
        issues.append(
            "citation_consistency_report.status 为 blocked 或 errors 非空时，"
            "final_readiness_decision.verdict 必须为 blocked_by_evidence_debt"
        )

    manifest_incomplete = (
        manifest.get("status") != "complete"
        or bool(_json_list(manifest, "missing_files"))
    )
    if manifest_incomplete:
        issues.append(
            "submission_package_manifest.status 非 complete 或 missing_files 非空时，"
            "Part 6 completion gate 必须失败"
        )

    unresolved_risk_items: list[dict] = []
    unresolved_blocked_items: list[dict] = []
    resolved_statuses = {"resolved", "mitigated", "downgraded"}
    for item in _json_list(claim_risk, "risk_items"):
        if not isinstance(item, dict):
            continue
        risk_level = item.get("risk_level")
        status = item.get("status")
        if risk_level in {"blocked", "high_risk"} and status not in resolved_statuses:
            unresolved_risk_items.append(item)
            if risk_level == "blocked":
                unresolved_blocked_items.append(item)

    if unresolved_risk_items and verdict == "formal_submission_ready":
        risk_ids = [str(item.get("risk_id", "unknown")) for item in unresolved_risk_items]
        issues.append(
            "claim_risk_report 存在未 resolved/mitigated/downgraded 的 blocked/high_risk，"
            f"final_readiness_decision.verdict 不得为 formal_submission_ready: {risk_ids}"
        )

    if unresolved_blocked_items and verdict != "blocked_by_evidence_debt":
        risk_ids = [str(item.get("risk_id", "unknown")) for item in unresolved_blocked_items]
        issues.append(
            "claim_risk_report 存在 blocked item，final_readiness_decision.verdict "
            f"必须为 blocked_by_evidence_debt: {risk_ids}"
        )

    return issues


def _source_id(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    source_id = value.strip()
    return source_id or None


def _source_id_is_policy_ref(source_id: str) -> bool:
    normalized = source_id.strip().replace("\\", "/").lstrip("./")
    if normalized == "writing-policy" or normalized.startswith("writing-policy/"):
        return True
    if normalized == "writing_policy" or normalized.startswith("writing_policy/"):
        return True
    if normalized.startswith("source_index.") and normalized.endswith(".json"):
        return True
    return (
        "/" in normalized
        and normalized.endswith((".json", ".md"))
        and any(
            segment in normalized
            for segment in [
                "policy",
                "rules",
                "rubrics",
                "style_guides",
                "reference_cases",
            ]
        )
    )


def _part6_reported_citation_source_ids(citation_report: dict) -> tuple[set[str], list[str]]:
    issues: list[str] = []
    checked_source_ids: set[str] = set()
    citation_item_source_ids: set[str] = set()

    for index, value in enumerate(_json_list(citation_report, "checked_source_ids")):
        source_id = _source_id(value)
        if source_id is None:
            issues.append(f"citation_consistency_report.checked_source_ids[{index}] 必须是非空 source_id")
            continue
        checked_source_ids.add(source_id)

    for index, item in enumerate(_json_list(citation_report, "citation_items")):
        if not isinstance(item, dict):
            issues.append(f"citation_consistency_report.citation_items[{index}] 必须是 object")
            continue
        source_id = _source_id(item.get("source_id"))
        if source_id is None:
            issues.append(f"citation_consistency_report.citation_items[{index}].source_id 不能为空")
            continue
        citation_item_source_ids.add(source_id)
        if checked_source_ids and source_id not in checked_source_ids:
            issues.append(
                "citation_consistency_report.citation_items[].source_id 未出现在 "
                f"checked_source_ids: {source_id}"
            )

    missing_item_source_ids = sorted(checked_source_ids - citation_item_source_ids)
    if missing_item_source_ids:
        issues.append(
            "citation_consistency_report.checked_source_ids 缺少对应 citation_items: "
            f"{missing_item_source_ids}"
        )

    source_ids = checked_source_ids | citation_item_source_ids
    if not source_ids:
        issues.append("citation_consistency_report 必须至少复核一个 citation source_id")

    return source_ids, issues


def _part6_citation_traceability_issues(citation_report: dict) -> list[str]:
    issues: list[str] = []
    source_ids, reported_issues = _part6_reported_citation_source_ids(citation_report)
    issues.extend(reported_issues)

    expected_refs = {
        "citation_map_ref": PART5_CITATION_MAP,
        "raw_metadata_ref": RAW_LIBRARY_METADATA,
        "wiki_index_ref": RESEARCH_WIKI_INDEX,
        "accepted_sources_ref": PART1_ACCEPTED_SOURCES,
        "authenticity_report_ref": PART1_AUTHENTICITY_REPORT,
    }
    for key, rel_path in expected_refs.items():
        if not _ref_matches(citation_report.get(key), rel_path):
            issues.append(f"citation_consistency_report.{key} 必须指向 {rel_path}")

    citation_map, citation_map_err = _load_json_artifact(PART5_CITATION_MAP)
    raw_metadata, raw_err = _load_json_artifact(RAW_LIBRARY_METADATA)
    wiki_index, wiki_err = _load_json_artifact(RESEARCH_WIKI_INDEX)
    accepted_sources, accepted_err = _load_json_artifact(PART1_ACCEPTED_SOURCES)
    authenticity_report, authenticity_err = _load_json_artifact(PART1_AUTHENTICITY_REPORT)

    for err in [citation_map_err, raw_err, wiki_err, accepted_err, authenticity_err]:
        if err:
            issues.append(f"Part 6 citation traceability 校验失败: {err}")

    if (
        citation_map_err
        or raw_err
        or wiki_err
        or accepted_err
        or authenticity_err
        or not source_ids
    ):
        return issues

    assert citation_map is not None
    assert raw_metadata is not None
    assert wiki_index is not None
    assert accepted_sources is not None
    assert authenticity_report is not None

    citation_status_by_source_id: dict[str, object] = {}
    for ref in _json_list(citation_map, "source_refs"):
        if not isinstance(ref, dict):
            continue
        source_id = _source_id(ref.get("source_id"))
        if source_id:
            citation_status_by_source_id[source_id] = ref.get("citation_status")

    raw_sources_by_id: dict[str, dict] = {}
    for source in _json_list(raw_metadata, "sources"):
        if not isinstance(source, dict):
            continue
        source_id = _source_id(source.get("source_id"))
        if source_id:
            raw_sources_by_id[source_id] = source

    wiki_source_ids: set[str] = set()
    for page in _json_list(wiki_index, "pages"):
        if not isinstance(page, dict):
            continue
        for value in page.get("source_ids", []) or []:
            source_id = _source_id(value)
            if source_id:
                wiki_source_ids.add(source_id)

    accepted_source_ids = {
        source_id
        for value in _json_list(accepted_sources, "source_ids")
        if (source_id := _source_id(value))
    }
    for source in _json_list(accepted_sources, "sources"):
        if not isinstance(source, dict):
            continue
        source_id = _source_id(source.get("source_id"))
        if source_id:
            accepted_source_ids.add(source_id)

    authenticity_verdicts_by_source_id: dict[str, object] = {}
    for result in _json_list(authenticity_report, "results"):
        if not isinstance(result, dict):
            continue
        source_id = _source_id(result.get("source_id"))
        if source_id:
            authenticity_verdicts_by_source_id[source_id] = result.get("verdict")

    for source_id in sorted(source_ids):
        if _source_id_is_policy_ref(source_id):
            issues.append(
                "citation_consistency_report 混入 writing-policy/policy ref，"
                f"不能作为 citation source_id: {source_id}"
            )

        citation_status = citation_status_by_source_id.get(source_id)
        if source_id not in citation_status_by_source_id:
            issues.append(
                "Part 6 citation source_id 不存在于 outputs/part5/citation_map.json: "
                f"{source_id}"
            )
        elif citation_status != "accepted_source":
            issues.append(
                "Part 6 citation source_id 在 outputs/part5/citation_map.json 中不是 "
                f"accepted_source: {source_id}={citation_status}"
            )

        raw_source = raw_sources_by_id.get(source_id)
        if raw_source is None:
            issues.append(
                "Part 6 citation source_id 不存在于 raw-library/metadata.json: "
                f"{source_id}"
            )

        if source_id not in wiki_source_ids:
            issues.append(
                "Part 6 citation source_id 未出现在 research-wiki/index.json.pages[].source_ids: "
                f"{source_id}"
            )

        if source_id not in accepted_source_ids:
            issues.append(
                "Part 6 citation source_id 不存在于 outputs/part1/accepted_sources.json.source_ids: "
                f"{source_id}"
            )

        if source_id in authenticity_verdicts_by_source_id:
            verdict = authenticity_verdicts_by_source_id[source_id]
            if verdict not in ACCEPTED_AUTHENTICITY_VERDICTS:
                issues.append(
                    "Part 6 citation source_id 在 outputs/part1/authenticity_report.json "
                    f"中 verdict 非 pass/warning: {source_id}={verdict}"
                )
            continue

        if not (
            raw_source
            and raw_source.get("authenticity_verdict") in ACCEPTED_AUTHENTICITY_VERDICTS
            and raw_source.get("authenticity_status") == "verified"
        ):
            issues.append(
                "Part 6 citation source_id 缺少 authenticity_report pass/warning 记录，且 "
                "raw metadata 未同时标记 authenticity_verdict=pass|warning/"
                f"authenticity_status=verified: {source_id}"
            )

    return issues


def _part6_docx_format_issues() -> list[str]:
    issues: list[str] = []
    docx_path = PROJECT_ROOT / PART6_FINAL_MANUSCRIPT_DOCX
    if not docx_path.exists():
        return [f"缺少 artifact: {PART6_FINAL_MANUSCRIPT_DOCX}"]
    if not docx_path.is_file() or docx_path.stat().st_size == 0:
        issues.append(f"{PART6_FINAL_MANUSCRIPT_DOCX} 不是有效文件")

    report, report_err = _load_json_artifact(PART6_DOCX_FORMAT_REPORT)
    if report_err:
        return issues + [report_err]
    assert report is not None

    if report.get("status") not in {"pass", "pass_with_warnings"}:
        issues.append("docx_format_report.status 必须为 pass 或 pass_with_warnings")
    if report.get("cover_excluded") is not True:
        issues.append("docx_format_report.cover_excluded 必须为 true")
    if not _ref_matches(report.get("source_manuscript_ref"), PART6_FINAL_MANUSCRIPT):
        issues.append(f"docx_format_report.source_manuscript_ref 必须指向 {PART6_FINAL_MANUSCRIPT}")
    if not _ref_matches(report.get("docx_ref"), PART6_FINAL_MANUSCRIPT_DOCX):
        issues.append(f"docx_format_report.docx_ref 必须指向 {PART6_FINAL_MANUSCRIPT_DOCX}")
    if not isinstance(report.get("paper_title"), str) or not report["paper_title"].strip():
        issues.append("docx_format_report.paper_title 不能为空")
    desktop_ref = report.get("desktop_docx_ref")
    if not isinstance(desktop_ref, str) or not desktop_ref.strip():
        issues.append("docx_format_report.desktop_docx_ref 不能为空")
    else:
        desktop_path = Path(desktop_ref).expanduser()
        if not desktop_path.exists():
            issues.append(f"docx_format_report.desktop_docx_ref 指向不存在的桌面文件: {desktop_ref}")

    return issues


def _part6_completion_package_issues() -> list[str]:
    issues: list[str] = []

    issues.extend(_part6_final_manuscript_issues())

    decision, decision_err = _load_json_artifact(PART6_FINAL_READINESS_DECISION)
    manifest, manifest_err = _load_json_artifact(PART6_SUBMISSION_PACKAGE_MANIFEST)
    claim_risk, claim_risk_err = _load_json_artifact(PART6_CLAIM_RISK_REPORT)
    citation_report, citation_err = _load_json_artifact(PART6_CITATION_CONSISTENCY_REPORT)

    if decision_err:
        issues.append(decision_err)
    if manifest_err:
        issues.append(manifest_err)
    if claim_risk_err:
        issues.append(claim_risk_err)
    if citation_err:
        issues.append(citation_err)
    if decision_err or manifest_err or claim_risk_err or citation_err:
        return issues

    assert decision is not None
    assert manifest is not None
    assert claim_risk is not None
    assert citation_report is not None

    if decision.get("verdict") not in PART6_READINESS_VERDICTS:
        issues.append(
            "final_readiness_decision.verdict 必须为 "
            + "/".join(sorted(PART6_READINESS_VERDICTS))
        )

    if decision.get("does_not_advance_part7") is not True:
        issues.append("final_readiness_decision.does_not_advance_part7 必须为 true")

    if not _ref_matches(decision.get("manifest_ref"), PART6_SUBMISSION_PACKAGE_MANIFEST):
        issues.append(
            "final_readiness_decision.manifest_ref 必须指向 "
            f"{PART6_SUBMISSION_PACKAGE_MANIFEST}"
        )

    if not _ref_matches(decision.get("claim_risk_report_ref"), PART6_CLAIM_RISK_REPORT):
        issues.append(
            "final_readiness_decision.claim_risk_report_ref 必须指向 "
            f"{PART6_CLAIM_RISK_REPORT}"
        )

    if not _ref_matches(
        decision.get("citation_consistency_report_ref"),
        PART6_CITATION_CONSISTENCY_REPORT,
    ):
        issues.append(
            "final_readiness_decision.citation_consistency_report_ref 必须指向 "
            f"{PART6_CITATION_CONSISTENCY_REPORT}"
        )

    required_files = _collect_ref_values(manifest.get("required_files"))
    included_files = _collect_ref_values(manifest.get("included_files"))
    missing_required_package_files = sorted(PART6_REQUIRED_PACKAGE_FILES - required_files)
    if missing_required_package_files:
        issues.append(
            "submission_package_manifest.required_files 缺少 Part 6 required files: "
            f"{missing_required_package_files}"
        )
    if PART6_FINAL_READINESS_DECISION not in required_files:
        issues.append(
            "submission_package_manifest.required_files 必须包含 "
            f"{PART6_FINAL_READINESS_DECISION}"
        )
    if PART6_FINAL_READINESS_DECISION not in included_files:
        issues.append(
            "submission_package_manifest.included_files 必须包含 "
            f"{PART6_FINAL_READINESS_DECISION}"
        )

    audit_refs = _collect_ref_values(manifest.get("audit_refs"))
    if PART6_CLAIM_RISK_REPORT not in audit_refs:
        issues.append(
            "submission_package_manifest.audit_refs 必须指向 "
            f"{PART6_CLAIM_RISK_REPORT}"
        )
    if PART6_CITATION_CONSISTENCY_REPORT not in audit_refs:
        issues.append(
            "submission_package_manifest.audit_refs 必须指向 "
            f"{PART6_CITATION_CONSISTENCY_REPORT}"
        )

    for rel_path in sorted(required_files):
        if rel_path.startswith("outputs/part6/") and not (PROJECT_ROOT / rel_path).exists():
            issues.append(f"submission_package_manifest.required_files 指向不存在的文件: {rel_path}")

    issues.extend(_part6_residual_risk_issues(decision, claim_risk))
    issues.extend(
        _part6_verdict_consistency_issues(
            decision,
            manifest,
            claim_risk,
            citation_report,
        )
    )
    issues.extend(_part6_citation_traceability_issues(citation_report))
    issues.extend(_part6_docx_format_issues())

    return issues


def _part5_prep_gate_issues() -> list[str]:
    issues = _missing_paths([
        "outputs/part5/claim_evidence_matrix.json",
        "outputs/part5/citation_map.json",
        "outputs/part5/figure_plan.json",
        "outputs/part5/open_questions.json",
    ])
    chapter_briefs_dir = PROJECT_ROOT / "outputs" / "part5" / "chapter_briefs"
    if not chapter_briefs_dir.exists() or not list(chapter_briefs_dir.glob("*.md")):
        issues.append("outputs/part5/chapter_briefs/*.md")
    case_templates_dir = PROJECT_ROOT / "outputs" / "part5" / "case_analysis_templates"
    if not case_templates_dir.exists() or not list(case_templates_dir.glob("*.md")):
        issues.append("outputs/part5/case_analysis_templates/*.md")
    return issues


def _part5_review_gate_issues() -> list[str]:
    return _missing_paths([
        "outputs/part5/manuscript_v1.md",
        "outputs/part5/review_matrix.json",
        "outputs/part5/review_summary.md",
        "outputs/part5/claim_risk_report.json",
        "outputs/part5/citation_consistency_precheck.json",
    ])


def _part5_acceptance_gate_issues() -> list[str]:
    return _missing_paths([
        "outputs/part5/manuscript_v2.md",
        "outputs/part5/revision_log.json",
        "outputs/part5/part6_readiness_decision.json",
    ])


def _ensure_human_gate_can_be_confirmed(gate_id: str) -> None:
    state = load_state()
    sequence_issues = _part5_gate_sequence_issues(gate_id, state)
    if sequence_issues:
        raise RuntimeError(
            f"{gate_id} 不能确认："
            + "；".join(sequence_issues)
        )

    if gate_id == "intake_confirmed":
        intake_issues = _part1_intake_gate_issues()
        if intake_issues:
            raise RuntimeError(
                "intake_confirmed 不能确认："
                + "；".join(intake_issues)
            )

    if gate_id == "part6_finalization_authorized":
        issues = _part6_entry_precondition_issues(state, require_authorization=False)
        if issues:
            raise RuntimeError(
                "part6_finalization_authorized 不能确认："
                + "；".join(issues)
            )

    if gate_id == "part6_final_decision_confirmed":
        issues = _part6_entry_precondition_issues(state, require_authorization=True)
        issues.extend(_part6_completion_package_issues())
        if issues:
            raise RuntimeError(
                "part6_final_decision_confirmed 不能确认："
                + "；".join(issues)
            )

    if gate_id == "part5_prep_confirmed":
        missing = _part5_prep_gate_issues()
        if missing:
            raise RuntimeError(
                "part5_prep_confirmed 不能确认：缺少写作输入包 artifact: "
                + ", ".join(missing)
            )
    if gate_id == "part5_review_completed":
        missing = _part5_review_gate_issues()
        if missing:
            raise RuntimeError(
                "part5_review_completed 不能确认：缺少 review artifact: "
                + ", ".join(missing)
            )
    if gate_id == "manuscript_v2_accepted":
        missing = _part5_acceptance_gate_issues()
        if missing:
            raise RuntimeError(
                "manuscript_v2_accepted 不能确认：缺少 revision artifact: "
                + ", ".join(missing)
            )


def check_part5_contract_gate() -> list[str]:
    """Validate Part 5 MVP draft/review/revision contract."""
    issues = _part5_step_artifacts_present()

    raw_metadata, raw_err = _load_json_artifact("raw-library/metadata.json")
    raw_sources: dict[str, dict] = {}
    if raw_err:
        issues.append(f"Part 5 source traceability 校验失败: {raw_err}")
    elif raw_metadata:
        raw_sources = {
            source.get("source_id"): source
            for source in raw_metadata.get("sources", []) or []
            if isinstance(source, dict) and isinstance(source.get("source_id"), str)
        }

    wiki_index, wiki_err = _load_json_artifact("research-wiki/index.json")
    wiki_page_ids: set[str] = set()
    wiki_source_ids: set[str] = set()
    if wiki_err:
        issues.append(f"Part 5 wiki traceability 校验失败: {wiki_err}")
    elif wiki_index:
        for page in wiki_index.get("pages", []) or []:
            if not isinstance(page, dict):
                continue
            page_id = page.get("page_id")
            if isinstance(page_id, str):
                wiki_page_ids.add(page_id)
            wiki_source_ids.update(
                source_id
                for source_id in page.get("source_ids", []) or []
                if isinstance(source_id, str)
            )

    matrix, err = _load_json_artifact("outputs/part5/claim_evidence_matrix.json")
    if err:
        issues.append(err)
    elif matrix:
        claims = _json_list(matrix, "claims")
        if not claims:
            issues.append("claim_evidence_matrix.claims 不能为空")
        for claim in claims:
            if not isinstance(claim, dict):
                issues.append("claim_evidence_matrix.claims 包含非 object 项")
                continue
            claim_id = claim.get("claim_id", "unknown")
            if not claim.get("claim"):
                issues.append(f"claim_evidence_matrix claim 缺少 claim 文本: {claim_id}")
            if claim.get("evidence_level") == "hard_evidence" and not claim.get("source_ids"):
                issues.append(f"hard-evidence claim 缺少 source_ids: {claim_id}")
            for source_id in claim.get("source_ids", []) or []:
                if source_id not in raw_sources:
                    issues.append(f"claim_evidence_matrix 引用了 raw-library 中不存在的 source_id [{claim_id}]: {source_id}")
                    continue
                source = raw_sources[source_id]
                verdict = source.get("authenticity_verdict")
                status = source.get("authenticity_status")
                if not _authenticity_verdict_is_accepted(verdict) or status not in (None, "verified"):
                    issues.append(f"claim_evidence_matrix 引用了未通过真实性校验的 source_id [{claim_id}]: {source_id}")
                if source_id not in wiki_source_ids:
                    issues.append(f"claim_evidence_matrix source_id 未出现在 research-wiki 映射中 [{claim_id}]: {source_id}")
            for page_id in claim.get("wiki_page_ids", []) or []:
                if page_id not in wiki_page_ids:
                    issues.append(f"claim_evidence_matrix 引用了不存在的 wiki page_id [{claim_id}]: {page_id}")
            if claim.get("risk_level") == "critical" and claim.get("status") not in ("blocked", "downgraded", "registered"):
                issues.append(f"critical claim risk 未登记处理: {claim_id}")

    citation_map, err = _load_json_artifact("outputs/part5/citation_map.json")
    if err:
        issues.append(err)
    elif citation_map:
        source_refs = _json_list(citation_map, "source_refs")
        if not source_refs:
            issues.append("citation_map.source_refs 不能为空")
        for ref in source_refs:
            if not isinstance(ref, dict):
                issues.append("citation_map.source_refs 包含非 object 项")
                continue
            source_id = ref.get("source_id", "unknown")
            if source_id not in raw_sources:
                issues.append(f"citation_map 引用了 raw-library 中不存在的 source_id: {source_id}")
            if source_id not in wiki_source_ids:
                issues.append(f"citation_map source_id 未出现在 research-wiki 映射中: {source_id}")
            if ref.get("citation_status") != "accepted_source":
                issues.append(
                    "citation_map 包含不可用于正文的引用状态: "
                    f"{source_id}={ref.get('citation_status')}"
                )

    review_matrix, err = _load_json_artifact("outputs/part5/review_matrix.json")
    unresolved_critical_reviews: list[dict] = []
    if err:
        issues.append(err)
        review_matrix = None
    elif review_matrix:
        reviews = _json_list(review_matrix, "reviews")
        if not reviews:
            issues.append("review_matrix.reviews 不能为空")
        for review in reviews:
            if not isinstance(review, dict):
                issues.append("review_matrix.reviews 包含非 object 项")
                continue
            if not review.get("review_id"):
                issues.append("review_matrix.reviews 每一项都必须包含 review_id")
            status = review.get("status")
            severity = review.get("severity")
            if severity == "critical" and status not in ("resolved", "mitigated", "downgraded"):
                unresolved_critical_reviews.append(review)

    revision_log, err = _load_json_artifact("outputs/part5/revision_log.json")
    if err:
        issues.append(err)
    elif revision_log:
        revisions = _json_list(revision_log, "revisions")
        if not revisions:
            issues.append("revision_log.revisions 不能为空")
        if revision_log.get("source_review_ref") != "outputs/part5/review_matrix.json":
            issues.append("revision_log.source_review_ref 必须指向 outputs/part5/review_matrix.json")
        if review_matrix:
            review_ids = {
                review.get("review_id")
                for review in _json_list(review_matrix, "reviews")
                if isinstance(review, dict) and review.get("review_id")
            }
            revised_review_ids = {
                revision.get("review_id")
                for revision in revisions
                if isinstance(revision, dict) and revision.get("review_id")
            }
            missing_review_ids = sorted(review_ids - revised_review_ids)
            if missing_review_ids:
                issues.append(f"revision_log 未覆盖 review_matrix 项: {missing_review_ids}")

    risk_report, err = _load_json_artifact("outputs/part5/claim_risk_report.json")
    if err:
        issues.append(err)
    elif risk_report:
        if not isinstance(risk_report.get("risk_items", []), list):
            issues.append("claim_risk_report.risk_items 必须是 list")

    precheck, err = _load_json_artifact("outputs/part5/citation_consistency_precheck.json")
    if err:
        issues.append(err)
    elif precheck and precheck.get("status") not in ("pass", "pass_with_warnings", "blocked"):
        issues.append("citation_consistency_precheck.status 必须为 pass/pass_with_warnings/blocked")
    elif precheck:
        if precheck.get("status") == "blocked":
            issues.append("citation_consistency_precheck.status 为 blocked，不能完成 Part 5 gate")
        if precheck.get("errors"):
            issues.append(
                "citation_consistency_precheck.errors 非空: "
                + "; ".join(str(item) for item in precheck["errors"])
            )

    readiness, err = _load_json_artifact("outputs/part5/part6_readiness_decision.json")
    if err:
        issues.append(err)
        readiness = None
    elif readiness:
        verdict = readiness.get("verdict")
        if verdict not in PART5_READINESS_VERDICTS:
            issues.append(
                "part6_readiness_decision.verdict 必须为 "
                + "/".join(sorted(PART5_READINESS_VERDICTS))
            )
        registered_blockers = _json_list(readiness, "registered_blockers")
        handoff_artifacts = set(_json_list(readiness, "handoff_artifacts"))
        required_handoff = {
            "outputs/part5/manuscript_v2.md",
            "outputs/part5/review_matrix.json",
            "outputs/part5/review_report.md",
            "outputs/part5/revision_log.json",
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part5/citation_map.json",
            "outputs/part5/figure_plan.json",
            "outputs/part5/part6_readiness_decision.json",
        }
        missing_handoff = sorted(required_handoff - handoff_artifacts)
        if missing_handoff:
            issues.append(f"part6_readiness_decision.handoff_artifacts 缺少: {missing_handoff}")
        if verdict == "ready_for_part6" and registered_blockers:
            issues.append("ready_for_part6 不得同时包含 registered_blockers")
        if verdict == "ready_for_part6" and readiness.get("residual_risks"):
            issues.append("ready_for_part6 不得携带 residual_risks；应使用 ready_for_part6_with_research_debt")
        if unresolved_critical_reviews and not registered_blockers:
            issues.append("Part 5 存在未登记 critical blocker，不能完成 gate")
        if verdict == "ready_for_part6" and unresolved_critical_reviews:
            issues.append("ready_for_part6 不能包含 unresolved critical blocker")

    return issues


# ── Gate validation ───────────────────────────────────────────────────────────

def validate_gate(stage_id: str, state: Optional[dict] = None) -> tuple[bool, list[str]]:
    """
    Validate all gate conditions for a stage.
    Returns (passed: bool, issues: list[str]).
    """
    if state is None:
        state = load_state()
    issues: list[str] = []

    # 1. Canonical artifact presence + schema
    issues.extend(check_previous_stage_gates(stage_id, state))

    for r in check_artifacts(stage_id):
        if not r["exists"]:
            if stage_id == "part6":
                continue
            issues.append(f"缺少 canonical artifact: {r['path']}")
        elif r["schema_valid"] is False:
            issues.append(f"Schema 校验失败 [{r['path']}]: {'; '.join(r['issues'])}")
        elif r["issues"]:
            # schema_valid is None (no jsonschema) — report as warning, not block
            issues.append(f"Schema 校验跳过 [{r['path']}]: {'; '.join(r['issues'])}")

    # 2. Human gates
    completed = set(_stage_state(state, stage_id).get("human_gates_completed", []))
    for gate_id in HUMAN_GATES.get(stage_id, []):
        if gate_id not in completed:
            issues.append(f"人工节点未确认: {gate_id}")

    # 3. Part 2 wiki-specific health check
    if stage_id == "part1":
        issues.extend(_part1_intake_gate_issues())
        issues.extend(check_part1_contract_gate())

    # 4. Part 2 wiki-specific health check
    if stage_id == "part2":
        wiki_path = PROJECT_ROOT / "research-wiki" / "index.json"
        if wiki_path.exists():
            try:
                with open(wiki_path, encoding="utf-8") as f:
                    wiki_index = json.load(f)
                health_issues = check_wiki_health_gate(wiki_index)
                issues.extend(health_issues)
                issues.extend(check_wiki_source_traceability(wiki_index))
            except json.JSONDecodeError as e:
                issues.append(f"research-wiki/index.json 无法解析: {e}")
        issues.extend(check_writing_policy_gate())

    if stage_id == "part3":
        issues.extend(check_part3_contract_gate())

    if stage_id == "part4":
        issues.extend(check_part4_alignment_gate())

    if stage_id == "part5":
        issues.extend(check_part5_contract_gate())

    if stage_id == "part6":
        issues.extend(_part6_entry_precondition_issues(state, require_authorization=True))
        issues.extend(_part6_completion_package_issues())
        issues.extend(_part6_final_decision_fingerprint_issues(state))

    return (len(issues) == 0), issues


# ── Stage lifecycle ───────────────────────────────────────────────────────────

def start_stage(stage_id: str) -> None:
    state = load_state()
    stage = _ensure_stage_state(state, stage_id)
    if stage["started_at"] is None:
        stage["started_at"] = now_iso()
    stage["status"] = "in_progress"
    state["current_stage"] = stage_id
    save_state(state)
    _write_process_memory("stage_started", {"stage_id": stage_id})


def advance_stage(stage_id: str) -> tuple[bool, list[str]]:
    """
    Try to mark a stage as completed by validating its gate.
    Returns (success: bool, issues: list[str]).
    """
    state = load_state()
    passed, issues = validate_gate(stage_id)

    if not passed:
        state["last_failure"] = {
            "stage_id": stage_id,
            "failed_at": now_iso(),
            "issues": issues,
        }
        save_state(state)
        _write_process_memory("gate_failed", {"stage_id": stage_id, "issues": issues})
        return False, issues

    stage = _ensure_stage_state(state, stage_id)
    stage["status"] = "completed"
    stage["gate_passed"] = True
    stage["completed_at"] = now_iso()
    if stage["started_at"] is None:
        stage["started_at"] = stage["completed_at"]

    state["current_stage"] = stage_id
    state["last_failure"] = None
    save_state(state)
    _write_process_memory("stage_advanced", {"stage_id": stage_id})
    return True, []


def confirm_human_gate(gate_id: str, notes: str = "") -> None:
    """Record a human gate as confirmed."""
    # Find the owning stage
    stage_id = next(
        (sid for sid, gates in HUMAN_GATES.items() if gate_id in gates),
        None
    )
    if stage_id is None:
        if gate_id in DEPRECATED_HUMAN_GATES:
            _record_deprecated_human_gate_noop(gate_id, notes)
            return
        raise ValueError(
            f"Unknown gate ID: '{gate_id}'\n"
            f"Valid gates: {[g for gs in HUMAN_GATES.values() for g in gs]}"
        )

    confirmed_at = now_iso()
    _ensure_human_gate_can_be_confirmed(gate_id)
    if gate_id == "part6_final_decision_confirmed":
        _mark_part6_final_decision_confirmed(confirmed_at, notes)

    state = load_state()
    stage = _ensure_stage_state(state, stage_id)
    if gate_id not in stage["human_gates_completed"]:
        stage["human_gates_completed"].append(gate_id)

    record = {
        "gate_id": gate_id,
        "stage_id": stage_id,
        "confirmed_at": confirmed_at,
        "notes": notes,
    }
    if gate_id == "part6_finalization_authorized":
        fingerprints = _part6_handoff_artifact_fingerprints()
        record["fingerprint_scope"] = "part5_handoff_artifacts"
    elif gate_id == "part6_final_decision_confirmed":
        fingerprints = _part6_completion_artifact_fingerprints()
        record["fingerprint_scope"] = "part6_completion_package"
    else:
        fingerprints = _part5_artifact_fingerprints(gate_id)
    if fingerprints:
        record["artifact_fingerprints"] = fingerprints
    state.setdefault("human_decision_log", []).append(record)
    save_state(state)
    _write_process_memory("human_gate_confirmed", record)


def _record_deprecated_human_gate_noop(gate_id: str, notes: str = "") -> None:
    state = load_state()
    record = {
        "gate_id": gate_id,
        "stage_id": DEPRECATED_HUMAN_GATES[gate_id],
        "confirmed_at": now_iso(),
        "notes": notes,
        "status": "deprecated_noop",
        "reason": "Part 4/Part 5 human gates were removed from the blocking workflow.",
    }
    state.setdefault("human_decision_log", []).append(record)
    save_state(state)
    _write_process_memory("human_gate_deprecated_noop", record)


def _mark_part4_outline_confirmed(confirmed_at: str) -> None:
    """Mirror the human outline confirmation into paper_outline.json when present."""
    outline_path = PROJECT_ROOT / "outputs" / "part4" / "paper_outline.json"
    if not outline_path.exists():
        raise FileNotFoundError(
            "缺少 outputs/part4/paper_outline.json，不能确认 outline_confirmed"
        )

    try:
        with open(outline_path, encoding="utf-8") as f:
            outline = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"paper_outline.json 无法解析，不能确认 outline: {e}") from e

    if not isinstance(outline, dict):
        raise RuntimeError("paper_outline.json 必须是 JSON object，不能确认 outline")

    if outline.get("confirmed_at"):
        return

    shutil.copy2(outline_path, str(outline_path) + ".bak")
    outline["confirmed_at"] = confirmed_at
    with open(outline_path, "w", encoding="utf-8") as f:
        json.dump(outline, f, ensure_ascii=False, indent=2)


# ── Status & diagnostics ──────────────────────────────────────────────────────

def get_status() -> dict:
    state = load_state()
    stage_statuses = {}
    for stage_id in STAGE_ORDER:
        stage = _stage_state(state, stage_id)
        stage_statuses[stage_id] = {
            "status":              stage["status"],
            "gate_passed":         stage["gate_passed"],
            "started_at":          stage["started_at"],
            "completed_at":        stage["completed_at"],
            "artifacts":           check_artifacts(stage_id),
            "pending_human_gates": [
                g for g in HUMAN_GATES.get(stage_id, [])
                if g not in stage.get("human_gates_completed", [])
            ],
        }
    return {
        "initialized_at": state.get("initialized_at"),
        "current_stage":  state.get("current_stage"),
        "stages":         stage_statuses,
        "last_failure":   state.get("last_failure"),
        "next_action":    get_next_action(state),
    }


def get_next_action(state: Optional[dict] = None) -> dict[str, str]:
    """Return a user-facing next action for CLI status/doctor."""
    state = state or load_state()

    for stage_id in STAGE_ORDER:
        stage = _stage_state(state, stage_id)
        if stage.get("status") == "completed" and stage.get("gate_passed") is True:
            continue

        passed, issues = validate_gate(stage_id, state)
        if passed:
            return {
                "stage_id": stage_id,
                "command": f"python3 cli.py advance {stage_id}",
                "reason": "当前 stage gate 已通过，可以显式推进阶段。",
            }

        joined = " ".join(issues)
        if stage_id == "part6":
            if "人工节点未确认: part6_finalization_authorized" in joined:
                command = 'python3 cli.py part6-authorize --notes "授权进入 Part 6 finalization"'
                reason = "Part 6 finalization 必须先由用户显式授权，runtime 不会自动跳过 HITL。"
            elif (
                "part6_finalization_authorized 缺少" in joined
                or "Part 5 handoff artifact 已变化" in joined
            ):
                command = 'python3 cli.py part6-authorize --notes "重新授权进入 Part 6 finalization"'
                reason = "Part 6 授权记录缺失或 handoff fingerprint 已变化，需要用户重新授权。"
            elif (
                "人工节点未确认: part6_final_decision_confirmed" in joined
                and not _part6_completion_package_issues()
            ):
                command = 'python3 cli.py part6-confirm-final --notes "最终状态确认"'
                reason = "Part 6 package 已齐备，需要用户确认最终决策后才能通过 gate。"
            elif any(
                marker in joined
                for marker in [
                    PART6_FINAL_MANUSCRIPT,
                    PART6_FINAL_ABSTRACT,
                    PART6_FINAL_KEYWORDS,
                    PART6_SUBMISSION_CHECKLIST,
                    PART6_CLAIM_RISK_REPORT,
                    PART6_CITATION_CONSISTENCY_REPORT,
                    PART6_FINAL_READINESS_DECISION,
                    PART6_SUBMISSION_PACKAGE_MANIFEST,
                ]
            ):
                command = "python3 cli.py part6-finalize --step all"
                reason = "Part 6 已授权但最终包产物不完整，应运行 finalizer 生成最终稿、审计、decision 与 manifest。"
            else:
                command = "python3 cli.py part6-check"
                reason = issues[0] if issues else "Part 6 package 或 gate 状态需要专用检查。"
        elif "人工节点未确认: intake_confirmed" in joined:
            intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
            if intake_path.exists():
                command = 'python3 cli.py confirm-gate intake_confirmed --notes "主题与 intake 参数已确认"'
                reason = "Part 1 检索执行前需要用户确认已填写的 intake 参数。"
            else:
                command = "python3 cli.py part1-intake"
                reason = "Part 1 的第一步是填写 intake；该命令会生成 intake 表单请求和 JSON 模板。"
        elif stage_id == "part2":
            command = "python3 cli.py part2-health"
            reason = "Part 2 需要先修复 research-wiki health 或 writing-policy layer。"
        elif "outputs/part3/argument_seed_map.json" in joined:
            command = "python3 cli.py part3-seed-map"
            reason = "Part 3 需要先从 Part 2 wiki 生成 argument seed map，再生成候选 argument tree。"
        elif "候选 argument tree 必须正好 3 份" in joined:
            command = "python3 cli.py part3-generate"
            reason = "Part 3 需要先生成 3 份候选 argument tree。"
        elif "candidate_comparison" in joined:
            command = "python3 cli.py part3-compare"
            reason = "Part 3 需要生成候选比较，供人工选择。"
        elif "人工节点未确认: argument_tree_selected" in joined:
            command = 'python3 cli.py part3-select --candidate-id <candidate_id> --notes "选择理由"'
            reason = "Part 3 canonical argument tree 必须由用户选择后锁定。"
        elif "缺少 canonical artifact: outputs/part4/paper_outline.json" in joined:
            command = "python3 cli.py part4-generate"
            reason = "Part 4 需要基于已锁定 argument tree 生成大纲草稿。"
        elif "claim_evidence_matrix" in joined or "chapter_briefs" in joined:
            command = "python3 cli.py part5-prep"
            reason = "Part 5 需要先生成章节 brief、claim-evidence matrix、citation map 与资料债务清单。"
        elif "manuscript_v1.md" in joined:
            command = "python3 cli.py part5-draft"
            reason = "Part 5 需要基于已确认的写作输入包生成 manuscript_v1。"
        elif (
            "review_matrix" in joined
            or "review_summary" in joined
            or "review_report" in joined
            or "citation_consistency_precheck" in joined
        ):
            command = "python3 cli.py part5-review"
            reason = "Part 5 需要对 manuscript_v1 做结构化 review 与 citation precheck。"
        elif "revision_log" in joined or "manuscript_v2.md" in joined or "part6_readiness_decision" in joined:
            command = "python3 cli.py part5-revise"
            reason = "Part 5 需要基于 review 生成 revision_log、manuscript_v2 与 Part 6 readiness decision。"
        else:
            command = f"python3 cli.py validate {stage_id}"
            reason = issues[0] if issues else "需要查看 gate 校验详情。"

        return {"stage_id": stage_id, "command": command, "reason": reason}

    return {
        "stage_id": "complete",
        "command": "无需下一步动作",
        "reason": "Part 1-6 stage gates 均已通过；后续提交或归档应由用户另行显式触发。",
    }


def run_doctor() -> list[str]:
    """Run diagnostics. Returns list of issues found."""
    issues: list[str] = []

    # 1. State file health
    try:
        state = load_state()
    except Exception as e:
        return [f"CRITICAL: 无法加载 state 文件 — {e}"]

    # 2. Re-validate completed stages (checks for post-completion drift)
    for stage_id in STAGE_ORDER:
        if _stage_state(state, stage_id)["status"] == "completed":
            _, gate_issues = validate_gate(stage_id)
            for issue in gate_issues:
                issues.append(f"[{stage_id}] {issue}")

    # 2b. Validate any existing schema-backed artifact, even if its stage is not
    # completed yet. A broken draft canonical artifact should be visible to doctor.
    for rel_path, schema_rel_path in SCHEMA_MAP.items():
        artifact_path = PROJECT_ROOT / rel_path
        if not artifact_path.exists():
            continue
        schema_valid, schema_issues = _validate_schema(
            artifact_path,
            PROJECT_ROOT / schema_rel_path,
        )
        if schema_valid is False:
            issues.append(f"[artifact] Schema 校验失败 [{rel_path}]: {'; '.join(schema_issues)}")
        elif schema_issues:
            issues.append(f"[artifact] Schema 校验跳过 [{rel_path}]: {'; '.join(schema_issues)}")

    # 3. Knowledge layer separation
    wiki_exists   = (PROJECT_ROOT / "research-wiki").exists()
    policy_exists = (PROJECT_ROOT / "writing-policy").exists()
    if wiki_exists and not policy_exists:
        issues.append("writing-policy/ 目录缺失 — 知识层分离受损")

    # 4. Process memory directory
    if not PROCESS_MEMORY_DIR.exists():
        issues.append("process-memory/ 目录缺失")

    return issues


# ── Internal helpers ──────────────────────────────────────────────────────────

def _write_process_memory(event_type: str, data: dict) -> None:
    PROCESS_MEMORY_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = PROCESS_MEMORY_DIR / f"{ts}_{event_type}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"event": event_type, "timestamp": now_iso(), **data},
                  f, ensure_ascii=False, indent=2)
