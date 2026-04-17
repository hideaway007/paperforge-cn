#!/usr/bin/env python3
"""
runtime/agents/search_planner.py

从已确认的 intake.json 生成结构化检索计划 (search_plan.json)。
可独立运行，也可被 part1_agent.py 调用。

用法：
  python3 runtime/agents/search_planner.py
  python3 runtime/agents/search_planner.py --dry-run  # 打印计划但不写文件
"""

import json
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402
from runtime.source_quota import default_source_quota_policy  # noqa: E402

DEFAULT_SOURCE_QUOTA_POLICY = default_source_quota_policy()
DEFAULT_CNKI_MAX_RESULTS_TOTAL = DEFAULT_SOURCE_QUOTA_POLICY["cnki_max_count"]
RESEARCHAGENT_REVIEW_REF = "outputs/part1/researchagent_search_plan_review.json"
RESEARCHAGENT_PROVENANCE_REF = "outputs/part1/researchagent_provenance.json"


def load_intake() -> dict:
    intake_path = PROJECT_ROOT / "outputs" / "part1" / "intake.json"
    if not intake_path.exists():
        raise FileNotFoundError(f"intake.json 不存在: {intake_path}")
    with open(intake_path) as f:
        return json.load(f)


def build_cnki_queries(intake: dict) -> list[dict]:
    """为 CNKI 生成查询组：聚焦主检索优先，宽泛扩展最后补充。"""
    required_kws = _as_list(intake.get("keywords_required", []))
    suggested_kws = _as_list(intake.get("keywords_suggested", []))
    time_range = intake.get("time_range", {"start_year": 2005, "end_year": 2025})
    if not isinstance(time_range, dict):
        time_range = {"start_year": 2005, "end_year": 2025}
    doc_types = _as_list(intake.get("source_preference", {}).get("document_types", ["期刊论文"]))

    base_filter = {
        "year_from": time_range.get("start_year", 2005),
        "year_to": time_range.get("end_year", 2025),
        "doc_type": doc_types,
    }

    groups = []

    all_terms = _expand_known_aliases(_unique_terms(
        required_kws
        + suggested_kws
        + _as_list(intake.get("discipline_fields", []))
        + _as_list(intake.get("expected_research_types", []))
    ))
    object_terms = _terms_matching(
        all_terms,
        [
            "研究对象", "建筑", "民居", "街区", "旧城", "空间", "形态", "风貌",
            "历史建筑", "传统建筑", "建筑文化", "建筑元素", "建筑装饰", "建筑美学",
        ],
    ) or all_terms[:2]
    application_terms = _terms_matching(
        all_terms,
        [
            "保护", "更新", "改造", "居住", "品质", "好房子", "居民", "案例",
            "政策", "财政", "产权", "基础设施", "市政", "应用",
            "高校", "教育", "教学", "课程", "美术", "艺术",
        ],
    ) or all_terms[1:4] or all_terms[:1]
    intervention_terms = _terms_matching(
        all_terms,
        [
            "微改造", "节能", "成套化", "厨房", "卫生间", "基础设施", "市政",
            "实践", "创作", "课程", "跨学科", "文化传承", "审美", "成果", "案例",
        ],
    )
    transformation_terms = _terms_matching(
        all_terms,
        [
            "保护更新", "城市更新", "历史文化街区", "风貌保护", "活化", "转化",
            "数字", "媒介", "文创", "设计", "装饰",
        ],
    )
    policy_culture_terms = _terms_matching(
        all_terms,
        [
            "政策", "财政", "产权", "公房", "私房", "专项资金", "名城保护",
            "美学", "文化", "传承", "审美", "理论",
        ],
    )

    core_terms = _unique_terms(
        _paired_terms(object_terms[:1], application_terms[:4], 4)
        + _paired_terms(object_terms[1:3], application_terms[:2], 4)
    ) or all_terms[:3]
    intervention_query_terms = (
        _paired_terms(application_terms[:4], intervention_terms[:6], 8)
        or _paired_terms(object_terms[:2], application_terms[:4], 6)
    )
    transformation_terms = (
        _paired_terms(object_terms[:3], transformation_terms[:6], 8)
        or _paired_terms(object_terms[:3], application_terms[:3], 6)
    )
    policy_culture_query_terms = (
        _paired_terms(object_terms[:3], policy_culture_terms[:5], 6)
        or object_terms[:4]
    )

    groups.append({
        "group_id": "cnki_g1_focused_core",
        "purpose": "CNKI 聚焦主检索：基于 confirmed intake 的研究对象与应用场景锚点",
        "queries": [{
            "query_id": "cnki_q1_1",
            "terms": core_terms,
            "operator": "OR",
            "field": "主题",
            "filters": base_filter,
            "expected_results": "40-120",
            "notes": "保留 cnki_q1_1 合同 ID；主检索由 confirmed intake 的研究对象词与保护、更新、改造、政策、教学、应用或案例锚点配对生成，不回退到固定主题模板，也不退化为 required keywords 宽 OR。",
        }],
    })
    groups.append({
        "group_id": "cnki_g2_intervention_practice",
        "purpose": "保护更新、改造实践、居住改善或应用场景线索",
        "queries": [{
            "query_id": "cnki_q2_1",
            "terms": intervention_query_terms,
            "operator": "OR",
            "field": "主题",
            "filters": base_filter,
            "expected_results": "20-80",
            "notes": "保留用户 intake 中的保护更新、微改造、节能改造、居住品质改善、实践应用或转化线索。",
        }],
    })
    groups.append({
        "group_id": "cnki_g3_transformation_context",
        "purpose": "风貌保护、城市更新、活化转化与场景机制线索",
        "queries": [{
            "query_id": "cnki_q3_1",
            "terms": transformation_terms,
            "operator": "OR",
            "field": "主题",
            "filters": base_filter,
            "expected_results": "30-100",
            "notes": "优先召回可支撑保护更新、历史街区活化、成果转化、数字媒介、文创转化或设计应用路径的研究。",
        }],
    })
    groups.append({
        "group_id": "cnki_g4_policy_culture",
        "purpose": "政策机制、财政产权、文化传承与理论基础线索",
        "queries": [{
            "query_id": "cnki_q4_1",
            "terms": policy_culture_query_terms,
            "operator": "OR",
            "field": "主题",
            "filters": base_filter,
            "expected_results": "20-80",
            "notes": "补充政策机制、财政产权、理论基础、传统文化理解、审美素养与文化传承方向文献。",
        }],
    })

    supplemental_terms = _unique_terms(required_kws + suggested_kws[:8])
    if supplemental_terms:
        groups.append({
            "group_id": "cnki_g5_broad_supplemental",
            "purpose": "召回不足后的宽泛补充检索",
            "queries": [{
                "query_id": "cnki_q5_1",
                "terms": supplemental_terms,
                "operator": "OR",
                "field": "主题",
                "filters": base_filter,
                "expected_results": "50-150",
                "notes": "宽泛扩展仅用于查漏补缺，结果必须经过相关性评分与真实性校验后才能进入主链。",
            }],
        })

    return groups


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [
            item.strip()
            for item in re.split(r"[；;、\n]+", value)
            if item.strip()
        ]
    return []


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _terms_matching(terms: list[str], needles: list[str]) -> list[str]:
    return [term for term in terms if _has_any(term, needles)]


