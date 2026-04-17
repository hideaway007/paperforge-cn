from __future__ import annotations

import re
from typing import Any


INTERNAL_MARKERS = [
    "Seed map",
    "Seed map 侧重",
    "Refine 补充",
    "本节核心论点",
    "本节围绕已确认论证",
    "展开该章节核心论点",
    "展开该层论点",
    "写作提示",
    "写作骨架",
    "scaffold",
    "Part 5 MVP",
    "claim-evidence matrix",
    "argument tree",
    "research-wiki",
    "research wiki",
    "raw-library",
    "citation_map",
    "cnki_",
    "Part2",
    "Part 2 Evidence",
    "argumenttree",
    "canonical artifact",
    "Part 1-5",
    "source_id",
    "risk_level",
    "当前风险等级",
    "风险等级控制结论强度",
    "low 风险等级",
    "medium 风险等级",
    "high 风险等级",
    "blocked 风险等级",
    "unknown 风险等级",
    "review_matrix",
    "revision_log",
    "review_id",
    "证据层显示",
    "章节brief",
    "已登记材料",
    "已登记证据",
    "相关判断限定在",
    "该判断对应的来源链为",
    "修订后论证整合",
    "这一部分首先说明",
    "相关判断以现有材料能够支持的范围为限",
    "从实践转化看，本节承担的是",
    "进一步说，本节的论述重点不是罗列材料",
    "其材料边界仍回到",
]


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_claim_text(value: Any) -> str:
    text = compact_text(value)
    if not text:
        return ""
    for marker in [
        "Seed map 侧重：",
        "Seed map 侧重:",
        "Refine 补充：",
        "Refine 补充:",
        " Seed map 侧重：",
        " Seed map 侧重:",
        " Refine 补充：",
        " Refine 补充:",
        " Seed map ",
        " Refine ",
    ]:
        if marker in text:
            before, after = text.split(marker, 1)
            text = (before if before.strip() else after).strip()
    text = re.sub(r"^Refine\s*补充后?的?", "", text).strip()
    text = text.replace("证据层显示，", "")
    text = text.replace("证据层显示,", "")
    text = re.sub(r"\bcnki_[A-Za-z0-9_]+\b", "已核验资料", text)
    text = text.replace("source_id", "来源")
    text = text.replace("risk_level", "风险等级")
    text = re.sub(r"承接 argument tree 节点\s*[A-Za-z0-9_]+[，,]?", "", text)
    text = re.sub(r"围绕论证节点\s*[A-Za-z0-9_]+展开[：:]?", "", text)
    text = re.sub(r"^本文主张[：:]\s*", "", text)
    def replace_source_title_fragment(match: re.Match[str]) -> str:
        label = match.group(1)
        title = match.group(2)
        if label in {"反方限制", "问题意识", "研究对象", "主论题"}:
            return match.group(0)
        if not any(token in title for token in ["研究", "保护", "更新", "建筑", "街区", "传统", "空间", "设计"]):
            return match.group(0)
        return f"{label}相关研究"

    text = re.sub(
        r"([\u4e00-\u9fffA-Za-z0-9《》“”]{2,16})\s*[:：]\s*([^、；。]{8,120})(?=、|；|。|$)",
        replace_source_title_fragment,
        text,
    )
    if "、" in text:
        fragments: list[str] = []
        for fragment in text.split("、"):
            compacted = fragment.strip()
            if compacted and compacted not in fragments:
                fragments.append(compacted)
        text = "、".join(fragments)
    cleaned = re.sub(r"\s+", " ", text).strip(" ：:，,。；;")
    if cleaned and not cleaned.endswith(("。", "！", "？")):
        cleaned += "。"
    return cleaned


def public_section_title(claim: Any, fallback: str) -> str:
    text = clean_claim_text(claim).rstrip("。")
    if not text:
        return fallback
    if "反方" in text or "限制" in text or "外推" in text:
        return "适用范围与论证限制"
    if "问题" in text or "矛盾" in text or "诊断" in text:
        return "研究问题与现实矛盾"
    if "文化基因" in text:
        return "文化基因视角下的更新逻辑"
    if "场所叙事" in text:
        return "场所叙事与更新路径"
    if "城市更新" in text:
        return "城市更新语境下的实践路径"
    if "转化机制" in text or "应用路径" in text:
        return "转化机制与应用路径"
    if len(text) <= 18:
        return text
    title = re.split(r"[，；。:：]", text, maxsplit=1)[0].strip()
    if 4 <= len(title) <= 20:
        return title
    return fallback


def remove_internal_lines(text: str) -> str:
    kept: list[str] = []
    skip_section = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## Review 驱动修订") or stripped.startswith("## Claim 级修订处理") or stripped.startswith("## Part 5 修订说明"):
            skip_section = True
            continue
        if stripped.startswith("## ") and skip_section:
            skip_section = False
        if skip_section:
            continue
        if stripped.startswith(">") and any(marker in stripped for marker in INTERNAL_MARKERS):
            continue
        if any(
            marker in stripped
            for marker in [
                "本节核心论点",
                "本节围绕已确认论证",
                "展开该章节核心论点",
                "展开该层论点",
                "写作提示",
                "证据状态：source_ids",
                "原论点：",
                "对应 review",
                "基于 research wiki",
            ]
        ):
            continue
        kept.append(line)
    return "\n".join(kept).strip() + "\n"


def public_text_has_internal_markers(text: str) -> list[str]:
    return [marker for marker in INTERNAL_MARKERS if marker in text]
