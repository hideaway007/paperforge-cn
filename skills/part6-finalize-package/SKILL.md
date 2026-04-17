---
name: part6-finalize-package
description: 学术研究 workflow Part 6 用户级 orchestration：按 precheck -> finalize -> audit-claim -> audit-citation -> package-draft -> export-docx -> decide -> package-final -> validate 执行最终稿、docx 与提交包流程。当用户说「开始 Part 6」「最终定稿」「生成提交包」「生成 docx」「part6-finalize-package」且未指定子步骤时触发。该 skill 不直接拥有子产物，不自动确认 part6_finalization_authorized 或 part6_final_decision_confirmed。
---

# Part 6 Finalize Package

你的任务是调度 Part 6 MVP，不直接写子产物。Part 6 是最终收束与提交准备层，不是新增研究事实层。

## Gate 规则

- 不得自动确认 `part6_finalization_authorized`。
- 不得自动确认 `part6_final_decision_confirmed`。
- 如授权 gate 未满足，只生成面向用户的下一步说明，不推进 finalize。
- `final_readiness_decision.json` 只表达 readiness，不授权提交或进入 Part 7。

## 执行顺序

1. `precheck`：确认 Part 5 canonical artifacts 存在，尤其是 `outputs/part5/manuscript_v2.md`、`review_matrix.json`、`revision_log.json` 与 `part6_readiness_decision.json`。
2. `finalize`：调用 `$part6-finalize-manuscript`。
3. `audit-claim`：调用 `$part6-audit-claim-risk`。
4. `audit-citation`：调用 `$part6-audit-citation-consistency`。
5. `package-draft`：调用 `$part6-build-submission-package` 生成 draft package artifacts。
6. `export-docx`：调用 `$part6-export-docx` 生成项目内 docx、format report 和桌面 `{论文题目}.docx`。
7. `decide`：调用 `$part6-decide-readiness`。
8. `package-final`：仅当 decision verdict 允许 final package 时，调用 `$part6-build-submission-package` 刷新 final manifest。
9. `validate`：校验 Part 6 canonical artifacts 齐备且所有权未越界。

## Artifact Ownership

本 skill 不拥有任何 Part 6 子产物，不直接写入：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

## 禁止事项

- 不得新增 claim、source、case fact、引文或图纸信息。
- 不得把 audit skill 当作改稿工具。
- 不得让 package manifest 覆盖 readiness decision。
- 不得自动授权提交、部署、出版或进入 Part 7。
