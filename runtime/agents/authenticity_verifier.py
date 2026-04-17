#!/usr/bin/env python3
"""
runtime/agents/authenticity_verifier.py

对 raw-library/provenance/ 下的来源文件执行 5 项真实性校验。
读取 download_manifest.json，写入 authenticity_report.json 和 excluded_sources_log.json。

用法：
  python3 runtime/agents/authenticity_verifier.py
  python3 runtime/agents/authenticity_verifier.py --source-id cnki_2023_001  # 单篇校验
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
AGENTS_DIR = Path(__file__).parent
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from provenance_store import provenance_complete as provenance_record_complete


# ── 校验函数 ──────────────────────────────────────────────────────────────────

def check_identifier(record: dict) -> tuple[bool, str]:
    """Check 1: CNKI ID 或 DOI 格式合法"""
    id_val = record.get("doi_or_cnki_id", "")
    if not id_val:
        return False, "标识符为空"
    # DOI 格式
    if re.match(r"^10\.\d{4,}/", id_val):
        return True, "DOI 格式合法"
    # CNKI 文章编号（通常是字母+数字组合）
    if re.match(r"^[A-Z0-9_\-]{6,}$", id_val.upper()):
        return True, "CNKI 标识符格式合法"
    # URL 形式的 CNKI 链接
    if "cnki.net" in id_val:
        return True, "CNKI URL 形式标识符"
    return False, f"标识符格式无法识别: {id_val[:50]}"


def check_metadata_consistency(record: dict, intake: dict) -> tuple[bool, str]:
    """Check 2: 元数据内部一致性（年份范围、标题非空）"""
    year = record.get("year")
    time_range = intake.get("time_range", {})

    if not record.get("title"):
        return False, "标题为空"

    if year:
        start = time_range.get("start_year", 0)
        end = time_range.get("end_year", 9999)
        if not (start <= year <= end):
            return False, f"年份 {year} 超出 intake 范围 {start}-{end}"

    # 标题和摘要长度基本合理
    title = record.get("title", "")
    if len(title) < 5:
        return False, f"标题过短（{len(title)} 字），可能不完整"

    return True, "元数据基本一致"


def check_journal(record: dict) -> tuple[bool, str]:
    """Check 3: 期刊名不为空且不明显虚构"""
    journal = record.get("journal", "").strip()
    if not journal:
        return False, "期刊名为空"
    # 期刊名过短（1-2字）很可能有问题
    if len(journal) < 3:
        return False, f"期刊名过短: '{journal}'"
    # 包含明显错误特征
    suspicious = ["未知", "unknown", "N/A", "null", "None"]
    if any(s.lower() in journal.lower() for s in suspicious):
        return False, f"期刊名疑似占位符: '{journal}'"
    return True, f"期刊名: {journal}"


def check_relevance(record: dict, intake: dict) -> tuple[bool, str]:
    """Check 4: 标题/摘要中至少包含 1 个必要关键词"""
    required_kws = intake.get("keywords_required", [])
    suggested_kws = intake.get("keywords_suggested", [])
    all_kws = required_kws + suggested_kws

    text = " ".join([
        record.get("title", ""),
        record.get("abstract", ""),
        " ".join(record.get("keywords", [])),
    ]).lower()

    for kw in required_kws:
        if kw.lower() in text:
            return True, f"包含必要关键词: {kw}"

    # 必要词都没有，检查扩展词
    matched_suggested = [kw for kw in suggested_kws[:5] if kw.lower() in text]
    if matched_suggested:
        return True, f"包含扩展关键词: {', '.join(matched_suggested)}"

    return False, f"标题/摘要中未出现任何相关关键词"


def check_no_duplicate(record: dict, seen: dict) -> tuple[bool, str]:
    """Check 5: 与已处理文献无重复"""
    key = f"{record.get('title', '').strip().lower()}||{record.get('year', '')}"
    if key in seen:
        return False, f"与 {seen[key]} 重复（相同标题+年份）"
    seen[key] = record.get("source_id", "unknown")
    return True, "无重复"


def check_source_landing(record: dict) -> tuple[bool, str]:
    """Source URL or landing evidence exists."""
    url = record.get("url", "")
    if isinstance(url, str) and url.strip():
        return True, "来源 URL 已记录"
    return False, "来源 URL 为空"


def check_local_download(record: dict) -> tuple[bool, str]:
    """Downloaded source artifact exists locally and provenance says success."""
    source_id = record.get("source_id")
    if not source_id:
        return False, "source_id 为空，无法定位本地 artifact"
    if record.get("download_status") != "success":
        return False, f"download_status != success: {record.get('download_status')}"
    if record.get("local_artifact_type") == "markdown":
        local_path = str(record.get("local_path") or "").strip()
        if not local_path:
            return False, "markdown local_path 为空"
        rel_parts = Path(local_path).parts
        if Path(local_path).is_absolute() or ".." in rel_parts:
            return False, f"markdown local_path 非法: {local_path}"
        artifact_path = (PROJECT_ROOT / local_path).resolve()
        if not str(artifact_path).startswith(str(PROJECT_ROOT.resolve())):
            return False, f"markdown local_path 越界: {local_path}"
        if not artifact_path.exists():
            return False, f"本地 Markdown 不存在: {local_path}"
        if artifact_path.stat().st_size == 0:
            return False, f"本地 Markdown 为空: {local_path}"
        return True, "本地 Markdown 已落地"
    pdf_path = PROJECT_ROOT / "raw-library" / "papers" / f"{source_id}.pdf"
    if not pdf_path.exists():
        return False, f"本地 PDF 不存在: raw-library/papers/{source_id}.pdf"
    if pdf_path.stat().st_size == 0:
        return False, f"本地 PDF 为空: raw-library/papers/{source_id}.pdf"
    return True, "本地 PDF 已落地"


def check_provenance_complete(record: dict) -> tuple[bool, str]:
    if provenance_record_complete(record):
        return True, "provenance 必填字段完整"
    return False, "provenance 必填字段不完整"


# ── 主校验逻辑 ────────────────────────────────────────────────────────────────

def verify_source(record: dict, intake: dict, seen_titles: dict) -> dict:
    """对单篇来源执行全部 5 项校验，返回结果 dict"""
    c1_pass, c1_note = check_identifier(record)
    c2_pass, c2_note = check_metadata_consistency(record, intake)
    c3_pass, c3_note = check_journal(record)
    c4_pass, c4_note = check_relevance(record, intake)
    c5_pass, c5_note = check_no_duplicate(record, seen_titles)
    c6_pass, c6_note = check_source_landing(record)
    c7_pass, c7_note = check_local_download(record)
    c8_pass, c8_note = check_provenance_complete(record)

    checks = {
        "identifier_valid": c1_pass,
        "metadata_consistent": c2_pass,
        "journal_verifiable": c3_pass,
        "relevant_to_intake": c4_pass,
        "no_duplicate": c5_pass,
        "identifier_evidence": c1_pass,
        "index_evidence": bool(record.get("db") and record.get("doi_or_cnki_id")),
        "source_landing_evidence": c6_pass,
        "local_download_success": c7_pass,
        "provenance_complete": c8_pass,
    }
    flags = [
        name for name, passed in [
            ("suspicious_id", not c1_pass),
            ("inconsistent_metadata", not c2_pass),
            ("unverified_journal", not c3_pass),
            ("irrelevant", not c4_pass),
            ("duplicate", not c5_pass),
            ("missing_source_landing", not c6_pass),
            ("local_download_missing", not c7_pass),
            ("incomplete_provenance", not c8_pass),
        ]
        if passed
    ]

    # 判断 verdict
    hard_fail = (
        not c1_pass
        or not c2_pass
        or not c4_pass
        or not c5_pass
        or not c6_pass
        or not c7_pass
        or not c8_pass
    )
    if hard_fail:
        verdict = "fail"
    elif not c3_pass:
        verdict = "warning"  # 期刊无法验证但其他项通过，保留但标注
    else:
        verdict = "pass"

    notes_parts = [c1_note, c2_note, c3_note, c4_note, c5_note, c6_note, c7_note, c8_note]
    return {
        "source_id": record.get("source_id"),
        "title": record.get("title", "")[:80],
        "checks": checks,
        "flags": flags,
        "verdict": verdict,
        "notes": "; ".join(notes_parts),
    }


def main():
    parser = argparse.ArgumentParser(description="Verify downloaded sources")
    parser.add_argument("--source-id", help="只校验指定 source_id")
    args = parser.parse_args()

    # 加载 intake
    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    manifest_path = PROJECT_ROOT / "outputs" / "part1" / "download_manifest.json"
    prov_dir = PROJECT_ROOT / "raw-library" / "provenance"

    if not intake_path.exists():
        print("错误: intake.json 不存在", file=sys.stderr)
        sys.exit(1)
    if not manifest_path.exists():
        print("错误: download_manifest.json 不存在，请先运行 CNKI 下载", file=sys.stderr)
        sys.exit(1)

    with open(intake_path, encoding="utf-8") as f:
        intake = json.load(f)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    if manifest.get("dry_run") is True or manifest.get("run_status") in ("failed", "fatal"):
        print("错误: download_manifest.json 不是可验真的成功下载结果", file=sys.stderr)
        sys.exit(1)

    source_ids = [args.source_id] if args.source_id else []
    if not source_ids:
        # 从 provenance 目录收集所有 source_id
        source_ids = [p.stem for p in prov_dir.glob("*.json")] if prov_dir.exists() else []

    if not source_ids:
        print("错误: provenance 目录为空，没有可校验的来源", file=sys.stderr)
        sys.exit(1)

    results = []
    excluded = []
    seen_titles: dict = {}
    now = datetime.now(timezone.utc).isoformat()

    for sid in sorted(source_ids):
        prov_file = prov_dir / f"{sid}.json"
        if not prov_file.exists():
            print(f"  跳过 {sid}：provenance 文件不存在")
            continue
        with open(prov_file, encoding="utf-8") as f:
            record = json.load(f)

        result = verify_source(record, intake, seen_titles)
        results.append(result)

        if result["verdict"] == "fail":
            excluded.append({
                "source_id": sid,
                "reason": result["flags"][0] if result["flags"] else "unknown",
                "details": result["notes"],
                "excluded_at": now,
            })

    passed = [r for r in results if r["verdict"] in ("pass", "warning")]
    failed = [r for r in results if r["verdict"] == "fail"]
    warnings = [r for r in results if r["verdict"] == "warning"]

    # 写 authenticity_report.json
    report = {
        "report_id": f"auth_report_{int(datetime.now(timezone.utc).timestamp())}",
        "created_at": now,
        "based_on_manifest": manifest.get("manifest_id", "unknown"),
        "total_checked": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "warnings": len(warnings),
        "pass_rate": round(len(passed) / len(results) * 100, 1) if results else 0,
        "results": results,
    }
    report_path = PROJECT_ROOT / "outputs" / "part1" / "authenticity_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 写真实性分层排除日志。最终 excluded_sources_log.json 由 registrar 汇总生成。
    excluded_path = PROJECT_ROOT / "outputs" / "part1" / "authenticity_exclusions.json"
    with open(excluded_path, "w", encoding="utf-8") as f:
        json.dump({"excluded": excluded}, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print(f"✓ 真实性校验完成")
    print(f"  检验总数:  {len(results)} 篇")
    print(f"  通过:      {len(passed)} 篇 ({report['pass_rate']}%)")
    print(f"  排除:      {len(failed)} 篇")
    print(f"  警告:      {len(warnings)} 篇（保留但标注）")
    print(f"  报告: {report_path}")

    if report["pass_rate"] < 50 and len(results) > 5:
        print(f"\n  ⚠ 通过率低于 50%，建议检查下载质量后再继续")


if __name__ == "__main__":
    main()
