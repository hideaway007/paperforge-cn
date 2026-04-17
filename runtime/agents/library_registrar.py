#!/usr/bin/env python3
"""
runtime/agents/library_registrar.py

将通过真实性校验的来源写入 canonical artifact: raw-library/metadata.json
并更新各 provenance 文件的注册状态。

用法：
  python3 runtime/agents/library_registrar.py
  python3 runtime/agents/library_registrar.py --dry-run
"""

import json
import shutil
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
AGENTS_DIR = Path(__file__).parent
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from provenance_store import provenance_complete as provenance_record_complete
from runtime.source_quota import build_source_quota_report

SCHEMA_VERSION = "1.0.0"
MIN_RELEVANCE_SCORE = 0.6

TIER1_SOURCES = {"cnki", "wanfang", "vip"}
TIER2_SOURCES = {"crossref", "openalex", "doaj"}
ZH_SOURCES = {"cnki", "wanfang", "vip"}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_relevance_score(value: Any) -> float:
    """Normalize scorer output to the schema range 0.0-1.0."""
    if value is None:
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 1:
        score = score / 100
    return max(0.0, min(round(score, 4), 1.0))


def source_tier_for(source_name: str) -> str:
    source = (source_name or "unknown").lower()
    if source in TIER1_SOURCES:
        return "tier1_chinese_primary"
    if source in TIER2_SOURCES:
        return "tier2_english_supplement"
    return "tier3_supplementary"


def language_for(source_name: str) -> str:
    source = (source_name or "unknown").lower()
    if source in ZH_SOURCES:
        return "zh"
    if source in TIER2_SOURCES:
        return "en"
    return "other"


def doi_from_identifier(identifier: str) -> str | None:
    if isinstance(identifier, str) and identifier.startswith("10."):
        return identifier
    return None


def provenance_complete(record: dict) -> bool:
    return provenance_record_complete(record)


def local_download_success(record: dict) -> bool:
    if "local_download_success" in record:
        return bool(record["local_download_success"])
    return record.get("download_status") == "success"


def local_artifact_rel_path(record: dict, source_id: str) -> str:
    local_path = str(record.get("local_path") or "").strip()
    if local_path:
        path = Path(local_path)
        if not path.is_absolute() and ".." not in path.parts:
            return path.as_posix()
    return f"raw-library/papers/{source_id}.pdf"


def local_artifact_exists(project_root: Path, record: dict, source_id: str) -> bool:
    rel_path = local_artifact_rel_path(record, source_id)
    path = (project_root / rel_path).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError:
        return False
    return path.exists() and path.stat().st_size > 0


def build_authenticity_checks(result: dict, record: dict) -> dict:
    checks = result.get("checks", {})
    local_success = local_download_success(record)

    return {
        "identifier_evidence": bool(checks.get("identifier_evidence", checks.get("identifier_valid"))),
        "index_evidence": bool(checks.get("index_evidence", record.get("db") and record.get("doi_or_cnki_id"))),
        "source_landing_evidence": bool(checks.get("source_landing_evidence", record.get("url"))),
        "local_download_success": bool(checks.get("local_download_success", local_success)),
        "provenance_complete": bool(checks.get("provenance_complete", provenance_complete(record))),
    }


def build_source_record(result: dict, record: dict, generated_at: str) -> dict:
    source_id = result["source_id"]
    source_name = record.get("db", "unknown")
    relevance_score = normalize_relevance_score(record.get("relevance_score"))
    local_path = local_artifact_rel_path(record, source_id)

    source = {
        "source_id": source_id,
        "title": record.get("title", ""),
        "authors": record.get("authors", []),
        "year": record.get("year"),
        "journal": record.get("journal", ""),
        "doi": doi_from_identifier(record.get("doi_or_cnki_id", "")),
        "cnki_or_source_id": record.get("doi_or_cnki_id", ""),
        "url": record.get("url", ""),
        "abstract": record.get("abstract", ""),
        "keywords": record.get("keywords", []),
        "source_tier": source_tier_for(source_name),
        "source_name": source_name,
        "language": language_for(source_name),
        "authenticity_status": "verified",
        "authenticity_verdict": result.get("verdict"),
        "authenticity_flags": result.get("flags", []),
        "authenticity_checks": build_authenticity_checks(result, record),
        "relevance_score": relevance_score,
        "relevance_tier": record.get("relevance_tier"),
        "local_path": local_path,
        "normalized_path": record.get("normalized_path"),
        "provenance_path": f"raw-library/provenance/{source_id}.json",
        "added_at": generated_at,
    }
    if record.get("local_artifact_type") is not None:
        source["local_artifact_type"] = record["local_artifact_type"]
    if record.get("relevance_dimensions") is not None:
        source["relevance_dimensions"] = record["relevance_dimensions"]
    return source


