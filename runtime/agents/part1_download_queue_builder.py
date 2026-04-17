#!/usr/bin/env python3
"""
Build Part 1 download_queue.json from search result candidates.

The queue builder is deterministic. researchagent may provide a triage sidecar,
but that sidecar is advisory and never becomes a gate or canonical artifact.
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402


CANDIDATES_REF = "outputs/part1/search_results_candidates.json"
TRIAGE_REF = "outputs/part1/researchagent_search_result_triage.json"
TRIAGE_PROVENANCE_REF = "outputs/part1/researchagent_search_result_triage_provenance.json"
QUEUE_REF = "outputs/part1/download_queue.json"

DEFAULT_DOWNLOAD_THRESHOLD = 0.55
SOURCE_PRIORITY_SCORE = {
    "cnki": 1.0,
    "wanfang": 0.8,
    "vip": 0.7,
    "crossref": 0.75,
    "openalex": 0.7,
    "doaj": 0.65,
}


def iso_now() -> str:
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


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [
            item.strip()
            for item in re.split(r"[；;、,，\n]+", value)
            if item.strip()
        ]
    return []


def _unique_terms(terms: list[str]) -> list[str]:
    seen = set()
    unique: list[str] = []
    for term in terms:
        normalized = str(term).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def expand_known_aliases(terms: list[str]) -> list[str]:
    aliases = {
        "何静堂": ["何镜堂", "何镜堂建筑创作", "何镜堂 两观三性", "何镜堂 岭南建筑"],
        "何镜堂": ["何静堂"],
    }
    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        for needle, replacements in aliases.items():
            if needle in term:
                expanded.extend(replacements)
    return _unique_terms(expanded)


def build_anchor_profile(intake: dict[str, Any]) -> dict[str, list[str]]:
    required = _as_list(intake.get("keywords_required", []))
    suggested = _as_list(intake.get("keywords_suggested", []))
    fields = _as_list(intake.get("discipline_fields", []))
    expected_types = _as_list(intake.get("expected_research_types", []))
    topic = str(intake.get("research_topic", ""))
    question = str(intake.get("research_question", ""))
    scope = str(intake.get("scope_notes", ""))
    all_terms = expand_known_aliases(_unique_terms(required + suggested + fields + expected_types))
    anchor_text = " ".join([topic, question, scope, " ".join(all_terms)])

    object_terms = [
        term for term in all_terms
        if any(marker in term for marker in [
            "岭南", "建筑", "建筑创作", "建筑学派", "建筑师", "何静堂", "何镜堂",
        ])
    ]
    context_terms = [
        term for term in all_terms
        if any(marker in term for marker in [
            "现代", "现代性", "地域", "地域性", "本土", "本土化", "传统",
            "融合", "气候", "环境", "理性", "审美", "两观三性",
            "现代主义", "国际风格", "全球化", "现代化", "自我批判",
        ])
    ]
    if "岭南" in anchor_text:
        object_terms.extend(["岭南建筑", "岭南现代建筑", "岭南建筑创作"])
    if "何静堂" in anchor_text or "何镜堂" in anchor_text:
        object_terms.extend(["何静堂", "何镜堂", "何镜堂建筑创作"])
        context_terms.append("两观三性")
    if "现代性" in anchor_text:
        context_terms.extend(["现代性", "现代建筑", "现代主义"])

    exclusions = _as_list(intake.get("exclusions", [])) + _as_list(intake.get("exclusion_rules", []))
    return {
        "object_terms": _unique_terms(object_terms),
        "context_terms": _unique_terms(context_terms),
        "exclusion_terms": _unique_terms(exclusions),
    }


def candidate_text(candidate: dict[str, Any]) -> str:
    return " ".join([
        str(candidate.get("title", "")),
        str(candidate.get("abstract", "")),
        str(candidate.get("journal", "")),
        " ".join(_as_list(candidate.get("keywords", []))),
    ]).lower()


def matched_terms(terms: list[str], text: str) -> list[str]:
    return [term for term in terms if term.lower() in text]


def deterministic_candidate_score(candidate: dict[str, Any], intake: dict[str, Any]) -> dict[str, Any]:
    profile = build_anchor_profile(intake)
    text = candidate_text(candidate)
    matched_object = matched_terms(profile["object_terms"], text)
    matched_context = matched_terms(profile["context_terms"], text)
    matched_exclusions = matched_terms(profile["exclusion_terms"], text)
    has_double_anchor = bool(matched_object and matched_context)

    score = 0.0
    if matched_object:
        score += min(0.35, 0.18 + 0.04 * len(matched_object))
    if matched_context:
        score += min(0.35, 0.18 + 0.04 * len(matched_context))
    title = str(candidate.get("title", "")).lower()
    if any(term.lower() in title for term in matched_object):
        score += 0.08
    if any(term.lower() in title for term in matched_context):
        score += 0.08
    if candidate.get("year"):
        score += 0.04
    if candidate.get("journal"):
        score += 0.04
    if matched_exclusions:
        score -= 0.25
    if not has_double_anchor:
        score = min(score, 0.49)

    score = round(max(0.0, min(score, 1.0)), 4)
    reasons = []
    if not has_double_anchor:
        reasons.append("missing_double_anchor")
    if matched_exclusions:
        reasons.append("matched_exclusion_terms")
    if candidate.get("hasDownload") is False and candidate.get("db") == "cnki":
        reasons.append("cnki_download_link_missing")

    return {
        "deterministic_score": score,
        "has_double_anchor": has_double_anchor,
        "matched_object_terms": matched_object,
        "matched_context_terms": matched_context,
        "matched_exclusion_terms": matched_exclusions,
        "skip_reasons": reasons,
    }


def normalize_semantic_relevance(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score > 1:
        score = score / 100
    return max(0.0, min(score, 1.0))


def triage_items_by_candidate_id(triage_doc: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not triage_doc:
        return {}
    payload = triage_doc.get("payload") if isinstance(triage_doc.get("payload"), dict) else triage_doc
    artifacts = triage_doc.get("artifacts") if isinstance(triage_doc.get("artifacts"), dict) else {}
    items = (
        payload.get("triage_items")
        or payload.get("items")
        or artifacts.get("triage_items")
        or []
    )
    if not isinstance(items, list):
        return {}
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get("candidate_id"):
            result[str(item["candidate_id"])] = item
    return result


def source_priority(candidate: dict[str, Any]) -> float:
    return SOURCE_PRIORITY_SCORE.get(str(candidate.get("db") or "").lower(), 0.45)


def final_score_for(
    candidate: dict[str, Any],
    deterministic: dict[str, Any],
    triage_item: dict[str, Any] | None,
) -> tuple[float, list[str]]:
    reasons = list(deterministic["skip_reasons"])
    if triage_item:
        recommendation = str(triage_item.get("recommendation", "")).lower()
        if recommendation == "skip":
            reasons.append("researchagent_skip")
        semantic = normalize_semantic_relevance(triage_item.get("semantic_relevance"))
    else:
        semantic = None

    if semantic is None:
        score = deterministic["deterministic_score"] * 0.9 + source_priority(candidate) * 0.1
    else:
        score = (
            deterministic["deterministic_score"] * 0.6
            + semantic * 0.3
            + source_priority(candidate) * 0.1
        )
    return round(max(0.0, min(score, 1.0)), 4), reasons


def candidate_sort_key(item: dict[str, Any]) -> tuple[int, float, int]:
    query_id = str(item.get("query_id") or "")
    focused_rank = 0 if query_id == "cnki_q1_1" else 1
    rank = item.get("rank")
    return (focused_rank, -float(item.get("final_download_score") or 0), int(rank or 9999))


def build_download_queue(
    *,
    intake: dict[str, Any],
    search_plan: dict[str, Any],
    candidates_doc: dict[str, Any],
    triage_doc: dict[str, Any] | None = None,
    threshold: float = DEFAULT_DOWNLOAD_THRESHOLD,
) -> dict[str, Any]:
    candidates = candidates_doc.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    quota = search_plan.get("source_quota_policy", {})
    max_cnki = int(quota.get("cnki_max_count", 28))
    triage_by_id = triage_items_by_candidate_id(triage_doc)

    queued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("candidate_id") or f"{candidate.get('query_id', 'candidate')}_rank_{index:03d}")
        title_key = re.sub(r"\s+", "", str(candidate.get("title", "")).lower())
        deterministic = deterministic_candidate_score(candidate, intake)
        triage_item = triage_by_id.get(candidate_id)
        final_score, skip_reasons = final_score_for(candidate, deterministic, triage_item)
        item = {
            **candidate,
            "candidate_id": candidate_id,
            "deterministic_score": deterministic["deterministic_score"],
            "final_download_score": final_score,
            "matched_object_terms": deterministic["matched_object_terms"],
            "matched_context_terms": deterministic["matched_context_terms"],
            "researchagent_triage": triage_item,
        }
        if title_key and title_key in seen_titles:
            skip_reasons.append("duplicate_title")
        if final_score < threshold:
            skip_reasons.append("below_download_threshold")
        if skip_reasons:
            skipped.append({**item, "skip_reasons": sorted(set(skip_reasons))})
            continue
        seen_titles.add(title_key)
        queued.append(item)

    queued.sort(key=candidate_sort_key)
    cnki_count = 0
    final_items: list[dict[str, Any]] = []
    for item in queued:
        if str(item.get("db") or "").lower() == "cnki":
            if cnki_count >= max_cnki:
                skipped.append({**item, "skip_reasons": ["cnki_quota_overflow"]})
                continue
            cnki_count += 1
        final_items.append(item)

    return {
        "created_at": iso_now(),
        "artifact_type": "part1_download_queue",
        "based_on_candidates": CANDIDATES_REF,
        "based_on_triage": TRIAGE_REF if triage_doc else None,
        "download_threshold": threshold,
        "llm_triage_is_gate": False,
        "total_candidates": len(candidates),
        "total_queued": len(final_items),
        "total_skipped": len(skipped),
        "items": final_items,
        "skipped_items": skipped,
    }


def write_researchagent_triage_sidecar(project_root: Path) -> dict[str, Any] | None:
    result = request_llm_agent(
        project_root,
        agent_name="researchagent",
        task="part1_search_result_triage",
        skill="part1-search-result-triage",
        output_ref=TRIAGE_REF,
        input_paths=[
            "outputs/part1/intake.json",
            "outputs/part1/search_plan.json",
            CANDIDATES_REF,
            "manifests/source-policy.json",
        ],
        instructions=[
            "Review search result candidates before download. Recommend download/maybe/skip with semantic_relevance and reasons.",
            "Return JSON with payload.triage_items. Do not write canonical artifacts, source_id, runtime state, or gate decisions.",
            "Use intake double-anchor relevance and CNKI-first policy. Do not treat this triage as final library acceptance.",
        ],
    )
    if result is None:
        write_llm_agent_provenance(
            project_root,
            TRIAGE_PROVENANCE_REF,
            agent_name="researchagent",
            task="part1_search_result_triage",
            skill="part1-search-result-triage",
            output_ref=TRIAGE_REF,
            mode="deterministic_fallback",
            fallback_reason="RTM_RESEARCHAGENT_COMMAND not configured",
        )
        return None

    write_json(project_root / TRIAGE_REF, result.raw)
    write_llm_agent_provenance(
        project_root,
        TRIAGE_PROVENANCE_REF,
        agent_name="researchagent",
        task="part1_search_result_triage",
        skill="part1-search-result-triage",
        output_ref=TRIAGE_REF,
        mode="llm",
    )
    return result.raw


def build_and_write_download_queue(
    project_root: Path = PROJECT_ROOT,
    *,
    run_researchagent: bool = True,
    threshold: float = DEFAULT_DOWNLOAD_THRESHOLD,
) -> dict[str, Any]:
    intake = load_json(project_root / "outputs" / "part1" / "intake.json")
    search_plan = load_json(project_root / "outputs" / "part1" / "search_plan.json")
    candidates_doc = load_json(project_root / CANDIDATES_REF)

    triage_doc = None
    triage_path = project_root / TRIAGE_REF
    if triage_path.exists():
        triage_doc = load_json(triage_path)
    elif run_researchagent:
        triage_doc = write_researchagent_triage_sidecar(project_root)

    queue = build_download_queue(
        intake=intake,
        search_plan=search_plan,
        candidates_doc=candidates_doc,
        triage_doc=triage_doc,
        threshold=threshold,
    )
    write_json(project_root / QUEUE_REF, queue)
    return queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Part 1 download queue from search result candidates")
    parser.add_argument("--project-root", metavar="PATH")
    parser.add_argument("--no-researchagent", action="store_true", help="Skip researchagent sidecar call")
    parser.add_argument("--threshold", type=float, default=DEFAULT_DOWNLOAD_THRESHOLD)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT
    queue = build_and_write_download_queue(
        project_root,
        run_researchagent=not args.no_researchagent,
        threshold=args.threshold,
    )
    print("✓ download_queue.json 写入完成")
    print(f"  candidates: {queue['total_candidates']}")
    print(f"  queued:     {queue['total_queued']}")
    print(f"  skipped:    {queue['total_skipped']}")
    print(f"  output:     {project_root / QUEUE_REF}")


if __name__ == "__main__":
    main()
