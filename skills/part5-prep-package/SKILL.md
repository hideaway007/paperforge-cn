---
name: part5-prep-package
description: 学术研究 workflow Part 5 写作准备包：Part 4 completion gate 通过后，自动生成章节 brief、案例分析模板、claim-evidence matrix、citation map、figure plan 与 open questions。当用户说「进入 Part 5 准备」「生成写作输入包」「part5-prep-package」时触发。Part 5 不再需要 writing_phase_authorized 或 part5_prep_confirmed。
---

# Part 5 Prep Package

你的任务是把 Part 4 canonical outline 转成 Part 5 写作输入包。这个 skill 只处理“开始写之前需要哪些约束和证据映射”，不负责正文起草。

## 前置检查

1. `outputs/part4/paper_outline.json`、`outline_rationale.json`、`reference_alignment_report.json` 已存在并通过 Part 4 completion gate。
2. `runtime/state.json` 中 Part 1-4 已完成；不再要求 `outline_confirmed`。
3. 不再要求 `writing_phase_authorized` 或 `part5_prep_confirmed`。
4. `research-wiki/` 是研究证据层；`writing-policy/` 只提供写作规则、结构和表达约束。
5. 不得虚构引文、图纸、案例事实或任何无法回溯到 `raw-library/metadata.json` / `research-wiki/index.json` 的研究性内容。

## 执行

生成写作输入包：

```bash
python3 cli.py part5-prep
```

生成后向用户展示这些产物的状态：

- `outputs/part5/chapter_briefs/`
- `outputs/part5/case_analysis_templates/`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `outputs/part5/figure_plan.json`
- `outputs/part5/open_questions.json`

生成后可自动进入 `$part5-draft-manuscript`。

## 停止点

完成 `part5-prep` 后不需要等待人工确认。若 prep artifacts 齐备且无 blocking error，可自动运行 `part5-draft`。

## 禁止事项

- 不得要求或写入 `writing_phase_authorized` 或 `part5_prep_confirmed`。
- 不得把 `writing-policy/` 当作 research evidence。
- 不得补造 source_id、citation、图纸信息或案例事实。
- 不得生成 `outputs/part5/manuscript_v1.md`。
- 不得自动进入 Part 6。
