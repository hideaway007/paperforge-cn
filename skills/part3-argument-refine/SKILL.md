---
name: part3-argument-refine
description: 学术研究 workflow Part 3 候选优化步骤：基于 argument_seed_map、argument_quality_report 和 candidate_comparison 生成 refined candidate argument trees，默认写入 outputs/part3/refined_candidate_argument_trees/。当用户说「优化论证树候选」「根据质量报告改候选」「part3-argument-refine」时触发。此 skill 不覆盖原始候选，不写 canonical，不跳过 part3-human-selection。
---

# Part 3 — Argument Tree Candidate Refinement

你的任务是默认读取 `argument_seed_map.json`、`candidate_comparison.json`、`argument_quality_report.json`，生成 refined candidates。refined candidate ID 统一为 `{original_candidate_id}_refined`，例如 `candidate_theory_first_refined`。refine 只产出新的候选版本，不覆盖原始候选，不锁定 canonical `outputs/part3/argument_tree.json`。refine 后仍必须由 `part3-human-selection` 让用户最终选定。

## 前置检查

1. `outputs/part3/argument_seed_map.json` 存在。
2. `outputs/part3/argument_quality_report.json` 存在。
3. `outputs/part3/candidate_comparison.json` 存在。
4. 原始候选目录 `outputs/part3/candidate_argument_trees/` 存在。
5. 如果 `outputs/part3/argument_tree.json` 或 `outputs/part3/human_selection_feedback.json` 已存在，默认必须停止；只有用户明确说明要进入重新生成或重新选择流程，才可继续生成新的 refined 候选，且仍不得覆盖 canonical。

不得用 refine 绕过 `argument_tree_selected` gate，也不得把既有 human selection 静默改写。

## 输入

- `outputs/part3/argument_seed_map.json`
- `outputs/part3/candidate_comparison.json`
- `outputs/part3/argument_quality_report.json`
- `outputs/part3/candidate_argument_trees/*.json`
- `research-wiki/index.json`

## 输出

默认写入：

- `outputs/part3/refined_candidate_argument_trees/{original_candidate_id}_refined.json`
- `outputs/part3/refined_candidate_argument_trees/refinement_summary.json`

示例 refined 文件：

- `outputs/part3/refined_candidate_argument_trees/candidate_theory_first_refined.json`

refined candidate 应保留原候选引用：

```json
{
  "schema_version": "1.0.0",
  "candidate_id": "candidate_theory_first_refined",
  "refined_at": "<ISO 时间>",
  "based_on_candidate_ref": "outputs/part3/candidate_argument_trees/candidate_theory_first.json",
  "argument_seed_map_ref": "outputs/part3/argument_seed_map.json",
  "argument_quality_report_ref": "outputs/part3/argument_quality_report.json",
  "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
  "wiki_ref": "research-wiki/index.json",
  "root": {}
}
```

## 执行步骤

1. 检查 canonical 和 human selection 是否已存在；存在则默认停止，除非用户明确要求重新生成或重新选择流程。
2. 读取 `argument_seed_map.json`、`candidate_comparison.json`、`argument_quality_report.json` 和原始候选；不得只用 comparison 中的摘要替代质量报告。
3. 针对阻断项和主要问题调整候选结构：收窄过大 claim、补足 warrant、强化反驳位置、降低案例外推、标明证据缺口。
4. 每个 refined 节点继续绑定 `support_source_ids` 和 `wiki_page_ids`；缺失来源的内容不得作为支撑链。
5. 写入 `outputs/part3/refined_candidate_argument_trees/` 和 `refinement_summary.json`；不要覆盖 `candidate_argument_trees/` 下的原始候选。

## 禁止事项

- 不得写入或覆盖 `outputs/part3/argument_tree.json`。
- 不得写入或覆盖 `outputs/part3/human_selection_feedback.json`。
- 不得覆盖原始候选文件。
- 不得自动选择 refined candidate。
- 不得把 refined candidate 复制或改名覆盖到 `outputs/part3/candidate_argument_trees/`。
- 不得进入 Part 4 或声称 outline 已被授权。
- 不得把 `writing-policy/` 当作研究证据。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 3 候选论证树优化完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Refined 输出目录: outputs/part3/refined_candidate_argument_trees/
  Refined 候选数量: <数量>
  Summary: outputs/part3/refined_candidate_argument_trees/refinement_summary.json
  仍需人工选择: 是

下一步：运行 part3-argument-compare 或通过 part3-human-selection 的 refined source 入口由用户明确选择 candidate_id
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
