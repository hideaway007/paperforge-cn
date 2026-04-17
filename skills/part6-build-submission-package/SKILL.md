---
name: part6-build-submission-package
description: 学术研究 workflow Part 6 submission package 构建：生成 outputs/part6/submission_checklist.md 与 submission_package_manifest.json，支持 draft/final 两段式。当用户说「生成提交包」「submission package」「Part 6 package draft」「Part 6 final package」「part6-build-submission-package」时触发。final manifest 必须与 final readiness decision verdict 一致。
---

# Part 6 Build Submission Package

你的任务是生成提交包清单与 manifest，不改稿、不审稿、不决定 readiness。

## 输入

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/final_readiness_decision.json`（final 阶段需要）

## 输出所有权

本 skill 只能写：

- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`

## Draft / Final 两段式

### Draft package

在 readiness decision 之前生成 draft checklist 和 draft manifest：

- 标记 `package_stage: "draft"`。
- 列出已有 final manuscript、abstract、keywords、docx export、audit reports。
- 明确阻断项、缺失项与待 decision 项。

### Final package

在 `final_readiness_decision.json` 生成后刷新 final manifest：

- 标记 `package_stage: "final"`。
- manifest verdict 必须与 `final_readiness_decision.json` 的 verdict 一致。
- 若 decision verdict 是 not_ready 或 blocked，final package 不得声明 ready。
- 若仍有 critical blocker，清单必须显式列出，不得隐藏。

## 禁止事项

- 不得修改 final manuscript、abstract 或 keywords。
- 不得修改 claim/citation audit reports。
- 不得写 `final_readiness_decision.json`。
- 不得把 package manifest 当作提交授权。
- 不得自动进入 Part 7。
