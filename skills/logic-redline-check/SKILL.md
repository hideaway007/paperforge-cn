---
name: logic-redline-check
description: 学术写作 workflow 的逻辑红线检查 skill：对论文片段、章节稿、manuscript_v1、manuscript_v2 或 final manuscript 做高容忍度的致命逻辑、术语漂移、段落断裂与读者误解风险检查。当用户要求「逻辑检查」「红线审查」「术语一致性检查」「查致命问题」「logic-redline-check」时触发。该 skill 只报告 blocking 问题，不做普通润色，不新增 claim、citation、source 或研究事实。
---

# Logic Redline Check

你的任务是找出会阻碍读者理解、破坏论证可信度或导致后续审稿失败的“红线问题”。不要把这项工作做成普通润色或挑刺；只报告必须处理的问题。

## 输出所有权

默认在对话中返回红线报告。需要落盘时，只能写：

- `outputs/part5/logic_redline_report.md`
- `outputs/part5/logic_redline_items.json`
- `outputs/part6/logic_redline_report.md`
- `outputs/part6/logic_redline_items.json`
- `process-memory/{YYYYMMDD}_logic_redline_check.json`

不得直接写或覆盖：

- `outputs/part5/review_matrix.json`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`
- `outputs/part5/manuscript_v1.md`
- `outputs/part5/manuscript_v2.md`
- `outputs/part6/final_manuscript.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `research-wiki/`
- `raw-library/`

## 输入

可读取：

- 用户提供的论文片段或章节。
- `outputs/part5/manuscript_v1.md`、`outputs/part5/manuscript_v2.md` 或 `outputs/part6/final_manuscript.md`。
- `outputs/part4/paper_outline.json` 与 `outputs/part3/argument_tree.json`，用于检查结构承接。
- `writing-policy/rubrics/logic_redline_review.md`。
- 既有 review、claim risk、citation report，只用于避免重复和识别风险边界。

没有正文文本时停止。不得为了“修复逻辑”自行补写新论据、案例、引文或结论。

## 检查范围

只报告以下问题：

- 前后陈述互相矛盾。
- 核心术语在未说明的情况下换名、缩小或扩大含义。
- 章节标题、段落主题句与实际内容不匹配。
- 从材料描述跳到价值判断，中间缺少必要论证台阶。
- 因果、比较、归纳、推论关系没有证据承托。
- 段落之间存在明显断裂，读者无法判断论证路径。
- 摘要、绪论、结论对同一核心 claim 的表述不一致。
- 风险标记、citation warning 或 evidence gap 被正文流畅语言掩盖。

不要报告：

- 可改可不改的措辞偏好。
- 只是“不够高级”的普通表达。
- 已被 claim/citation audit 明确覆盖且没有新增判断的问题。
- 需要用户审美偏好决定的标题风格。

## 严重度

- `blocking`: 不处理会影响论文成立、来源可信或读者理解。
- `major`: 会削弱章节论证或评审观感，但可通过局部修订解决。
- `minor`: 只在多个同类问题集中出现时报告；单点 minor 默认忽略。

## 输出格式

报告必须包含：

- `Verdict`: `pass`、`pass_with_major_notes` 或 `blocked`。
- `Blocking Items`: 只列真正阻断的问题。
- `Major Items`: 每条说明位置、问题、为什么构成风险、建议处理方向。
- `Term Drift`: 如果存在术语漂移，列出漂移链。
- `Do Not Fix By`: 明确不得用新增来源、伪造证据或提高判断强度来修复。

JSON 至少包含：

- `event_type`: `logic_redline_check`
- `input_path`
- `verdict`
- `items`
- `term_drift`
- `claim_strength_risks`
- `does_not_modify_manuscript`: `true`
- `research_facts_added`: `false`

## 与其他 skill 的关系

- `academic-register-polish` 负责表达收束；本 skill 负责阻断级逻辑风险。
- `part5-review-manuscript` 拥有 Part 5 canonical review artifacts；本 skill 的报告只能作为补充输入。
- `part6-audit-claim-risk` 和 `part6-audit-citation-consistency` 负责最终证据与引用审计；本 skill 不替代它们。

## 禁止事项

- 不得改写 canonical manuscript。
- 不得生成新的 claim、source_id、citation、案例事实或图纸信息。
- 不得把 writing-policy 当作 research evidence。
- 不得为了让文本显得连贯而删除风险标记。
- 不得把普通风格偏好升级成 blocking 问题。