def _paired_terms(left_terms: list[str], right_terms: list[str], max_terms: int) -> list[str]:
    paired = []
    for left in left_terms:
        for right in right_terms:
            if left == right:
                continue
            paired.append(f"{left} {right}")
            if len(paired) >= max_terms:
                return _unique_terms(paired)
    return _unique_terms(paired)


def _unique_terms(terms: list[str]) -> list[str]:
    seen = set()
    unique = []
    for term in terms:
        normalized = term.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _expand_known_aliases(terms: list[str]) -> list[str]:
    """Expand known domain aliases without replacing the user's original terms."""
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


def build_wanfang_queries(intake: dict) -> list[dict]:
    required_kws = intake.get("keywords_required", [])
    time_range = intake.get("time_range", {"start_year": 2005, "end_year": 2025})

    return [{
        "group_id": "wf_g1_main",
        "purpose": "万方主题检索",
        "queries": [{
            "query_id": "wf_q1_1",
            "terms": required_kws[:2],  # 万方检索词不宜太多
            "operator": "OR",
            "field": "主题",
            "filters": {
                "year_from": time_range["start_year"],
                "year_to": time_range["end_year"],
            },
            "expected_results": "30-80",
            "notes": "万方补充检索，重点查 CNKI 未收录的期刊",
        }],
    }]


def build_vip_queries(intake: dict) -> list[dict]:
    required_kws = intake.get("keywords_required", [])
    time_range = intake.get("time_range", {"start_year": 2005, "end_year": 2025})

    return [{
        "group_id": "vip_g1_main",
        "purpose": "维普主题检索",
        "queries": [{
            "query_id": "vip_q1_1",
            "terms": required_kws[:2],
            "operator": "OR",
            "field": "M",  # 维普字段代码
            "filters": {
                "year_from": time_range["start_year"],
                "year_to": time_range["end_year"],
            },
            "expected_results": "20-60",
            "notes": "维普补充，主要覆盖工程技术类建筑学期刊",
        }],
    }]


