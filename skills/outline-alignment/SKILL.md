---
name: outline-alignment
description: 学术研究 workflow Part 4：当 agent 生成或检查 outputs/part4/paper_outline.json、outline_rationale.json、reference_alignment_report.json 时触发。用于确认 paper outline 覆盖 canonical argument tree、可回溯 research-wiki、遵守 writing-policy 分层，并对齐中文论文参考案例与章节 rubric；Part 4 不再需要 outline_confirmed。
---

# Part 4 — Outline Alignment

你的任务是生成或复核 Part 4 的 outline artifacts，确保大纲通过 completion gate 后可以自动进入 Part 5。

## 前置检查

1. 只读当前基线：`docs/01_build_target.md`、`docs/02_architecture.md`。二者已吸收 Part 3 / Part 5 / Part 6 专项架构结论；如与 runtime gate 冲突，以 `AGENTS.md`、`manifests/pipeline-stages.json` 与 runtime gate 为准，并报告冲突。
2. `outputs/part3/argument_tree.json` 存在，且显示已由 `argument_tree_selected` gate 锁定。
3. `research-wiki/index.json` 与 `research-wiki/pages/` 可读取，outline 的每个研究性章节都能回溯到 wiki 页面和 `source_id`。
4. `writing-policy/` 与 `research-wiki/` 必须物理分离；`writing-policy/source_index.json` 是 Part 4 写作规范审计入口，缺失时不能通过 completion gate。导师规范、格式要求、参考案例、rubric 只能作为写作约束，不得作为研究证据。
5. 查找中文论文参考案例与章节 rubric。二者是可选输入；缺失时仍可生成草稿，但必须写入 `reference_alignment_report.json` 风险项，不得伪造参考来源。
6. `outputs/part4/` 可写；不得改动 Part 3 canonical 文件。

## 输入

- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `research-wiki/pages/*.md`
- `writing-policy/rules/*.md`
- `writing-policy/style_guides/*.md`
- `writing-policy/reference_cases/*`（可选）
- `writing-policy/rubrics/*`（可选）

## 输出

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`

建议最小结构：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "confirmed_at": null,
  "argument_tree_ref": "outputs/part3/argument_tree.json",
  "wiki_ref": "research-wiki/index.json",
  "writing_policy_ref": "writing-policy/source_index.json",
  "reference_cases_used": ["writing-policy/reference_cases/case_001.md"],
  "sections": [
    {
      "section_id": "sec_1",
      "title": "章节标题",
      "level": 1,
      "brief": "本章承担的论证任务",
      "argument_node_ids": ["node_id"],
      "support_source_ids": ["source_id"],
      "writing_constraints": ["rule_id 或约束摘要"],
      "subsections": []
    }
  ]
}
```

`confirmed_at` 只作为旧 schema 兼容字段保留，不再作为 Part 4 completion gate 或 Part 5 entry 的判断条件。

## 对齐规则

1. **Argument tree 覆盖**：每个核心 `argument_node` 必须进入某个章节；未覆盖节点写入 `outline_rationale.json` 的 `coverage_gaps`。
2. **Research-wiki 回溯**：章节中的研究判断必须绑定 `wiki_pages` 与 `source_ids`；证据不足时标注缺口，不得从 raw PDF 或外部摘要绕过 wiki。
3. **Writing-policy 分层**：写作规范只影响章节顺序、表达要求、篇幅比例、格式与风格；不得把规范材料当成文献证据。
4. **Reference cases / rubric 对齐**：`reference_alignment_report.json` 需说明参考案例影响了哪些结构选择，rubric 哪些项通过、部分通过或未通过。
5. **自动进入 Part 5**：生成完成并通过校验后，Part 4 可自动进入 Part 5；不得要求 `outline_confirmed`。

## 执行步骤

1. 读取 canonical argument tree，列出所有必须覆盖的核心论点、反驳、限制与结论节点。
2. 从 research wiki 建立 `argument_node -> wiki_page -> source_id` 回溯表。
3. 从 writing policy、参考案例和 rubric 提取结构约束，不混入 research evidence。
4. 生成或检查章节层级，确认章节顺序服务于论证路线，而不是简单堆砌材料。
5. 写入或更新三份 Part 4 artifacts，并在 rationale 中记录覆盖缺口、证据缺口、写作约束不足和 Part 5 必须继承的风险项。

项目内默认 agent：

```bash
python3 runtime/agents/part4_outline_generator.py
```

## 禁止事项

- 不得修改 `outputs/part3/argument_tree.json` 或任何 Part 3 候选文件。
- 不得把 `outline_confirmed` 作为正常流程条件。
- 不得跳过 reference alignment report。
- 不得把 writing-policy、参考案例、rubric 与 research evidence 混为一层。
- 不得用无法回溯到 research wiki 的内容支撑研究性章节。
- 不得在 Part 4 artifacts 未通过校验时进入 Part 5。
- 不得自动进入 Part 6。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 4 Outline Alignment 完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Outline: outputs/part4/paper_outline.json
  Rationale: outputs/part4/outline_rationale.json
  Reference alignment: outputs/part4/reference_alignment_report.json
  Argument tree 覆盖: <完整 / 有缺口>
  Research wiki 回溯: <完整 / 有缺口>
  Writing-policy 分层: <通过 / 有风险>
  outline_confirmed: 不再需要
  Part 5 自动进入条件: <满足 / 阻断及原因>

下一步：Part 4 completion gate 通过后自动进入 Part 5 prep → draft → review → revise。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
