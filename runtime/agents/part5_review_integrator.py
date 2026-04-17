#!/usr/bin/env python3
"""
Part 5 review fragment integrator.

Review agents write only dimension fragments under
outputs/part5/review_fragments/. This module is the only Part 5 review module
that writes canonical review artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from part5_mvp_generator import PREP_ARTIFACTS, require_files, require_part5_entry


REVIEW_DIMENSIONS = [
    "structure",
    "argument",
    "evidence",
    "citation",
    "writing_policy",
]

FRAGMENT_FILENAMES = {
    "structure": "structure_review.json",
    "argument": "argument_review.json",
    "evidence": "evidence_review.json",
    "citation": "citation_review.json",
    "writing_policy": "writing_policy_review.json",
}

MANUSCRIPT_REF = "outputs/part5/manuscript_v1.md"
FRAGMENT_DIR = "outputs/part5/review_fragments"
FRAGMENT_SCHEMA_REF = "schemas/part5_review_fragment.schema.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_required_json(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {rel_path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{rel_path} 必须是 JSON object")
    return data


def require_manuscript_v1(project_root: Path) -> str:
    path = project_root / MANUSCRIPT_REF
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {MANUSCRIPT_REF}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"{MANUSCRIPT_REF} 不能为空")
    return text


def fragment_schema_path(project_root: Path) -> Path:
    project_schema = project_root / FRAGMENT_SCHEMA_REF
    if project_schema.exists():
        return project_schema
    return Path(__file__).resolve().parents[2] / FRAGMENT_SCHEMA_REF


def validate_review_fragment_schema(
    project_root: Path,
    rel_path: str,
    fragment: dict[str, Any],
) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema 不可用，不能校验 Part 5 review fragment schema") from exc

    schema_path = fragment_schema_path(project_root)
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=fragment, schema=schema)
    except jsonschema.ValidationError as exc:
        raise RuntimeError(f"{rel_path} schema validation failed: {exc.message}") from exc
    except jsonschema.SchemaError as exc:
        raise RuntimeError(f"{FRAGMENT_SCHEMA_REF} schema invalid: {exc.message}") from exc


def validate_review_fragment(
    project_root: Path,
    dimension: str,
    fragment: dict[str, Any],
) -> None:
    expected_ref = fragment_rel_path(dimension)
    validate_review_fragment_schema(project_root, expected_ref, fragment)
    if fragment.get("dimension") != dimension:
        raise RuntimeError(f"{expected_ref} dimension 不一致")
    if fragment.get("fragment_ref") != expected_ref:
        raise RuntimeError(f"{expected_ref} fragment_ref 不一致")


def write_json(project_root: Path, rel_path: str, data: dict[str, Any]) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(project_root: Path, rel_path: str, text: str) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def require_part5_prep_confirmed(project_root: Path) -> None:
    require_part5_entry(project_root)
    require_files(project_root, PREP_ARTIFACTS)


def fragment_rel_path(dimension: str) -> str:
    filename = FRAGMENT_FILENAMES.get(dimension)
    if not filename:
        raise ValueError(f"unknown review dimension: {dimension}")
    return f"{FRAGMENT_DIR}/{filename}"


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [item for item in as_list(value) if isinstance(item, str)]


def write_review_fragment(
    project_root: Path,
    dimension: str,
    reviews: list[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if dimension not in REVIEW_DIMENSIONS:
        raise ValueError(f"unknown review dimension: {dimension}")
    if not reviews:
        raise RuntimeError(f"{dimension} review fragment reviews 不能为空")

    artifact = {
        "schema_version": "1.0.0",
        "generated_at": generated_at or now_iso(),
        "dimension": dimension,
        "manuscript_ref": MANUSCRIPT_REF,
        "fragment_ref": fragment_rel_path(dimension),
        "reviews": reviews,
    }
    write_json(project_root, artifact["fragment_ref"], artifact)
    return artifact


def review_item(
    *,
    review_id: str,
    dimension: str,
    severity: str,
    finding: str,
    status: str = "registered",
    claim_ids: list[str] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "review_id": review_id,
        "dimension": dimension,
        "severity": severity,
        "finding": finding,
        "claim_ids": claim_ids or [],
        "status": status,
    }
    if evidence_refs is not None:
        item["evidence_refs"] = evidence_refs
    if source_refs is not None:
        item["source_refs"] = source_refs
    if "evidence_refs" not in item and "source_refs" not in item:
        item["evidence_refs"] = [{"artifact": MANUSCRIPT_REF}]
    return item


def load_claims(project_root: Path) -> list[dict[str, Any]]:
    matrix = load_required_json(project_root, "outputs/part5/claim_evidence_matrix.json")
    return [claim for claim in as_list(matrix.get("claims")) if isinstance(claim, dict)]


def claims_by_id(project_root: Path) -> dict[str, dict[str, Any]]:
    return {
        claim["claim_id"]: claim
        for claim in load_claims(project_root)
        if isinstance(claim.get("claim_id"), str)
    }


def raw_source_ids(project_root: Path) -> set[str]:
    metadata = load_required_json(project_root, "raw-library/metadata.json")
    return {
        source["source_id"]
        for source in as_list(metadata.get("sources"))
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }


def wiki_trace_sets(project_root: Path) -> tuple[set[str], set[str]]:
    wiki_index = load_required_json(project_root, "research-wiki/index.json")
    page_ids: set[str] = set()
    source_ids: set[str] = set()
    for page in as_list(wiki_index.get("pages")):
        if not isinstance(page, dict):
            continue
        page_id = page.get("page_id")
        if isinstance(page_id, str):
            page_ids.add(page_id)
        source_ids.update(string_list(page.get("source_ids")))
    return page_ids, source_ids


def load_review_fragments(project_root: Path) -> list[dict[str, Any]]:
    fragments: list[dict[str, Any]] = []
    for dimension in REVIEW_DIMENSIONS:
        fragment = load_required_json(project_root, fragment_rel_path(dimension))
        validate_review_fragment(project_root, dimension, fragment)
        fragments.append(fragment)
    return fragments


def flatten_fragment_reviews(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fragment in fragments:
        fragment_dimension = fragment.get("dimension")
        fragment_ref = fragment.get("fragment_ref")
        for review in as_list(fragment.get("reviews")):
            if not isinstance(review, dict):
                continue
            review_id = review.get("review_id")
            if not isinstance(review_id, str) or not review_id:
                raise RuntimeError("review fragment item 缺少 review_id")
            if review.get("dimension") != fragment_dimension:
                raise RuntimeError(
                    f"{fragment_ref} review item dimension 不一致: {review_id}"
                )
            if review_id in seen:
                raise RuntimeError(f"重复 review_id: {review_id}")
            seen.add(review_id)
            reviews.append({**review, "source_fragment_ref": fragment.get("fragment_ref")})
    if not reviews:
        raise RuntimeError("review fragments 没有可整合 review")
    return reviews


def build_claim_risk_report(
    project_root: Path,
    reviews: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    claim_lookup = claims_by_id(project_root)
    risk_items: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for claim_id, claim in claim_lookup.items():
        risk_level = claim.get("risk_level")
        if risk_level and risk_level != "low":
            seen_keys.add((claim_id, "claim_evidence_matrix"))
            risk_items.append({
                "claim_id": claim_id,
                "risk_level": risk_level,
                "reason": "claim_evidence_matrix 已登记非 low 风险。",
                "mitigation": "正文中降低断言强度，或保留为 research debt。",
                "source_review_id": None,
            })

    for review in reviews:
        severity = review.get("severity")
        if severity not in {"medium", "high", "critical"}:
            continue
        dimension = review.get("dimension")
        if dimension not in {"argument", "evidence", "citation"}:
            continue
        for claim_id in string_list(review.get("claim_ids")):
            key = (claim_id, str(review.get("review_id")))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            risk_items.append({
                "claim_id": claim_id,
                "risk_level": severity,
                "reason": review.get("finding", "review registered risk"),
                "mitigation": "按 review matrix 修订；critical 项不得在 Part 6 前静默跳过。",
                "source_review_id": review.get("review_id"),
            })

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "risk_items": risk_items,
    }


def build_citation_precheck(
    project_root: Path,
    reviews: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    claims = load_claims(project_root)
    errors: list[str] = []
    warnings = ["v1 是 scaffold，扩写时必须逐条保留 source_id 回溯。"]

    for review in reviews:
        if review.get("dimension") != "citation":
            continue
        if review.get("severity") == "critical":
            for source_ref in as_list(review.get("source_refs")):
                if not isinstance(source_ref, dict):
                    continue
                source_id = source_ref.get("source_id", "unknown")
                detail = "; ".join(string_list(source_ref.get("errors"))) or review.get("finding", "")
                errors.append(f"{source_id}: {detail}")
        elif review.get("severity") in {"medium", "high"}:
            warnings.append(str(review.get("finding")))

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "status": "blocked" if errors else "pass_with_warnings",
        "checked_claim_ids": [
            claim.get("claim_id")
            for claim in claims
            if isinstance(claim.get("claim_id"), str)
        ],
        "warnings": warnings,
        "errors": errors,
    }


def build_review_summary(
    reviews: list[dict[str, Any]],
    risk_report: dict[str, Any],
    citation_precheck: dict[str, Any],
) -> str:
    severity_counts = {
        severity: sum(1 for review in reviews if review.get("severity") == severity)
        for severity in ["critical", "high", "medium", "low"]
    }
    dimension_counts = {
        dimension: sum(1 for review in reviews if review.get("dimension") == dimension)
        for dimension in REVIEW_DIMENSIONS
    }
    lines = [
        "# Part 5 Review Summary",
        "",
        f"- review items: {len(reviews)}",
        f"- critical: {severity_counts['critical']}",
        f"- high: {severity_counts['high']}",
        f"- medium: {severity_counts['medium']}",
        f"- low: {severity_counts['low']}",
        f"- claim risks: {len(as_list(risk_report.get('risk_items')))}",
        f"- citation precheck: {citation_precheck.get('status')}",
        f"- citation errors: {len(as_list(citation_precheck.get('errors')))}",
        "",
        "## Dimensions",
    ]
    lines.extend(f"- {dimension}: {count}" for dimension, count in dimension_counts.items())
    lines.extend([
        "",
        "结论：review 已由 fragments 汇总；修订可继续执行，无需 Part 5 人工 gate。",
        "",
    ])
    return "\n".join(lines)


def integrate_review_fragments(project_root: Path) -> dict[str, Any]:
    require_part5_prep_confirmed(project_root)
    generated_at = now_iso()
    fragments = load_review_fragments(project_root)
    reviews = flatten_fragment_reviews(fragments)

    review_matrix = {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "manuscript_ref": MANUSCRIPT_REF,
        "fragment_refs": [fragment["fragment_ref"] for fragment in fragments],
        "reviews": reviews,
    }
    claim_risk_report = build_claim_risk_report(project_root, reviews, generated_at)
    citation_precheck = build_citation_precheck(project_root, reviews, generated_at)
    review_summary = build_review_summary(reviews, claim_risk_report, citation_precheck)

    write_json(project_root, "outputs/part5/review_matrix.json", review_matrix)
    write_json(project_root, "outputs/part5/claim_risk_report.json", claim_risk_report)
    write_json(project_root, "outputs/part5/citation_consistency_precheck.json", citation_precheck)
    write_text(project_root, "outputs/part5/review_summary.md", review_summary)

    return {
        "review_matrix": review_matrix,
        "claim_risk_report": claim_risk_report,
        "citation_consistency_precheck": citation_precheck,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Integrate Part 5 review fragments")
    parser.add_argument("--project-root", required=True, metavar="PATH")
    args = parser.parse_args()
    integrate_review_fragments(Path(args.project_root).resolve())


if __name__ == "__main__":
    main()
