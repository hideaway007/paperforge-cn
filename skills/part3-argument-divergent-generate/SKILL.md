---
name: part3-argument-divergent-generate
description: 学术研究 workflow Part 3 发散论点生成约束：当候选 argument tree 论点数量偏少、三份候选过于同构、创新点不足或过度局限于 local research wiki 时触发。用于在不绕过 Part 1/2 来源追溯、不写 canonical argument_tree.json、不跳过 argument_tree_selected 人工 gate 的前提下，扩展论点数量、创新角度、反方处理与证据缺口登记。
---

# Part 3 发散论点生成

## 用途

本 skill 用于修正 Part 3 候选论证树过薄的问题。它不替代 `part3-argument-generate`，而是约束 LLM `argumentagent` 在生成候选树时必须先做论点池发散，再组织候选论证树。

正式流程中，论点池、创新角度和候选论证树必须由 LLM 生成；deterministic runtime 只做 seed map、校验和落盘。任何 deterministic fallback 都只能作为显式离线降级，不得作为正式 Part 3 论点生成结果。

读取基准见 `references/repository_argument_density.md`。当前仓库的 clean root 没有真实 `raw-library` 论文全文，因此该基准来自项目内 reference case、Part 3 runtime generator 和测试样例，不得伪装成真实文献库统计。

## 输入边界

允许读取：

- `outputs/part3/argument_seed_map.json`
- `research-wiki/index.json`
- `research-wiki/pages/*.md`
- `raw-library/metadata.json`
- `outputs/part3/argument_quality_report.json` 和 `candidate_comparison.json`，仅在 refine 阶段读取
- `writing-policy/reference_cases/`，只作为结构密度参考，不作为 research evidence

禁止：

- 不得新增不可回溯的 `source_id`、案例事实、数据或研究结论。
- 不得把创新点写成已证实结论，除非它能绑定 `source_ids`、`wiki_page_ids` 和 `seed_item_ids`。
- 不得写入 `outputs/part3/argument_tree.json`。
- 不得写入或替用户确认 `human_selection_feedback.json`。
- 不得绕过 `argument_tree_selected` human gate。

## 数量要求

每一份候选 argument tree 的建议密度：

- 总节点数：`12-18`
- 观点节点数：`9-13`，包括 `thesis`、`main_argument`、`sub_argument`、`counterargument`、`rebuttal`
- `main_argument`：`3-5`
- 每个 `main_argument` 下至少 `2` 个 `sub_argument`
- 至少 `1` 个 `counterargument`
- 至少 `1` 个 `rebuttal` 或在 `limitations` 中说明为何暂不设置 rebuttal
- 纯 `evidence` 节点不计入观点数量，只计入证据支撑

如果 `argument_seed_map.json` 过小，不能硬凑成强结论；应把不足部分写成 `risk_flags: ["innovation_hypothesis", "requires_evidence_followup"]` 的假说型 sub-argument，并在 `limitations` 中说明需要 Part 1/2 补证。

## 创新点类型

至少覆盖以下 7 类中的 `4` 类，且三份候选之间不得使用完全相同的组合：

| 类型 | 作用 | 风险控制 |
|------|------|----------|
| concept_reframe | 重新界定核心概念或研究对象 | 必须绑定概念页或 topic 页 |
| contradiction_finding | 从材料中提取矛盾、张力或未解决问题 | 必须绑定 contradiction / evidence gap / counterclaim |
| scale_shift | 在建筑单体、街区、城市、制度、使用者之间转换尺度 | 标注适用尺度与外推边界 |
| method_transfer | 把方法页转化为分析框架 | 不得把方法描述当作结论 |
| case_boundary | 用案例说明机制，同时限制外推 | 必须写明案例不能代表整体 |
| policy_or_practice_mechanism | 把政策、运营、教学、财政、产权等机制纳入论证 | 没有证据时只能列为待补证假说 |
| counter_position | 主动设置反方或竞争解释 | 必须有回应或保留为风险 |

## 生成步骤

1. 读取 `argument_seed_map.json`，先列出所有 `candidate_claims`、`method_paths`、`contradictions`、`counterclaims`、`case_boundaries`、`evidence_gaps`。
2. 先生成一个论点池，而不是直接写树。论点池至少包含：
   - `6-10` 个 evidence-backed claims
   - `3-5` 个 innovation hypotheses
   - `2-4` 个 counter positions
   - `2-3` 个 boundary claims
3. 为每个论点标注：
   - `argument_role`
   - `innovation_type`
   - `support_source_ids`
   - `wiki_page_ids`
   - `seed_item_ids`
   - `evidence_status`: `backed | weak | gap`
   - `risk_flags`
4. 再从论点池组织 3 份候选树：
   - `candidate_theory_first`: 偏概念重组、方法迁移、反方处理。
   - `candidate_problem_solution`: 偏矛盾发现、机制解释、解决路径。
   - `candidate_case_application`: 偏案例边界、尺度转换、应用机制。
5. 每份候选都必须有不同的 thesis、不同的主线排序、不同的创新点组合。
6. 输出仍然只能写入 `outputs/part3/candidate_argument_trees/` 或 refined candidate 目录；不得写 canonical。

## 质量检查

生成后逐项检查：

- 三份候选是否只有章节顺序不同，而非论点不同；如果是，必须重写。
- 是否只有 `3` 个 main arguments；如果是，必须扩展 sub-argument。
- 是否所有创新点都被写成硬结论；如果是，必须降级为 hypothesis 或 evidence gap。
- 是否每个主论点都能回答 research question 的一个不同侧面。
- 是否至少有一条反方观点，避免论文只做正向堆叠。
- 是否保留 source/wiki/seed trace，避免“创新”变成幻觉。

## 输出摘要

结果摘要应报告：

```text
Part 3 发散论点生成检查
- 每候选总节点数: <min-max>
- 每候选观点节点数: <min-max>
- 创新点类型覆盖: <list>
- 假说型论点: <count>
- 证据缺口: <count>
- 是否仍需人工选择: 是
```
