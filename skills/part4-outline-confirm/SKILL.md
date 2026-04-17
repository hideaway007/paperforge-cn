---
name: part4-outline-confirm
description: 已废弃/兼容 skill：旧 workflow 中用于执行 outline_confirmed 人工 gate。当前正常流程不再需要 Part 4 人工确认；Part 4 三件套通过校验后可自动进入 Part 5。仅当需要读取旧项目状态或兼容历史记录时参考，不作为正常 workflow surface。
---

# Deprecated — Part 4 Outline Confirmation

当前 workflow 已移除 `outline_confirmed` 人工 gate。本 skill 仅为旧状态兼容说明，正常流程不得要求用户确认 outline，也不得把缺少 `outline_confirmed` 视为 Part 5 阻断条件。

## 前置检查

1. `outputs/part4/paper_outline.json` 存在且可解析。
2. `outputs/part4/outline_rationale.json` 存在且可解析。
3. `outputs/part4/reference_alignment_report.json` 存在且可解析。
4. 如发现旧状态中存在 `outline_confirmed`，只可作为历史记录展示；不得要求补写。

## 输入

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`
- 旧项目状态中的历史 `outline_confirmed` 记录（如存在）

## 输出

- 不产生新的 workflow 输出。
- 不写入新的 `outline_confirmed`。
- 不修改 `runtime/state.json`、`process-memory/` 或 Part 4 artifacts。

## 执行步骤

1. 读取三份 Part 4 artifacts，向用户展示章节结构、论证路线、主要风险、reference alignment 状态。
2. 明确说明当前流程不再需要 `outline_confirmed`。
3. 如需验证 Part 4，运行：

```bash
python3 cli.py validate part4
```

4. 向用户报告验证状态，并提示可进入自动 Part 5。

## 禁止事项

- 不得要求用户提供 outline confirmation notes。
- 不得写入新的 `outline_confirmed`。
- 不得把 `paper_outline.confirmed_at` 作为正常流程判断依据。
- 不得手动改 `runtime/state.json`、`process-memory/` 或 `paper_outline.confirmed_at`。
- 不得修改 research-wiki、writing-policy 或 Part 3 canonical artifacts。
- 不得进入 Part 6。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 4 Outline Confirm 已废弃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Outline: outputs/part4/paper_outline.json
  outline_confirmed: 不再需要
  Gate validate: <通过 / 未通过>

下一步：Part 4 completion gate 通过后，可自动进入 Part 5。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
