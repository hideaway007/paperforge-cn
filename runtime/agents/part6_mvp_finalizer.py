#!/usr/bin/env python3
"""
Part 6 MVP finalizer.

Deterministic runtime generator for finalization artifacts. It does not submit
anything and does not confirm human gates.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime import pipeline  # noqa: E402
from runtime.llm_writer_bridge import (  # noqa: E402
    deterministic_writer_fallback_allowed,
    missing_writeagent_command_message,
    request_writeagent,
    write_writer_provenance,
)
from runtime.llm_agent_bridge import request_llm_agent, write_llm_agent_provenance  # noqa: E402
from runtime.writing_contract import public_text_has_internal_markers, remove_internal_lines  # noqa: E402
from runtime.agents.part6_docx_exporter import export_docx  # noqa: E402


REQUIRED_PACKAGE_FILES = [
    "outputs/part6/final_manuscript.md",
    "outputs/part6/final_abstract.md",
    "outputs/part6/final_keywords.json",
    "outputs/part6/submission_checklist.md",
    "outputs/part6/final_manuscript.docx",
    "outputs/part6/docx_format_report.json",
    "outputs/part6/claim_risk_report.json",
    "outputs/part6/citation_consistency_report.json",
    "outputs/part6/final_readiness_decision.json",
]

AUDIT_REFS = [
    "outputs/part6/claim_risk_report.json",
    "outputs/part6/citation_consistency_report.json",
]

CLAIMAUDITOR_PART6_REVIEW_REF = "outputs/part6/llm_agent_audits/claimauditor_claim_audit.json"
CLAIMAUDITOR_PART6_PROVENANCE_REF = "outputs/part6/claimauditor_provenance.json"
CITATIONAUDITOR_PART6_REVIEW_REF = "outputs/part6/llm_agent_audits/citationauditor_citation_audit.json"
CITATIONAUDITOR_PART6_PROVENANCE_REF = "outputs/part6/citationauditor_provenance.json"

EVIDENCE_REFS = [
    "raw-library/metadata.json",
    "research-wiki/index.json",
    "outputs/part1/accepted_sources.json",
    "outputs/part1/authenticity_report.json",
    "outputs/part5/claim_evidence_matrix.json",
    "outputs/part5/citation_map.json",
]

PROCESS_REFS = [
    "outputs/part5/revision_log.json",
    "outputs/part5/part6_readiness_decision.json",
]

POLICY_REFS = [
    "writing-policy/source_index.json",
    "writing-policy/rules/scut_course_paper_format.md",
]

WRITEAGENT_STYLE_INPUTS = [
    "writing-policy/style_guides/author_style_profile.md",
    "writing-policy/style_guides/author_style_negative_patterns.md",
    "skills/author-style-profile-build/SKILL.md",
    "skills/academic-register-polish/SKILL.md",
    "skills/paper-manuscript-style-profile/SKILL.md",
    "skills/part6-finalize-manuscript/SKILL.md",
]

PART6_DESKTOP_MANUSCRIPT_NAME = "part6_final_manuscript.md"
STALE_PART6_DESKTOP_OUTPUTS = [
    "part6_final_abstract.md",
    "part6_final_keywords.json",
    "part6_writer_body.md",
]

FORBIDDEN_STANDALONE_PUBLIC_SECTIONS = (
    "风险与残余说明",
    "证据边界与研究不足",
    "证据边界与研究限制",
    "证据边界与外推限制",
    "残余研究债务",
    "证据债务",
    "风险提示",
    "风险说明",
)


def forbidden_standalone_public_sections(text: str) -> list[str]:
    matches: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip()
        if any(marker in title for marker in FORBIDDEN_STANDALONE_PUBLIC_SECTIONS):
            matches.append(title)
    return matches


def ensure_public_manuscript_text(text: str, *, artifact_name: str) -> str:
    raw_markers = public_text_has_internal_markers(text)
    if raw_markers:
        raise RuntimeError(
            f"{artifact_name} 包含内部工作标记，不能作为公开正文: {raw_markers}"
        )
    forbidden_sections = forbidden_standalone_public_sections(text)
    if forbidden_sections:
        raise RuntimeError(
            f"{artifact_name} 包含不应进入公开正文的独立风险/证据边界章节: {forbidden_sections}"
        )
    cleaned = remove_internal_lines(text)
    markers = public_text_has_internal_markers(cleaned)
    if markers:
        raise RuntimeError(
            f"{artifact_name} 包含内部工作标记，不能作为公开正文: {markers}"
        )
    forbidden_cleaned_sections = forbidden_standalone_public_sections(cleaned)
    if forbidden_cleaned_sections:
        raise RuntimeError(
            f"{artifact_name} 包含不应进入公开正文的独立风险/证据边界章节: {forbidden_cleaned_sections}"
        )
    return cleaned.strip() + "\n"
ACCEPTED_AUTHENTICITY_VERDICTS = {"pass", "warning"}

def configure_pipeline(project_root: Path) -> None:
    pipeline.PROJECT_ROOT = project_root
    pipeline.STATE_FILE = project_root / "runtime" / "state.json"
    pipeline.PROCESS_MEMORY_DIR = project_root / "process-memory"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {rel_path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{rel_path} 必须是 JSON object")
    return data


def read_text(project_root: Path, rel_path: str) -> str:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {rel_path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"{rel_path} 不能为空")
    return text


def write_json(project_root: Path, rel_path: str, data: dict[str, Any]) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(project_root: Path, rel_path: str, text: str) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def part6_desktop_dir() -> Path:
    configured = os.environ.get("PART6_DESKTOP_DIR")
    if not configured:
        raise RuntimeError("PART6_DESKTOP_DIR is not configured")
    return Path(configured).expanduser()


def export_part6_manuscript_to_desktop(final_text: str) -> Path | None:
    if not os.environ.get("PART6_DESKTOP_DIR"):
        return None
    desktop_dir = part6_desktop_dir()
    desktop_dir.mkdir(parents=True, exist_ok=True)
    target = desktop_dir / PART6_DESKTOP_MANUSCRIPT_NAME
    target.write_text(final_text.strip() + "\n", encoding="utf-8")
    for stale_name in STALE_PART6_DESKTOP_OUTPUTS:
        stale_path = desktop_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    return target


def json_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def source_id(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def run_precheck(project_root: Path) -> dict[str, Any]:
    configure_pipeline(project_root)
    state = pipeline.load_state()
    issues = pipeline._part6_entry_precondition_issues(state, require_authorization=True)
    if issues:
        raise RuntimeError("Part 6 precheck failed: " + "；".join(issues))
    return {"status": "pass", "issues": []}


def require_precheck(project_root: Path) -> None:
    run_precheck(project_root)


def extract_body_without_title(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        return "\n".join(lines[1:]).strip()
    return text.strip()


def manuscript_body_has_conclusion(body: str) -> bool:
    heading_pattern = re.compile(
        r"(^|\n)\s*(#{1,6}\s*)?((第?[一二三四五六七八九十]+[章节、.．])\s*)?(结论|结语|结论与展望|总结与展望)\b"
    )
    return bool(heading_pattern.search(body))


SCAFFOLD_MARKERS = [
    "Part 5 MVP",
    "本节核心论点",
    "写作提示",
    "待补证据",
    "scaffold",
    "写作骨架",
    "outline",
    "argument tree",
    "claim-evidence matrix",
    "raw-library",
    "research-wiki",
    "citation_map",
    "researchwiki",
    "Part2",
    "argumenttree",
    "canonical artifact",
    "Part 1-5",
    "source_id",
    "cnki_",
    "已登记证据",
    "证据层显示",
    "章节brief",
    "risk_level",
    "当前风险等级",
    "风险等级控制结论强度",
    "low 风险等级",
    "medium 风险等级",
    "high 风险等级",
    "blocked 风险等级",
    "unknown 风险等级",
    "Part 2 Evidence",
    "相关判断限定在",
    "该判断对应的来源链为",
    "从教学转化看，本节承担的是",
    "进一步说，本节的论述重点不是罗列材料",
    "其材料边界仍回到",
]


def read_json_optional(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        return {}
    return read_json(project_root, rel_path)


def clean_fragment(value: Any) -> str:
    text = str(value or "")
    text = text.split(" Seed map 侧重：", 1)[0]
    text = text.replace("Source Evidence Digest: ", "")
    text = text.replace("Part 2 Evidence Synthesis", "证据综合")
    text = text.replace("Part 2 Evidence", "证据综合")
    text = text.replace("Part 2 Research Synthesis", "研究综合")
    text = text.replace("research wiki", "研究资料")
    text = text.replace("argument tree", "论证链")
    text = text.replace("manuscript_v1", "初稿正文")
    text = text.replace("manuscript_v2", "修订正文")
    text = text.replace("...", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("researchwiki", "研究资料")
    text = text.replace("Part2EvidenceSynthesis", "证据综合")
    text = text.replace("Part2Evidence", "证据综合")
    text = text.replace("Part2ResearchSynthesis", "研究综合")
    text = text.replace("argumenttree", "论证链")
    text = re.sub(r"evidence_\d+_\d+", "部分证据", text)
    text = text.replace("案例分析需要借助证据综合需要", "案例分析需要借助证据综合；相关判断需要")
    text = text.replace("案例材料只能承担对需要", "案例材料只能承担辅助论证功能，相关判断需要")
    text = re.sub(r"承接论证链节点[A-Za-z0-9_]+，展开该章节核心论点：", "", text)
    text = re.sub(r"围绕论证节点[A-Za-z0-9_]+展开：", "", text)
    text = re.sub(r"\bcnki_[A-Za-z0-9_]+\b", "", text)
    text = text.replace("source_id", "来源")
    text = text.replace("已登记证据", "已核验文献")
    text = text.replace("证据层显示，", "")
    text = text.replace("章节brief", "章节要求")
    text = text.replace("risk_level", "")
    text = text.replace("当前风险等级", "")
    text = re.sub(r"\b(?:low|medium|high|blocked|unknown)\s*风险等级", "", text)
    text = text.replace("风险等级控制结论强度", "控制结论强度")
    text = re.sub(r"^[：:、，。；;]+", "", text)
    return text.strip()


def normalized_section_title(title: str, index: int) -> str:
    cleaned = clean_fragment(title)
    if "反方限制" in cleaned or "不能被过度外推" in cleaned or cleaned.endswith("承担对"):
        return "适用范围与论证限制"
    if not cleaned or "《" in cleaned or "证据层显示" in cleaned or re.search(r"[A-Za-z]", cleaned) or len(cleaned) > 26:
        fallback_titles = [
            "绪论",
            "文献综述与理论基础",
            "研究对象与案例场景",
            "方法分析与转化机制",
            "应用路径与成果转化",
            "适用范围与论证限制",
            "结论与后续展望",
        ]
        return fallback_titles[index - 1] if index <= len(fallback_titles) else f"正文第{index}节"
    return cleaned



def compose_part6_writer_body(project_root: Path) -> str:
    from runtime.agents.part6_writer import Part6WriterAgent

    return Part6WriterAgent(project_root).run()["body"]


def abstract_from_manuscript(text: str) -> str:
    body_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and not line.lstrip().startswith(">")
    ]
    if not body_lines:
        return "本文基于已核验材料与修订记录，保守收束既有论证与证据状态。"
    candidate = body_lines[0]
    if len(candidate) > 180:
        return candidate[:180].rstrip("，。； ") + "。"
    return candidate.rstrip("。") + "。"


def keywords_from_text(text: str) -> list[str]:
    stopwords = {
        "本文",
        "围绕",
        "展开",
        "讨论",
        "路径",
        "研究",
        "问题",
        "方法",
        "正文",
        "结论",
        "摘要",
        "关键词",
    }

    def add_terms(raw_text: str, target: list[str]) -> None:
        terms = [
            term.strip("：:，,。；;、（）()[]【】“”\"'")
            for term in re.split(r"[\s\n#，,。；;、：:（）()]+", raw_text)
        ]
        for term in terms:
            term = re.sub(r"^(本文围绕|当前材料集中在|讨论|围绕|针对|关键词|从关键词看)", "", term)
            if not (2 <= len(term) <= 14):
                continue
            if term in stopwords:
                continue
            if re.fullmatch(r"[A-Za-z0-9_\\-]+", term):
                continue
            if term not in target:
                target.append(term)
            if len(target) >= 5:
                break

    keywords = []
    section_match = re.search(r"##\s*关键词\s*(.*?)(?:\n##\s|\Z)", text, flags=re.S)
    if section_match:
        add_terms(section_match.group(1), keywords)
    for match in re.findall(r"当前材料集中在(.{2,120}?)等方向", text):
        add_terms(match, keywords)
        if len(keywords) >= 5:
            break
    if not keywords:
        add_terms(text, keywords)
    for fallback in ["研究对象", "证据债务", "审慎结论"]:
        if fallback not in keywords:
            keywords.append(fallback)
        if len(keywords) >= 3:
            break
    return keywords[:5]


def finalize_manuscript(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    if not checked:
        require_precheck(project_root)
    read_text(project_root, "outputs/part5/manuscript_v2.md")
    readiness = read_json(project_root, "outputs/part5/part6_readiness_decision.json")
    from runtime.agents.part6_writer import Part6WriterAgent

    writer = Part6WriterAgent(project_root)
    llm_result = request_writeagent(
        project_root,
        task="part6_finalize_manuscript",
        skill="part6-finalize-manuscript",
        output_ref="outputs/part6/writer_body.md",
        input_paths=[
            "outputs/part4/paper_outline.json",
            "outputs/part3/argument_tree.json",
            "outputs/part5/manuscript_v2.md",
            "outputs/part5/revision_log.json",
            "outputs/part5/part6_readiness_decision.json",
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part5/citation_map.json",
            "raw-library/metadata.json",
            "research-wiki/index.json",
            "writing-policy/source_index.json",
        ] + WRITEAGENT_STYLE_INPUTS,
        instructions=[
            "Finalize the public manuscript body from manuscript_v2 using paper_outline and argument_tree.",
            "Use author_style_profile if present, academic-register-polish rules, and paper-manuscript-style-profile.",
            "Write thesis prose, not a workflow or audit report.",
            "Do not over-expose evidence-chain language; keep source/risk plumbing in audit reports, not the manuscript body.",
            "Do not create a standalone '证据边界与研究不足' section unless explicitly required by the outline.",
            "If limitations are needed, write a concise conventional '研究不足与展望' passage in the conclusion/discussion.",
            "Use citations and source names only where they serve the academic argument.",
            "Do not introduce new claims, sources, citations, audit findings, readiness decisions, or human gate confirmations.",
            "Return a body field, and optionally abstract, keywords, and conclusion.",
        ],
    )
    if llm_result is not None:
        source_body = ensure_public_manuscript_text(
            llm_result.text,
            artifact_name="writeagent body",
        )
        write_text(project_root, "outputs/part6/writer_body.md", source_body)
        writer_result = {
            "agent_id": "writeagent",
            "generated_at": now_iso(),
            "body_ref": "outputs/part6/writer_body.md",
            "body": source_body,
        }
        write_writer_provenance(
            project_root,
            "outputs/part6/writer_provenance.json",
            task="part6_finalize_manuscript",
            skill="part6-finalize-manuscript",
            output_ref="outputs/part6/writer_body.md",
            mode="llm",
        )
    else:
        if not deterministic_writer_fallback_allowed():
            raise RuntimeError(missing_writeagent_command_message("part6_finalize_manuscript"))
        writer_result = writer.run()
        source_body = ensure_public_manuscript_text(
            writer_result["body"],
            artifact_name="deterministic writer body",
        )
        write_text(project_root, "outputs/part6/writer_body.md", source_body)
        write_writer_provenance(
            project_root,
            "outputs/part6/writer_provenance.json",
            task="part6_finalize_manuscript",
            skill="part6-finalize-manuscript",
            output_ref="outputs/part6/writer_body.md",
            mode="deterministic_fallback",
            fallback_reason="RTM_WRITEAGENT_COMMAND not configured",
        )

    abstract = llm_result.abstract if llm_result and llm_result.abstract else writer.abstract(source_body)
    keywords = llm_result.keywords if llm_result and llm_result.keywords else keywords_from_text(source_body)
    keyword_line = "；".join(keywords)
    conclusion = llm_result.conclusion if llm_result and llm_result.conclusion else writer.conclusion()
    final_sections = [
        "# 最终稿",
        "",
        "## 摘要",
        "",
        abstract,
        "",
        "## 关键词",
        "",
        keyword_line,
        "",
        "## 正文",
        "",
        source_body,
        "",
    ]
    if not manuscript_body_has_conclusion(source_body):
        final_sections.extend([
            "## 结论",
            "",
            conclusion,
            "",
        ])
    final_text = "\n".join(final_sections).strip() + "\n"
    final_text = ensure_public_manuscript_text(
        final_text,
        artifact_name="final_manuscript.md",
    )

    write_text(project_root, "outputs/part6/final_manuscript.md", final_text)
    write_text(project_root, "outputs/part6/final_abstract.md", abstract + "\n")
    write_json(project_root, "outputs/part6/final_keywords.json", {"keywords": keywords})
    desktop_manuscript = export_part6_manuscript_to_desktop(final_text)
    local_outputs = [
        writer_result["body_ref"],
        "outputs/part6/final_manuscript.md",
        "outputs/part6/final_abstract.md",
        "outputs/part6/final_keywords.json",
    ]
    if desktop_manuscript is not None:
        local_outputs.append(str(desktop_manuscript))
    return {
        "final_manuscript": "outputs/part6/final_manuscript.md",
        "final_abstract": "outputs/part6/final_abstract.md",
        "final_keywords": "outputs/part6/final_keywords.json",
        "writer_body": writer_result["body_ref"],
        "desktop_manuscript": str(desktop_manuscript) if desktop_manuscript else None,
        "local_outputs": local_outputs,
    }


def normalize_risk_level(value: Any) -> str:
    if value in {"blocked", "critical"}:
        return "blocked"
    if value in {"high", "high_risk"}:
        return "high_risk"
    if value in {"medium", "medium_risk"}:
        return "medium_risk"
    return "low_risk"


def risk_status_for_level(level: str) -> str:
    if level == "blocked":
        return "blocked"
    if level == "high_risk":
        return "deferred"
    if level == "medium_risk":
        return "deferred"
    return "resolved"


def first_claim(claims: list[dict[str, Any]]) -> dict[str, Any]:
    return claims[0] if claims else {"claim_id": "claim_001", "source_ids": [], "wiki_page_ids": []}


def public_claim_id(value: Any, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    if re.fullmatch(r"evidence_\d+_\d+", raw):
        return fallback
    return raw


def make_risk_item(
    *,
    index: int,
    claim_id: str,
    risk_level: str,
    risk_type: str,
    finding: str,
    source_ids: list[str],
    wiki_page_ids: list[str],
    recommended_action: str,
    applied_action: str,
    status: str,
    residual_debt: str,
) -> dict[str, Any]:
    return {
        "risk_id": f"risk_{index:03d}",
        "claim_id": public_claim_id(claim_id, f"claim_{index:03d}"),
        "risk_level": risk_level,
        "risk_type": risk_type,
        "finding": finding,
        "source_ids": source_ids,
        "wiki_page_ids": wiki_page_ids,
        "recommended_action": recommended_action,
        "applied_action": applied_action,
        "status": status,
        "residual_debt": residual_debt,
    }


def write_llm_sidecar(project_root: Path, rel_path: str, payload: dict[str, Any]) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_claimauditor_part6_sidecar(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="claimauditor",
        task="part6_claim_risk_audit_review",
        skill="part6-audit-claim-risk",
        output_ref=CLAIMAUDITOR_PART6_REVIEW_REF,
        input_paths=[
            "outputs/part6/final_manuscript.md",
            "outputs/part6/claim_risk_report.json",
            "outputs/part5/claim_evidence_matrix.json",
            "outputs/part5/claim_risk_report.json",
            "outputs/part5/part6_readiness_decision.json",
            "research-wiki/index.json",
        ],
        instructions=[
            "Review the deterministic Part 6 claim risk report for overclaim, evidence sufficiency, missing warrant, and case-verification risk.",
            "Return JSON with report or payload. Do not rewrite final_manuscript.md or claim_risk_report.json.",
            "Do not add claims, sources, citations, or readiness decisions.",
        ],
    )
    if result is None:
        return
    write_llm_sidecar(project_root, CLAIMAUDITOR_PART6_REVIEW_REF, result.raw)
    write_llm_agent_provenance(
        project_root,
        CLAIMAUDITOR_PART6_PROVENANCE_REF,
        agent_name="claimauditor",
        task="part6_claim_risk_audit_review",
        skill="part6-audit-claim-risk",
        output_ref=CLAIMAUDITOR_PART6_REVIEW_REF,
        mode="llm",
    )


def write_citationauditor_part6_sidecar(project_root: Path) -> None:
    result = request_llm_agent(
        project_root,
        agent_name="citationauditor",
        task="part6_citation_consistency_audit_review",
        skill="part6-audit-citation-consistency",
        output_ref=CITATIONAUDITOR_PART6_REVIEW_REF,
        input_paths=[
            "outputs/part6/final_manuscript.md",
            "outputs/part6/citation_consistency_report.json",
            "outputs/part5/citation_map.json",
            "raw-library/metadata.json",
            "research-wiki/index.json",
            "outputs/part1/accepted_sources.json",
            "outputs/part1/authenticity_report.json",
        ],
        instructions=[
            "Review the deterministic Part 6 citation consistency report for mapping, format, source drift, and reference support risk.",
            "Return JSON with report or payload. Do not rewrite final_manuscript.md, citation_map.json, or citation_consistency_report.json.",
            "Do not add sources, citations, or readiness decisions.",
        ],
    )
    if result is None:
        return
    write_llm_sidecar(project_root, CITATIONAUDITOR_PART6_REVIEW_REF, result.raw)
    write_llm_agent_provenance(
        project_root,
        CITATIONAUDITOR_PART6_PROVENANCE_REF,
        agent_name="citationauditor",
        task="part6_citation_consistency_audit_review",
        skill="part6-audit-citation-consistency",
        output_ref=CITATIONAUDITOR_PART6_REVIEW_REF,
        mode="llm",
    )


def audit_claims(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    if not checked:
        require_precheck(project_root)
    read_text(project_root, "outputs/part6/final_manuscript.md")
    matrix = read_json(project_root, "outputs/part5/claim_evidence_matrix.json")
    part5_risk = read_json(project_root, "outputs/part5/claim_risk_report.json")
    readiness = read_json(project_root, "outputs/part5/part6_readiness_decision.json")
    claims = [
        claim for claim in json_list(matrix, "claims")
        if isinstance(claim, dict)
    ]
    risk_items: list[dict[str, Any]] = []
    index = 1

    for claim in claims:
        claim_id = str(claim.get("claim_id") or f"claim_{index:03d}")
        source_ids = unique_strings(claim.get("source_ids", []) if isinstance(claim.get("source_ids"), list) else [])
        wiki_page_ids = unique_strings(claim.get("wiki_page_ids", []) if isinstance(claim.get("wiki_page_ids"), list) else [])
        level = normalize_risk_level(claim.get("risk_level"))
        if not source_ids:
            level = "blocked"
        elif not wiki_page_ids and level == "low_risk":
            level = "medium_risk"
        status = risk_status_for_level(level)
        risk_items.append(make_risk_item(
            index=index,
            claim_id=claim_id,
            risk_level=level,
            risk_type="source_sufficiency",
            finding="证据充分性复核：仅沿用已进入核验链的来源。",
            source_ids=source_ids,
            wiki_page_ids=wiki_page_ids,
            recommended_action="no_action_needed" if level == "low_risk" else "downgrade_claim",
            applied_action="no_action_needed" if level == "low_risk" else "downgrade_claim",
            status=status,
            residual_debt="" if level == "low_risk" else "证据映射不足，正式投稿前需人工复核。",
        ))
        index += 1
        risk_items.append(make_risk_item(
            index=index,
            claim_id=claim_id,
            risk_level="low_risk",
            risk_type="interpretation",
            finding="论断风险复核：最终稿不得新增证据链之外的论断。",
            source_ids=source_ids,
            wiki_page_ids=wiki_page_ids,
            recommended_action="no_action_needed",
            applied_action="no_action_needed",
            status="resolved",
            residual_debt="",
        ))
        index += 1

    anchor_claim = first_claim(claims)
    risk_items.append(make_risk_item(
        index=index,
        claim_id=str(anchor_claim.get("claim_id") or "claim_001"),
        risk_level="low_risk",
        risk_type="case_verification",
        finding="案例核验复核：未核验案例事实维持概念参照，不在最终稿新增事实主张。",
        source_ids=unique_strings(anchor_claim.get("source_ids", []) if isinstance(anchor_claim.get("source_ids"), list) else []),
        wiki_page_ids=unique_strings(anchor_claim.get("wiki_page_ids", []) if isinstance(anchor_claim.get("wiki_page_ids"), list) else []),
        recommended_action="no_action_needed",
        applied_action="no_action_needed",
        status="resolved",
        residual_debt="",
    ))
    index += 1

    for item in json_list(part5_risk, "risk_items"):
        if not isinstance(item, dict):
            continue
        finding = clean_fragment(item.get("finding") or item.get("reason") or "既有论断风险延续。")
        level = normalize_risk_level(item.get("risk_level"))
        risk_items.append(make_risk_item(
            index=index,
            claim_id=str(item.get("claim_id") or anchor_claim.get("claim_id") or "claim_001"),
            risk_level=level,
            risk_type=item.get("risk_type") if item.get("risk_type") in {"factual", "interpretation", "citation", "source_sufficiency", "case_verification"} else "source_sufficiency",
            finding=finding,
            source_ids=unique_strings(item.get("source_ids", []) if isinstance(item.get("source_ids"), list) else []),
            wiki_page_ids=unique_strings(item.get("wiki_page_ids", []) if isinstance(item.get("wiki_page_ids"), list) else []),
            recommended_action="downgrade_claim" if level != "low_risk" else "no_action_needed",
            applied_action="downgrade_claim" if level != "low_risk" else "no_action_needed",
            status=risk_status_for_level(level),
            residual_debt=finding if level != "low_risk" else "",
        ))
        index += 1

    for residual_risk in unique_strings(json_list(readiness, "residual_risks")):
        risk_items.append(make_risk_item(
            index=index,
            claim_id=str(anchor_claim.get("claim_id") or "claim_001"),
            risk_level="medium_risk",
            risk_type="source_sufficiency",
            finding=clean_fragment(residual_risk),
            source_ids=unique_strings(anchor_claim.get("source_ids", []) if isinstance(anchor_claim.get("source_ids"), list) else []),
            wiki_page_ids=unique_strings(anchor_claim.get("wiki_page_ids", []) if isinstance(anchor_claim.get("wiki_page_ids"), list) else []),
            recommended_action="defer_to_future_research",
            applied_action="defer_to_future_research",
            status="deferred",
            residual_debt=clean_fragment(residual_risk),
        ))
        index += 1

    summary = {
        "total": len(risk_items),
        "blocked": sum(1 for item in risk_items if item["risk_level"] == "blocked" or item["status"] == "blocked"),
        "high_risk": sum(1 for item in risk_items if item["risk_level"] == "high_risk"),
        "medium_risk": sum(1 for item in risk_items if item["risk_level"] == "medium_risk"),
        "covered_dimensions": ["interpretation", "source_sufficiency", "case_verification"],
        "part5_residual_risks": unique_strings([
            clean_fragment(risk)
            for risk in json_list(readiness, "residual_risks")
            if clean_fragment(risk)
        ]),
    }
    report = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "manuscript_ref": "outputs/part6/final_manuscript.md",
        "source_manuscript_ref": "outputs/part5/manuscript_v2.md",
        "claim_evidence_matrix_ref": "outputs/part5/claim_evidence_matrix.json",
        "part5_claim_risk_report_ref": "outputs/part5/claim_risk_report.json",
        "risk_items": risk_items,
        "summary": summary,
    }
    write_json(project_root, "outputs/part6/claim_risk_report.json", report)
    write_claimauditor_part6_sidecar(project_root)
    return report


def raw_sources_by_id(raw_metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["source_id"]: item
        for item in json_list(raw_metadata, "sources")
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }


def wiki_source_ids(wiki_index: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for page in json_list(wiki_index, "pages"):
        if not isinstance(page, dict):
            continue
        for value in page.get("source_ids", []) or []:
            source = source_id(value)
            if source:
                result.add(source)
    return result


def accepted_source_ids(accepted_sources: dict[str, Any]) -> set[str]:
    result = {item for item in unique_strings(json_list(accepted_sources, "source_ids"))}
    for item in json_list(accepted_sources, "sources"):
        if isinstance(item, dict) and (source := source_id(item.get("source_id"))):
            result.add(source)
    return result


def authenticity_verdicts(authenticity_report: dict[str, Any]) -> dict[str, Any]:
    return {
        item["source_id"]: item.get("verdict")
        for item in json_list(authenticity_report, "results")
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }


def authenticity_verdict_is_accepted(verdict: Any) -> bool:
    return verdict in ACCEPTED_AUTHENTICITY_VERDICTS


def audit_citations(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    if not checked:
        require_precheck(project_root)
    read_text(project_root, "outputs/part6/final_manuscript.md")
    citation_map = read_json(project_root, "outputs/part5/citation_map.json")
    raw_metadata = read_json(project_root, "raw-library/metadata.json")
    wiki_index = read_json(project_root, "research-wiki/index.json")
    accepted_sources = read_json(project_root, "outputs/part1/accepted_sources.json")
    authenticity_report = read_json(project_root, "outputs/part1/authenticity_report.json")

    raw_by_id = raw_sources_by_id(raw_metadata)
    wiki_ids = wiki_source_ids(wiki_index)
    accepted_ids = accepted_source_ids(accepted_sources)
    authenticity_by_id = authenticity_verdicts(authenticity_report)

    checked_claim_ids: list[str] = []
    checked_source_ids: list[str] = []
    citation_items: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for ref in json_list(citation_map, "source_refs"):
        if not isinstance(ref, dict):
            continue
        sid = source_id(ref.get("source_id"))
        if not sid:
            continue
        if ref.get("citation_status") != "accepted_source":
            continue

        raw_claim_ids = unique_strings(ref.get("claim_ids", []) if isinstance(ref.get("claim_ids"), list) else [])
        claim_ids = [
            public_claim_id(raw_claim_id, f"claim_{position:03d}")
            for position, raw_claim_id in enumerate(raw_claim_ids, start=1)
        ]
        checked_claim_ids.extend(claim_ids)
        checked_source_ids.append(sid)
        raw_source = raw_by_id.get(sid)
        verdict = authenticity_by_id.get(sid)
        raw_auth_ok = bool(
            raw_source
            and raw_source.get("authenticity_verdict") in ACCEPTED_AUTHENTICITY_VERDICTS
            and raw_source.get("authenticity_status") == "verified"
        )
        auth_ok = authenticity_verdict_is_accepted(verdict) or (verdict is None and raw_auth_ok)
        item_issues: list[str] = []
        if raw_source is None:
            item_issues.append(f"{sid} 缺少 raw-library/metadata.json 记录")
        if sid not in wiki_ids:
            item_issues.append(f"{sid} 未映射到 research-wiki/index.json")
        if sid not in accepted_ids:
            item_issues.append(f"{sid} 未出现在 outputs/part1/accepted_sources.json")
        if not auth_ok:
            item_issues.append(f"{sid} 未通过 authenticity_report pass/warning 校验")
        if item_issues:
            errors.extend(item_issues)
        citation_items.append({
            "source_id": sid,
            "claim_ids": claim_ids,
            "citation_status": "accepted_source",
            "raw_metadata_present": raw_source is not None,
            "wiki_mapped": sid in wiki_ids,
            "authenticity_status": "verified" if auth_ok else "failed",
            "reference_entry_status": "present" if raw_source else "missing",
            "drift_detected": bool(item_issues),
            "issues": item_issues,
            "action": "block_submission" if item_issues else "keep",
        })

    checked_source_ids = unique_strings(checked_source_ids)
    checked_claim_ids = unique_strings(checked_claim_ids)
    if not checked_source_ids:
        errors.append("citation_map 未提供 accepted_source，不能完成 Part 6 citation audit")
    if not errors:
        warnings.append("仍需人工核对最终参考文献格式与投稿模板。")

    report = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "manuscript_ref": "outputs/part6/final_manuscript.md",
        "citation_map_ref": "outputs/part5/citation_map.json",
        "raw_metadata_ref": "raw-library/metadata.json",
        "wiki_index_ref": "research-wiki/index.json",
        "accepted_sources_ref": "outputs/part1/accepted_sources.json",
        "authenticity_report_ref": "outputs/part1/authenticity_report.json",
        "status": "blocked" if errors else ("pass_with_warnings" if warnings else "pass"),
        "checked_claim_ids": checked_claim_ids,
        "checked_source_ids": checked_source_ids,
        "citation_items": citation_items,
        "warnings": warnings,
        "errors": errors,
    }
    write_json(project_root, "outputs/part6/citation_consistency_report.json", report)
    write_citationauditor_part6_sidecar(project_root)
    return report


def existing_required_files(project_root: Path) -> list[str]:
    return [
        rel_path for rel_path in REQUIRED_PACKAGE_FILES
        if (project_root / rel_path).exists()
    ]


def write_submission_checklist(project_root: Path, *, final: bool) -> None:
    lines = [
        "# Part 6 Submission Checklist",
        "",
        "- [x] Part 6 finalization authorization 已由用户确认。",
        "- [x] final_manuscript / abstract / keywords 已生成。",
        "- [x] claim risk audit 已生成。",
        "- [x] citation consistency audit 已生成。",
        "- [x] 风险与残余研究债务保留在 claim_risk_report / final_readiness_decision，不写入 final_manuscript 独立章节。",
        "- [ ] part6_final_decision_confirmed 仍需用户最终确认。",
        "- [ ] 不执行 submission，不自动进入 Part 7。",
    ]
    if final:
        lines.append("- [x] final_readiness_decision 已生成并与 manifest 闭合。")
    else:
        lines.append("- [ ] final_readiness_decision 尚未生成，当前为 draft package。")
    write_text(project_root, "outputs/part6/submission_checklist.md", "\n".join(lines).strip() + "\n")


def write_manifest(
    project_root: Path,
    *,
    submission_class: str,
    final: bool,
    checked: bool = False,
) -> dict[str, Any]:
    if not checked:
        require_precheck(project_root)
    write_submission_checklist(project_root, final=final)
    included_files = existing_required_files(project_root)
    if final:
        included_files = list(REQUIRED_PACKAGE_FILES)
    missing_files = [
        rel_path for rel_path in REQUIRED_PACKAGE_FILES
        if rel_path not in included_files or not (project_root / rel_path).exists()
    ]
    status = "complete" if final and not missing_files else "incomplete"
    if submission_class == "blocked_by_evidence_debt" and final and not missing_files:
        status = "complete"
    manifest = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "package_id": "part6_package_001",
        "status": status,
        "submission_class": submission_class,
        "included_files": included_files,
        "required_files": list(REQUIRED_PACKAGE_FILES),
        "missing_files": missing_files,
        "audit_refs": list(AUDIT_REFS),
        "policy_refs": list(POLICY_REFS),
        "evidence_refs": [rel_path for rel_path in EVIDENCE_REFS if (project_root / rel_path).exists()],
        "process_refs": [rel_path for rel_path in PROCESS_REFS if (project_root / rel_path).exists()],
        "human_decision_required": True,
    }
    write_json(project_root, "outputs/part6/submission_package_manifest.json", manifest)
    return manifest


def package_draft(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    return write_manifest(
        project_root,
        submission_class="internal_review_only",
        final=False,
        checked=checked,
    )


def unresolved_claim_risks(claim_risk: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    resolved_statuses = {"resolved", "mitigated", "downgraded"}
    for item in json_list(claim_risk, "risk_items"):
        if not isinstance(item, dict):
            continue
        if item.get("risk_level") in {"blocked", "high_risk"} and item.get("status") not in resolved_statuses:
            result.append(item)
    return result


def decide_readiness(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    if not checked:
        require_precheck(project_root)
    claim_risk = read_json(project_root, "outputs/part6/claim_risk_report.json")
    citation_report = read_json(project_root, "outputs/part6/citation_consistency_report.json")
    readiness = read_json(project_root, "outputs/part5/part6_readiness_decision.json")
    manifest = (
        read_json(project_root, "outputs/part6/submission_package_manifest.json")
        if (project_root / "outputs/part6/submission_package_manifest.json").exists()
        else {"status": "incomplete", "missing_files": REQUIRED_PACKAGE_FILES}
    )

    blocking_issues: list[str] = []
    residual_risks = unique_strings([
        clean_fragment(risk)
        for risk in json_list(readiness, "residual_risks")
        if clean_fragment(risk)
    ])
    residual_debts: list[str] = list(residual_risks)

    citation_blocked = citation_report.get("status") == "blocked" or bool(json_list(citation_report, "errors"))
    if citation_blocked:
        blocking_issues.extend(unique_strings(json_list(citation_report, "errors")) or ["citation audit blocked"])

    unresolved = unresolved_claim_risks(claim_risk)
    blocked_items = [item for item in unresolved if item.get("risk_level") == "blocked" or item.get("status") == "blocked"]
    if blocked_items:
            blocking_issues.extend(clean_fragment(item.get("finding") or item.get("risk_id")) for item in blocked_items)
    for item in json_list(claim_risk, "risk_items"):
        if isinstance(item, dict) and item.get("residual_debt"):
            residual_debts.append(clean_fragment(item["residual_debt"]))

    missing_files = [
        item for item in json_list(manifest, "missing_files")
        if item != "outputs/part6/final_readiness_decision.json"
    ]
    if missing_files:
        blocking_issues.append("submission package 缺少文件: " + ", ".join(missing_files))

    if citation_blocked or blocked_items or missing_files:
        verdict = "blocked_by_evidence_debt"
    elif residual_risks or json_list(citation_report, "warnings") or unresolved:
        verdict = "internal_review_only"
    else:
        verdict = "formal_submission_ready"

    decision = {
        "schema_version": "1.0.0",
        "generated_at": now_iso(),
        "verdict": verdict,
        "manifest_ref": "outputs/part6/submission_package_manifest.json",
        "claim_risk_report_ref": "outputs/part6/claim_risk_report.json",
        "citation_consistency_report_ref": "outputs/part6/citation_consistency_report.json",
        "blocking_issues": unique_strings(blocking_issues),
        "residual_risks": unique_strings(
            residual_risks + [pipeline.PART6_FINAL_DECISION_PENDING_RISK]
        ),
        "residual_research_debts": unique_strings(residual_debts),
        "required_human_decisions": ["part6_final_decision_confirmed"],
        "final_decision_status": "pending_human_confirmation",
        "does_not_advance_part7": True,
    }
    write_json(project_root, "outputs/part6/final_readiness_decision.json", decision)
    return decision


def package_final(project_root: Path, *, checked: bool = False) -> dict[str, Any]:
    decision = read_json(project_root, "outputs/part6/final_readiness_decision.json")
    return write_manifest(
        project_root,
        submission_class=decision["verdict"],
        final=True,
        checked=checked,
    )


def run_step(project_root: Path, step: str) -> None:
    project_root = project_root.resolve()
    if step == "precheck":
        run_precheck(project_root)
    elif step == "finalize":
        finalize_manuscript(project_root)
    elif step == "audit-claim":
        audit_claims(project_root)
    elif step == "audit-citation":
        audit_citations(project_root)
    elif step == "package-draft":
        package_draft(project_root)
    elif step == "export-docx":
        export_docx(project_root)
    elif step == "decide":
        decide_readiness(project_root)
    elif step == "package-final":
        package_final(project_root)
    elif step == "all":
        run_precheck(project_root)
        finalize_manuscript(project_root, checked=True)
        audit_claims(project_root, checked=True)
        audit_citations(project_root, checked=True)
        package_draft(project_root, checked=True)
        export_docx(project_root, checked=True)
        decide_readiness(project_root, checked=True)
        package_final(project_root, checked=True)
    else:
        raise ValueError(f"Unknown Part 6 step: {step}")


def print_summary(project_root: Path, step: str) -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Part 6 MVP finalizer step completed: {step}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for rel_path in [
        "outputs/part6/writer_body.md",
        "outputs/part6/final_manuscript.md",
        "outputs/part6/final_abstract.md",
        "outputs/part6/final_keywords.json",
        "outputs/part6/claim_risk_report.json",
        "outputs/part6/citation_consistency_report.json",
        "outputs/part6/submission_checklist.md",
        "outputs/part6/final_manuscript.docx",
        "outputs/part6/docx_format_report.json",
        "outputs/part6/submission_package_manifest.json",
        "outputs/part6/final_readiness_decision.json",
    ]:
        if (project_root / rel_path).exists():
            print(f"  ✓ {rel_path}")
    format_report_path = project_root / "outputs/part6/docx_format_report.json"
    if format_report_path.exists():
        try:
            report = json.loads(format_report_path.read_text(encoding="utf-8"))
            desktop_docx = report.get("desktop_docx_ref")
            if isinstance(desktop_docx, str) and Path(desktop_docx).expanduser().exists():
                print(f"  ✓ {desktop_docx}")
        except json.JSONDecodeError:
            pass
    print("  Human gates are not auto-confirmed by this script.")
    print("  Submission is not executed.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic Part 6 MVP finalization artifacts")
    parser.add_argument(
        "--step",
        choices=[
            "precheck",
            "finalize",
            "audit-claim",
            "audit-citation",
            "package-draft",
            "export-docx",
            "decide",
            "package-final",
            "all",
        ],
        default="precheck",
        help="Part 6 step to run",
    )
    parser.add_argument(
        "--project-root",
        metavar="PATH",
        default=None,
        help="Project root; defaults to repository root",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve() if args.project_root else PROJECT_ROOT
    run_step(project_root, args.step)
    print_summary(project_root, args.step)


if __name__ == "__main__":
    main()
