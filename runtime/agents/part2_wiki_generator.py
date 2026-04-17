#!/usr/bin/env python3
"""
runtime/agents/part2_wiki_generator.py

Deterministic MVP generator for Part 2 Research Wiki.

Inputs:
  - raw-library/metadata.json

Outputs:
  - research-wiki/pages/*.md
  - research-wiki/index.json
  - research-wiki/update_log.json
  - research-wiki/contradictions_report.json
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402

SCHEMA_VERSION = "1.0.0"
RAW_METADATA_REF = "raw-library/metadata.json"
WIKI_INDEX_REF = "research-wiki/index.json"
WIKI_MARKDOWN_INDEX_REF = "research-wiki/index.md"
WIKI_LOG_REF = "research-wiki/log.md"
WIKI_PAGES_REF = "research-wiki/pages"
UPDATE_LOG_REF = "research-wiki/update_log.json"
CONTRADICTIONS_REPORT_REF = "research-wiki/contradictions_report.json"
WIKISYNTHESISAGENT_REVIEW_REF = "research-wiki/wikisynthesisagent_review.json"
WIKISYNTHESISAGENT_PROVENANCE_REF = "research-wiki/wikisynthesisagent_provenance.json"

ALLOWED_PAGE_TYPES = {
    "concept",
    "topic",
    "method",
    "contradiction",
    "evidence_aggregation",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must be a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            result.append(stripped)
    return result


def as_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value).strip() or fallback


def source_authors(source: dict[str, Any]) -> str:
    authors = source.get("authors", [])
    if isinstance(authors, list):
        return "、".join(unique_strings(authors)) or "未标注"
    return as_text(authors, "未标注")


def source_keywords(source: dict[str, Any]) -> list[str]:
    keywords = source.get("keywords", [])
    if isinstance(keywords, list):
        return unique_strings(keywords)
    if isinstance(keywords, str):
        return unique_strings(re.split(r"[,，;；、\s]+", keywords))
    return []


def slugify(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", value.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "source"


def page_id_for_source(source: dict[str, Any], index: int, page_type: str) -> str:
    source_id = slugify(as_text(source.get("source_id"), f"source_{index:03d}"))
    return f"{page_type}_{source_id}"


def source_digest_page_id(source: dict[str, Any], index: int) -> str:
    source_id = slugify(as_text(source.get("source_id"), f"source_{index:03d}"))
    return f"source_digest_{source_id}"


def classify_page_type(source: dict[str, Any]) -> str:
    title = as_text(source.get("title"))
    abstract = as_text(source.get("abstract"))
    keywords = " ".join(source_keywords(source))
    text = f"{title} {abstract} {keywords}".lower()

    if any(term in text for term in ("矛盾", "冲突", "争议", "张力", "悖论", "contradiction", "conflict", "tension")):
        return "contradiction"
    if any(term in text for term in ("方法", "模型", "框架", "分析", "句法", "method", "syntax", "model", "analysis")):
        return "method"
    if any(term in text for term in ("类型", "概念", "理论", "机制", "范式", "concept", "typology", "theory")):
        return "concept"
    return "topic"


def directory_for_page_type(page_type: str) -> str:
    return {
        "concept": "concepts",
        "topic": "topics",
        "method": "methods",
        "contradiction": "contradictions",
        "evidence_aggregation": "evidence-aggregation",
    }.get(page_type, "topics")


def page_tags(page: dict[str, Any]) -> set[str]:
    tags = page.get("tags", [])
    if not isinstance(tags, list):
        return set()
    return set(unique_strings(tags))


def is_source_digest_page(page: dict[str, Any]) -> bool:
    return (
        as_text(page.get("page_id")).startswith("source_digest_")
        or "source_digest" in page_tags(page)
    )


def is_synthesis_page(page: dict[str, Any]) -> bool:
    return (
        as_text(page.get("page_id")) == "synthesis_all_sources"
        or "synthesis" in page_tags(page)
    )


def primary_theme(source: dict[str, Any]) -> str:
    keywords = source_keywords(source)
    if keywords:
        return keywords[0]
    return as_text(source.get("title"), as_text(source.get("source_id"), "未命名主题"))


def source_ids_text(source_ids: list[str]) -> str:
    return "[" + ", ".join(source_ids) + "]"


def link_target_for_page(file_path: str, *, current_file_path: str | None = None) -> str:
    if current_file_path:
        return posixpath.relpath(file_path, start=posixpath.dirname(current_file_path))
    return file_path.removeprefix("research-wiki/")


def related_page_lines(
    related_page_ids: list[str],
    page_lookup: dict[str, dict[str, Any]],
    *,
    current_file_path: str,
) -> list[str]:
    if not related_page_ids:
        return ["- related_pages: []"]

    lines = ["- related_pages:"]
    for related_page_id in related_page_ids:
        related_page = page_lookup.get(related_page_id)
        if related_page is None:
            lines.append(f"  - {related_page_id}")
            continue
        target = link_target_for_page(
            as_text(related_page.get("file_path")),
            current_file_path=current_file_path,
        )
        title = as_text(related_page.get("title"), related_page_id)
        lines.append(f"  - [{related_page_id} - {title}]({target})")
    return lines


def validate_metadata_sources(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    sources = metadata.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("raw-library/metadata.json sources must be a non-empty array")

    normalized_sources: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise RuntimeError(f"raw-library/metadata.json sources[{index - 1}] must be an object")
        source_id = as_text(source.get("source_id"))
        if not source_id:
            raise RuntimeError("raw-library/metadata.json sources entries must include source_id")
        if source_id in seen_source_ids:
            raise RuntimeError(f"raw-library/metadata.json contains duplicate source_id: {source_id}")
        seen_source_ids.add(source_id)
        normalized_sources.append(source)
    return normalized_sources


def source_digest_markdown(
    source: dict[str, Any],
    page: dict[str, Any],
    page_lookup: dict[str, dict[str, Any]],
) -> str:
    source_id = as_text(source.get("source_id"))
    title = as_text(source.get("title"), source_id)
    year = as_text(source.get("year"), "未标注")
    journal = as_text(source.get("journal"), "未标注")
    abstract = as_text(source.get("abstract"), "metadata 未提供摘要。")
    keywords = source_keywords(source)
    keyword_text = "、".join(keywords) if keywords else "未标注"
    relevance = as_text(source.get("relevance_score"), "未标注")
    source_tier = as_text(source.get("source_tier"), "未标注")
    source_name = as_text(source.get("source_name"), "未标注")

    return "\n".join(
        [
            f"# Source Evidence Digest: {title}",
            "",
            "## Traceability",
            f"- source_ids: {source_ids_text([source_id])}",
            f"- page_id: {page['page_id']}",
            f"- page_type: {page['page_type']}",
            *related_page_lines(
                page.get("related_pages", []),
                page_lookup,
                current_file_path=page["file_path"],
            ),
            "",
            "## 来源信息",
            f"- 作者: {source_authors(source)}",
            f"- 年份: {year}",
            f"- 期刊: {journal}",
            f"- 来源: {source_name}",
            f"- 来源层级: {source_tier}",
            f"- 相关性评分: {relevance}",
            f"- 关键词: {keyword_text}",
            "",
            "## 摘要",
            abstract,
            "",
            "## 可支撑论点",
            f"- 该来源可用于讨论「{title}」中呈现的研究对象、方法或概念边界。",
            "- 论证使用时必须回溯到本页列出的 source_id，不得扩展到未登记来源。",
            "",
        ]
    )


def theme_markdown(
    source: dict[str, Any],
    page: dict[str, Any],
    page_lookup: dict[str, dict[str, Any]],
) -> str:
    source_id = as_text(source.get("source_id"))
    title = as_text(source.get("title"), source_id)
    abstract = as_text(source.get("abstract"), "metadata 未提供摘要。")
    keywords = source_keywords(source)
    keyword_text = "、".join(keywords) if keywords else "未标注"
    theme = primary_theme(source)

    return "\n".join(
        [
            f"# {page['title']}",
            "",
            "## Traceability",
            f"- source_ids: {source_ids_text([source_id])}",
            f"- page_id: {page['page_id']}",
            f"- page_type: {page['page_type']}",
            *related_page_lines(
                page.get("related_pages", []),
                page_lookup,
                current_file_path=page["file_path"],
            ),
            "",
            "## 主题提要",
            f"- 主题锚点: {theme}",
            f"- 来源标题: {title}",
            f"- 关键词: {keyword_text}",
            "",
            "## 来源摘要",
            abstract,
            "",
            "## 写入依据",
            "- 本页由 Part 1 canonical metadata 中的 title、abstract 与 keywords 生成。",
            "- 仅保留可回溯到 source_ids 的研究信息，不引入写作规则层材料。",
            "",
        ]
    )


def cumulative_concept_markdown(
    sources: list[dict[str, Any]],
    page: dict[str, Any],
    page_lookup: dict[str, dict[str, Any]],
) -> str:
    source_lines = []
    keyword_values: list[Any] = []
    for source in sources:
        source_id = as_text(source.get("source_id"))
        title = as_text(source.get("title"), source_id)
        keywords = source_keywords(source)
        keyword_values.extend(keywords)
        keyword_text = "、".join(keywords) if keywords else "未标注"
        source_lines.append(f"- {source_id}: {title}；关键词: {keyword_text}")

    theme_text = "、".join(unique_strings(keyword_values)) or "未标注"

    return "\n".join(
        [
            f"# {page['title']}",
            "",
            "## Traceability",
            f"- source_ids: {source_ids_text(page['source_ids'])}",
            f"- page_id: {page['page_id']}",
            f"- page_type: {page['page_type']}",
            *related_page_lines(
                page.get("related_pages", []),
                page_lookup,
                current_file_path=page["file_path"],
            ),
            "",
            "## 跨来源概念锚点",
            f"- 共同主题: {theme_text}",
            "- 生成原则: 只综合 raw-library/metadata.json 已接受来源中的标题、摘要与关键词。",
            "",
            "## 来源映射",
            *source_lines,
            "",
            "## 累计判断",
            "- 本页用于承载跨来源的概念/主题入口，避免 Research Wiki 退化为一源一卡。",
            "- 后续论证应回到 source_ids 与 related_pages 中登记的页面继续核对。",
            "",
        ]
    )


def aggregation_markdown(
    sources: list[dict[str, Any]],
    page: dict[str, Any],
    page_lookup: dict[str, dict[str, Any]],
) -> str:
    source_lines = []
    for source in sources:
        source_id = as_text(source.get("source_id"))
        title = as_text(source.get("title"), source_id)
        year = as_text(source.get("year"), "未标注")
        source_lines.append(f"- {source_id}: {title}（{year}）")

    return "\n".join(
        [
            "# Part 2 Evidence Aggregation",
            "",
            "## Traceability",
            f"- source_ids: {source_ids_text(page['source_ids'])}",
            f"- page_id: {page['page_id']}",
            f"- page_type: {page['page_type']}",
            *related_page_lines(
                page.get("related_pages", []),
                page_lookup,
                current_file_path=page["file_path"],
            ),
            "",
            "## 来源范围",
            "本页仅汇总 raw-library/metadata.json 中已登记的 Part 1 canonical sources。",
            "",
            "## 已登记来源",
            *source_lines,
            "",
            "## 聚合判断",
            "- 所有 Research Wiki 页面均保留非空 source_ids。",
            "- 后续 Argument Tree 只能引用 index 中登记的 page_id 与 source_id。",
            "",
        ]
    )


def synthesis_markdown(
    sources: list[dict[str, Any]],
    page: dict[str, Any],
    page_lookup: dict[str, dict[str, Any]],
) -> str:
    source_lines = []
    keyword_values: list[Any] = []
    for source in sources:
        source_id = as_text(source.get("source_id"))
        title = as_text(source.get("title"), source_id)
        keywords = source_keywords(source)
        keyword_values.extend(keywords)
        keyword_text = "、".join(keywords) if keywords else "未标注"
        source_lines.append(f"- {source_id}: {title}；关键词: {keyword_text}")

    synthesis_terms = "、".join(unique_strings(keyword_values)) or "未标注"

    return "\n".join(
        [
            "# Part 2 Research Synthesis",
            "",
            "## Traceability",
            f"- source_ids: {source_ids_text(page['source_ids'])}",
            f"- page_id: {page['page_id']}",
            f"- page_type: {page['page_type']}",
            *related_page_lines(
                page.get("related_pages", []),
                page_lookup,
                current_file_path=page["file_path"],
            ),
            "",
            "## 综合范围",
            "本页只综合 raw-library/metadata.json 中已接受来源的标题、摘要与关键词。",
            "",
            "## 综合锚点",
            f"- 关键词集合: {synthesis_terms}",
            "",
            "## 来源映射",
            *source_lines,
            "",
            "## 综合判断",
            "- source_digest 页面负责单篇来源消化；evidence_aggregation 页面负责证据清单聚合。",
            "- 本 synthesis 页面承载跨来源综合判断，不引入写作规则层材料或未登记来源。",
            "",
        ]
    )


def build_update_log(timestamp: str, page_count: int, source_count: int) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "source_bundle_ref": RAW_METADATA_REF,
        "events": [
            {
                "event_type": "part2_wiki_generated",
                "created_at": timestamp,
                "source_count": source_count,
                "page_count": page_count,
                "notes": "Deterministic MVP generated from raw-library/metadata.json only.",
            }
        ],
    }


def build_contradictions_report(timestamp: str, contradiction_pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "source_bundle_ref": RAW_METADATA_REF,
        "contradiction_count": len(contradiction_pages),
        "pages": [
            {
                "page_id": page["page_id"],
                "title": page["title"],
                "source_ids": page["source_ids"],
                "status": "needs_human_review",
            }
            for page in contradiction_pages
        ],
    }


def build_index_markdown(index: dict[str, Any]) -> str:
    pages = index.get("pages", [])
    if not isinstance(pages, list):
        raise RuntimeError("wiki index pages must be an array")

    sections = [
        (
            "来源消化 Source Digest",
            is_source_digest_page,
        ),
        (
            "概念与主题 Concept / Topic",
            lambda page: as_text(page.get("page_type")) in {"concept", "topic"},
        ),
        ("方法 Method", lambda page: as_text(page.get("page_type")) == "method"),
        (
            "证据聚合 Evidence Aggregation",
            lambda page: (
                as_text(page.get("page_type")) == "evidence_aggregation"
                and not is_source_digest_page(page)
                and not is_synthesis_page(page)
            ),
        ),
        (
            "综合判断 Synthesis",
            is_synthesis_page,
        ),
        ("矛盾与冲突 Contradiction", lambda page: as_text(page.get("page_type")) == "contradiction"),
    ]
    lines = [
        "# Research Wiki 内容目录",
        "",
        f"- source_bundle_ref: {index.get('source_bundle_ref', RAW_METADATA_REF)}",
        f"- source_mapping_complete: {index.get('source_mapping_complete')}",
        f"- total_pages: {len(pages)}",
        "",
    ]

    for section_title, predicate in sections:
        lines.extend([f"## {section_title}", ""])
        section_pages = [
            page
            for page in pages
            if isinstance(page, dict) and predicate(page)
        ]
        if not section_pages:
            lines.extend(["_暂无页面。_", ""])
            continue
        for page in section_pages:
            file_path = as_text(page.get("file_path"))
            target = link_target_for_page(file_path)
            title = as_text(page.get("title"), as_text(page.get("page_id"), "untitled"))
            page_id = as_text(page.get("page_id"))
            source_ids = page.get("source_ids", [])
            source_text = source_ids_text(source_ids) if isinstance(source_ids, list) else "[]"
            lines.append(f"- [{title}]({target}) — `{page_id}`; source_ids: {source_text}")
        lines.append("")

    return "\n".join(lines)


def build_log_entry(timestamp: str, sources: list[dict[str, Any]], page_count: int) -> str:
    source_ids = [as_text(source.get("source_id")) for source in sources]
    source_lines = [f"  - {source_id}" for source_id in source_ids]
    return "\n".join(
        [
            f"## {timestamp} generation",
            f"- event: ingest/generation from {RAW_METADATA_REF}",
            f"- source_bundle_ref: {RAW_METADATA_REF}",
            f"- source_count: {len(source_ids)}",
            f"- page_count: {page_count}",
            "- source_ids:",
            *source_lines,
            "- notes: 仅从 raw-library/metadata.json 生成 Research Wiki；不读取写作规则层材料。",
        ]
    )


def cleanup_previous_indexed_pages(project_root: Path, pages_root: Path, keep_targets: set[Path]) -> None:
    existing_index_path = project_root / WIKI_INDEX_REF
    if not existing_index_path.exists():
        return

    try:
        existing_index = load_json(existing_index_path)
    except (json.JSONDecodeError, RuntimeError):
        return

    pages = existing_index.get("pages", [])
    if not isinstance(pages, list):
        return

    for page in pages:
        if not isinstance(page, dict):
            continue
        rel_path = page.get("file_path")
        if not isinstance(rel_path, str):
            continue
        target = (project_root / rel_path).resolve()
        try:
            target.relative_to(pages_root)
        except ValueError:
            continue
        if target.name == ".gitkeep" or target in keep_targets or not target.is_file():
            continue
        target.unlink()


def generate_wiki_bundle(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    metadata_path = project_root / RAW_METADATA_REF
    if not metadata_path.exists():
        raise FileNotFoundError(f"缺少必需输入: {RAW_METADATA_REF}")

    metadata = load_json(metadata_path)
    sources = validate_metadata_sources(metadata)
    timestamp = now_iso()
    aggregation_page_id = "evidence_aggregation_all_sources"
    synthesis_page_id = "synthesis_all_sources"
    cumulative_concept_page_id = "concept_cross_source_research_anchors"

    pages: list[dict[str, Any]] = []
    seen_page_ids: set[str] = set()
    seen_file_paths: set[str] = set()

    def ensure_unique_page(page_id: str, file_path: str) -> None:
        if page_id in seen_page_ids:
            raise RuntimeError(f"duplicate page_id generated after slug normalization: {page_id}")
        if file_path in seen_file_paths:
            raise RuntimeError(f"duplicate wiki page file_path generated: {file_path}")
        seen_page_ids.add(page_id)
        seen_file_paths.add(file_path)

    source_digest_pages: list[dict[str, Any]] = []
    theme_pages: list[dict[str, Any]] = []

    for index, source in enumerate(sources, start=1):
        source_id = as_text(source.get("source_id"))
        source_title = as_text(source.get("title"), source_id)

        digest_page_id = source_digest_page_id(source, index)
        digest_file_path = f"{WIKI_PAGES_REF}/source-digest/{digest_page_id}.md"
        ensure_unique_page(digest_page_id, digest_file_path)
        digest_page = {
            "page_id": digest_page_id,
            "title": f"Source Evidence Digest: {source_title}",
            "page_type": "evidence_aggregation",
            "source_ids": [source_id],
            "related_pages": [aggregation_page_id, synthesis_page_id],
            "file_path": digest_file_path,
            "tags": ["source_digest", *source_keywords(source)],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        pages.append(digest_page)
        source_digest_pages.append(digest_page)

        page_type = classify_page_type(source)
        page_id = page_id_for_source(source, index, page_type)
        title = as_text(source.get("title"), as_text(source.get("source_id"), page_id))
        file_path = f"{WIKI_PAGES_REF}/{directory_for_page_type(page_type)}/{page_id}.md"
        ensure_unique_page(page_id, file_path)
        page = {
            "page_id": page_id,
            "title": f"{primary_theme(source)}: {title}",
            "page_type": page_type,
            "source_ids": [source_id],
            "related_pages": [digest_page_id, aggregation_page_id, synthesis_page_id],
            "file_path": file_path,
            "tags": source_keywords(source),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        pages.append(page)
        theme_pages.append(page)
        digest_page["related_pages"] = [page_id, aggregation_page_id, synthesis_page_id]

    all_source_ids = [as_text(source.get("source_id")) for source in sources]

    concept_related_page_ids = [page["page_id"] for page in theme_pages] + [aggregation_page_id, synthesis_page_id]
    concept_path = f"{WIKI_PAGES_REF}/concepts/{cumulative_concept_page_id}.md"
    ensure_unique_page(cumulative_concept_page_id, concept_path)
    cumulative_concept_page = {
        "page_id": cumulative_concept_page_id,
        "title": "跨来源研究锚点",
        "page_type": "concept",
        "source_ids": all_source_ids,
        "related_pages": concept_related_page_ids,
        "file_path": concept_path,
        "tags": ["concept", "cross_source", "part2"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    pages.append(cumulative_concept_page)

    related_page_ids = [page["page_id"] for page in pages]
    aggregation_path = f"{WIKI_PAGES_REF}/evidence-aggregation/{aggregation_page_id}.md"
    ensure_unique_page(aggregation_page_id, aggregation_path)
    aggregation_page = {
        "page_id": aggregation_page_id,
        "title": "Part 2 Evidence Synthesis",
        "page_type": "evidence_aggregation",
        "source_ids": all_source_ids,
        "related_pages": [*related_page_ids, synthesis_page_id],
        "file_path": aggregation_path,
        "tags": ["evidence_aggregation", "part2"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    pages.append(aggregation_page)

    synthesis_path = f"{WIKI_PAGES_REF}/synthesis/{synthesis_page_id}.md"
    ensure_unique_page(synthesis_page_id, synthesis_path)
    synthesis_page = {
        "page_id": synthesis_page_id,
        "title": "Part 2 Research Synthesis",
        "page_type": "evidence_aggregation",
        "source_ids": all_source_ids,
        "related_pages": [*related_page_ids, aggregation_page_id],
        "file_path": synthesis_path,
        "tags": ["synthesis", "cross_source", "part2"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    pages.append(synthesis_page)

    page_lookup = {page["page_id"]: page for page in pages}
    page_files: dict[str, str] = {}
    source_by_id = {as_text(source.get("source_id")): source for source in sources}
    for page in source_digest_pages:
        source = source_by_id[page["source_ids"][0]]
        page_files[page["file_path"]] = source_digest_markdown(source, page, page_lookup)
    for page in theme_pages:
        source = source_by_id[page["source_ids"][0]]
        page_files[page["file_path"]] = theme_markdown(source, page, page_lookup)
    page_files[concept_path] = cumulative_concept_markdown(sources, cumulative_concept_page, page_lookup)
    page_files[aggregation_path] = aggregation_markdown(sources, aggregation_page, page_lookup)
    page_files[synthesis_path] = synthesis_markdown(sources, synthesis_page, page_lookup)

    contradiction_pages = [page for page in pages if page["page_type"] == "contradiction"]
    unsourced_pages = sum(1 for page in pages if not page.get("source_ids"))
    orphan_pages = sum(1 for page in pages if not page.get("related_pages"))

    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "last_updated": timestamp,
        "source_bundle_ref": RAW_METADATA_REF,
        "source_mapping_complete": unsourced_pages == 0,
        "pages": pages,
        "health_summary": {
            "total_pages": len(pages),
            "orphan_pages": orphan_pages,
            "isolated_pages": orphan_pages,
            "unsourced_pages": unsourced_pages,
            "contradiction_count": len(contradiction_pages),
            "contradiction_pages": len(contradiction_pages),
            "unresolved_contradiction_pages": len(contradiction_pages),
            "last_health_check": timestamp,
        },
    }

    return {
        "index": index,
        "page_files": page_files,
        "markdown_files": {
            WIKI_MARKDOWN_INDEX_REF: build_index_markdown(index),
        },
        "log_entry": build_log_entry(timestamp, sources, len(pages)),
        "update_log": build_update_log(timestamp, len(pages), len(sources)),
        "contradictions_report": build_contradictions_report(timestamp, contradiction_pages),
    }


def write_wiki_bundle(project_root: Path, package: dict[str, Any], force: bool = False) -> None:
    project_root = project_root.resolve()
    wiki_root = (project_root / "research-wiki").resolve()
    pages_root = (project_root / WIKI_PAGES_REF).resolve()
    if not isinstance(package, dict):
        raise RuntimeError("wiki package must be an object")
    for key in ("index", "update_log", "contradictions_report"):
        if not isinstance(package.get(key), dict):
            raise RuntimeError(f"wiki package {key} must be an object")

    page_files = package.get("page_files", {})
    if not isinstance(page_files, dict):
        raise RuntimeError("wiki package page_files must be an object")

    markdown_files = package.get("markdown_files", {})
    if not isinstance(markdown_files, dict):
        raise RuntimeError("wiki package markdown_files must be an object")
    allowed_markdown_paths = {WIKI_MARKDOWN_INDEX_REF}

    target_page_files: list[tuple[Path, str]] = []
    seen_targets: set[Path] = set()
    for rel_path, content in sorted(page_files.items()):
        if not isinstance(rel_path, str):
            raise RuntimeError(f"Invalid wiki page path in package: {rel_path!r}")
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid wiki page content for package path: {rel_path!r}")
        target = (project_root / rel_path).resolve()
        try:
            target.relative_to(pages_root)
        except ValueError as exc:
            raise RuntimeError(f"Invalid wiki page path traversal in package: {rel_path!r}") from exc
        if target in seen_targets:
            raise RuntimeError(f"duplicate wiki page target in package: {rel_path!r}")
        seen_targets.add(target)
        target_page_files.append((target, content))

    target_markdown_files: list[tuple[Path, str]] = []
    for rel_path, content in sorted(markdown_files.items()):
        if not isinstance(rel_path, str) or rel_path not in allowed_markdown_paths:
            raise RuntimeError(f"Invalid wiki markdown path in package: {rel_path!r}")
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid wiki markdown content for package path: {rel_path!r}")
        target = (project_root / rel_path).resolve()
        try:
            target.relative_to(wiki_root)
        except ValueError as exc:
            raise RuntimeError(f"Invalid wiki markdown path traversal in package: {rel_path!r}") from exc
        if target in seen_targets:
            raise RuntimeError(f"duplicate wiki target in package: {rel_path!r}")
        seen_targets.add(target)
        target_markdown_files.append((target, content))

    canonical_targets = [
        project_root / WIKI_INDEX_REF,
        project_root / WIKI_MARKDOWN_INDEX_REF,
        project_root / WIKI_LOG_REF,
        project_root / UPDATE_LOG_REF,
        project_root / CONTRADICTIONS_REPORT_REF,
        *[target for target, _content in target_markdown_files],
        *[target for target, _content in target_page_files],
    ]
    if not force:
        existing_targets = [path for path in canonical_targets if path.exists()]
        if existing_targets:
            existing_refs = ", ".join(str(path.relative_to(project_root)) for path in existing_targets)
            raise RuntimeError(f"wiki canonical artifact already exists; use force to overwrite: {existing_refs}")
    else:
        cleanup_previous_indexed_pages(
            project_root,
            pages_root,
            {target for target, _content in target_page_files},
        )

    for path, content in target_page_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    for path, content in target_markdown_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    log_entry = package.get("log_entry")
    if not isinstance(log_entry, str):
        timestamp = as_text(package["index"].get("generated_at"), now_iso())
        page_count = len(package["index"].get("pages", []))
        log_entry = "\n".join(
            [
                f"## {timestamp} generation",
                f"- event: ingest/generation from {RAW_METADATA_REF}",
                f"- source_bundle_ref: {RAW_METADATA_REF}",
                "- source_count: 未标注",
                f"- page_count: {page_count}",
            ]
        )
    log_path = project_root / WIKI_LOG_REF
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if force and log_path.exists():
        existing_log = log_path.read_text(encoding="utf-8").rstrip()
        log_path.write_text(f"{existing_log}\n\n{log_entry.rstrip()}\n", encoding="utf-8")
    else:
        log_path.write_text(f"# Research Wiki Generation Log\n\n{log_entry.rstrip()}\n", encoding="utf-8")

    write_json(project_root / WIKI_INDEX_REF, package["index"])
    write_json(project_root / UPDATE_LOG_REF, package["update_log"])
    write_json(project_root / CONTRADICTIONS_REPORT_REF, package["contradictions_report"])
    write_wikisynthesisagent_sidecar(project_root)


def write_wikisynthesisagent_sidecar(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="wikisynthesisagent",
        task="part2_research_wiki_synthesis_review",
        skill="part2-policy-build",
        output_ref=WIKISYNTHESISAGENT_REVIEW_REF,
        input_paths=[
            RAW_METADATA_REF,
            WIKI_INDEX_REF,
            WIKI_MARKDOWN_INDEX_REF,
            UPDATE_LOG_REF,
            CONTRADICTIONS_REPORT_REF,
        ],
        instructions=[
            "Review the generated Part 2 research wiki for synthesis quality, contradictions, evidence aggregation, and source-grounded concept/topic/method coverage.",
            "Return JSON with report or payload. Do not rewrite research-wiki/index.json, wiki pages, raw metadata, or runtime state.",
            "Do not use writing-policy material as research evidence.",
        ],
    )
    if result is None:
        return

    path = project_root / WIKISYNTHESISAGENT_REVIEW_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.raw, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_llm_agent_provenance(
        project_root,
        WIKISYNTHESISAGENT_PROVENANCE_REF,
        agent_name="wikisynthesisagent",
        task="part2_research_wiki_synthesis_review",
        skill="part2-policy-build",
        output_ref=WIKISYNTHESISAGENT_REVIEW_REF,
        mode="llm",
    )


def run_wiki_generation(project_root: Path, dry_run: bool = False, force: bool = False) -> dict[str, Any]:
    package = generate_wiki_bundle(project_root)
    if not dry_run:
        write_wiki_bundle(project_root, package, force=force)
    return package


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Part 2 Research Wiki from raw-library/metadata.json")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--dry-run", action="store_true", help="Print package JSON without writing wiki artifacts")
    parser.add_argument("--force", action="store_true", help="Allow regeneration of existing wiki artifacts")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    package = run_wiki_generation(args.project_root, dry_run=args.dry_run, force=args.force)
    if args.dry_run:
        json.dump(package, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return package


if __name__ == "__main__":
    main()
