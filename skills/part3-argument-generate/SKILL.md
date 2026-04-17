---
name: part3-argument-generate
description: 学术研究 workflow Part 3 候选生成步骤：必须先由 deterministic script 生成 existing outputs/part3/argument_seed_map.json，然后必须由 LLM argumentagent 基于该 seed map 发散设计 3 份候选 argument tree，写入 outputs/part3/candidate_argument_trees/。当用户说「生成论证树候选」「开始 Part 3」「part3-argument-generate」时触发。此 skill 不生成、不改写、不拥有 seed map；只生成候选，不写 canonical argument_tree.json，不得跳过人工选择 gate。正式流程不得使用 deterministic fallback 代写论点。
---

# Part 3 Step 1 — Argument Tree Candidate Generation

你的任务是读取 deterministic script 已生成的 `outputs/part3/argument_seed_map.json`，并由 LLM `argumentagent` 基于其中可追溯的论证零件设计 3 份可比较的候选论证树。`argument_seed_map.json` 的所有权属于 deterministic runtime script（例如 `python3 cli.py part3-seed-map` / `runtime/agents/part3_argument_seed_map_generator.py`）；argumentagent 不得从 research wiki 自行生成、改写或拥有 seed map。候选树是草稿层产物，用于后续 stress-test、比较和 `part3-human-selection` 人工选择；本步骤不得锁定 canonical `outputs/part3/argument_tree.json`。

正式 Part 3 候选论点必须由 LLM 生成。Runtime script 只能负责请求封装、来源追溯校验、密度校验、schema 校验和落盘；不得在未显式降级时用 deterministic fallback 代写论点。`--allow-deterministic-fallback` 只允许用于离线调试或测试，不属于正常 workflow surface。

生成候选时必须同时应用 `part3-argument-divergent-generate` 的数量与创新点约束：先形成论点池，再组织 3 份候选树，避免只生成 3 个主论点的薄树。创新点可以是 evidence-bounded hypothesis，但必须带 trace、risk flag 与 evidence gap，不得写成无来源硬结论。

## 前置检查

1. `research-wiki/index.json` 存在且可读取。
2. `research-wiki/pages/` 存在，并且页面包含可回溯的 `source_ids` 或来源映射。
3. `writing-policy/` 可作为后续 comparison / outline 约束参考；当前 runtime generator 不读取 writing-policy，不得把写作规范当作研究证据。
4. Part 1 canonical artifacts 存在：`raw-library/metadata.json`、`outputs/part1/authenticity_report.json`。
5. Part 2 canonical artifact 存在：`research-wiki/index.json`。
6. `outputs/part3/argument_seed_map.json` 已由 deterministic script 生成并通过校验；缺失时停止，提示先运行 `python3 cli.py part3-seed-map`。
7. `outputs/part3/candidate_argument_trees/` 可写；不存在则创建。
8. `skills/part3-argument-divergent-generate/SKILL.md` 可读取；用于校准候选树的论点密度、发散角度与创新点边界。

如果 research wiki 不完整，停止并提示先完成 Part 2 health check。不得用 raw PDF 直接绕过 wiki 生成论证树。不得由 argumentagent 临时补造、重写或修复 `argument_seed_map.json`。

## 输入

- `research-wiki/index.json`
- `research-wiki/pages/*.md`
- `outputs/part3/argument_seed_map.json`（必需，且必须是 deterministic script 的既有输出）
- `writing-policy/rules/*.md`（可选，当前生成器不读取）
- `writing-policy/style_guides/*.md`（可选，当前生成器不读取）
- 用户确认过的研究主题、范围边界与核心研究问题

## 输出

