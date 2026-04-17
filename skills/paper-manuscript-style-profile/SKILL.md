---
name: paper-manuscript-style-profile
description: 中文论文正文写作范式 skill：当 writeagent 需要把 argument tree、paper outline 与 manuscript_v2 写成连续中文学术正文时触发。重点防止 workflow 腔、证据链外露、审计报告式正文和 AI 套话；可与 author-style-profile-build、academic-register-polish 一起使用。
---

# Paper Manuscript Style Profile

你的任务是约束 writeagent 写出“论文正文”，不是把 workflow artifact 翻译成段落。正文应让读者看到研究对象、问题、论证和结论，而不是看到系统如何审计证据。

## 适用范围

用于 Part 5 / Part 6 的中文学术正文写作，尤其是：

- 从 `outputs/part3/argument_tree.json` 和 `outputs/part4/paper_outline.json` 起草正文。
- 从 `outputs/part5/manuscript_v2.md` 收束为 `outputs/part6/final_manuscript.md`。
- 在 Part 5 draft 中配合 `$part5-formal-manuscript-authoring`，把报告型 Markdown 外壳收束为正式论文的题名、摘要、关键词、章节层级、章节小结、结论与参考文献形态。
- 与 `writing-policy/style_guides/author_style_profile.md`、`academic-register-polish` 一起压降 AI 腔和脚手架腔。

## 正文目标

正文应满足四点：

1. 章节职责清楚：每章回答一个明确问题，不重复解释系统输入。
2. 论证自然推进：从研究背景、对象界定、问题诊断、路径分析到结论收束。
3. 文献嵌入自然：引用和来源服务于论证，不把“证据链”本身写成正文主题。
4. 学术谨慎隐含在表达中：必要时降级判断，但不要反复声明“已核验”“可回溯”“证据边界”。

## 输入使用顺序

1. `paper_outline.json` 决定章节结构和章节职责。
2. `argument_tree.json` 决定主论点、分论点和反论点处理。
3. `manuscript_v2.md` 是 Part 6 的正文基线；优先保留其中已经像论文的连续段落。
4. `author_style_profile.md` 决定问题进入方式、段落节奏和判断强度。
5. `academic-register-polish` 只用于语体收束，不新增事实。
6. claim/citation/risk 报告只用于避免越界，不直接写成正文。

## 禁止写法

不得在正文中出现以下 workflow 腔：

- “已核验资料显示”“可回溯资料显示”“当前进入主证据链”
- “证据边界需要明确说明”“来源边界”“材料边界仍回到”
- “Part 2 Evidence”“claim-evidence matrix”“review_matrix”
- “本文不把相关判断写成成熟的实证结论”这类审计报告式自我说明
- 单独设置“证据边界与研究不足”作为机械章节
- 每章反复写“本节围绕……展开”“这一部分首先说明……”
- 把 source_id、risk_level、artifact 名称、内部 gate 名称写进正文

## 推荐写法

### 文献和材料进入正文

不要写：

> 已核验资料显示，某文献为本文提供了可回溯的理论入口。

改为：

> 既有研究从案例保护、使用品质改善和微更新实践等角度，为研究对象的更新问题提供了讨论基础。

### 研究不足

不要单列“证据边界与研究不足”，除非 outline 明确要求。优先放在结论末段，使用常规论文表达：

> 受资料获取范围与案例材料完整性的限制，本文对更新成效的讨论仍以文献归纳和机制分析为主。后续研究可进一步结合居民访谈、改造前后对比资料和运营维护记录，对不同更新策略的适用条件与实施效果进行验证。

### 引用密度

正文只在三种位置显式引用：

- 引出关键概念或研究现状。
- 支撑一个章节的核心判断。
- 交代案例、政策或方法来源。

其他位置使用概括性学术表达，不要连续堆叠来源名称、作者年份或“证据链”说明。

## 输出规则

- 输出必须是连续论文正文。
- 标题应贴近论文常规：绪论、文献综述、研究对象、问题分析、路径机制、策略建议、结论与展望。
- “研究不足”应短、自然、放在结论或讨论部分。
- 不新增 claim、source、citation、案例事实、图纸事实或数据。
- 不删除必要的不确定性，但要把不确定性写成论文语言，而不是系统风险提示。
- 如果材料不足以写成完整正文，应输出保守正文并在 JSON 的 `notes` 或 sidecar 报告中说明，不要把缺口直接扩写成正文主体。
