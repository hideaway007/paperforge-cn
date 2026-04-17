---
name: part3-argument-compare
description: 学术研究 workflow Part 3 第二步：比较 3 份候选 argument tree，生成 outputs/part3/candidate_comparison.json，列出优缺点、证据强度、风险和选择建议。当用户说「比较论证树」「生成候选比较」「part3-argument-compare」时触发。此 skill 不锁定 canonical，不替用户做最终选择。
---

# Part 3 Step 2 — Candidate Argument Tree Comparison

你的任务是比较 3 份候选论证树，帮助用户做人工选择。比较结果是 human selection 的依据，不是最终拍板。

## 前置检查

1. `outputs/part3/candidate_argument_trees/` 存在。
2. 至少存在且只能以 3 份候选进入正式比较：`candidate_theory_first.json`、`candidate_problem_solution.json`、`candidate_case_application.json`。
3. 每份候选都包含 `candidate_id`、`strategy`、`root`、`support_source_ids` 和 `wiki_page_ids` 或等价来源映射。
4. `research-wiki/index.json` 存在，用于抽查候选节点的 wiki 回溯。
5. `outputs/part3/argument_quality_report.json` 可选；如果已存在，比较时必须吸收其中的 `candidate_findings`、`quality_dimensions` 和 `outline_readiness`。
6. 不要求 `human_selection_feedback.json` 存在；如果已存在，提示可能是在复核既有选择，不要覆盖除非用户明确要求。

如果候选不齐，停止并提示先运行 `part3-argument-generate`。

## 输入

- `outputs/part3/candidate_argument_trees/candidate_theory_first.json`
- `outputs/part3/candidate_argument_trees/candidate_problem_solution.json`
- `outputs/part3/candidate_argument_trees/candidate_case_application.json`
- `research-wiki/index.json`
- `outputs/part3/argument_quality_report.json`（可选）
- `writing-policy/`

## 输出

- `outputs/part3/candidate_comparison.json`

建议结构：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "wiki_ref": "research-wiki/index.json",
  "argument_quality_report_ref": "outputs/part3/argument_quality_report.json",
  "candidate_tree_refs": [
    "outputs/part3/candidate_argument_trees/candidate_theory_first.json"
  ],
  "candidates": [
    {
      "candidate_id": "candidate_theory_first",
      "strategy": "theory_first",
      "strengths": [],
      "weaknesses": [],
      "evidence_coverage": {
        "source_ids": ["source_id"],
        "source_count": 1
      },
      "wiki_coverage": {
        "page_ids": ["page_id"],
        "page_count": 1
      },
      "risks": [],
      "quality_findings": [],
      "outline_readiness": "ready | risky | blocked"
    }
  ],
  "recommendation": {
    "recommended_candidate_id": "candidate_theory_first",
    "reason": "推荐理由",
    "human_decision_required": true,
    "selection_cautions": []
  }
}
```

## 执行步骤

1. 读取 3 份候选树，确认候选 ID 与文件名一致。
2. 按以下维度比较：
   - 论证主线是否清晰。
   - 研究问题覆盖是否完整。
   - 节点是否能回溯到 wiki 页面和 source_id。
   - 证据强度与证据缺口。
   - 对争议、反驳和限制的处理能力。
   - `argument_quality_report.json` 中的 `candidate_findings`、`quality_dimensions`、`outline_readiness`，尤其是跳跃论证、warrant 缺失、claim 过大、case 外推过度与 Part 4 outline 风险。
   - 与中文学术写作规范和导师偏好的适配度。
3. 对每份候选写出优点、缺点、风险与适用条件。
4. 给出选择建议，但明确最终选择必须由用户完成。
5. 写入 `candidate_comparison.json`。

建议执行：

```bash
python3 cli.py part3-compare
```

## 禁止事项

- 不得写入或覆盖 `outputs/part3/argument_tree.json`。
- 不得写入 `human_selection_feedback.json`。
- 不得把 `recommendation` 当作用户选择。
- 不得在比较完成后自动推进 Part 4。
- 不得为了推荐某候选而忽略证据缺口或来源不可追溯问题。
- 不得把 `argument_quality_report.json` 当作人工选择；它只提供质量维度和风险证据。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 3 候选比较完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  比较文件: outputs/part3/candidate_comparison.json
  候选数量: 3
  推荐候选: <candidate_id>
  主要理由: <一句话>
  仍需人工确认: 是

下一步：运行 part3-human-selection，用户必须提供 candidate_id 和选择理由
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
