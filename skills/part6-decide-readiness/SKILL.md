---
name: part6-decide-readiness
description: 学术研究 workflow Part 6 readiness decision：只读 claim/citation/package artifacts，写 outputs/part6/final_readiness_decision.json。当用户说「判断 Part 6 是否 ready」「final readiness decision」「决定是否可提交」「part6-decide-readiness」时触发。不授权提交；does_not_advance_part7 必须为 true。
---

# Part 6 Decide Readiness

你的任务是形成最终 readiness 判断，不授权提交、不推进下一阶段。

## 输入

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`

## 输出所有权

本 skill 只能写：

- `outputs/part6/final_readiness_decision.json`

## 判断规则

1. 只读 claim/citation/package artifacts，不改稿、不改 report、不改 manifest。
2. 若存在 critical claim risk、无法追溯 citation、缺失 final manuscript 三件套或 package blocker，verdict 必须是 `not_ready` 或 `blocked`。
3. 若只有非阻断问题，可给出 `ready_with_notes`，并列出 residual risks。
4. 若所有关键项通过，可给出 `ready`。
5. 输出必须包含 `does_not_advance_part7: true`。
6. 输出必须明确：该 decision 不是提交授权，也不是 Part 7 授权。

## 禁止事项

- 不得写 `submission_package_manifest.json`。
- 不得修改 audit reports。
- 不得修改 final manuscript。
- 不得自动确认 `part6_final_decision_confirmed`。
- 不得自动进入 Part 7。
