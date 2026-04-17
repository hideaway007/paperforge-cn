#!/usr/bin/env python3
"""Part 5 evidence review fragment generator."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from part5_review_integrator import (
    load_claims,
    require_manuscript_v1,
    require_part5_prep_confirmed,
    review_item,
    write_review_fragment,
)
from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402


DIMENSION = "evidence"
CLAIMAUDITOR_REVIEW_REF = "outputs/part5/llm_agent_reviews/claimauditor_evidence_review.json"
CLAIMAUDITOR_PROVENANCE_REF = "outputs/part5/claimauditor_provenance.json"


def severity_for_risk(risk_level: str) -> str:
    if risk_level == "critical":
        return "critical"
    if risk_level in {"high", "medium"}:
        return risk_level
    return "medium"


def generate_review_fragment(project_root: Path) -> dict:
    require_part5_prep_confirmed(project_root)
    require_manuscript_v1(project_root)
    reviews: list[dict] = []
    claims = load_claims(project_root)

    for claim in claims:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        source_ids = [source_id for source_id in claim.get("source_ids", []) or [] if isinstance(source_id, str)]
        wiki_page_ids = [page_id for page_id in claim.get("wiki_page_ids", []) or [] if isinstance(page_id, str)]
        risk_level = claim.get("risk_level", "medium")
        has_gap = risk_level != "low" or not source_ids or not wiki_page_ids
        if not has_gap:
            continue

        reviews.append(
            review_item(
                review_id=f"evidence_review_{len(reviews) + 1:03d}",
                dimension=DIMENSION,
                severity=severity_for_risk(str(risk_level)),
                finding=f"{claim_id} 证据映射不足，正文需降低断言强度。",
                claim_ids=[claim_id],
                evidence_refs=[
                    {
                        "artifact": "outputs/part5/claim_evidence_matrix.json",
                        "claim_id": claim_id,
                        "risk_level": risk_level,
                        "source_ids": source_ids,
                        "wiki_page_ids": wiki_page_ids,
                    }
                ],
            )
        )

    if not reviews:
        reviews = [
            review_item(
                review_id="evidence_review_001",
                dimension=DIMENSION,
                severity="low",
                finding="claim_evidence_matrix 中的 claim 均已具备基础 source/wiki 映射。",
                status="resolved",
                claim_ids=[
                    claim["claim_id"]
                    for claim in claims
                    if isinstance(claim.get("claim_id"), str)
                ],
                evidence_refs=[{"artifact": "outputs/part5/claim_evidence_matrix.json"}],
            )
        ]

    fragment = write_review_fragment(project_root, DIMENSION, reviews)
    write_claimauditor_sidecar(project_root)
    return fragment


def write_claimauditor_sidecar(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="claimauditor",
        task="part5_claim_evidence_review",
        skill="part5-review-manuscript",
        output_ref=CLAIMAUDITOR_REVIEW_REF,
        input_paths=[
            "outputs/part5/manuscript_v1.md",
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part3/argument_tree.json",
            "research-wiki/index.json",
            "raw-library/metadata.json",
        ],
        instructions=[
            "Review Part 5 manuscript_v1 for overclaims, evidence sufficiency, missing warrants, and case-verification risk.",
            "Return JSON with report or payload. Do not rewrite manuscript_v1 or review_matrix.json.",
            "Do not add sources or claims. Keep writing-policy material separate from research evidence.",
        ],
    )
    if result is None:
        return

    path = project_root / CLAIMAUDITOR_REVIEW_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.raw, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_llm_agent_provenance(
        project_root,
        CLAIMAUDITOR_PROVENANCE_REF,
        agent_name="claimauditor",
        task="part5_claim_evidence_review",
        skill="part5-review-manuscript",
        output_ref=CLAIMAUDITOR_REVIEW_REF,
        mode="llm",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Part 5 evidence review fragment")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    generate_review_fragment(Path(args.project_root).resolve())
