---
name: part4-outline-generate
description: 学术研究 workflow Part 4：基于已锁定的 outputs/part3/argument_tree.json、research-wiki 与 writing-policy 生成并校验 canonical paper_outline.json、outline_rationale.json、reference_alignment_report.json。当用户说「生成论文大纲」「开始 Part 4」「part4-outline-generate」时触发。Part 4 不再需要 outline_confirmed，生成通过后可自动进入 Part 5。
---

# Part 4 — Outline Generation

你的任务是生成 Part 4 三份 canonical outline artifacts。Part 4 不再设置 `outline_confirmed` 人工 gate；三件套通过校验后即可作为 Part 4 completion，并允许自动进入 Part 5。

## 前置检查

1. 只读历史基线：`docs/01_build_target.md`、`docs/02_architecture.md`。二者是不可改原始设计文档；如其旧 HITL / MVP 表述与当前 workflow 冲突，以 `AGENTS.md`、`manifests/pipeline-stages.json`、`docs/part5_architecture.md` 与 runtime gate 为准，并报告冲突。
2. `outputs/part3/argument_tree.json` 存在，且来自用户选择后的 canonical lock。
3. `runtime/state.json` 中 Part 3 已完成且 `argument_tree_selected` 已记录；否则停止。
4. `research-wiki/index.json` 与 `research-wiki/pages/` 可读取，outline 的研究性章节必须能回溯到 wiki 页面和 `source_id`。
5. `writing-policy/` 与 `research-wiki/` 必须物理分离；`writing-policy/source_index.json` 缺失时可以生成草稿，但必须在 alignment report 中标记为风险。
6. `writing-policy/reference_cases/` 与 `writing-policy/rubrics/` 是 Part 4 参考约束；缺失时不得伪造参考案例或 rubric。
7. `outputs/part4/` 可写；不得改动 Part 3 canonical 文件。

## 输入

- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `research-wiki/pages/*.md`
- `writing-policy/source_index.json`
- `writing-policy/rules/*.md`
- `writing-policy/style_guides/*.md`
- `writing-policy/reference_cases/*`（可选）
- `writing-policy/rubrics/*`（可选）

## 输出

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`

如旧 schema 仍包含 `confirmed_at` 字段，该字段仅为兼容旧流程，不再作为 Part 4 completion 或进入 Part 5 的阻断条件。

## 执行步骤

1. 读取 canonical argument tree，列出必须覆盖的 thesis、main argument、counter、rebuttal、limitation 与 conclusion 节点。
2. 建立 `argument_node -> wiki_page -> source_id` 回溯表；证据不足时写入 rationale 或 alignment report，不得编造来源。
3. 使用 `$part4-outline-authoring` 判断章节应该写什么、怎么写、如何把 argument tree 转译成 Part 5 可写正文结构。
4. 从 writing policy、reference cases、rubrics 提取章节顺序、表达、篇幅、格式和风格约束；不得把这些材料当作研究证据。
5. 生成章节结构，确保章节服务于论证路线，而不是简单按材料堆叠。
6. 生成 `outline_rationale.json`，记录结构选择理由、argument tree 覆盖情况、证据缺口和自动进入 Part 5 时需继承的风险项。
7. 生成 `reference_alignment_report.json`，记录 reference cases / rubrics 使用情况、通过项、部分通过项和风险项。
8. 向用户摘要结果，并说明 Part 4 completion gate 通过后可自动进入 Part 5。

建议先 dry-run：

```bash
python3 cli.py part4-generate --dry-run
```

正式生成：

```bash
python3 cli.py part4-generate
```

如需指定工作区：

```bash
python3 cli.py part4-generate --project-root /path/to/workspace
```

## 禁止事项

- 不得调用旧流程的 `python3 cli.py confirm-gate outline_confirmed ...` 作为正常步骤。
- 不得把 `outline_confirmed` 作为进入 Part 5 的必需条件。
- 不得修改 `outputs/part3/argument_tree.json`、Part 3 候选树或 `human_selection_feedback.json`。
- 不得把 writing-policy、reference cases、rubrics 混入 research-wiki 或当作研究证据。
- 不得用无法回溯到 research wiki 的内容支撑研究性章节。
- 不得自动进入 Part 6。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 4 大纲草稿生成完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Outline: outputs/part4/paper_outline.json
  Rationale: outputs/part4/outline_rationale.json
  Reference alignment: outputs/part4/reference_alignment_report.json
  Argument tree 覆盖: <完整 / 有缺口>
  Research wiki 回溯: <完整 / 有缺口>
  Writing-policy 分层: <通过 / 有风险>
  outline_confirmed: 不再需要
  Part 5 自动进入条件: <满足 / 阻断及原因>

下一步：Part 4 completion gate 通过后，自动进入 Part 5 prep → draft → review → revise。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