def build_english_journal_queries(intake: dict, db_id: str) -> list[dict]:
    """Build English journal supplement queries for Crossref/OpenAlex/DOAJ."""
    time_range = intake.get("time_range", {"start_year": 2005, "end_year": 2025})
    if not isinstance(time_range, dict):
        time_range = {"start_year": 2005, "end_year": 2025}
    english_terms = _english_terms_from_intake(intake)
    core_terms = english_terms[:6] or ["architecture", "cultural heritage", "design education"]
    method_terms = [
        term
        for term in english_terms
        if any(token in term for token in ["education", "renewal", "conservation", "heritage", "design"])
    ][:6] or core_terms[:3]

    return [{
        "group_id": f"{db_id}_g1_english_journals",
        "purpose": "英文期刊补充检索：用于方法、国际背景、术语映射与前沿讨论",
        "queries": [
            {
                "query_id": f"{db_id}_q1_1",
                "terms": core_terms,
                "operator": "OR",
                "field": "title_abstract_keyword",
                "filters": {
                    "year_from": time_range.get("start_year", 2005),
                    "year_to": time_range.get("end_year", 2025),
                    "document_type": "journal-article",
                    "language": "en",
                    "peer_reviewed": True,
                },
                "expected_results": "10-40",
                "notes": "只纳入英文期刊论文；不得替代 CNKI 中文主检索，只作为补充证据层。",
            },
            {
                "query_id": f"{db_id}_q1_2",
                "terms": method_terms,
                "operator": "OR",
                "field": "title_abstract_keyword",
                "filters": {
                    "year_from": time_range.get("start_year", 2005),
                    "year_to": time_range.get("end_year", 2025),
                    "document_type": "journal-article",
                    "language": "en",
                    "peer_reviewed": True,
                },
                "expected_results": "10-40",
                "notes": "优先补充可支撑研究方法、国际讨论或概念翻译的英文 journal article。",
            },
        ],
    }]


def _english_terms_from_intake(intake: dict) -> list[str]:
    explicit = _as_list(intake.get("english_keywords", [])) + _as_list(intake.get("keywords_english", []))
    if explicit:
        return _unique_terms(explicit)

    source_terms = _unique_terms(
        _as_list(intake.get("keywords_required", []))
        + _as_list(intake.get("keywords_suggested", []))
        + _as_list(intake.get("discipline_fields", []))
        + _as_list(intake.get("expected_research_types", []))
    )
    joined = " ".join(source_terms + [
        str(intake.get("research_topic", "")),
        str(intake.get("research_question", "")),
        str(intake.get("scope_notes", "")),
    ])

    dictionary = [
        ("建筑符号", "architectural symbols"),
        ("地方性", "regional identity"),
        ("建筑美学", "architectural aesthetics"),
        ("传统建筑装饰元素", "traditional architectural ornament"),
        ("设计", "design"),
        ("教育", "education"),
        ("实践教学", "practice-based design education"),
        ("课程", "curriculum design"),
        ("文化传承", "cultural heritage education"),
        ("审美素养", "aesthetic literacy"),
        ("文创转化", "creative industry transformation"),
        ("数字媒介艺术", "digital media art"),
        ("历史街区居住建筑", "residential buildings in historic districts"),
        ("历史文化街区", "historic conservation area"),
        ("旧城片区", "old urban district"),
        ("保护更新", "conservation and renewal"),
        ("风貌保护", "historic character conservation"),
        ("城市更新", "urban regeneration"),
        ("微改造", "micro-renewal"),
        ("节能改造", "energy retrofit"),
        ("居住品质", "residential quality"),
        ("居住品质提升", "housing quality improvement"),
        ("产权政策", "property rights policy"),
        ("财政专项资金", "public funding mechanism"),
        ("建筑", "architecture"),
        ("设计", "design"),
        ("传统", "tradition"),
        ("文化", "cultural heritage"),
        ("教育", "education"),
    ]

    terms = [translation for zh, translation in dictionary if zh in joined]
    if "architecture" not in " ".join(terms):
        terms.append("architecture")
    if "design" not in " ".join(terms):
        terms.append("design")
    if "heritage" not in " ".join(terms):
        terms.append("cultural heritage")
    return _unique_terms(terms)


