#!/usr/bin/env python3
"""
Dedicated Part 6 writer agent.

This agent owns only the public manuscript body. It reads canonical handoff
artifacts, writes outputs/part6/writer_body.md, and leaves final package,
audit, readiness, and human gate handling to the Part 6 finalizer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.writing_contract import remove_internal_lines  # noqa: E402

WRITER_BODY_REF = "outputs/part6/writer_body.md"

SCAFFOLD_MARKERS = [
    "Part 5 MVP",
    "本节核心论点",
    "本节围绕已确认论证",
    "展开该章节核心论点",
    "展开该层论点",
    "围绕该章节论点展开",
    "围绕该层论点展开",
    "这一部分首先说明",
    "相关判断以现有材料能够支持的范围为限",
    "基于已整理研究材料梳理",
    "提出研究背景、问题意识",
    "经结构、论证、证据、引用和写作规范复核",
    "修订稿的任务不是扩大论证范围",
    "论述范围限定在现有材料可以支持的边界内",
    "在此基础上，论文首先说明",
    "回收主论题",
    "claim audit",
    "claimaudit",
    "citation audit",
    "citationaudit",
    "写作提示",
    "待补证据",
    "scaffold",
    "写作骨架",
    "outline",
    "argument tree",
    "claim-evidence matrix",
    "raw-library",
    "research-wiki",
    "research wiki",
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
    "已登记材料",
    "本文主张：",
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
    "从实践转化看，本节承担的是",
    "进一步说，本节的论述重点不是罗列材料",
    "其材料边界仍回到",
]


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


def read_json_optional(project_root: Path, rel_path: str) -> dict[str, Any]:
    path = project_root / rel_path
    if not path.exists():
        return {}
    return read_json(project_root, rel_path)


def read_text(project_root: Path, rel_path: str) -> str:
    path = project_root / rel_path
    if not path.exists():
        raise FileNotFoundError(f"缺少必需 artifact: {rel_path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"{rel_path} 不能为空")
    return text


def write_text(project_root: Path, rel_path: str, text: str) -> None:
    path = project_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def json_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    return value if isinstance(value, list) else []


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


def text_values(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return unique_strings([str(value).strip() for value in values if str(value).strip()])


def source_records(raw_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in json_list(raw_metadata, "sources"):
        if isinstance(item, dict):
            records.append(item)
    return records


def primary_source(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return records[0] if records else None


def clean_author(value: Any) -> str:
    text = clean_fragment(value)
    text = re.sub(r"[(（].*?[)）]", "", text)
    return text or "相关作者"


def source_citation(source: dict[str, Any] | None) -> str:
    if not source:
        return "已核验资料"
    authors = source.get("authors") if isinstance(source.get("authors"), list) else []
    author = clean_author(authors[0]) if authors else "相关作者"
    year = str(source.get("year") or "").strip()
    return f"{author}（{year}）" if year else author


def source_title(source: dict[str, Any] | None) -> str:
    if not source:
        return "已核验资料"
    return clean_fragment(source.get("title") or "已核验资料")


def display_source_title(source: dict[str, Any] | None) -> str:
    title = source_title(source)
    if title.startswith("《") and "》:" in title:
        return title.split(":", 1)[0]
    return title if title.startswith("《") else f"《{title}》"


def clean_source_abstract(value: Any) -> str:
    text = clean_fragment(value)
    text = text.replace("<正>", "")
    text = re.sub(r"^作者.*?出版时间\d{4}年", "", text)
    text = re.sub(r"ISBN[0-9Xx-]+", "", text)
    return text.strip()


def source_abstract_points(source: dict[str, Any] | None) -> list[str]:
    if not source:
        return ["现有资料提示，当前研究对象需要结合已核验来源进行保守分析。"]
    abstract = clean_source_abstract(source.get("abstract") or "")
    raw_sentences = re.split(r"[。；;]", abstract)
    points = [
        sentence.strip()
        for sentence in raw_sentences
        if sentence.strip() and len(sentence.strip()) >= 14
    ]
    if points:
        return points[:4]
    keywords = "、".join(text_values(source.get("keywords")))
    return [f"该来源围绕{keywords or '当前研究主题'}展开。"]


def public_part5_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(">") or line.startswith("-"):
            continue
        if any(marker in line for marker in SCAFFOLD_MARKERS):
            continue
        cleaned = clean_fragment(line)
        if len(cleaned) >= 36:
            paragraphs.append(cleaned.rstrip("。") + "。")
    return unique_strings(paragraphs)[:6]


class Part6WriterAgent:
    agent_id = "part6_writer"
    output_ref = WRITER_BODY_REF

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def run(self) -> dict[str, Any]:
        body = self.compose_body()
        write_text(self.project_root, self.output_ref, body)
        return {
            "agent_id": self.agent_id,
            "generated_at": now_iso(),
            "body_ref": self.output_ref,
            "body": body,
        }

    def write(self) -> dict[str, Any]:
        return self.run()

    def write_body(self) -> str:
        return self.run()["body"]

    def intake_profile(self) -> dict[str, Any]:
        intake = read_json_optional(self.project_root, "outputs/part1/intake.json")
        return {
            "topic": clean_fragment(intake.get("research_topic") or "当前研究主题"),
            "question": clean_fragment(
                intake.get("research_question")
                or "当前研究问题尚未填写，正文只能依据已核验材料保守展开。"
            ),
            "core_questions": [clean_fragment(item) for item in text_values(intake.get("core_research_questions"))],
            "required_keywords": [clean_fragment(item) for item in text_values(intake.get("keywords_required"))],
            "suggested_keywords": [clean_fragment(item) for item in text_values(intake.get("keywords_suggested"))],
            "scope_notes": clean_fragment(intake.get("scope_notes") or ""),
        }

    def source_records(self) -> list[dict[str, Any]]:
        raw_metadata = read_json_optional(self.project_root, "raw-library/metadata.json")
        records = source_records(raw_metadata)
        citation_map = read_json_optional(self.project_root, "outputs/part5/citation_map.json")
        accepted_ids = [
            item.get("source_id")
            for item in json_list(citation_map, "source_refs")
            if isinstance(item, dict)
            and item.get("citation_status") == "accepted_source"
            and isinstance(item.get("source_id"), str)
        ]
        if not accepted_ids:
            return records
        by_id = {
            item.get("source_id"): item
            for item in records
            if isinstance(item.get("source_id"), str)
        }
        ordered = [by_id[source_id] for source_id in accepted_ids if source_id in by_id]
        return ordered or records

    def evidence_overview(self, records: list[dict[str, Any]]) -> str:
        if not records:
            return "现有已核验资料数量不足，正文只能提出保守的写作框架。"
        source = primary_source(records)
        assert source is not None
        title = display_source_title(source)
        citation = source_citation(source)
        return f"目前可直接回溯的资料以{title}为核心，正文据此采用{citation}所提供的摘要与关键词信息。"

    def writer_keywords(self, profile: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
        values = list(profile["required_keywords"]) + list(profile["suggested_keywords"])
        for source in records:
            values.extend(text_values(source.get("keywords")))
        return unique_strings([item for item in values if item])[:12]

    def abstract(self, body: str | None = None) -> str:
        profile = self.intake_profile()
        records = self.source_records()
        source = primary_source(records)
        source_part = display_source_title(source) if source else "已核验资料"
        source_count = len(records)
        evidence_scope = (
            "由于当前证据仍以单一来源为主，本文将结论限定为阶段性判断。"
            if source_count <= 1
            else "本文在多来源材料之间保持证据边界，避免把个别材料扩大为普遍结论。"
        )
        abstract = (
            f"本文围绕{profile['topic']}展开，针对“{profile['question']}”这一问题，"
            f"基于{source_part}等已核验资料，分析研究对象、问题场景、实施路径与证据边界之间的关系。"
            "研究采用文献消化、概念提炼、路径归纳与边界审查的方法，将来源材料转化为可回溯的论文论证。"
            "正文围绕“对象识别—问题诊断—路径建构—条件说明—边界收束”的链条展开，并说明关键概念、实践机制与治理条件之间的衔接关系。"
            f"{evidence_scope}"
        )
        return abstract.rstrip("。；;") + "。"

    def conclusion(self) -> str:
        profile = self.intake_profile()
        records = self.source_records()
        source_count = len(records)
        evidence_sentence = (
            "受限于当前可回溯资料数量，相关结论仍需后续案例材料、过程记录与评价材料继续验证。"
            if source_count <= 1
            else "后续仍需结合更多案例材料和评价材料检验其适用范围。"
        )
        return (
            f"综上，{profile['topic']}需要在明确研究对象、问题场景和证据范围的基础上推进，"
            "不能把材料描述直接写成普遍结论。"
            "正文可以确认的是：已核验资料能够支撑对象识别、问题诊断、路径归纳和实施条件说明，"
            "但强结论仍必须受到来源数量、材料类型与案例充分性的约束。"
            f"{evidence_sentence}"
        )

    def compose_body(self) -> str:
        profile = self.intake_profile()
        records = self.source_records()
        source = primary_source(records)
        points = source_abstract_points(source)
        overview = self.evidence_overview(records)
        keywords = self.writer_keywords(profile, records)
        topic = profile["topic"]
        question = profile["question"]
        source_name = display_source_title(source)
        citation = source_citation(source)
        accepted_source_count = len(records)
        keyword_line = "、".join(keywords[:8]) or topic
        first_point = points[0].rstrip("。；;") if points else "该来源围绕当前研究主题展开"
        single_source_note = (
            "由于当前进入主证据链的已核验资料仍以单一来源为主，本文不把相关判断写成成熟的实证结论，"
            "而是将其处理为路径分析与条件说明层面的阶段性论证。"
            if accepted_source_count <= 1
            else "由于不同来源的材料类型与论证侧重点并不完全一致，本文在综合时保持来源边界与表述强度。"
        )

        sections = [
            (
                "绪论：研究背景与问题提出",
                [
                    (
                        f"{topic}的研究价值，首先来自现实问题与既有材料之间的张力。"
                        f"围绕“{question}”这一问题，本文不把研究对象处理为孤立概念，"
                        "而是把它放回具体场景、行动路径与制度条件中理解。"
                        "这样的写法能够避免把背景描述直接替代问题分析。"
                    ),
                    (
                        f"{overview}这一资料基础提示，本文需要同时处理对象界定、问题诊断与路径论证。"
                        "相较于罗列资料，正文更关注材料能够支撑哪些判断、不能支撑哪些判断，"
                        "并在每一层论证中保留来源边界。"
                        f"{single_source_note}"
                    ),
                    (
                        "因此，本文的写作目标不是证明某一套方案已经完全成立，"
                        "而是在已核验材料范围内搭建一条可解释、可回溯、可继续验证的论证路径。"
                        "这一定位能够避免把局部材料拔高为总体结论，同时为后续补充案例和评价材料留下空间。"
                    ),
                ],
            ),
            (
                "文献综述与理论基础",
                [
                    (
                        f"已核验资料显示，{source_name}为本文提供了可回溯的理论入口。"
                        f"{first_point}。这一表述说明，当前论文不宜只做概念铺陈，"
                        "还需要把来源中的对象、问题、方法和边界转化为可检验的论证单元。"
                    ),
                    (
                        f"从关键词看，当前材料集中在{keyword_line}等方向。"
                        "这些关键词共同指向一个基本任务：先明确研究对象的范围，"
                        "再解释对象与问题场景之间的联系，最后说明可操作路径与实施条件。"
                        "文献综述部分因此不宜写成宽泛的研究史罗列，而应围绕“资料如何支撑本文主张”展开。"
                    ),
                    (
                        f"同时，{citation}所能支撑的是材料消化和案例参考层面的论证，而不是完整的实证证明。"
                        "这意味着本文在综述中需要保留两个边界：一是不能使用“学界普遍认为”等缺乏来源支撑的说法；"
                        "二是不能把对象价值直接等同于实践结果。"
                        "后续章节的分析必须在这一边界内推进。"
                    ),
                ],
            ),
            (
                "研究对象与问题场景",
                [
                    (
                        "研究对象的界定决定了论文能够讨论到什么程度。"
                        "如果对象边界不清，后续路径就会变成泛化建议；如果场景边界不清，材料就难以进入问题分析。"
                        "因此，本节首先把对象、空间、主体、制度和实施条件区分开来，避免把不同层次的问题混写在一起。"
                    ),
                    (
                        "问题场景的分析需要回答三件事：谁受到影响，影响体现在哪里，改善或更新需要依赖哪些条件。"
                        "这些问题不能只依靠价值判断完成，还需要回到已核验材料中的案例、政策、方法和评价描述。"
                        "当场景被拆解为主体需求、设施条件、行动路径和治理约束时，论文主张才有可落地的解释基础。"
                    ),
                    (
                        "在这一基础上，正文可以把对象价值、问题压力和实施条件连接起来。"
                        "对象价值说明为什么值得研究，问题压力说明为什么必须行动，实施条件说明哪些做法可以被审慎提出。"
                        "三者相互制约，能够防止论文从单一材料直接跳到全局性结论。"
                    ),
                ],
            ),
            (
                "路径机制与实施条件",
                [
                    (
                        "路径机制可以按照“识别—诊断—介入—评估—反馈”的顺序展开。"
                        "识别阶段解决对象与问题范围，诊断阶段确认主要矛盾，介入阶段提出可执行做法，"
                        "评估阶段检查效果与副作用，反馈阶段把经验重新纳入后续修正。"
                    ),
                    (
                        "这一机制能够把资料分析和实践建议连接起来。"
                        "资料分析不应只说明已有研究说了什么，还应判断哪些做法具有条件，哪些做法仍缺少证据。"
                        "当路径从识别逐步进入实施时，论文需要持续说明责任主体、资源条件、政策约束和评价依据。"
                    ),
                    (
                        "实施条件是路径能否成立的关键。"
                        "如果缺少资金、产权协调、技术标准、维护责任或公众参与，方案就容易停留在文本层面。"
                        "因此，本文把路径写成条件化建议：能做什么、由谁推动、依赖哪些资源、如何判断效果，都需要在来源范围内说明。"
                    ),
                ],
            ),
            (
                "应用路径与治理建议",
                [
                    (
                        "应用路径需要从低风险、可验证的环节开始。"
                        "第一步是建立对象台账和问题清单，第二步是把问题按紧迫程度、实施难度和资金需求分层，"
                        "第三步是选择可回溯的试点做法，第四步是根据评价结果调整后续安排。"
                    ),
                    (
                        "这种路径的优势在于把目标、资源和评价放在同一治理框架中。"
                        "前期通过资料整理明确研究对象，中期通过方法比较筛选行动方案，后期通过过程记录和反馈材料判断方案效果。"
                        "如果研究还涉及成果转化或公共传播，也应以证据充分性和主体需求为前提。"
                    ),
                    (
                        "评价方式也需要与研究目标一致。"
                        "评价不能只看是否提出了方案，还应考察对象识别是否准确、问题诊断是否充分、实施条件是否明确、证据边界是否被遵守。"
                        "这种评价标准能够把研究判断和实践建议连接起来，使论文结论保持可执行但不过度外推。"
                    ),
                ],
            ),
            (
                "研究收束与后续展望",
                [
                    (
                        f"本文的证据边界需要明确说明。当前进入主证据链的资料数量为{accepted_source_count}，"
                        "且主要依赖题名、摘要、关键词和研究维度映射；这足以支持实践路径转化框架的保守搭建，"
                        "但不足以支撑具体实施成效或长期影响的强结论。"
                        "因此，本文只把相关路径写成可操作建议，而不把它写成已经被实证检验的模式。"
                    ),
                    (
                        "另一个限制来自案例材料。若缺少图纸、过程记录、访谈、评价表和后续反馈等材料，"
                        "案例分析就不能承担完整证明功能，只能承担对象说明、方法示范和问题提示功能。"
                        "这并不削弱本文的写作价值，反而能够让论证保持清楚边界：当前材料可以支撑路径归纳和条件说明，"
                        "但具体成效还需要后续实践记录和评价材料继续验证。"
                    ),
                    (
                        "基于上述边界，后续研究可以从三个方向补强：一是扩展文献来源，补充不同类型的案例；"
                        "二是整理对象清单、问题清单、过程资料和评价材料，形成可复核的数据基础；"
                        "三是通过实践跟踪记录主体反馈、实施成本和维护结果。"
                        "这些补充将使本文提出的路径从理论框架进一步走向实践检验。"
                    ),
                ],
            ),
        ]

        body_parts = [
            f"## {title}\n\n" + "\n\n".join(paragraphs)
            for title, paragraphs in sections
        ]
        preserved_paragraphs = public_part5_paragraphs(read_text(self.project_root, "outputs/part5/manuscript_v2.md"))
        if preserved_paragraphs:
            body_parts.append("## 补充论证\n\n" + "\n\n".join(preserved_paragraphs))

        body = "\n\n".join(body_parts)
        for marker in SCAFFOLD_MARKERS:
            body = body.replace(marker, "")
        body = remove_internal_lines(body)
        return body.strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the dedicated Part 6 writer agent")
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
    result = Part6WriterAgent(project_root).run()
    print(f"Part 6 writer agent completed: {result['body_ref']}")


if __name__ == "__main__":
    main()
