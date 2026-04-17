#!/usr/bin/env python3
"""Part 5 structure review fragment generator."""

from __future__ import annotations

from pathlib import Path

from part5_review_integrator import (
    load_required_json,
    require_manuscript_v1,
    require_part5_prep_confirmed,
    review_item,
    write_review_fragment,
)


DIMENSION = "structure"


def generate_review_fragment(project_root: Path) -> dict:
    require_part5_prep_confirmed(project_root)
    manuscript = require_manuscript_v1(project_root)
    outline = load_required_json(project_root, "outputs/part4/paper_outline.json")
    sections = [section for section in outline.get("sections", []) or [] if isinstance(section, dict)]

    missing_titles = [
        section.get("title", "")
        for section in sections
        if section.get("title") and f"## {section.get('title')}" not in manuscript
    ]
    if missing_titles:
        reviews = [
            review_item(
                review_id="structure_review_001",
                dimension=DIMENSION,
                severity="high",
                finding="manuscript_v1 缺少 outline 中的章节标题: " + ", ".join(missing_titles),
                claim_ids=[],
                evidence_refs=[
                    {"artifact": "outputs/part4/paper_outline.json"},
                    {"artifact": "outputs/part5/manuscript_v1.md"},
                ],
            )
        ]
    else:
        reviews = [
            review_item(
                review_id="structure_review_001",
                dimension=DIMENSION,
                severity="medium",
                finding="当前 v1 是章节级 scaffold，需要后续扩写为连续中文学术段落。",
                claim_ids=[],
                evidence_refs=[
                    {"artifact": "outputs/part4/paper_outline.json"},
                    {"artifact": "outputs/part5/manuscript_v1.md"},
                ],
            )
        ]

    return write_review_fragment(project_root, DIMENSION, reviews)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Part 5 structure review fragment")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    generate_review_fragment(Path(args.project_root).resolve())
