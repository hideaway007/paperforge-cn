---
rule_id: figure_table_caption
rule_type: expression
title: 图表标题与说明文字规范
source: distilled_external_writing_practice
priority: medium
applies_to: [figure_plan, manuscript_draft, final_manuscript]
may_be_used_as_research_evidence: false
---

# 图表标题与说明文字规范

## 规则定位

本规则只约束图题、表题、图注和表注的表达方式。它不能作为新增图表、数据、案例事实或研究结论的依据。

## 通用要求

- 图号、表号、单位、样本范围、时间范围和来源说明必须保留。
- caption 应直接说明图表对象和比较维度，避免“如下图所示”“本文展示了”等冗余开头。
- caption 不承担证明任务；证明关系应留在正文论证中。
- 来源不清的图表必须保留来源风险提示，不能用流畅表述遮蔽。
- 中英文术语、专名、案例名必须与正文和 `figure_plan.json` 一致。

## 图题要求

- 空间图、流程图、概念图应说明对象、关系和适用范围。
- 案例图应保留案例名称、图纸类型、年代或来源信息。
- 框架图不使用宣传性词汇，如“创新性框架”“完美模型”等。

## 表题要求

- 表题应说明比较对象、指标维度、样本范围和数据来源。
- 有单位或指标方向时，应在表头或表注中明确。
- 文献归纳表不得把归纳结果写成未经论证的结论。

## 风险标记

以下情况必须提示，而不是私自修复：

- `source_missing`
- `citation_needed`
- 图表内容与正文 claim 不一致
- 表格数据口径不清
- 案例图来源无法追溯