def is_canonical_source(result: dict, record: dict | None) -> bool:
    if record is None:
        return False
    if result.get("verdict") not in ("pass", "warning"):
        return False
    if not local_download_success(record):
        return False
    if not provenance_complete(record):
        return False
    return normalize_relevance_score(record.get("relevance_score")) >= MIN_RELEVANCE_SCORE


def manifest_failed_download_count(download_manifest: dict | None, result_ids: set[str]) -> int:
    if not download_manifest:
        return 0
    return sum(
        1
        for item in download_manifest.get("failed_downloads", [])
        if item.get("source_id") not in result_ids
    )


def build_metadata(
    report: dict,
    intake: dict,
    records_by_id: dict[str, dict],
    generated_at: str,
    download_manifest: dict | None = None,
) -> dict:
    results = report.get("results", [])
    result_ids = {r.get("source_id") for r in results}
    canonical_sources = [
        build_source_record(result, records_by_id[result["source_id"]], generated_at)
        for result in results
        if is_canonical_source(result, records_by_id.get(result.get("source_id")))
    ]

    tier_counts = {
        "tier1_count": sum(1 for source in canonical_sources if source["source_tier"] == "tier1_chinese_primary"),
        "tier2_count": sum(1 for source in canonical_sources if source["source_tier"] == "tier2_english_supplement"),
        "tier3_count": sum(1 for source in canonical_sources if source["source_tier"] == "tier3_supplementary"),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "intake_ref": intake.get("intake_id", "unknown"),
        "search_plan_ref": "outputs/part1/search_plan.json",
        "sources": canonical_sources,
        "summary": {
            "total_accepted": len(canonical_sources),
            "total_excluded": (
                max(len(results) - len(canonical_sources), 0)
                + manifest_failed_download_count(download_manifest, result_ids)
            ),
            **tier_counts,
        },
    }


def exclusion_reason_for(result: dict, record: dict | None) -> str:
    if record is None:
        return "missing_provenance"
    if not local_download_success(record) or record.get("download_status") != "success":
        return "download_failed"
    if not provenance_complete(record):
        return "provenance_incomplete"
    if result.get("verdict") not in ("pass", "warning"):
        return result.get("flags", ["authenticity_failed"])[0]
    if normalize_relevance_score(record.get("relevance_score")) < MIN_RELEVANCE_SCORE:
        return "relevance_score_below_0.6"
    return "not_canonical"


def build_final_excluded_log(
    report: dict,
    records_by_id: dict[str, dict],
    generated_at: str,
    download_manifest: dict | None = None,
) -> dict:
    excluded = []
    seen_source_ids = set()
    for result in report.get("results", []):
        source_id = result.get("source_id", "unknown")
        seen_source_ids.add(source_id)
        record = records_by_id.get(source_id)
        if is_canonical_source(result, record):
            continue

        excluded.append({
            "source_id": source_id,
            "reason": exclusion_reason_for(result, record),
            "authenticity_verdict": result.get("verdict"),
            "relevance_score": normalize_relevance_score(record.get("relevance_score")) if record else 0.0,
            "details": result.get("notes", ""),
            "excluded_at": generated_at,
        })

    if download_manifest:
        for item in download_manifest.get("failed_downloads", []):
            source_id = item.get("source_id", "unknown")
            if source_id in seen_source_ids:
                continue
            excluded.append({
                "source_id": source_id,
                "reason": "download_failed",
                "authenticity_verdict": None,
                "relevance_score": 0.0,
                "details": item.get("reason", ""),
                "excluded_at": generated_at,
            })

    return {
        "created_at": generated_at,
        "minimum_relevance_score": MIN_RELEVANCE_SCORE,
        "total_excluded": len(excluded),
        "excluded": excluded,
    }


