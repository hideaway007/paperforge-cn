"""
Part 1 source quota policy and validation.

The quota is enforced on canonical accepted sources, not on raw search hits.
This keeps retrieval broad while ensuring the evidence layer that feeds Part 2
matches the user-approved source mix.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEFAULT_SOURCE_QUOTA_POLICY: dict[str, Any] = {
    "target_total": 40,
    "cnki_min_count": 24,
    "cnki_max_count": 28,
    "cnki_target_count": 26,
    "cnki_min_ratio": 0.60,
    "cnki_max_ratio": 0.70,
    "english_journal_min_count": 5,
    "enforced_on": "accepted_sources",
    "notes": (
        "Part 1 final accepted sources must contain exactly 40 sources; "
        "CNKI must be 60%-70% (24-28 sources); English journal sources must be at least 5; "
        "remaining sources come from non-CNKI supplementary databases or user-approved sources."
    ),
}


def default_source_quota_policy() -> dict[str, Any]:
    return dict(DEFAULT_SOURCE_QUOTA_POLICY)


def normalize_quota_policy(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = default_source_quota_policy()
    if policy:
        normalized.update(policy)
    return normalized


def is_cnki_source(source: dict[str, Any]) -> bool:
    return str(source.get("source_name") or "").lower() == "cnki"


def is_english_journal_source(source: dict[str, Any]) -> bool:
    source_name = str(source.get("source_name") or "").lower()
    return (
        source.get("language") == "en"
        and source_name in {"crossref", "openalex", "doaj"}
        and bool(str(source.get("journal") or "").strip())
    )


def source_quota_counts(metadata: dict[str, Any]) -> dict[str, Any]:
    sources = metadata.get("sources", [])
    if not isinstance(sources, list):
        sources = []

    total = len(sources)
    cnki = sum(1 for source in sources if isinstance(source, dict) and is_cnki_source(source))
    english_journal = sum(
        1
        for source in sources
        if isinstance(source, dict) and is_english_journal_source(source)
    )
    other = max(total - cnki - english_journal, 0)
    cnki_ratio = round(cnki / total, 4) if total else 0.0

    return {
        "total": total,
        "cnki": cnki,
        "english_journal": english_journal,
        "other": other,
        "cnki_ratio": cnki_ratio,
    }


def validate_source_quota(
    metadata: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    quota = normalize_quota_policy(policy)
    counts = source_quota_counts(metadata)
    issues: list[str] = []

    target_total = int(quota["target_total"])
    cnki_min = int(quota["cnki_min_count"])
    cnki_max = int(quota["cnki_max_count"])
    english_min = int(quota["english_journal_min_count"])

    if counts["total"] != target_total:
        issues.append(f"Part 1 accepted source 总量必须为 {target_total}，当前为 {counts['total']}")
    if counts["cnki"] < cnki_min or counts["cnki"] > cnki_max:
        issues.append(
            f"CNKI accepted source 必须为 {cnki_min}-{cnki_max} 篇 "
            f"({quota['cnki_min_ratio']:.0%}-{quota['cnki_max_ratio']:.0%})，当前为 {counts['cnki']}"
        )
    if counts["english_journal"] < english_min:
        issues.append(f"英文期刊 accepted source 至少 {english_min} 篇，当前为 {counts['english_journal']}")

    return len(issues) == 0, issues, counts


def build_source_quota_report(
    metadata: dict[str, Any],
    policy: dict[str, Any] | None = None,
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    quota = normalize_quota_policy(policy)
    passed, issues, counts = validate_source_quota(metadata, quota)
    return {
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "policy": quota,
        "counts": counts,
        "passed": passed,
        "issues": issues,
    }
