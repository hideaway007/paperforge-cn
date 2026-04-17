---
name: academic-register-polish
description: 学术写作 workflow 的中文学术语体保守润色 skill：对论文片段、manuscript_v1、manuscript_v2 或 final manuscript proposal 做段落级学术化、术语一致、口语化清理和 AI 腔压降。当用户要求「让论文更学术化」「中文学术润色」「去口语化」「去 AI 味」「academic-register-polish」时触发。该 skill 不新增 claim、citation、source、案例事实或研究结论，不直接覆盖 Part 5/Part 6 主稿。
---

# Academic Register Polish

你的任务是把已有中文论文文本收束为更稳健的学术书面语。不要把这项工作理解为“扩写”“拔高”或“换成高级词”，而是减少口语、宣传腔、AI 套话、判断过强和段落跳跃，同时保留原有研究事实、论证边界和作者风格。

## 输出所有权

默认在对话中返回润色结果和修改说明。需要落盘时，只能写 sidecar proposal 或报告：

- `outputs/part5/academic_register_polish_report.md`
- `outputs/part5/academic_register_polish_changes.json`
- `outputs/part5/manuscript_v1_academic_polish_proposal.md`
- `outputs/part5/manuscript_v2_academic_polish_proposal.md`
- `outputs/part6/academic_register_polish_report.md`
- `outputs/part6/academic_register_polish_changes.json`
- `outputs/part6/final_manuscript_academic_polish_proposal.md`
- `process-memory/{YYYYMMDD}_academic_register_polish.json`

不得直接写或覆盖：

- `outputs/part5/manuscript_v1.md`
- `outputs/part5/manuscript_v2.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`
- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `research-wiki/`
- `raw-library/`

## 输入要求

可处理：

- 用户直接提供的中文论文片段。
- `outputs/part5/manuscript_v1.md` 或 `outputs/part5/manuscript_v2.md`。
- `outputs/part6/final_manuscript.md`，但只能生成 proposal，不得覆盖 final manuscript。
- `writing-policy/rules/` 与 `writing-policy/style_guides/`。
- `writing-policy/rules/ai_style_markers.md`，用于识别机械化表达和 AI 腔风险。
- `writing-policy/style_guides/author_style_profile.md`，如果存在，用于保留匿名作者风格。
- `review_matrix.json`、`claim_risk_report.json`、`citation_consistency_report.json`，只用于识别风险标记，不用于新增内容。

没有正文文本时停止。不能为了完成润色而自行补写研究背景、研究对象、案例、数据、引用或结论。

## 执行流程

1. 识别输入文本的层级：片段、章节、`manuscript_v1`、`manuscript_v2` 或 final proposal。
2. 读取适用的 writing-policy。若存在 `author_style_profile.md`，先保留其段落组织和判断节奏。
3. 标记不可改动单元：citation、source_id、图表编号、案例事实、数据、风险提示、`[CITATION NEEDED]`、`[EVIDENCE GAP]`。
4. 对每段执行保守润色：只处理语体、衔接、冗余、术语一致和判断强度。
5. 输出润色文本，并给出 change log。若落盘，必须同时写 changes JSON 或 report。
6. 对无法保守处理的问题，保留原文并写入 blocked item，不得凭空修复。

## 润色规则

### 语体收束

- 将明显口语化表达改为现代中文学术书面语。
- 避免陈旧公文腔，不要无故使用“系”“拟”“兹”等僵硬表达。
- 避免宣传腔和价值口号，例如“具有划时代意义”“极大推动”等，除非已有证据直接支持。
- 避免为了显得高级而堆砌抽象名词。
- 对 `ai_style_markers.md` 标记的机械化表达，只在确有必要时压降；不得把稳定作者风格误判为 AI 腔。

### 判断强度

- 不提高 claim 强度。原文是“可能”“有助于”“体现出”时，不得改成“证明”“决定”“必然导致”。
- 对缺少证据承托的判断，优先降级为“提示”“表明”“可见”“在一定程度上反映”。
- 保留风险标记和证据缺口，不得用流畅语言把不确定性遮蔽掉。

### 段落与衔接

- 优先保持原有段落职责，不为追求顺滑而重排论证链。
- 允许补充必要的过渡词，但不要机械堆砌“首先、其次、最后”“值得注意的是”等模板。
- 一个段落只服务一个核心判断。多主题混杂时，可建议拆段，但不要私自新增内容。

### 术语一致

- 统一同一概念的称谓，优先遵守 `paper_outline.json`、writing-policy 和既有正文。
- 不替换专业术语为更“好听”的词。
- 中英文术语、图表编号和引用格式保持原样，除非 writing-policy 明确要求修正。

### 作者风格

- 如果存在匿名作者风格画像，优先保留其问题进入方式、段落节奏和证据托举方式。
- 学术化处理不得把文本磨成通用 AI 论文腔。
- 作者风格与事实约束冲突时，事实约束优先；作者风格与学术规范冲突时，学术规范优先，并在 change log 中说明。

## 输出格式

对片段任务，输出：

- `Refined Text`: 润色后的文本。
- `Change Log`: 简要说明做了哪些必要修改。
- `Risk Notes`: 若发现证据缺口、过强判断或引用风险，列出但不补造。

对文件任务，sidecar JSON 至少包含：

- `event_type`: `academic_register_polish`
- `input_path`
- `proposal_path`
- `policy_refs`
- `author_style_profile_used`
- `changed_units`
- `unchanged_units`
- `claim_strength_changes`
- `blocked_items`
- `citations_preserved`: `true`
- `research_facts_added`: `false`
- `does_not_modify_canonical_manuscript`: `true`

## 与其他 skill 的关系

- `author-style-profile-build` 先建立匿名作者风格画像；本 skill 可读取画像做表达收束。
- `part5-draft-manuscript` 与 `part5-revise-manuscript` 仍然拥有 Part 5 主稿文件。
- `part6-finalize-manuscript` 仍然拥有 Part 6 final manuscript 三件套。
- 本 skill 可向 Part 5 / Part 6 owner 提供 proposal，但不替代 owner 决策。
- 外部通用 prompt 库只能作为启发，不得原样复制进项目 skill 或 writing-policy。

## 禁止事项

- 不得新增 claim、source_id、citation、案例事实、图纸信息、数据或研究结论。
- 不得把 writing-policy、作者风格或外部 prompt 当作 research evidence。
- 不得删除 `citation needed`、evidence gap、risk note 或 audit warning。
- 不得把“语言更像学术论文”作为提高论证强度的理由。
- 不得覆盖 canonical manuscript 或绕过 Part 5 / Part 6 artifact owner。
- 不得在未确认语境时把中文建筑/设计类论文改成计算机顶会风格。
