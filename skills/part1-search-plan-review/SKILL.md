---
name: part1-search-plan-review
description: 学术研究 workflow Part 1 检索计划审查 skill：用于 researchagent 审查 outputs/part1/search_plan.json 是否符合 intake、CNKI 优先策略、来源边界和后续真实性校验要求。只输出 sidecar review，不得改写 canonical Part 1 artifacts，不得确认 intake_confirmed gate。
---

# Part 1 Search Plan Review

## 目标

审查既有 `outputs/part1/search_plan.json`，判断它是否能支撑 Part 1 文献收集的下一步执行。你的职责是发现检索策略风险、来源策略偏差和 gate 边界问题；不是重新生成 search plan。

## 输入

- `outputs/part1/intake.json`
- `outputs/part1/search_plan.json`
- `manifests/source-policy.json`
- `docs/01_build_target.md`（只读背景，如 runtime 提供）
- `docs/02_architecture.md`（只读背景，如 runtime 提供）

缺少 `intake.json` 或 `search_plan.json` 时停止并报告，不要补造。

## 输出

只输出 sidecar review，例如：

- `outputs/part1/researchagent_search_plan_review.json`

建议 JSON 结构：

```json
{
  "verdict": "pass | needs_revision | blocked",
  "findings": [
    {
      "severity": "high | medium | low",
      "finding": "问题说明",
      "evidence_refs": [
        {"artifact": "outputs/part1/search_plan.json", "field": "queries.cnki"}
      ],
      "recommended_action": "下一步处理建议"
    }
  ],
  "cnki_priority_checked": true,
  "does_not_modify_canonical_artifacts": true,
  "does_not_confirm_human_gate": true
}
```

## 审查重点

1. CNKI 是否是第一优先来源；英文来源只能作为补充，不得替代中文主检索。
2. 检索式是否来自 `intake.json` 的研究主题、关键词、时间范围和排除条件。
3. search plan 是否保留后续真实性校验、去重、来源标注所需字段。
4. 是否存在绕过 `manifests/source-policy.json` 的来源或运行时动态覆盖策略。
5. 是否把 writing-policy、作者风格或论文表达偏好混入 research evidence 检索条件。
6. 是否错误确认或暗示 `intake_confirmed` 已由 agent 自动完成。

## 禁止行为

- 不得改写 `outputs/part1/intake.json`。
- 不得改写 `outputs/part1/search_plan.json`。
- 不得生成或修改 `raw-library/metadata.json`、`outputs/part1/accepted_sources.json`、`outputs/part1/authenticity_report.json`。
- 不得确认、跳过或伪造 `intake_confirmed` human gate。
- 不得降低 CNKI 优先级，也不得把英文来源作为主检索替代。
