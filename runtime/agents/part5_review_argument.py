#!/usr/bin/env python3
"""Part 5 argument review fragment generator."""

from __future__ import annotations

from pathlib import Path

from part5_review_integrator import (
    load_claims,
    require_manuscript_v1,
    require_part5_prep_confirmed,
    review_item,
    write_review_fragment,
)


DIMENSION = "argument"


def generate_review_fragment(project_root: Path) -> dict:
    require_part5_prep_confirmed(project_root)
    manuscript = require_manuscript_v1(project_root)

    reviews: list[dict] = []
    for claim in load_claims(project_root):
        claim_id = claim.get("claim_id")
        claim_text = claim.get("claim")
        if not isinstance(claim_id, str) or not isinstance(claim_text, str):
            continue
        if claim_text and claim_text not in manuscript:
            reviews.append(
                review_item(
                    review_id=f"argument_review_{len(reviews) + 1:03d}",
                    dimension=DIMENSION,
                    severity="medium",
                    finding=f"{claim_id} 未在 manuscript_v1 中形成可见论证位置。",
                    claim_ids=[claim_id],
                    evidence_refs=[
                        {
                            "artifact": "outputs/part5/claim_evidence_matrix.json",
                            "claim_id": claim_id,
                        },
                        {"artifact": "outputs/part5/manuscript_v1.md"},
                    ],
                )
            )

    if not reviews:
        reviews = [
            review_item(
                review_id="argument_review_001",
                dimension=DIMENSION,
                severity="low",
                finding="claim_evidence_matrix 中的论点已在 v1 scaffold 中获得基本承接。",
                status="resolved",
                claim_ids=[
                    claim["claim_id"]
                    for claim in load_claims(project_root)
                    if isinstance(claim.get("claim_id"), str)
                ],
                evidence_refs=[
                    {"artifact": "outputs/part5/claim_evidence_matrix.json"},
                    {"artifact": "outputs/part5/manuscript_v1.md"},
                ],
            )
        ]

    return write_review_fragment(project_root, DIMENSION, reviews)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Part 5 argument review fragment")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    generate_review_fragment(Path(args.project_root).resolve())
