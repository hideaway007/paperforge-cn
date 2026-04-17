#!/usr/bin/env python3
"""
runtime/agents/part3_argument_seed_map_generator.py

Generate Part 3 argument seed map from Part 2 research-wiki only.

用法：
  python3 runtime/agents/part3_argument_seed_map_generator.py
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
SCHEMA_VERSION = "1.0.0"
STATE_REF = "runtime/state.json"
WIKI_REF = "research-wiki/index.json"
RAW_METADATA_REF = "raw-library/metadata.json"
SEED_MAP_REF = "outputs/part3/argument_seed_map.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def assert_part2_gate_passed(project_root: Path) -> None:
    state_path = project_root / STATE_REF
    if not state_path.exists():
        raise FileNotFoundError(f"缺少 state 文件: {STATE_REF}；不能在无状态审计下生成 argument seed map")
    state = load_json(state_path)
    part2 = state.get("stages", {}).get("part2", {})
    if part2.get("status") != "completed" or part2.get("gate_passed") is not True:
        raise RuntimeError("Part 2 gate 尚未通过，不能生成 Part 3 argument seed map")


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def resolve_page_path(project_root: Path, file_path: str) -> Path:
    raw = Path(file_path)
    candidates = [raw] if raw.is_absolute() else [
        project_root / raw,
        project_root / "research-wiki" / raw,
        project_root / "research-wiki" / "pages" / raw.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Wiki page file not found for file_path={file_path!r}")


def load_raw_source_ids(project_root: Path) -> set[str]:
    metadata_path = project_root / RAW_METADATA_REF
    if not metadata_path.exists():
        raise FileNotFoundError(f"缺少 raw-library metadata: {RAW_METADATA_REF}")
    metadata = load_json(metadata_path)
    source_ids = {
        source.get("source_id")
        for source in metadata.get("sources", []) or []
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }
    if not source_ids:
        raise ValueError("raw-library/metadata.json 没有可追溯 source_id")
    return source_ids


def load_wiki_pages(project_root: Path, raw_source_ids: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index_path = project_root / WIKI_REF
    if not index_path.exists():
        raise FileNotFoundError(f"缺少 Part 2 canonical wiki index: {WIKI_REF}")
    wiki_index = load_json(index_path)
    if wiki_index.get("source_mapping_complete") is not True:
        raise RuntimeError("research-wiki/index.json source_mapping_complete 不是 true，不能生成 argument seed map")
    pages = wiki_index.get("pages", [])
    if not isinstance(pages, list) or not pages:
        raise ValueError("research-wiki/index.json pages must be a non-empty array")

    enriched_pages: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Each wiki page index entry must be an object")
        page_id = page.get("page_id")
        file_path = page.get("file_path")
        source_ids = page.get("source_ids")
        if not isinstance(page_id, str) or not page_id:
            raise ValueError("Each wiki page must include page_id")
        if not isinstance(file_path, str) or not file_path:
            raise ValueError(f"Wiki page {page_id} must include file_path")
        if not isinstance(source_ids, list) or not source_ids:
            raise ValueError(f"Wiki page {page_id} must preserve at least one source_id")
        unknown_sources = sorted(set(source_ids) - raw_source_ids)
        if unknown_sources:
            raise ValueError(f"Wiki page {page_id} references source_ids missing from raw-library: {unknown_sources}")
        resolved_path = resolve_page_path(project_root, file_path)
        enriched_pages.append({
            **page,
            "content": resolved_path.read_text(encoding="utf-8"),
            "resolved_file_path": str(resolved_path),
        })
    return wiki_index, sorted(enriched_pages, key=lambda item: item.get("page_id", ""))


def first_sentence(text: str, fallback: str) -> str:
    compact = re.sub(r"\s+", "", text.replace("#", ""))
    for delimiter in ("。", "；", ";", "."):
        if delimiter in compact:
            candidate = compact.split(delimiter, 1)[0]
            return candidate[:90] or fallback
    return compact[:90] or fallback


def markdown_section(content: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return ""
    rest = content[match.end():]
    next_heading = re.search(r"^##\s+", rest, re.MULTILINE)
    section = rest[:next_heading.start()] if next_heading else rest
    lines = [
        line.strip(" -")
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("- source_id:")
    ]
    return "；".join(lines)


def item(
    item_id: str,
    text: str,
    pages: list[dict[str, Any]],
    *,
    confidence: float = 0.72,
    notes: str = "",
) -> dict[str, Any]:
    source_ids = unique_strings([
        source_id
        for page in pages
        for source_id in page.get("source_ids", [])
        if isinstance(source_id, str)
    ])
    wiki_page_ids = unique_strings([
        page.get("page_id", "")
        for page in pages
        if isinstance(page.get("page_id"), str)
    ])
    page_types = unique_strings([
        page.get("page_type", "")
        for page in pages
        if isinstance(page.get("page_type"), str)
    ])
    return {
        "item_id": item_id,
        "text": text,
        "source_ids": source_ids,
        "wiki_page_ids": wiki_page_ids,
        "page_type": ",".join(page_types) if page_types else "unknown",
        "confidence": confidence,
        "notes": notes,
    }


def pages_by_type(pages: list[dict[str, Any]], page_type: str) -> list[dict[str, Any]]:
    return [page for page in pages if page.get("page_type") == page_type]


def pages_matching(pages: list[dict[str, Any]], terms: tuple[str, ...]) -> list[dict[str, Any]]:
    matched = []
    for page in pages:
        haystack = f"{page.get('title', '')} {page.get('content', '')} {' '.join(page.get('tags', []) or [])}"
        if any(term in haystack for term in terms):
            matched.append(page)
    return matched


def clean_topic_title(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value)
    cleaned = cleaned.replace("SourceEvidenceDigest", "")
    cleaned = cleaned.replace("Part2ResearchSynthesis", "")
    cleaned = cleaned.replace("Part2EvidenceSynthesis", "")
    cleaned = cleaned.strip(" :：-—")
    pieces = [piece.strip(" :：-—") for piece in re.split(r"[:：]", cleaned) if piece.strip(" :：-—")]
    if pieces:
        cleaned = pieces[-1]
    cleaned = re.sub(r"^《[^》]+》", "", cleaned).strip(" :：-—")
    return cleaned[:36]


def infer_research_subject(pages: list[dict[str, Any]]) -> str:
    tagged_terms: list[str] = []
    for page in pages:
        tags = page.get("tags", [])
        if isinstance(tags, list):
            tagged_terms.extend(str(tag).strip() for tag in tags if str(tag).strip())
    hits = unique_strings(tagged_terms)
    if hits:
        return "、".join(hits[:3])

    for page in pages:
        title = clean_topic_title(str(page.get("title", "")))
        if title and title not in {"跨来源研究锚点"}:
            return title
    return "本研究对象"


def build_seed_map(
    wiki_index: dict[str, Any],
    pages: list[dict[str, Any]],
    raw_source_ids: set[str],
    generated_at: str,
) -> dict[str, Any]:
    concept_pages = pages_by_type(pages, "concept") or pages[:1]
    method_pages = pages_by_type(pages, "method") or pages_matching(pages, ("方法", "路径", "机制")) or pages[:1]
    topic_pages = pages_by_type(pages, "topic") or pages[:1]
    contradiction_pages = pages_by_type(pages, "contradiction") or pages_matching(pages, ("矛盾", "不足", "问题", "边界")) or topic_pages
    case_pages = pages_matching(pages, ("案例", "实践", "课程", "创作", "应用", "博物馆")) or topic_pages
    all_sources = unique_strings([
        source_id
        for page in pages
        for source_id in page.get("source_ids", [])
        if isinstance(source_id, str)
    ])
    titles = "、".join(page.get("title", page.get("page_id", "")) for page in pages[:3])
    research_subject = infer_research_subject(pages)
    research_question = (
        f"如何基于 Part 2 Research Wiki 中的{titles}，构造围绕{research_subject}的可回溯、可反驳、可进入论文大纲的论证主线？"
    )

    candidate_claims = []
    for index, page in enumerate(pages, start=1):
        title = page.get("title", page.get("page_id", "研究材料"))
        claim_text = f"{title}可作为论文论证中的一个候选主张，但必须限定在该 wiki 页面和登记 source_id 的证据范围内。"
        candidate_claims.append(item(f"claim_{index:03d}", claim_text, [page], confidence=0.76))

    evidence_points = []
    for index, page in enumerate(pages, start=1):
        content = page.get("content", "")
        summary = first_sentence(
            markdown_section(content, "摘要") or markdown_section(content, "聚合判断") or content,
            page.get("title", "该页面"),
        )
        evidence_points.append(item(
            f"evidence_{index:03d}",
            f"{summary}；该证据可用于支撑论点或限定论点边界。",
            [page],
            confidence=0.78,
        ))

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "wiki_ref": WIKI_REF,
        "raw_metadata_ref": RAW_METADATA_REF,
        "research_question": research_question,
        "source_traceability": {
            "wiki_page_count": len(pages),
            "wiki_source_ids": all_sources,
            "raw_source_ids": sorted(raw_source_ids),
        },
        "candidate_claims": candidate_claims,
        "evidence_points": evidence_points,
        "contradictions": [
            item(
                "contradiction_001",
                "理论框架、方法路径与案例材料之间可能存在解释尺度不一致，需要在论证树中显式处理。",
                contradiction_pages,
                confidence=0.64,
                notes="来自 wiki 页面中的问题/边界线索，不新增外部证据。",
            )
        ],
        "counterclaims": [
            item(
                "counterclaim_001",
                f"若证据主要来自单一案例或单一主题页，论文结论应避免外推为全部{research_subject}规律。",
                case_pages,
                confidence=0.68,
            )
        ],
        "method_paths": [
            item(
                "method_path_001",
                "先界定概念边界，再以方法页或主题页转换为分析维度，最后回到案例或应用结论。",
                method_pages + concept_pages,
                confidence=0.74,
            )
        ],
        "case_boundaries": [
            item(
                "case_boundary_001",
                "案例材料只能承担对象说明与机制验证角色，不能替代全部研究证据。",
                case_pages,
                confidence=0.7,
            )
        ],
        "evidence_gaps": [
            item(
                "gap_001",
                "当前 wiki 若缺少独立方法页或矛盾页，后续大纲需要把方法依据与反方处理标为研究债。",
                method_pages + contradiction_pages,
                confidence=0.58,
            )
        ],
        "background_only_materials": [
            item(
                "background_001",
                "仅描述地域文化、历史价值或材料背景的内容只能作为背景，不应直接升级为主论点。",
                concept_pages + topic_pages,
                confidence=0.62,
            )
        ],
        "generation_notes": "Seed map 只读取 research-wiki/index.json、wiki pages 与 raw-library/metadata.json；不读取 writing-policy。",
        "wiki_generated_at": wiki_index.get("generated_at"),
    }


def generate_seed_map(project_root: Path = PROJECT_ROOT, generated_at: str | None = None) -> dict[str, Any]:
    assert_part2_gate_passed(project_root)
    raw_source_ids = load_raw_source_ids(project_root)
    wiki_index, pages = load_wiki_pages(project_root, raw_source_ids)
    seed_map = build_seed_map(wiki_index, pages, raw_source_ids, generated_at or now_iso())
    write_json(project_root / SEED_MAP_REF, seed_map)
    return seed_map


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Part 3 argument seed map from Part 2 wiki.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT), help="Project root; defaults to repository root.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = Path(args.project_root).resolve()
    try:
        generate_seed_map(project_root=project_root)
    except Exception as exc:
        print(f"[ERR] Part 3 argument seed map generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"[OK] {SEED_MAP_REF}")
    print("[INFO] 只生成 argument seed map；未生成候选树，也未写入 canonical argument_tree.json。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
