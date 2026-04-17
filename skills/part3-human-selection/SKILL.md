---
name: part3-human-selection
description: 学术研究 workflow Part 3 第三步：执行 argument_tree_selected 人工 gate。只有用户明确提供 candidate_id、候选来源（original/refined）和选择理由后，才写入 outputs/part3/human_selection_feedback.json，并将对应候选锁定为 canonical outputs/part3/argument_tree.json。当用户说「选择论证树」「锁定 argument tree」「part3-human-selection」时触发。不得自动跳过 gate 或进入 Part 4。
---

# Part 3 Step 3 — Human Selection and Canonical Lock

你的任务是展示候选与比较结果，记录用户明确选择，并在 human gate 通过后锁定 canonical `outputs/part3/argument_tree.json`。这是 Part 3 的人工决策点，不允许由 agent 代替用户完成。用户可以选择原始候选或 refined 候选；选择 refined candidate 时必须通过工程 CLI 的 refined source 入口，不得覆盖原始 candidate 文件。

## 前置检查

1. 原始候选目录 `outputs/part3/candidate_argument_trees/` 存在；如果用户选择 refined candidate，`outputs/part3/refined_candidate_argument_trees/` 也必须存在。
2. 原始候选至少包含 `candidate_theory_first.json`、`candidate_problem_solution.json`、`candidate_case_application.json`。
3. refined candidate 只能从 `outputs/part3/refined_candidate_argument_trees/` 读取，ID 必须是 `{original_candidate_id}_refined`，例如 `candidate_theory_first_refined`；不得复制到原始候选目录后再选择。
4. `outputs/part3/candidate_comparison.json` 存在。
5. `outputs/part3/candidate_selection_table.md` 应存在；缺失时先运行 `python3 cli.py part3-review` 生成并展示表格。
6. 用户在当前对话中明确提供：
   - `candidate_id`
   - 候选来源：`original` 或 `refined`
   - 选择理由
7. 如果 `outputs/part3/argument_tree.json` 已存在，必须提示这是重新锁定场景；只有用户明确要求覆盖时才继续。

如果用户只说“按推荐的来”但没有提供 candidate_id 和理由，应先展示推荐与候选摘要，并要求用户明确确认。不得推断为已选择。

## 输入

- `outputs/part3/candidate_argument_trees/{candidate_id}.json`，或通过 refined source 入口读取 `outputs/part3/refined_candidate_argument_trees/{original_candidate_id}_refined.json`
- `outputs/part3/candidate_comparison.json`
- `outputs/part3/argument_quality_report.json`（选择 refined candidate 时建议存在）
- `outputs/part3/candidate_selection_table.md`
- 用户明确给出的 `candidate_id`
- 用户明确给出的候选来源：`original` 或 `refined`
- 用户明确给出的选择理由

## 输出

- `outputs/part3/candidate_selection_table.md`（人工选择前的三候选表格）
- `outputs/part3/human_selection_feedback.json`
- `outputs/part3/argument_tree.json`

`human_selection_feedback.json` 建议结构：

```json
{
  "schema_version": "1.0.0",
  "selected_at": "<ISO 时间>",
  "selected_candidate_id": "candidate_theory_first",
  "candidate_source": "original | refined",
  "selection_notes": "用户选择理由",
  "candidate_tree_ref": "outputs/part3/candidate_argument_trees/candidate_theory_first.json",
  "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
  "locked_artifact": "outputs/part3/argument_tree.json"
}
```

`argument_tree.json` 应复制并规范化所选候选内容，同时增加 canonical 锁定字段：

```json
{
  "schema_version": "1.0.0",
  "locked_at": "<ISO 时间>",
  "selected_candidate_id": "candidate_theory_first",
  "human_selection_ref": "outputs/part3/human_selection_feedback.json",
  "candidate_comparison_ref": "outputs/part3/candidate_comparison.json",
  "wiki_ref": "research-wiki/index.json",
  "root": {}
}
```

## 执行步骤

1. 读取 comparison 和 3 份候选，运行 `python3 cli.py part3-review`，生成并展示 `candidate_selection_table.md`。
2. 检查用户是否明确提供 `candidate_id` 和选择理由。
3. 如果缺任一项，停止，要求用户补充；不要写文件。
4. 验证 `candidate_id` 对应候选文件存在；如果来源是 `refined`，必须通过工程 CLI 的 refined source 入口读取 `outputs/part3/refined_candidate_argument_trees/`，不得覆盖原始候选。
5. 写入 `human_selection_feedback.json`，记录选择理由、候选树路径、comparison 路径与 locked artifact。
6. 将所选候选复制为 canonical `outputs/part3/argument_tree.json`，保留候选 root，并追加 canonical 锁定字段。
7. 通过 CLI 调用时，记录 `argument_tree_selected` human gate；不得启动 Part 4。

建议执行：

```bash
python3 cli.py part3-review
python3 cli.py part3-select --candidate-id candidate_theory_first --notes "人工选择理由"
# 选择 refined candidate 时，使用工程 CLI 提供的 refined source 入口，例如：
python3 cli.py part3-select --candidate-id candidate_theory_first_refined --candidate-source refined --notes "人工选择理由"
```

如果已存在 `outputs/part3/argument_tree.json`，只有用户明确要求重新锁定时才可追加 `--force`。

## 禁止事项

- 不得替用户选择候选。
- 不得把 agent recommendation 当作 human selection。
- 不得在没有选择理由时写入 `human_selection_feedback.json`。
- 不得通过复制 refined candidate 覆盖原始 candidate 的方式绕过 refined source 入口。
- 不得自动进入 Part 4，或生成 `outputs/part4/paper_outline.json`。
- 不得覆盖既有 canonical `argument_tree.json`，除非用户明确要求重新锁定。
- 不得手动修改 `runtime/` 或 `process-memory/`；必须通过 `python3 cli.py part3-select ...` 或 selection locker 记录 `argument_tree_selected`，保证 state 与 process-memory 可审计。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 3 人工选择已记录
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Gate: argument_tree_selected
  选择候选: <candidate_id>
  候选来源: <original / refined>
  选择理由: <用户理由摘要>
  候选表格: outputs/part3/candidate_selection_table.md
  反馈文件: outputs/part3/human_selection_feedback.json
  Canonical: outputs/part3/argument_tree.json

Part 3 gate 状态: 已满足
Part 4 授权状态: 未授权

下一步：等待用户明确要求进入 Part 4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
