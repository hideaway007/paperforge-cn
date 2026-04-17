#!/usr/bin/env python3
"""Deterministic Part 5 citation review fragment generator."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from part5_review_integrator import (
    load_required_json,
    raw_source_ids,
    require_manuscript_v1,
    require_part5_prep_confirmed,
    review_item,
    string_list,
    wiki_trace_sets,
    write_review_fragment,
)
from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402


DIMENSION = "citation"
CITATIONAUDITOR_REVIEW_REF = "outputs/part5/llm_agent_reviews/citationauditor_citation_review.json"
CITATIONAUDITOR_PROVENANCE_REF = "outputs/part5/citationauditor_provenance.json"


def review_source_ref(
    source_ref: dict[str, Any],
    raw_ids: set[str],
    wiki_source_ids: set[str],
) -> dict[str, Any] | None:
    source_id = source_ref.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        return {
            "source_id": "unknown",
            "citation_status": source_ref.get("citation_status"),
            "claim_ids": string_list(source_ref.get("claim_ids")),
            "errors": ["citation_map.source_refs 存在缺少 source_id 的项"],
        }

    claim_ids = string_list(source_ref.get("claim_ids"))
    errors: list[str] = []
    if source_ref.get("citation_status") != "accepted_source":
        errors.append(f"citation_status={source_ref.get('citation_status')}")
    if source_id not in raw_ids:
        errors.append("source_id 不存在于 raw-library/metadata.json")
    if source_id not in wiki_source_ids:
        errors.append("source_id 不存在于 research-wiki/index.json 页面 source_ids 映射")

    if not errors:
        return None
    return {
        "source_id": source_id,
        "citation_status": source_ref.get("citation_status"),
        "claim_ids": claim_ids,
        "errors": errors,
    }


def generate_review_fragment(project_root: Path) -> dict:
    require_part5_prep_confirmed(project_root)
    require_manuscript_v1(project_root)
    citation_map = load_required_json(project_root, "outputs/part5/citation_map.json")
    raw_ids = raw_source_ids(project_root)
    _wiki_page_ids, wiki_source_ids = wiki_trace_sets(project_root)

    refs = [ref for ref in citation_map.get("source_refs", []) or [] if isinstance(ref, dict)]
    problem_refs = [
        problem
        for ref in refs
        for problem in [review_source_ref(ref, raw_ids, wiki_source_ids)]
        if problem is not None
    ]

    for source_id in string_list(citation_map.get("unmapped_sources")):
        if not any(ref.get("source_id") == source_id for ref in problem_refs):
            problem_refs.append({
                "source_id": source_id,
                "citation_status": "unmapped_source",
                "claim_ids": [],
                "errors": ["citation_map.unmapped_sources 中仍有未映射来源"],
            })

    reviews: list[dict] = []
    for problem in problem_refs:
        source_id = problem.get("source_id", "unknown")
        reviews.append(
            review_item(
                review_id=f"citation_review_{len(reviews) + 1:03d}",
                dimension=DIMENSION,
                severity="critical",
                finding=f"{source_id} 引用不可进入正文硬证据。",
                claim_ids=string_list(problem.get("claim_ids")),
                source_refs=[problem],
            )
        )

    if not refs:
        reviews.append(
            review_item(
                review_id=f"citation_review_{len(reviews) + 1:03d}",
                dimension=DIMENSION,
                severity="critical",
                finding="citation_map.source_refs 为空，无法执行引用一致性预检。",
                claim_ids=[],
                evidence_refs=[{"artifact": "outputs/part5/citation_map.json"}],
            )
        )

    if not reviews:
        reviews = [
            review_item(
                review_id="citation_review_001",
                dimension=DIMENSION,
                severity="low",
                finding="citation_map 中的 accepted_source 均可回溯到 raw-library/research-wiki。",
                status="resolved",
                claim_ids=sorted({
                    claim_id
                    for ref in refs
                    for claim_id in string_list(ref.get("claim_ids"))
                }),
                source_refs=[
                    {
                        "source_id": ref.get("source_id"),
                        "citation_status": ref.get("citation_status"),
                        "claim_ids": string_list(ref.get("claim_ids")),
                    }
                    for ref in refs
                ],
            )
        ]

    fragment = write_review_fragment(project_root, DIMENSION, reviews)
    write_citationauditor_sidecar(project_root)
    return fragment


def write_citationauditor_sidecar(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="citationauditor",
        task="part5_citation_consistency_review",
        skill="part5-review-manuscript",
        output_ref=CITATIONAUDITOR_REVIEW_REF,
        input_paths=[
            "outputs/part5/manuscript_v1.md",
            "outputs/part5/citation_map.json",
            "outputs/part5/claim_evidence_matrix.json",
            "raw-library/metadata.json",
            "research-wiki/index.json",
        ],
        instructions=[
            "Review Part 5 citation consistency, source drift, orphan citations, missing mapping, and reference support.",
            "Return JSON with report or payload. Do not rewrite manuscript_v1, citation_map.json, or review_matrix.json.",
            "Do not add new sources or citations. Use only accepted source mappings.",
        ],
    )
    if result is None:
        return

    path = project_root / CITATIONAUDITOR_REVIEW_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.raw, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_llm_agent_provenance(
        project_root,
        CITATIONAUDITOR_PROVENANCE_REF,
        agent_name="citationauditor",
        task="part5_citation_consistency_review",
        skill="part5-review-manuscript",
        output_ref=CITATIONAUDITOR_REVIEW_REF,
        mode="llm",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Part 5 citation review fragment")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    generate_review_fragment(Path(args.project_root).resolve())
