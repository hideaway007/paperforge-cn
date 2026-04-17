---
name: caption-polish
description: 学术写作 workflow 的图表标题与说明文字润色 skill：对中文论文中的图题、表题、caption、figure_plan proposal 做学术化、格式一致、来源标注与 claim 强度检查。当用户要求「润色图题」「润色表题」「生成 caption」「图表标题规范」「caption-polish」时触发。该 skill 不新增图表、不新增数据、不修改 figure_plan canonical artifact。
---

# Caption Polish

你的任务是把已有图题、表题和说明文字收束为清晰、克制、可追溯的中文学术表达。caption 只能解释图表呈现的内容和必要来源，不得借 caption 新增研究结论。

## 输出所有权

默认在对话中返回 caption proposal。需要落盘时，只能写：

- `outputs/part5/caption_polish_report.md`
- `outputs/part5/caption_polish_proposal.json`
- `outputs/part6/caption_polish_report.md`
- `outputs/part6/caption_polish_proposal.json`
- `process-memory/{YYYYMMDD}_caption_polish.json`

不得直接写或覆盖：

- `outputs/part5/figure_plan.json`
- `outputs/part5/manuscript_v1.md`
- `outputs/part5/manuscript_v2.md`
- `outputs/part6/final_manuscript.md`
- `outputs/part6/submission_package_manifest.json`
- `research-wiki/`
- `raw-library/`

## 输入

可读取：

- 用户提供的图题、表题、图注或表注。
- `outputs/part5/figure_plan.json`，只读。
- `outputs/part5/manuscript_v1.md`、`outputs/part5/manuscript_v2.md` 或 `outputs/part6/final_manuscript.md`，用于上下文对齐。
- `outputs/part5/citation_map.json` 与 `raw-library/metadata.json`，只用于核对来源标注。
- `writing-policy/rules/figure_table_caption.md`。

没有图表对象或 caption 草稿时停止；不得凭空创建新图表需求。

## 处理规则

### 通用规则

- 保留图号、表号、source_id、单位、样本范围、年份和来源说明。
- 标题应直接描述对象、范围和关系，避免“本文展示了”“如下图所示”等冗余。
- 不在 caption 中引入正文没有出现的新 claim。
- 不把视觉判断写成研究结论，例如“完美证明”“显著优于”。
- 来源不清时保留 `source_missing` 或 `citation_needed`，不得补造来源。

### 图题

- 优先说明图的对象、空间/流程/关系、时间或案例范围。
- 概念图可说明构成关系，但不得暗示已被实证验证。
- 案例图必须保留案例名、图纸类型和来源标注。
- 框架图标题应克制，不使用宣传式表达。

### 表题

- 优先说明比较对象、维度、样本范围和数据来源。
- 指标方向、单位和口径必须清楚。
- 如果表格用于归纳文献或案例，caption 不能替代正文论证。
- 不添加正文或 metadata 未提供的数据解释。

## 输出格式

对单个 caption，输出：

- `Original`
- `Proposed`
- `Change Log`
- `Source / Claim Risk Notes`

JSON proposal 至少包含：

- `event_type`: `caption_polish`
- `input_path`
- `items`
- `numbering_preserved`: `true`
- `sources_preserved`
- `claims_added`: `false`
- `figures_added`: `false`
- `does_not_modify_figure_plan`: `true`

## 与其他 skill 的关系

- `part5-prep-package` 拥有 `figure_plan.json` 的生成逻辑；本 skill 只能做 caption proposal。
- `part6-audit-citation-consistency` 负责最终来源一致性审计；本 skill 只做 caption 层面的来源风险提示。
- `academic-register-polish` 可处理正文语体；本 skill 只处理图表标题和说明文字。

## 禁止事项

- 不得新增图表、指标、数据、claim、案例事实、source_id 或 citation。
- 不得修改 canonical `figure_plan.json`。
- 不得把图表说明写成新的论证段落。
- 不得删除来源不明或证据不足提示。
- 不得将英文顶会 caption 风格无条件套入中文建筑/设计类论文。