本 skill 不输出、不覆盖 `outputs/part3/argument_seed_map.json`。该文件必须已经存在，且至少包含：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "wiki_ref": "research-wiki/index.json",
  "research_question": "研究问题",
  "candidate_claims": [],
  "evidence_points": [],
  "contradictions": [],
  "counterclaims": [],
  "method_paths": [],
  "case_boundaries": [],
  "evidence_gaps": [],
  "background_only_materials": []
}
```

`candidate_claims`、`evidence_points`、`contradictions`、`counterclaims` 中每一项都必须绑定 `source_ids` 和 `wiki_page_ids`。`method_paths`、`case_boundaries`、`evidence_gaps`、`background_only_materials` 如引用具体材料，也必须保留 `source_ids` 和 `wiki_page_ids`；无法追溯的内容只能进入 `evidence_gaps` 或被排除，不得支撑论点。

读取既有 seed map 后，生成 3 个候选文件：

- `outputs/part3/candidate_argument_trees/candidate_theory_first.json`
- `outputs/part3/candidate_argument_trees/candidate_problem_solution.json`
- `outputs/part3/candidate_argument_trees/candidate_case_application.json`

每个候选至少包含：

```json
{
  "schema_version": "1.0.0",
  "candidate_id": "candidate_theory_first",
  "generated_at": "<ISO 时间>",
  "strategy": "theory_first | problem_solution | case_application",
  "wiki_ref": "research-wiki/index.json",
  "argument_seed_map_ref": "outputs/part3/argument_seed_map.json",
  "root": {
    "node_id": "thesis_001",
    "claim": "核心论点",
    "node_type": "thesis",
    "support_source_ids": ["source_id"],
    "wiki_page_ids": ["page_id"],
    "seed_item_ids": ["claim_001"],
    "children": []
  }
}
```

每个候选还必须满足最低密度：

- 总节点数建议 `12-18`。
- 观点节点数建议 `9-13`，包括 `thesis`、`main_argument`、`sub_argument`、`counterargument`、`rebuttal`。
- `main_argument` 为 `3-5` 个；每个 `main_argument` 下至少 `2` 个 `sub_argument`。
- 至少设置 `1` 个 `counterargument`；如无 `rebuttal`，必须在 `limitations` 中说明反方如何进入 Part 4。
- 三份候选必须呈现不同 thesis、不同主线排序、不同创新点组合，不能只是章节顺序不同。

## 执行步骤

1. 读取 wiki index，确认可用页面、来源映射、争议页面与证据聚合页面。
2. 读取 deterministic script 已生成的 `outputs/part3/argument_seed_map.json`；缺失、schema 错误或追溯字段不完整时停止，不得自行生成或改写 seed map。
3. 检查 seed map 中每条 claim / evidence / counterclaim 是否有 `source_ids` 和 `wiki_page_ids`；缺失则降级为证据缺口，不得进入候选树支撑链。
4. 先按 `part3-argument-divergent-generate` 生成论点池：至少包含 evidence-backed claims、innovation hypotheses、counter positions 与 boundary claims。论点池不是 canonical artifact；它只用于候选设计。
5. 基于 existing deterministic seed map 和论点池设计 3 种不同论证策略：
   - `candidate_theory_first`: 从概念或理论框架组织证据。
   - `candidate_problem_solution`: 从问题提出到原因分析再到回应。
   - `candidate_case_application`: 从案例、类型或材料比较推进论证。
6. 为每个节点绑定 `support_source_ids`、`wiki_page_ids` 和 `seed_item_ids`；`seed_item_ids` 必须引用 `argument_seed_map.json` 中已存在的 `item_id`，且节点的 source/page 不得超出这些 seed item 的追溯范围。
7. 检查三份候选是否结构不同、证据可追溯、创新点类型不同、没有混入 writing policy 作为研究证据。
8. 只写入候选文件，保留为草稿层产物；不得写入 seed map、canonical argument tree 或 human selection 产物。

建议执行：

```bash
export RTM_ARGUMENTAGENT_COMMAND="python3 runtime/agents/argumentagent_codex_cli.py"
python3 cli.py part3-seed-map
python3 cli.py part3-generate
```

必须先由 deterministic script 生成 `argument_seed_map.json`，再由 `part3-generate` 生成候选树；不要直接运行单个 `part3-generate` 作为完整流程。若你是 argumentagent，只能执行第二步的候选设计职责，不能接管第一步 seed map 生成职责。

## 禁止事项

- 不得写入或覆盖 `outputs/part3/argument_tree.json`。
- 不得生成、改写、修复或拥有 `outputs/part3/argument_seed_map.json`。
- 不得声称 argumentagent 从 research wiki 生成 seed map；seed map 必须来自 deterministic script 的既有输出。
- 不得生成 `human_selection_feedback.json`。
- 不得进入 Part 4 或提示已经可以生成 outline。
- 不得把导师规范、学校格式、写作偏好当作研究证据。
- 不得使用未通过真实性校验或未进入 research wiki 的来源支撑论点。
- 不得让缺少 `source_ids` 或 `wiki_page_ids` 的 claim / evidence / counterclaim 进入候选树。
- 不得在候选不足 3 份时伪造完成；应报告缺口。
- 不得把创新点写成无来源硬结论；证据不足的创新点必须标记为 `innovation_hypothesis` 或 `requires_evidence_followup`。
- 不得只生成 `1 thesis + 3 main_argument` 的薄树；如果 seed map 太小，应生成带风险标记的假说型 sub-argument，并登记证据缺口。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 3 候选论证树生成完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  候选数量: 3
  Seed map: outputs/part3/argument_seed_map.json
  输出目录: outputs/part3/candidate_argument_trees/
  候选文件:
    - candidate_theory_first.json
    - candidate_problem_solution.json
    - candidate_case_application.json

  证据缺口: <数量>
  写作规范约束: <充足 / 不足>

下一步：运行 part3-argument-compare 生成 candidate_comparison.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
