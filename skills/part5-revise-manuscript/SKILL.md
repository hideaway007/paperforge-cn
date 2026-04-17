---
name: part5-revise-manuscript
description: 学术研究 workflow Part 5 修订：基于 manuscript_v1、review_matrix、claim risk 与 citation precheck 自动生成 manuscript_v2、revision_log 和 part6_readiness_decision。当用户说「修订 manuscript_v2」「生成 Part 5 revision」「导出最终稿」「part5-revise-manuscript」时触发。Part 5 不再需要 manuscript_v2_accepted；不得进入 Part 6。
---

# Part 5 Revise Manuscript

你的任务是把 canonical review artifacts 转成 `manuscript_v2.md` 与可审计修订记录，并保存在 `outputs/part5/`。`part6_readiness_decision.json` 只表达 readiness verdict，不授权进入 Part 6。

## 前置检查

1. Part 4 completion gate 已通过。
2. Prep、draft、review artifacts 已自动完成。
3. 不再要求 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted`。
4. `outputs/part5/review_matrix.json` 是 integrator 写入的 canonical review matrix。
5. `outputs/part5/citation_consistency_precheck.json` 不得为 blocked 或含未解决 errors。
6. `outputs/part5/review_report.md` 已生成。
7. `writing-policy/` 只能指导修订表达，不得补充研究证据。

## 执行

```bash
python3 cli.py part5-revise
```

生成后展示：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`

生成最终稿后必须先校验 `outputs/part5/manuscript_v2.md` 存在，再验证 Part 5：

```bash
python3 cli.py validate part5
```

## 停止点

完成 `part5-revise` 和 `validate part5` 后停止。不得因为 `part6_readiness_decision.json` verdict 是 ready 而自动运行任何 Part 6 操作。

## 禁止事项

- 不得要求或写入 `part5_review_completed` 或 `manuscript_v2_accepted`。
- 不得运行旧流程的 `part5-accept` 作为正常步骤。
- 不得把 `part6_readiness_decision.json` 当作 Part 6 授权。
- 不得进入 Part 6。
- 不得把 writing-policy 当作 research evidence。
- 不得虚构引文、图纸、案例事实或 source_id。
