---
name: part3-argument-stress-test
description: 学术研究 workflow Part 3 质量攻击步骤：审查候选 argument tree 的论证跳跃、证据不足、claim 过大、warrant 缺失、反驳薄弱、案例外推过度和 Part 4 outline 风险，输出 argument_quality_report.json。当用户说「压力测试论证树」「审查候选论证质量」「part3-argument-stress-test」时触发。此 skill 只评审候选，不改 canonical，不做人工选择。
---

# Part 3 — Argument Tree Stress Test

你的任务是攻击候选 argument tree，找出会让论文论证不成立或无法进入 Part 4 outline 的结构问题。此步骤只评审，不修改候选，不写 canonical `outputs/part3/argument_tree.json`，不替用户选择。

## 前置检查

1. `research-wiki/index.json` 存在且可读取。
2. `outputs/part3/argument_seed_map.json` 存在；缺失时提示先运行 `part3-argument-generate`。
3. `outputs/part3/candidate_argument_trees/` 中存在 3 份候选。
4. 每个候选节点的 claim / evidence / counterclaim 必须能回溯到 `source_ids` 和 `wiki_page_ids`。

如果候选不齐或来源不可追溯，停止并记录为质量阻断项。不得绕过 Part 2 wiki 或直接用 raw PDF 补证据。

## 输入

- `outputs/part3/argument_seed_map.json`
- `outputs/part3/candidate_argument_trees/*.json`
- `research-wiki/index.json`

## 输出

- `outputs/part3/argument_quality_report.json`

质量报告至少必须描述 `candidate_findings`、`quality_dimensions`、`outline_readiness`。建议结构：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "wiki_ref": "research-wiki/index.json",
  "argument_seed_map_ref": "outputs/part3/argument_seed_map.json",
  "candidate_tree_refs": [],
  "candidate_findings": [
    {
      "candidate_id": "candidate_theory_first",
      "blocking_issues": [],
      "major_issues": [],
      "minor_issues": [],
      "outline_readiness": "ready | risky | blocked",
      "quality_dimensions": {
        "logical_jumps": [],
        "insufficient_evidence": [],
        "overbroad_claims": [],
        "missing_warrants": [],
        "weak_counterarguments": [],
        "case_overextension": [],
        "part4_outline_risks": []
      }
    }
  ],
  "overall_recommendations": []
}
```

## 执行步骤

1. 读取 seed map、3 份候选和 wiki index。
2. 逐候选检查：论证跳跃、证据不足、claim 过大、warrant 缺失、counterargument 薄弱、case 外推过度、无法转化为 Part 4 outline 的结构问题。
3. 每条问题必须指向 `candidate_id`、节点或 claim，并尽量保留对应 `source_ids` / `wiki_page_ids`。
4. 标记阻断项、主要问题、次要问题和 outline readiness。
5. 写入 `argument_quality_report.json`，供 compare 或 refine 使用。

## 禁止事项

- 不得写入或覆盖 `outputs/part3/argument_tree.json`。
- 不得修改原始候选文件。
- 不得写入 `human_selection_feedback.json` 或替用户选择候选。
- 不得自动进入 Part 4。
- 不得把 `writing-policy/` 当作研究证据；写作规范最多用于判断表达或 outline 风险。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 3 论证树压力测试完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  质量报告: outputs/part3/argument_quality_report.json
  候选数量: 3
  阻断项: <数量>
  Outline readiness: <ready / risky / blocked>

下一步：运行 part3-argument-compare 或 part3-argument-refine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
