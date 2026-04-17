---
name: part5-mvp-drafting
description: 学术研究 workflow Part 5 MVP 导航入口：把用户请求分流到少量主 skill：part5-prep-package、part5-draft-manuscript、part5-review-manuscript、part5-revise-manuscript。当用户笼统说「开始 Part 5」「Part 5 MVP」「part5-mvp-drafting」且未指定具体阶段时触发。Part 5 不再设置人工 gate，正常流程自动 prep → draft → review → revise。
---

# Part 5 MVP Skill Surface

Part 5 对用户暴露为四个目标级 skill，不为每个小产物单独建 skill。Part 5 不再要求 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted`。

## 选择入口

- 准备写作输入包：使用 `$part5-prep-package`
- 生成 `manuscript_v1.md`：使用 `$part5-draft-manuscript`
- 审稿、review fragments 归并与用户汇报生成：使用 `$part5-review-manuscript`
- 生成 `manuscript_v2.md`、revision log、readiness decision 与验证：使用 `$part5-revise-manuscript`

## 分段流程

### 1. 自动生成 Part 5 写作准备包

Part 4 completion gate 通过后直接运行：

```bash
python3 cli.py part5-prep
```

### 2. 自动生成 `manuscript_v1.md`

```bash
python3 cli.py part5-draft
```

`manuscript_v1.md` 是中间稿，不是 canonical artifact。

### 3. 自动 review 与用户汇报

Review agents 生成 review fragments，integrator 汇总 canonical review artifacts，并生成面向用户的 `review_report.md`。

```bash
python3 cli.py part5-review
```

`outputs/part5/review_report.md` 必须生成，并作为面向用户的 review 汇报。

### 4. 自动修订、生成最终稿与验证

```bash
python3 cli.py part5-revise
```

生成 `manuscript_v2.md`、revision log 与 readiness decision 后，必须校验这些文件存在。然后运行：

```bash
python3 cli.py validate part5
```

验证只确认 Part 5 artifact 状态，不授权进入 Part 6。

## 全局规则

- 不得要求或写入 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted`。
- Review fragments 只能由 review agents 写；canonical `outputs/part5/review_matrix.json` 只能由 integrator 写。
- `review_report.md` 必须由 review artifacts 派生，并保存在 `outputs/part5/`。
- `manuscript_v2.md` 必须保存在 `outputs/part5/`。
- 不得把 writing-policy、reference cases 或 rubrics 当作 research evidence。
- 不得虚构来源、图纸、案例事实或引文。
- 不得把 `manuscript_v1.md` 当作 canonical artifact。
- 不得自动进入 Part 6；`part6_readiness_decision.json` 只表达 readiness verdict。