def build_no_canonical_source_feedback(
    report: dict,
    records_by_id: dict[str, dict],
    excluded_log: dict,
) -> list[str]:
    results = report.get("results", [])
    total_checked = len(results)
    authenticity_passed = sum(
        1
        for result in results
        if result.get("verdict") in ("pass", "warning")
    )
    downloaded = sum(
        1
        for result in results
        if local_download_success(records_by_id.get(result.get("source_id"), {}))
    )
    complete = sum(
        1
        for result in results
        if provenance_complete(records_by_id.get(result.get("source_id"), {}))
    )

    scored = []
    for result in results:
        source_id = result.get("source_id", "unknown")
        record = records_by_id.get(source_id)
        if not record:
            continue
        scored.append((
            normalize_relevance_score(record.get("relevance_score")),
            source_id,
            record,
            result,
        ))
    scored.sort(key=lambda item: item[0], reverse=True)

    reason_counts: dict[str, int] = {}
    for entry in excluded_log.get("excluded", []):
        reason = entry.get("reason") or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    lines = [
        "错误: 没有来源同时满足入库条件：真实性通过、下载成功、provenance 完整、相关性 >= 0.6。",
        (
            "诊断: "
            f"authenticity 通过/警告 {authenticity_passed}/{total_checked}；"
            f"下载成功 {downloaded}/{total_checked}；"
            f"provenance 完整 {complete}/{total_checked}。"
        ),
    ]

    if scored:
        top_lines = []
        for score, source_id, record, result in scored[:3]:
            title = record.get("title") or result.get("title") or "无题名"
            top_lines.append(
                f"{source_id} score={score:.2f} tier={record.get('relevance_tier') or 'unknown'} title={title}"
            )
        lines.append("最高相关性: " + "；".join(top_lines))
    else:
        lines.append("最高相关性: 未找到可评分的 provenance 记录。")

    if reason_counts:
        reason_summary = "；".join(
            f"{reason}={count}"
            for reason, count in sorted(reason_counts.items())
        )
        lines.append(f"排除原因: {reason_summary}")

    lines.append(
        "下一步: 正式运行请扩大下载数量后从 Step 3/4 续跑，或调整 intake / 检索词后重新从 Step 1 开始；"
        "如果只是自动衔接测试，可以保留当前 workspace 的中止状态。"
    )
    lines.append("保护: 系统不会把 tier_B 或低相关来源降级写入 raw-library/metadata.json。")
    return lines


def load_records_by_id(prov_dir: Path, results: list[dict]) -> dict[str, dict]:
    records_by_id = {}
    for result in results:
        source_id = result.get("source_id")
        if not source_id:
            continue
        prov_file = prov_dir / f"{source_id}.json"
        if not prov_file.exists():
            print(f"  警告: {source_id} 的 provenance 文件不存在，跳过")
            continue
        record = load_json(prov_file)
        normalized_path = PROJECT_ROOT / "raw-library" / "normalized" / f"{source_id}.txt"
        records_by_id[source_id] = {
            **record,
            "local_download_success": (
                record.get("download_status") == "success"
                and local_artifact_exists(PROJECT_ROOT, record, source_id)
            ),
            "normalized_path": (
                f"raw-library/normalized/{source_id}.txt"
                if normalized_path.exists()
                else None
            ),
        }
    return records_by_id


