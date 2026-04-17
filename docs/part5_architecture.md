# Part 5 Architecture

> Current status: Part 5 is part of the active MVP main chain. Part 4 completion can flow into Part 5 without `outline_confirmed`; Part 5 has no blocking human gates. The required user-facing outputs are `outputs/part5/review_report.md` and `outputs/part5/manuscript_v2.md`. Part 6 is now an active but human-gated finalization surface.

## 1. Stage Purpose
Part 5 的职责不是单纯“评审”，而是把 **Part 4 的 canonical outline** 进一步推进为：

1. 可写作的章节级输入包
2. 第一版整合稿 `manuscript_v1`
3. 结构化评审结果
4. 修订后的 canonical draft `manuscript_v2`

因此，Part 5 的推荐定义为：

**Draft + Review + Revision**

它连接的是：

- 上游：Part 4 的 `paper_outline.json`
- 下游：`outputs/part5/` 中的 Part 5 review report 与 `manuscript_v2.md`

Part 6 当前可作为显式授权后的 finalization surface。`part6_readiness_decision.json` 只表达后续准备度，不自动确认 `part6_finalization_authorized`，也不触发 submission。

---

## 2. Entry Preconditions
进入 Part 5 前，必须满足以下条件：

### 2.1 Upstream Completion
- Part 1 gate = passed
- Part 2 gate = passed
- Part 3 gate = passed
- Part 4 gate = passed

### 2.2 Canonical Inputs Ready
至少应具备以下 canonical inputs：

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`
- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `writing-policy/source_index.json`

### 2.3 Research Debt Visible
已知资料债务必须显式记录，而不能在写作中被默默吞掉。至少包括：

- 中文正式文献层缺口（如 CNKI / 万方 / 维普未补足）
- 案例核验风险（如仅能作为概念参照而非硬建筑事实的案例）
- 案例深描缺口（图纸、动线、视线、建筑师说明等）

### 2.4 Automation Boundary
Part 5 不再要求人工授权或中途确认。Part 4 completion gate 通过后，可自动执行：

`prep -> draft -> review -> revise`

自动化边界是：不得虚构证据，不得吞掉 blocker，不得把 Part 6 readiness verdict 当作 Part 6 授权。Part 6 只能在用户确认 `part6_finalization_authorized` 后进入。

---

## 3. Stage Scope
Part 5 的范围分为四个子阶段。

### 3.1 Writing Preparation
把 outline 变成真正可写正文的输入包：

- 章节 brief 拆解
- 案例分析模板
- claim-evidence 对照表
- citation map
- figure / image 需求计划
- 写作优先级与章节顺序自动派生

### 3.2 Draft Generation
基于上一步产出，生成正文初稿：

- 摘要初稿
- 绪论初稿
- 理论框架章节
- 案例分析章节
- 结论初稿
- 整合稿 `manuscript_v1`

### 3.3 Structured Review
对 `manuscript_v1` 进行结构化评审，而不是只给模糊意见：

- 结构评审
- 论证评审
- 证据评审
- 引用评审
- 中文学术写作规范评审
- 风险与缺口评审

### 3.4 Revision
基于 review matrix 进行修订，生成：

- `revision_log.json`
- `manuscript_v2`
- residual risks
- Part 6 readiness decision

---

## 4. Core Inputs
Part 5 的输入分为五类。

### 4.1 Research Evidence Inputs
- `raw-library/metadata.json`
- `outputs/part1/accepted_sources.json`
- `outputs/part1/authenticity_report.json`
- `research-wiki/pages/`
- `research-wiki/index.json`

### 4.2 Argument and Outline Inputs
- `outputs/part3/argument_tree.json`
- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`

### 4.3 Writing Policy Inputs
- `writing-policy/source_index.json`
- 中文学术写作规范
- 学校或学院格式要求
- 导师 PPT / 课堂资料提炼规则
- 参考案例结构约束

### 4.4 Debt and Risk Inputs
- `mvp_acceptance_report.md`
- research debt register
- case verification notes
- image / drawing gaps

