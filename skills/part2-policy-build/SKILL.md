---
name: part2-policy-build
description: 学术研究 workflow Part 2 writing-policy 构建：从导师 PPT、课程资料、中文学术写作规范、参考案例和章节 rubric 中提炼写作规则层，写入 writing-policy/ 并生成 source_index.json。当用户说「构建写作规范层」「补 writing-policy」「part2-policy-build」时触发。此 skill 必须保持 writing-policy 与 research-wiki 物理分离，不得把写作规范当作研究证据。
---

# Part 2 — Writing Policy Build

你的任务是建立 writing policy layer，让 Part 3 / Part 4 可以读取写作规范、参考案例和章节 rubric。这个层只约束结构、表达和格式，不提供研究证据。

## 前置检查

1. 只读参考真相源：`docs/01_build_target.md`、`docs/02_architecture.md`。如与本 skill 冲突，以 docs 为准并报告。
2. `research-wiki/` 与 `writing-policy/` 必须是两个物理目录。
3. 写作规范输入可以来自导师 PPT、课程要求、学校格式规范、中文论文参考案例、章节结构 rubric。
4. 研究证据输入必须留在 `research-wiki/`；不得把 writing-policy 材料写入 `research-wiki/pages/`。
5. `writing-policy/` 不存在时可以创建；不得改写 `raw-library/`。

## 输入

- 导师 PPT / 课程资料 / 学校格式规范
- 中文学术论文参考案例
- 章节结构 rubric
- 用户提供的写作偏好、禁区或导师反馈
- `docs/01_build_target.md` 与 `docs/02_architecture.md` 中关于 knowledge layering 的约束

## 输出

- `writing-policy/source_index.json`
- `writing-policy/rules/{rule_id}.md`
- `writing-policy/style_guides/{guide_id}.md`
- `writing-policy/reference_cases/{case_id}.md`
- `writing-policy/rubrics/{rubric_id}.md`

`source_index.json` 建议至少记录：

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<ISO 时间>",
  "layer": "writing-policy",
  "research_evidence_layer": "research-wiki/",
  "physical_separation_required": true,
  "sources": [
    {
      "source_id": "policy_001",
      "source_type": "advisor_ppt | school_rule | reference_case | rubric | user_note",
      "path": "writing-policy/rules/rule_001.md",
      "scope": "structure | style | formatting | expression | chapter_rubric",
      "may_be_used_as_research_evidence": false
    }
  ]
}
```

## 执行步骤

1. 识别输入材料类型：规则、风格、参考案例、rubric 或用户偏好。
2. 按目录写入：
   - 规则与禁区写入 `writing-policy/rules/`
   - 表达和风格偏好写入 `writing-policy/style_guides/`
   - 中文论文参考案例写入 `writing-policy/reference_cases/`
   - 章节结构检查标准写入 `writing-policy/rubrics/`
3. 为每个条目分配稳定 ID，使用小写字母、数字和下划线，例如 `rule_001`、`case_001`。
4. 在每个文件中标明来源、适用范围、不可作为研究证据的声明。
5. 生成或更新 `writing-policy/source_index.json`，确保每个 policy 文件都有索引记录。
6. 确认没有任何 writing-policy 内容被写入 `research-wiki/`。
7. 运行 Part 2 gate 校验：

```bash
python3 cli.py part2-health
python3 cli.py validate part2
```

`part2-health` 是面向用户的检查入口；`validate part2` 是底层 gate 校验入口。两者都不能替代人工 HITL 节点，也不能自动推进 Part 3。

## 禁止事项

- 不得把导师 PPT、学校规范、参考案例或 rubric 当作 research evidence。
- 不得把 writing-policy 材料写入 `research-wiki/pages/`。
- 不得用 writing-policy 补 research-wiki 的来源缺口。
- 不得修改 `raw-library/` 原始资料。
- 不得修改 `docs/01_build_target.md` 或 `docs/02_architecture.md`。
- 不得推进 Part 3；Part 2 gate 是否通过必须由项目 gate 校验决定。

## 结果摘要格式

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Part 2 Writing Policy 构建完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Source index: writing-policy/source_index.json
  Rules: <数量>
  Style guides: <数量>
  Reference cases: <数量>
  Rubrics: <数量>
  Research-wiki 分离: <通过 / 有风险>
  Part 2 gate validate: <通过 / 未通过>

下一步：Part 2 gate 通过后，才能进入 Part 3 candidate argument tree generation。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
