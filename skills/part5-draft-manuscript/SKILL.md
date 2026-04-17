---
name: part5-draft-manuscript
description: 学术研究 workflow Part 5 正文初稿：基于自动生成的 prep package 生成 outputs/part5/manuscript_v1.md。当用户说「生成 manuscript_v1」「起草 Part 5 正文」「part5-draft-manuscript」时触发。Part 5 不再需要 prep 人工确认；draft 完成后可自动进入 review。
---

# Part 5 Draft Manuscript

你的任务是生成保守但可读的 `manuscript_v1.md`。v1 是中间稿，不是 canonical artifact；它必须忠实使用 prep package 的论证和证据约束，但正文不能写成证据审计报告。

## 前置检查

1. Part 4 completion gate 已通过。
2. 不再要求 `writing_phase_authorized` 或 `part5_prep_confirmed`。
3. Prep artifacts 已存在：
   - `outputs/part5/claim_evidence_matrix.json`
   - `outputs/part5/citation_map.json`
   - `outputs/part5/figure_plan.json`
   - `outputs/part5/open_questions.json`
4. `writing-policy/` 只能约束表达、结构、风格和风险表述；不得作为研究证据。
5. 任何论点、引文、图纸、案例事实都必须能回溯到 `research-wiki/` 或 `raw-library/metadata.json`。

## 执行

```bash
python3 cli.py part5-draft
```

生成后报告：

- `outputs/part5/manuscript_v1.md`
- 后续自动 `part5-review`
- `manuscript_v1.md` 不是 canonical artifact

## 停止点

完成 `part5-draft` 后，如 `manuscript_v1.md` 存在且无 blocking error，可自动运行 `part5-review`。

## 正文风格

- 优先使用 `paper_outline.json` 组织章节，用 `argument_tree.json` 控制论证推进。
- 若存在 `writing-policy/style_guides/author_style_profile.md`，按其问题进入方式、段落职责和判断节奏写作。
- 使用 `$part5-formal-manuscript-authoring` 将 `manuscript_v1.md` 写成接近正式中文论文的结构：题名独立置顶，摘要/关键词规范，章节编号统一，核心章节具备二级标题与本章小结，结尾保留结论与参考文献部件。
- 使用 `paper-manuscript-style-profile` 和 `academic-register-polish` 降低 workflow 腔、AI 腔和口语化表达。
- 不要在正文中反复写“证据链”“已核验资料”“可回溯来源”等系统语言。
- 不要单独生成“证据边界与研究不足”章节，除非 outline 明确要求。

## 禁止事项

- 不得要求或写入 `part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted`。
- 不得把 `manuscript_v1.md` 当作 Part 5 canonical artifact。
- 不得把 writing-policy、reference cases、rubrics 当作 research evidence。
- 不得虚构引文、图纸、案例事实或 source_id。
- 不得自动进入 Part 6。