### 4.5 Automated Policy Inputs
- outline 与 rationale 中记录的章节重点
- reference alignment report 中的结构约束
- claim-evidence matrix 中的证据强弱
- open questions 与 risk register 中的保守表述规则

---

## 5. Stage Outputs

### 5.1 Writing Preparation Outputs
建议至少生成：

- `outputs/part5/chapter_briefs/`
- `outputs/part5/case_analysis_templates/`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `outputs/part5/figure_plan.json`
- `outputs/part5/open_questions.json`

### 5.2 Draft Outputs
建议至少生成：

- `outputs/part5/abstract_draft.md`
- `outputs/part5/introduction_draft.md`
- `outputs/part5/theory_chapter_draft.md`
- `outputs/part5/case_chapters/`
- `outputs/part5/conclusion_draft.md`
- `outputs/part5/manuscript_v1.md`

### 5.3 Review Outputs
建议至少生成：

- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/review_summary.md`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`

### 5.4 Revision Outputs
建议至少生成：

- `outputs/part5/revision_log.json`
- `outputs/part5/revision_plan.json`
- `outputs/part5/manuscript_v2.md`
- `outputs/part5/part6_readiness_decision.json`

### 5.5 User-Facing Outputs
Part 5 完成时，面向用户的结果只保存在阶段目录：

- `outputs/part5/review_report.md`
- `outputs/part5/manuscript_v2.md`

这两个文件本身就是用户交互层和 canonical artifacts，不再额外复制到阶段目录之外。
Part 5 completion gate 必须校验这两个项目内目标文件实际存在，且最终稿文件名固定为 `manuscript_v2.md`。

---