def main():
    parser = argparse.ArgumentParser(description="Register verified sources to raw-library")
    parser.add_argument("--dry-run", action="store_true", help="打印将写入的内容但不实际写文件")
    args = parser.parse_args()

    report_path = PROJECT_ROOT / "outputs" / "part1" / "authenticity_report.json"
    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    manifest_path = PROJECT_ROOT / "outputs" / "part1" / "download_manifest.json"
    prov_dir = PROJECT_ROOT / "raw-library" / "provenance"
    metadata_path = PROJECT_ROOT / "raw-library" / "metadata.json"
    excluded_path = PROJECT_ROOT / "outputs" / "part1" / "excluded_sources_log.json"
    quota_report_path = PROJECT_ROOT / "outputs" / "part1" / "source_quota_report.json"

    for p in [report_path, intake_path, manifest_path]:
        if not p.exists():
            print(f"错误: {p.name} 不存在", file=sys.stderr)
            sys.exit(1)

    report = load_json(report_path)
    intake = load_json(intake_path)
    download_manifest = load_json(manifest_path)

    if report["passed"] == 0:
        print("错误: authenticity_report.json 中没有通过校验的来源，无法注册", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()
    metadata_id = f"raw_library_metadata_{int(datetime.now(timezone.utc).timestamp())}"
    records_by_id = load_records_by_id(prov_dir, report.get("results", []))
    metadata = build_metadata(report, intake, records_by_id, now, download_manifest=download_manifest)
    metadata["metadata_id"] = metadata_id
    metadata["last_updated"] = now
    excluded_log = build_final_excluded_log(report, records_by_id, now, download_manifest=download_manifest)
    quota_report = build_source_quota_report(metadata, created_at=now)

    if metadata["summary"]["total_accepted"] == 0:
        for line in build_no_canonical_source_feedback(report, records_by_id, excluded_log):
            print(line, file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] 将写入 {metadata['summary']['total_accepted']} 条来源到 raw-library/metadata.json")
        print(f"[DRY RUN] source quota passed: {quota_report['passed']}")
        for issue in quota_report["issues"]:
            print(f"  - {issue}")
        print(json.dumps(metadata, ensure_ascii=False, indent=2)[:500] + "...")
        return

    quota_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(quota_report_path, "w", encoding="utf-8") as f:
        json.dump(quota_report, f, ensure_ascii=False, indent=2)
    if not quota_report["passed"]:
        print("错误: Part 1 source quota 未满足，不能写入 canonical raw-library/metadata.json", file=sys.stderr)
        for issue in quota_report["issues"]:
            print(f"  - {issue}", file=sys.stderr)
        print(f"  已写入配额报告: {quota_report_path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        sys.exit(1)

    # 备份已有的 metadata.json
    if metadata_path.exists():
        bak = metadata_path.with_suffix(f".json.bak_{int(datetime.now(timezone.utc).timestamp())}")
        shutil.copy2(metadata_path, bak)
        print(f"  已备份旧 metadata.json → {bak.name}")

    # 写 metadata.json
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    with open(excluded_path, "w", encoding="utf-8") as f:
        json.dump(excluded_log, f, ensure_ascii=False, indent=2)

    # 更新各 provenance 文件。重跑时必须清除旧的注册状态，避免已排除来源
    # 因历史 metadata_id 残留而被 Part 2 误用。
    accepted_ids = {source["source_id"] for source in metadata["sources"]}
    updated_count = 0
    for source_id in records_by_id:
        pf = prov_dir / f"{source_id}.json"
        if pf.exists():
            record = load_json(pf)
            if source_id in accepted_ids:
                record["registered_to_library"] = True
                record["registration_status"] = "accepted"
                record["registered_at"] = now
                record["metadata_id"] = metadata_id
            else:
                record["registered_to_library"] = False
                record["registration_status"] = "excluded"
                record["registration_checked_at"] = now
                record.pop("registered_at", None)
                record.pop("metadata_id", None)
            with open(pf, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            updated_count += 1

    print(f"✓ 来源注册完成")
    print(f"  写入: raw-library/metadata.json ({metadata['summary']['total_accepted']} 条来源)")
    print(f"  写入: outputs/part1/source_quota_report.json (passed={quota_report['passed']})")
    print(f"  更新: outputs/part1/excluded_sources_log.json ({excluded_log['total_excluded']} 条排除记录)")
    print(f"  更新 provenance 文件: {updated_count} 个")
    print(f"  metadata_id: {metadata_id}")


if __name__ == "__main__":
    main()