def generate_plan(intake: dict) -> dict:
    intake_id = intake.get("intake_id", "unknown")
    now = datetime.now(timezone.utc).isoformat()

    cnki_groups = build_cnki_queries(intake)
    wf_groups = build_wanfang_queries(intake)
    vip_groups = build_vip_queries(intake)
    quota_policy = default_source_quota_policy()
    quota_policy["cnki_max_count"] = int(DEFAULT_CNKI_MAX_RESULTS_TOTAL)
    quota_policy["cnki_target_count"] = min(
        int(quota_policy.get("cnki_target_count", 26)),
        int(DEFAULT_CNKI_MAX_RESULTS_TOTAL),
    )

    # 估算总量（粗略）
    estimated_total = "40 accepted sources after relevance/authenticity gates"

    return {
        "plan_id": f"search_plan_{intake_id}",
        "created_at": now,
        "based_on_intake": intake_id,
        "source_quota_policy": quota_policy,
        "databases": [
            {
                "db_id": "cnki",
                "db_name": "中国知网 CNKI",
                "priority": 1,
                "tier": "tier1",
                "query_groups": cnki_groups,
                "max_results_total": DEFAULT_CNKI_MAX_RESULTS_TOTAL,
                "target_results": quota_policy["cnki_target_count"],
                "accepted_min_results": quota_policy["cnki_min_count"],
                "accepted_max_results": quota_policy["cnki_max_count"],
                "download_priority": "high",
            },
            {
                "db_id": "wanfang",
                "db_name": "万方数据",
                "priority": 2,
                "tier": "tier1",
                "query_groups": wf_groups,
                "max_results_total": 8,
                "target_results": 5,
                "download_priority": "medium",
            },
            {
                "db_id": "vip",
                "db_name": "维普期刊",
                "priority": 3,
                "tier": "tier1",
                "query_groups": vip_groups,
                "max_results_total": 8,
                "target_results": 4,
                "download_priority": "low",
            },
            {
                "db_id": "crossref",
                "db_name": "Crossref",
                "priority": 4,
                "tier": "tier2",
                "query_groups": build_english_journal_queries(intake, "crossref"),
                "max_results_total": 2,
                "target_results": 2,
                "download_priority": "medium",
                "english_journal_required": True,
            },
            {
                "db_id": "openalex",
                "db_name": "OpenAlex",
                "priority": 5,
                "tier": "tier2",
                "query_groups": build_english_journal_queries(intake, "openalex"),
                "max_results_total": 2,
                "target_results": 2,
                "download_priority": "medium",
                "english_journal_required": True,
            },
            {
                "db_id": "doaj",
                "db_name": "DOAJ",
                "priority": 6,
                "tier": "tier2",
                "query_groups": build_english_journal_queries(intake, "doaj"),
                "max_results_total": 1,
                "target_results": 1,
                "download_priority": "medium",
                "english_journal_required": True,
            },
        ],
        "dedup_strategy": {
            "fields": ["title", "author", "year", "journal"],
            "prefer_source": "cnki",
        },
        "estimated_total_papers": estimated_total,
        "retrieval_sequence": ["cnki", "wanfang", "vip", "crossref", "openalex", "doaj"],
        "notes": intake.get("scope_notes", ""),
    }


def write_researchagent_sidecar() -> None:
    result = request_llm_agent(
        PROJECT_ROOT,
        agent_name="researchagent",
        task="part1_search_strategy_review",
        skill="part1-search-plan-review",
        output_ref=RESEARCHAGENT_REVIEW_REF,
        input_paths=[
            "outputs/part1/intake.json",
            "outputs/part1/search_plan.json",
            "manifests/source-policy.json",
        ],
        instructions=[
            "Review the Part 1 search plan for CNKI-first strategy, relevance rationale, source triage, and research gaps.",
            "Return JSON with report or payload. Do not rewrite search_plan.json, source-policy.json, or runtime state.",
            "Do not bypass intake_confirmed, authenticity verification, deduplication, or provenance requirements.",
        ],
    )
    if result is None:
        return

    path = PROJECT_ROOT / RESEARCHAGENT_REVIEW_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.raw, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_llm_agent_provenance(
        PROJECT_ROOT,
        RESEARCHAGENT_PROVENANCE_REF,
        agent_name="researchagent",
        task="part1_search_strategy_review",
        skill="part1-search-plan-review",
        output_ref=RESEARCHAGENT_REVIEW_REF,
        mode="llm",
    )


def main():
    parser = argparse.ArgumentParser(description="Generate search plan from intake")
    parser.add_argument("--dry-run", action="store_true", help="打印计划但不写文件")
    args = parser.parse_args()

    try:
        intake = load_intake()
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    plan = generate_plan(intake)

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    output_path = PROJECT_ROOT / "outputs" / "part1" / "search_plan.json"
    with open(output_path, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    write_researchagent_sidecar()

    total_queries = sum(
        len(g["queries"])
        for db in plan["databases"]
        for g in db["query_groups"]
    )
    print(f"✓ search_plan.json 写入完成")
    print(f"  数据库: {len(plan['databases'])} 个")
    print(f"  查询总数: {total_queries} 条")
    print(f"  估计文献量: {plan['estimated_total_papers']} 篇")
    print(f"  输出: {output_path}")


if __name__ == "__main__":
    main()
