#!/usr/bin/env python3
"""
runtime/agents/relevance_scorer.py

对 raw-library/provenance/ 下的每篇文献做相关性评分（0-100），
生成 relevance_scores.json、accepted_sources.json、relevance_exclusions.json，
并在每个 provenance JSON 中追加 relevance_score / relevance_tier 字段。

用法：
  python3 runtime/agents/relevance_scorer.py
  python3 runtime/agents/relevance_scorer.py --min-tier A   # 只保留 tier_A（默认，符合 source-policy >=0.6）
  python3 runtime/agents/relevance_scorer.py --min-tier B   # 保留 tier_A + tier_B
  python3 runtime/agents/relevance_scorer.py --dry-run      # 只打印统计，不写文件
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# 研究范围与评分权重。分值仍输出为 0-100，但各维度先归一化到 0-1，
# 便于后续 metadata.json 按 schema 写入 0-1 的 relevance_score。
TIME_RANGE_START = 2005
TIME_RANGE_END = 2025

DIMENSION_WEIGHTS = {
    "topic_consistency": 30,
    "research_question_match": 20,
    "title_abstract_keyword_hit": 10,
    "method_sample_object_match": 15,
    "time_range_fit": 10,
    "chinese_writing_usability": 10,
    "source_credibility": 5,
}


def score_source(record: dict, intake: dict) -> dict:
    """
    对单篇文献打分，返回评分明细 dict。

    record 字段参考 authenticity_verifier.py 中的使用方式：
      title, abstract, keywords (list), year
    """
    required_kws: list[str] = _as_list(intake.get("keywords_required", []))
    suggested_kws: list[str] = _as_list(intake.get("keywords_suggested", []))

    title: str = record.get("title", "")
    abstract: str = record.get("abstract", "")
    kw_field: list[str] = record.get("keywords", [])
    year = record.get("year")

    title_lower = title.lower()
    abstract_lower = abstract.lower()
    kw_field_text = " ".join(kw_field).lower()
    combined = f"{title_lower} {abstract_lower} {kw_field_text}"

    matched_required = _matched_terms(required_kws, combined)
    matched_suggested = _matched_terms(suggested_kws, combined)

    return _score_intake_driven_source(
        record=record,
        intake=intake,
        title=title_lower,
        combined=combined,
        matched_required=matched_required,
        matched_suggested=matched_suggested,
    )


def _matched_terms(terms: list[str], text: str) -> list[str]:
    return [term for term in terms if term.lower() in text]


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.replace("；", ";").replace("、", ";").split(";") if part.strip()]
    return []


def _score_intake_driven_source(
    record: dict,
    intake: dict,
    title: str,
    combined: str,
    matched_required: list[str],
    matched_suggested: list[str],
) -> dict:
    profile = _build_intake_anchor_profile(intake)

    matched_object_terms = _matched_terms(profile["object_terms"], combined)
    matched_context_terms = [
        term for term in _matched_terms(profile["context_terms"], combined)
        if term not in matched_object_terms
    ]
    matched_application_terms = _matched_terms(profile["application_terms"], combined)
    matched_exclusion_terms = _matched_terms(profile["exclusion_terms"], combined)
    matched_domain_terms = _matched_terms(profile["domain_required_terms"], combined)

    has_object_anchor = bool(matched_object_terms)
    has_context_anchor = bool(matched_context_terms)
    has_application_anchor = bool(matched_application_terms)
    has_exclusion_anchor = bool(matched_exclusion_terms)
    has_domain_requirement = bool(profile["domain_required_terms"])
    has_domain_anchor = not has_domain_requirement or bool(matched_domain_terms)
    qualifies_for_tier_a = has_object_anchor and has_context_anchor and has_domain_anchor

    dimensions = {
        "topic_consistency": _intake_topic_consistency(has_object_anchor, has_context_anchor),
        "research_question_match": _intake_research_question_match(
            has_object_anchor,
            has_context_anchor,
            has_application_anchor,
        ),
        "title_abstract_keyword_hit": _keyword_hit_score(
            title,
            combined,
            matched_required + matched_object_terms[:2],
            matched_suggested + matched_context_terms[:2] + matched_application_terms[:2],
        ),
        "method_sample_object_match": _intake_method_sample_score(
            has_object_anchor,
            has_context_anchor,
            has_application_anchor,
        ),
        "time_range_fit": _time_range_fit(record.get("year"), intake),
        "chinese_writing_usability": _writing_usability_score(record),
        "source_credibility": 1.0 if record.get("db", "cnki") in ("cnki", "wanfang", "vip") else 0.6,
    }

    total = sum(dimensions[key] * weight for key, weight in DIMENSION_WEIGHTS.items())

    downgrade_reasons = []
    if has_exclusion_anchor and not (has_object_anchor and has_context_anchor):
        total *= 0.55
        downgrade_reasons.append("命中排除范围，且缺少当前 intake 的研究对象 + 问题场景双锚点")
    if has_domain_requirement and not matched_domain_terms:
        downgrade_reasons.append("不满足当前 intake 的地域/对象硬锚点，不能进入 tier_A")
    if not qualifies_for_tier_a and total >= 60:
        total = 59
        downgrade_reasons.append("不满足当前 intake 的 tier_A 双锚点规则，分数封顶至 tier_B")

    total = round(max(0, min(total, 100)))
    if total >= 60:
        tier = "tier_A"
    elif total >= 30:
        tier = "tier_B"
    else:
        tier = "tier_C"

    return {
        "source_id": record.get("source_id", "unknown"),
        "score": total,
        "tier": tier,
        "matched_required": matched_required,
        "matched_suggested": matched_suggested,
        "breakdown": {
            key: round(dimensions[key] * weight, 2)
            for key, weight in DIMENSION_WEIGHTS.items()
        },
        "dimensions": dimensions,
        "matched_research_anchors": {
            "has_intake_object_anchor": has_object_anchor,
            "has_intake_context_anchor": has_context_anchor,
            "has_intake_application_anchor": has_application_anchor,
            "has_intake_exclusion_anchor": has_exclusion_anchor,
            "has_intake_domain_anchor": has_domain_anchor,
            "matched_intake_object_terms": matched_object_terms,
            "matched_intake_context_terms": matched_context_terms,
            "matched_intake_application_terms": matched_application_terms,
            "matched_intake_domain_terms": matched_domain_terms,
            "matched_exclusion_terms": matched_exclusion_terms,
            "qualifies_for_tier_A": qualifies_for_tier_a,
        },
        "downgrade_reasons": downgrade_reasons,
    }


def _build_intake_anchor_profile(intake: dict) -> dict[str, list[str]]:
    required = _as_list(intake.get("keywords_required", []))
    suggested = _as_list(intake.get("keywords_suggested", []))
    discipline_fields = _as_list(intake.get("discipline_fields", []))
    expected_types = _as_list(intake.get("expected_research_types", []))
    topic = str(intake.get("research_topic", ""))
    question = str(intake.get("research_question", ""))
    scope_text = str(intake.get("scope_notes", ""))

    all_terms = _unique_terms(required + suggested + discipline_fields + expected_types)
    anchor_text = " ".join([topic, question, scope_text, " ".join(all_terms)])
    object_terms = [
        term
        for term in all_terms
        if _contains_any(
            term,
            [
                "建筑", "民居", "院落", "街区", "老城", "古城", "住房", "房子",
                "空间", "风貌", "遗产", "社区", "历史建筑", "传统建筑", "建筑文化",
                "建筑元素", "建筑装饰", "建筑美学",
            ],
        )
    ]
    context_terms = [
        term
        for term in all_terms
        if _contains_any(
            term,
            [
                "保护", "更新", "改造", "居住", "品质", "好房子", "居民", "政策",
                "财政", "产权", "基础设施", "市政", "入户", "治理", "实施",
                "高校", "教育", "教学", "课程", "美术", "艺术", "审美",
                "现代", "现代性", "现代化", "现代主义", "国际风格", "全球化",
                "地域", "地域性", "本土", "本土化", "气候", "环境", "理性",
                "传统", "学派", "两观三性", "开放多元", "传承创新",
            ],
        )
    ]
    application_terms = [
        term
        for term in all_terms
        if _contains_any(
            term,
            [
                "微改造", "节能", "成套化", "厨房", "卫生间", "基础设施", "市政",
                "居民意愿", "产权", "财政", "专项资金", "补助", "支持", "机制",
                "挖掘", "提炼", "应用", "融合", "实践", "创作", "转化", "传承",
                "活化", "媒介", "路径", "适应", "批判", "建构", "体系", "团队",
            ],
        )
    ]

    if _contains_any(question, ["审美素养"]):
        context_terms.append("审美素养")
    if _contains_any(question, ["创作能力"]):
        application_terms.append("创作能力")
    if _contains_any(question, ["传统文化理解"]):
        application_terms.append("传统文化理解")
    if _contains_any(anchor_text, ["挖掘"]):
        application_terms.append("挖掘")

    if _contains_any(anchor_text, ["现代性", "现代化", "全球化", "地域性", "本土化"]):
        context_terms.extend(["现代性", "现代化", "全球化", "地域性", "本土化", "现代主义", "国际风格"])

    if _contains_any(anchor_text, ["气候", "环境适应"]):
        context_terms.extend(["气候环境", "气候", "环境适应"])
        application_terms.extend(["气候环境适应", "地域适应"])

    object_terms.extend(_derived_anchor_variants(object_terms))
    context_terms.extend(_derived_anchor_variants(context_terms))
    application_terms.extend(_derived_anchor_variants(application_terms))

    exclusions = _as_list(intake.get("exclusions", [])) + _as_list(intake.get("exclusion_rules", []))
    exclusion_terms = exclusions + _derived_anchor_variants(exclusions)

    return {
        "object_terms": _unique_terms(object_terms),
        "context_terms": _unique_terms(context_terms),
        "application_terms": _unique_terms(application_terms),
        "domain_required_terms": [],
        "exclusion_terms": _unique_terms(exclusion_terms),
    }


def _derived_anchor_variants(terms: list[str]) -> list[str]:
    variants: list[str] = []
    for term in terms:
        if "保护更新" in term:
            variants.append(term.replace("保护更新", "保护与更新"))
        if "居住品质提升" in term:
            variants.extend(["居住品质", "居住条件", "改善居住条件"])
        if "历史文化街区" in term:
            variants.append("历史文化街区")
        if "市政基础设施入户" in term:
            variants.extend(["市政基础设施", "基础设施入户"])
        if "独立厨房卫生间" in term:
            variants.extend(["厨房卫生间", "厨房", "卫生间"])
        if "教育" in term and "美术" in term:
            variants.append(term.replace("高校", ""))
        if "建筑元素" in term:
            variants.append(term.replace("中国", ""))
        if "历史建筑" in term and "元素" in term:
            variants.append(term.replace("元素", ""))
        if "保护工程" in term:
            variants.append("保护工程")
        if "建筑史" in term:
            variants.append("建筑史")
        if term.startswith("纯") and len(term) > 1:
            variants.append(term[1:])
    return variants


def _intake_topic_consistency(has_object_anchor: bool, has_context_anchor: bool) -> float:
    if has_object_anchor and has_context_anchor:
        return 1.0
    if has_object_anchor or has_context_anchor:
        return 0.3
    return 0.0


def _intake_research_question_match(
    has_object_anchor: bool,
    has_context_anchor: bool,
    has_application_anchor: bool,
) -> float:
    if has_object_anchor and has_context_anchor and has_application_anchor:
        return 1.0
    if has_object_anchor and has_context_anchor:
        return 0.8
    if has_application_anchor and (has_object_anchor or has_context_anchor):
        return 0.35
    return 0.0


def _intake_method_sample_score(
    has_object_anchor: bool,
    has_context_anchor: bool,
    has_application_anchor: bool,
) -> float:
    if has_object_anchor and has_context_anchor and has_application_anchor:
        return 0.85
    if has_object_anchor and has_context_anchor:
        return 0.65
    if has_application_anchor and (has_object_anchor or has_context_anchor):
        return 0.25
    return 0.0


def _time_range_fit(year, intake: dict) -> float:
    time_range = intake.get("time_range", {})
    if isinstance(time_range, dict):
        start = int(time_range.get("start_year", TIME_RANGE_START))
        end = int(time_range.get("end_year", TIME_RANGE_END))
    else:
        start = TIME_RANGE_START
        end = TIME_RANGE_END
    return 1.0 if isinstance(year, int) and start <= year <= end else 0.0


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _unique_terms(terms: list[str]) -> list[str]:
    seen = set()
    unique = []
    for term in terms:
        normalized = str(term).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def infer_keywords_for_provenance(record: dict, score_result: dict) -> list[str]:
    """Infer a small keyword list when CNKI metadata leaves keywords empty."""
    if record.get("keywords"):
        return list(record.get("keywords", []))

    anchors = score_result.get("matched_research_anchors", {})
    candidates = (
        score_result.get("matched_required", [])
        + score_result.get("matched_suggested", [])
        + anchors.get("matched_intake_object_terms", [])
        + anchors.get("matched_intake_context_terms", [])
        + anchors.get("matched_intake_application_terms", [])
    )
    return _unique_terms(candidates)[:8]


def _keyword_hit_score(
    title: str,
    text: str,
    matched_required: list[str],
    matched_suggested: list[str],
) -> float:
    title_hits = [term for term in matched_required if term.lower() in title]
    score = 0.0
    if matched_required:
        score += min(len(matched_required) * 0.25, 0.55)
    if title_hits:
        score += min(len(title_hits) * 0.2, 0.3)
    if matched_suggested:
        score += min(len(matched_suggested) * 0.15, 0.3)
    return min(score, 1.0)


def _writing_usability_score(record: dict) -> float:
    score = 0.0
    if record.get("journal"):
        score += 0.3
    if len(record.get("abstract", "")) >= 80:
        score += 0.4
    if record.get("authors"):
        score += 0.2
    if record.get("keywords"):
        score += 0.1
    return min(score, 1.0)


def tier_rank(tier: str) -> int:
    """A=0（最高），B=1，C=2，用于比较。"""
    return {"tier_A": 0, "tier_B": 1, "tier_C": 2}.get(tier, 9)


def main():
    parser = argparse.ArgumentParser(description="Score relevance of provenance sources")
    parser.add_argument(
        "--min-tier",
        choices=["A", "B"],
        default="A",
        help="最低保留层级（A=只保留 tier_A，默认；B=保留 tier_A + tier_B）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印统计，不写入任何文件",
    )
    args = parser.parse_args()

    # 解析 min_tier
    min_tier = f"tier_{args.min_tier}"  # "tier_A" or "tier_B"

    # ── 路径 ────────────────────────────────────────────────────────────────────
    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    prov_dir = PROJECT_ROOT / "raw-library" / "provenance"
    out_dir = PROJECT_ROOT / "outputs" / "part1"

    # ── 加载 intake ─────────────────────────────────────────────────────────────
    if not intake_path.exists():
        print("错误: intake.json 不存在，请先完成 Part 1 intake 步骤", file=sys.stderr)
        sys.exit(1)

    with open(intake_path, encoding="utf-8") as f:
        intake = json.load(f)

    intake_id: str = intake.get("intake_id", "unknown")

    # ── 收集 provenance 文件 ────────────────────────────────────────────────────
    prov_files = sorted(prov_dir.glob("*.json")) if prov_dir.exists() else []

    if not prov_files:
        print("提示: provenance 目录为空，没有可评分的来源")
        print("  请先执行文献下载步骤，将 provenance JSON 写入 raw-library/provenance/")
        if not args.dry_run:
            # 仍然写出空的结果文件，保持 pipeline 可继续
            now = datetime.now(timezone.utc).isoformat()
            _write_empty_outputs(out_dir, intake_id, now)
            print("  已写出空结果文件（relevance_scores.json / accepted_sources.json）")
        sys.exit(0)

    # ── 逐篇评分 ────────────────────────────────────────────────────────────────
    scores: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    for prov_file in prov_files:
        with open(prov_file, encoding="utf-8") as f:
            record = json.load(f)

        result = score_source(record, intake)
        scores.append(result)

        # 写回 provenance（追加两个字段，不覆盖其他字段），dry-run 跳过
        if not args.dry_run:
            inferred_keywords = infer_keywords_for_provenance(record, result)
            if inferred_keywords and not record.get("keywords"):
                record["keywords"] = inferred_keywords
                record["keywords_inferred"] = True
                record["keywords_inferred_from"] = "title_abstract_intake_anchor_match"
            record["relevance_score"] = result["score"]
            record["relevance_tier"] = result["tier"]
            record["relevance_dimensions"] = result["dimensions"]
            record["relevance"] = {
                "score": round(result["score"] / 100, 4),
                "tier": result["tier"],
                "scored_at": now,
            }
            record["relevance_matched_anchors"] = result.get("matched_research_anchors", {})
            record["relevance_downgrade_reasons"] = result.get("downgrade_reasons", [])
            with open(prov_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

    # ── 汇总统计 ────────────────────────────────────────────────────────────────
    tier_a = [s for s in scores if s["tier"] == "tier_A"]
    tier_b = [s for s in scores if s["tier"] == "tier_B"]
    tier_c = [s for s in scores if s["tier"] == "tier_C"]

    # accepted: 满足 min_tier 的文献
    accepted = [s for s in scores if tier_rank(s["tier"]) <= tier_rank(min_tier)]
    excluded = [s for s in scores if tier_rank(s["tier"]) > tier_rank(min_tier)]

    # ── 打印摘要 ─────────────────────────────────────────────────────────────────
    print(f"相关性评分完成（intake: {intake_id}）")
    print(f"  评分总数: {len(scores)} 篇")
    print(f"  tier_A (>=60):  {len(tier_a)} 篇")
    print(f"  tier_B (30-59): {len(tier_b)} 篇")
    print(f"  tier_C (<30):   {len(tier_c)} 篇")
    print(f"  最低保留层级: {min_tier}  → 保留 {len(accepted)} 篇，排除 {len(excluded)} 篇")

    if args.dry_run:
        print("  [dry-run] 未写入任何文件")
        _print_top_scores(scores, n=10)
        return

    # ── 写 relevance_scores.json ─────────────────────────────────────────────────
    relevance_scores_doc = {
        "scored_at": now,
        "intake_id": intake_id,
        "total_scored": len(scores),
        "tier_A": len(tier_a),
        "tier_B": len(tier_b),
        "tier_C": len(tier_c),
        "scores": sorted(scores, key=lambda s: s["score"], reverse=True),
    }
    relevance_path = out_dir / "relevance_scores.json"
    with open(relevance_path, "w", encoding="utf-8") as f:
        json.dump(relevance_scores_doc, f, ensure_ascii=False, indent=2)

    # ── 写 accepted_sources.json ─────────────────────────────────────────────────
    accepted_doc = {
        "created_at": now,
        "intake_id": intake_id,
        "min_tier": min_tier,
        "total": len(accepted),
        "source_ids": [s["source_id"] for s in sorted(accepted, key=lambda s: s["score"], reverse=True)],
    }
    accepted_path = out_dir / "accepted_sources.json"
    with open(accepted_path, "w", encoding="utf-8") as f:
        json.dump(accepted_doc, f, ensure_ascii=False, indent=2)

    # ── 写 relevance_exclusions.json ─────────────────────────────────────────────
    excluded_log = {
        "created_at": now,
        "intake_id": intake_id,
        "min_tier": min_tier,
        "total_excluded": len(excluded),
        "excluded": [
            {
                "source_id": s["source_id"],
                "score": s["score"],
                "tier": s["tier"],
                "reason": f"低于最低保留层级 {min_tier}",
                "breakdown": s["breakdown"],
                "matched_research_anchors": s.get("matched_research_anchors", {}),
                "downgrade_reasons": s.get("downgrade_reasons", []),
                "excluded_at": now,
            }
            for s in sorted(excluded, key=lambda s: s["score"], reverse=True)
        ],
    }
    excluded_path = out_dir / "relevance_exclusions.json"
    with open(excluded_path, "w", encoding="utf-8") as f:
        json.dump(excluded_log, f, ensure_ascii=False, indent=2)

    print(f"  输出文件:")
    print(f"    {relevance_path}")
    print(f"    {accepted_path}")
    print(f"    {excluded_path}")
    print(f"  provenance 文件已追加 relevance_score / relevance_tier 字段")

    _print_top_scores(scores, n=5)


def _print_top_scores(scores: list[dict], n: int = 5) -> None:
    """打印得分最高的前 n 篇，便于快速预览。"""
    if not scores:
        return
    top = sorted(scores, key=lambda s: s["score"], reverse=True)[:n]
    print(f"\n  得分最高 {len(top)} 篇:")
    for s in top:
        print(f"    [{s['tier']}] {s['score']:>3}分  {s['source_id']}")


def _write_empty_outputs(out_dir: Path, intake_id: str, now: str) -> None:
    """provenance 为空时写出合法的空结果文件，保持下游 pipeline 可读。"""
    empty_scores = {
        "scored_at": now,
        "intake_id": intake_id,
        "total_scored": 0,
        "tier_A": 0,
        "tier_B": 0,
        "tier_C": 0,
        "scores": [],
    }
    with open(out_dir / "relevance_scores.json", "w", encoding="utf-8") as f:
        json.dump(empty_scores, f, ensure_ascii=False, indent=2)

    empty_accepted = {
        "created_at": now,
        "intake_id": intake_id,
        "min_tier": "tier_A",
        "total": 0,
        "source_ids": [],
    }
    with open(out_dir / "accepted_sources.json", "w", encoding="utf-8") as f:
        json.dump(empty_accepted, f, ensure_ascii=False, indent=2)

    empty_excluded = {
        "created_at": now,
        "intake_id": intake_id,
        "min_tier": "tier_A",
        "total_excluded": 0,
        "excluded": [],
    }
    with open(out_dir / "relevance_exclusions.json", "w", encoding="utf-8") as f:
        json.dump(empty_excluded, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