## 6. Canonical Artifacts
Part 5 的 canonical artifacts 建议定义为：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`

说明：

- `manuscript_v1.md` 是中间稿，不应视为 canonical 终态
- 只有完成 review 与 revision 后的 `manuscript_v2.md` 才能作为 Part 5 canonical draft
- `review_report.md` 是面向用户的 review 汇报，必须由结构化 review artifacts 派生，不得替代 `review_matrix.json`
- `part6_readiness_decision.json` 只表达 readiness，不自动授权 Part 6；Part 6 entry 仍需要 `part6_finalization_authorized`

---

## 7. Drafting Strategy

### 7.1 Contract-First Writing
正文生成必须服从上游契约，而不是自由发挥。写作时必须同时受以下约束：

- argument tree
- paper outline
- research wiki
- writing policy
- claim-evidence matrix

### 7.2 Evidence Discipline
所有正文内容分成三类：

1. **Hard-evidence claims**：必须能回溯到已验真来源
2. **Synthesized interpretations**：允许综合推理，但必须有来源支撑
3. **Conceptual framing**：允许较强解释性，但必须明确不是硬建筑事实

### 7.3 Risk Carryover Rules
对于 Part 1–4 已知风险，Part 5 必须延续处理：

- 未核验建筑项目不得在正文里被写成确定事实
- 中文核心文献缺口必须在 claim risk 中保留标记
- 缺图纸 / 缺动线依据的案例段落必须降低断言强度

---

## 8. Review Architecture
Part 5 的 review 不应只是“再让 AI 看一遍”，而应拆成明确维度。

### 8.1 Structure Review
检查：

- 章节顺序是否合理
- 章节之间是否存在重复与断裂
- 论证主线是否持续围绕 canonical argument tree

### 8.2 Argument Review
检查：

- 论点是否明确
- 子论点是否支撑总论点
- 案例与理论之间是否建立对应关系

### 8.3 Evidence Review
检查：

- 每个关键 claim 是否有来源
- 是否存在跳跃性结论
- 是否误把概念参照当作硬案例

### 8.4 Citation Review
检查：

- 引用是否能回溯到 accepted sources
- 引文与正文论述是否错位
- 是否存在虚构或不完整引文

### 8.5 Writing Policy Review
检查：

- 是否符合中文学术写作规范
- 是否符合导师 / 学院 / 学校格式与表达要求
- 语气是否过于口语化、宣传化或概念空转

### 8.6 Debt Review
检查：

- 哪些研究债务已经消解
- 哪些必须延续到 Part 6 claim / citation audit
- 哪些债务会阻止正式定稿

---

## 9. Automated Part 5 Flow
Part 5 MVP 不再保留人工阻断节点。系统必须自动完成以下步骤，并把风险显式写入 artifacts：

- 生成章节 brief、案例模板、claim-evidence matrix、citation map、figure plan 与 open questions
- 生成保守 `manuscript_v1.md`
- 生成 review fragments 并整合为 canonical review artifacts
- 从 review artifacts 派生 `review_report.md`
- 基于 review 自动修订为 `manuscript_v2.md`
- 生成 `revision_log.json` 与 `part6_readiness_decision.json`
- 将 `manuscript_v2.md` 写入 `outputs/part5/`

自动化不能把“不确定”改写成“已证实”。高风险 claim 必须降级、标注或进入 blocker，而不是为了完成流程被删除。

---

## 10. Stage Gates

### 10.1 Writing Prep Gate
通过条件：

- `chapter_briefs` 已生成
- `claim_evidence_matrix.json` 已生成
- `citation_map.json` 已生成
- `figure_plan.json` 已生成
- 主要 open questions 已登记

### 10.2 Draft Gate
通过条件：

- `manuscript_v1.md` 已生成
- 摘要、绪论、理论框架、案例章节、结论齐备
- 各章节与 outline 对齐
- 关键 claims 至少已有初步 evidence mapping

### 10.3 Review Gate
通过条件：

- `review_matrix.json` 已生成
- `review_report.md` 已生成
- `review_summary.md` 已生成
- 关键结构问题已被识别
- 高风险 claim 已被标红或降级
- citation precheck 已完成

### 10.4 Part 5 Completion Gate
通过条件：

- `manuscript_v2.md` 已生成
- `review_matrix.json` 齐备
- `revision_log.json` 齐备
- `part6_readiness_decision.json` 已生成
- `review_report.md` 已生成
- `manuscript_v2.md` 已生成
- 不存在未登记的 critical blocker
- 所有未解决问题必须已显式记录，而不是被忽略

---

## 11. Readiness Outcomes
Part 5 完成后，建议输出三种 readiness verdict 之一：

- `ready_for_part6`
- `ready_for_part6_with_research_debt`
- `blocked_by_evidence_debt`

说明：

- 若中文核心资料仍明显不足，但已可进入内部定稿准备，可标为 `ready_for_part6_with_research_debt`
- 若关键案例事实仍无法成立，或高风险 claim 无法回溯，应标为 `blocked_by_evidence_debt`
- 任一 verdict 都不得自动触发 Part 6；`ready_for_part6` 只允许系统建议用户执行 `part6-authorize`。

---

## 12. State and Diagnostics
运行时应至少记录：

- 当前子阶段（prep / draft / review / revision）
- 当前 canonical draft 版本
- 最近一次 review 结论
- 未解决 blocker 列表
- 本地产物生成状态

诊断工具至少应支持：

- draft completeness check
- claim-evidence completeness check
- citation precheck
- review coverage check
- readiness decision validation

---

## 13. ECC Reference Boundary
Part 5 仍可参考 ECC 的工程思想，包括：

- contract-first
- staged gates
- audit / doctor
- hooks 做自动校验
- process-memory 留痕

但不应照搬 ECC 的 coding workflow。Part 5 的业务核心是：

- 论文正文生成
- 学术论证评审
- 研究债务透明化
- 中文写作规范一致性

---

## 14. Part 6 Handoff Interface
Part 6 已有 active MVP finalization surface。Part 5 负责提供 handoff 包，但不拥有 Part 6 gate：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `outputs/part5/figure_plan.json`
- `outputs/part5/part6_readiness_decision.json`

这些文件支持当前 Part 6，但不会自动创建 `final_manuscript.*` 或 submission package。进入 Part 6 的条件是：

- Part 5 gate passed
- `part6_readiness_decision.verdict != blocked_by_evidence_debt`
- 用户执行 `python3 cli.py part6-authorize --notes "..."`
- Part 6 precheck 确认 Part 5 handoff fingerprints 未漂移

Part 6 completion 再由 `part6-finalize`、`part6-check` 和 `part6-confirm-final` 收口。
