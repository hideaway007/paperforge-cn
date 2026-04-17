---
name: reviewer-perspective-audit
description: 学术写作 workflow 的审稿人视角评估 skill：从读者和评审角度审查论文稿件的贡献定位、结构承接、论证链、证据边界、风险暴露和可修改路径。当用户要求「审稿人视角」「整体审视论文」「模拟评审」「投稿前审查」「reviewer-perspective-audit」时触发。该 skill 只写审查报告，不修改 canonical artifacts，不替代 claim/citation audit。
---

# Reviewer Perspective Audit

你的任务是模拟严谨但建设性的学术评审，判断稿件是否容易被读者理解、是否明确呈现贡献、是否存在会被审稿人抓住的结构性问题。它是读者视角检查，不是事实补全器。

## 输出所有权

默认在对话中返回审查报告。需要落盘时，只能写：

- `outputs/part5/reviewer_perspective_report.md`
- `outputs/part5/reviewer_perspective_items.json`
- `outputs/part6/reviewer_perspective_report.md`
- `outputs/part6/reviewer_perspective_items.json`
- `process-memory/{YYYYMMDD}_reviewer_perspective_audit.json`

不得直接写或覆盖：

- `outputs/part5/review_matrix.json`
- `outputs/part5/review_summary.md`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/manuscript_v1.md`
- `outputs/part5/manuscript_v2.md`
- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_readiness_decision.json`
- `research-wiki/`
- `raw-library/`

## 输入

可读取：

- 用户提供的论文稿、章节稿或 PDF 抽取文本。
- `outputs/part5/manuscript_v1.md`、`outputs/part5/manuscript_v2.md` 或 `outputs/part6/final_manuscript.md`。
- `outputs/part4/paper_outline.json`、`outputs/part3/argument_tree.json`。
- `outputs/part5/review_matrix.json`、`outputs/part6/claim_risk_report.json`、`outputs/part6/citation_consistency_report.json`，只用于避免重复和确认风险边界。
- `writing-policy/rubrics/reviewer_perspective_audit.md`。

没有稿件时停止。不得为了提出“修改建议”而新编研究贡献、实验、案例、引用或结论。

## 审查维度

1. 贡献定位：读者能否在摘要和绪论中理解论文解决什么问题、贡献在哪里。
2. 结构承接：章节顺序是否支撑 argument tree，是否存在章节职责重叠或缺口。
3. 论证链：主要 claim 是否从材料、分析到结论逐步推进。
4. 证据边界：是否有明显 overclaim、证据不足、案例表述风险。只标记，不补证据。
5. 读者体验：标题、段落入口、术语、图表说明是否会造成误读。
6. 可修改路径：区分可通过写作修订解决的问题与必须回到 evidence layer 的问题。

## 报告原则

- Findings 先行，按 severity 排序。
- 每条问题必须具体到稿件位置或章节，不写泛泛意见。
- 区分 `writing_fix`、`evidence_required`、`structure_fix`、`citation_audit_required`。
- 不给虚假的投稿分数；可给 readiness 判断。
- 对没有实质问题的维度明确写 `no blocking issue found`。

## 输出格式

报告必须包含：

- `Overall Readiness`: `ready_with_minor_notes`、`needs_revision` 或 `blocked`。
- `Critical Findings`: 阻断性问题。
- `Major Findings`: 影响评审观感或论证完整性的主要问题。
- `Reader Confusion Points`: 读者可能误解的位置。
- `Revision Path`: 按写作修订、结构修订、证据补充、引用审计分类。
- `Do Not Solve By`: 明确哪些问题不能靠润色解决。

JSON 至少包含：

- `event_type`: `reviewer_perspective_audit`
- `input_path`
- `overall_readiness`
- `findings`
- `revision_path`
- `requires_evidence_layer_update`
- `does_not_modify_manuscript`: `true`
- `research_facts_added`: `false`

## 与其他 skill 的关系

- `logic-redline-check` 只查致命逻辑红线；本 skill 给整体审稿视角。
- `academic-register-polish` 负责语言收束；本 skill 判断是否值得修、从哪里修。
- `part5-review-manuscript` 与 Part 6 audit 仍是 canonical review/audit owner；本 skill 的报告只能作为附加评审意见。

## 禁止事项

- 不得修改 canonical artifact。
- 不得新增 claim、source_id、citation、案例事实、图纸信息或研究结论。
- 不得把外部写作技巧当作研究证据。
- 不得用“审稿人会喜欢”作为提高 claim 强度的理由。
- 不得把可写作修复的问题夸大为证据失败，也不得把证据失败包装成语言问题。
