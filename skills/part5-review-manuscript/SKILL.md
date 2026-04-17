---
name: part5-review-manuscript
description: 学术研究 workflow Part 5 审稿：对 outputs/part5/manuscript_v1.md 先生成 review fragments，再由 integrator 汇总生成 canonical review_matrix、claim risk report、citation consistency precheck、review summary 与面向用户的 review_report.md。当用户说「审稿 Part 5」「生成 review_matrix」「生成 review report」「part5-review-manuscript」时触发。Part 5 不再需要 review 人工确认；review 完成后可自动修订。
---

# Part 5 Review Manuscript

你的任务是审查 `manuscript_v1.md` 并形成可执行的修订依据。review 是 Part 5 修订前的自动质量门，不再等待人工确认。

## 前置检查

1. Part 4 completion gate 已通过。
2. Prep artifacts 已完成；不再要求 `writing_phase_authorized` 或 `part5_prep_confirmed`。
3. `outputs/part5/manuscript_v1.md` 已存在。
4. Prep artifacts 已存在且未绕过来源映射。
5. `writing-policy/` 只能作为写作评价规则，不得作为 research evidence。

## Review Fragments 规则

1. Review fragments 是当前已启用的中间产物，只能由 review agents 写。
2. Review agents 不得直接写 `outputs/part5/review_matrix.json`。
3. Canonical `outputs/part5/review_matrix.json`、`outputs/part5/review_summary.md`、`outputs/part5/review_report.md`、`outputs/part5/claim_risk_report.json` 与 `outputs/part5/citation_consistency_precheck.json` 只能由 integrator 写。
4. 在当前 CLI 尚未暴露独立 fragments/integrator 命令时，把 `python3 cli.py part5-review` 视为唯一合法 integrator surface；不得手工拼接 canonical review matrix。
5. Fragments 与 canonical matrix 都不得新增研究事实、source_id、引文、图纸或案例事实。

## 执行

```bash
python3 cli.py part5-review
```

该命令会先运行各 review agent 写入 `outputs/part5/review_fragments/`，再由 integrator 汇总生成 canonical review artifacts。

生成后展示：

- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/review_summary.md`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`

`review_report.md` 必须面向用户汇报：说明主要问题、已降级的高风险 claim、需要用户知道但不阻断 Part 5 自动修订的研究债务。生成后保存在 `outputs/part5/review_report.md`。

## 停止点

完成 `part5-review` 且 review artifacts 齐备后，可自动运行 `part5-revise`。

## 禁止事项

- 不得要求或写入 `part5_review_completed`。
- 不得运行旧流程的 `part5-confirm-review`。
- 不得让 review agents 写 canonical `review_matrix.json`。
- 不得让 review report 取代 canonical `review_matrix.json`。
- 不得把 writing-policy 当作 research evidence。
- 不得虚构引文、图纸、案例事实或 source_id。
- 不得自动进入 Part 6。
