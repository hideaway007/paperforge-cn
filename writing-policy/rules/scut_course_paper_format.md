---
rule_id: scut_course_paper_format
rule_type: format
title: 华南理工大学研究生课程论文正文格式规范
source: user_provided_scut_course_paper_template_docx_2026_04_17
priority: high
applies_to: [part6_docx_export, final_manuscript_docx]
may_be_used_as_research_evidence: false
cover_scope: excluded
---

# 华南理工大学研究生课程论文正文格式规范

## 规则定位

本规则从用户提供的《华南理工大学研究生课程论文（模板）.docx》中抽取，只约束 Part 6 最终 `.docx` 导出的版式。它不是研究证据，不能用于新增论文事实、案例结论、引用来源或论证内容。

封面、学号 / 学院 / 任课教师表格、教师评语、成绩评定、模板说明与蓝色提示文字不进入本项目的 docx 导出流程。

## 页面设置

- 纸张：A4，21.0 cm x 29.7 cm。
- 页边距：上 2.5 cm，下 2.5 cm，左 3.0 cm，右 2.5 cm。
- 正文区页眉距边界 1.5 cm，页脚距边界 1.5 cm。
- 打印要求为双面打印；运行时只负责生成 A4 docx，不执行打印。
- 正文页应保留页码；封面页码不在本流程设计范围内。

## 中文正文格式

- 全文中文字体使用宋体简体。
- 论文题目：宋体，小二号，18 pt，加粗，居中。
- 作者姓名：宋体，四号，14 pt，加粗，居中。
- 摘要标签：宋体，小四号，12 pt，加粗。
- 摘要正文：宋体，小四号，12 pt。
- 关键词标签：宋体，小四号，12 pt，加粗。
- 关键词正文：宋体，小四号，12 pt；关键词之间使用分号分隔。
- 正文标题行：宋体，小四号，12 pt，加粗。
- 正文内容：宋体，小四号，12 pt。
- 行距：2 倍行距。

## 参考文献格式

- “参考文献”标题：宋体，小四号，12 pt，加粗。
- 参考文献条目：宋体，五号，10.5 pt。
- 参考文献著录规则继续服从 `writing-policy/rules/citation_format.md`。
- `.docx` 导出器只能格式化已存在的参考文献，不得新增 citation map 之外的来源。

## 博士课程论文英文部分

模板要求博士课程论文包含英文摘要。若运行时识别为博士课程论文，导出器应检查以下字段：

- 英文题目：Times New Roman，18 pt，加粗，居中。
- 作者姓名拼音：Times New Roman，14 pt，加粗，居中。
- Abstract 标签：Times New Roman，12 pt，加粗。
- Abstract 正文：Times New Roman，12 pt。
- Key words 标签：Times New Roman，12 pt，加粗。
- Key words 正文：Times New Roman，12 pt。

若无法从项目 intake 或 Part 6 metadata 中识别学位类别，导出器不得静默假定博士要求；应在 `outputs/part6/docx_format_report.json` 中登记 `degree_level_unknown`。

## 导出边界

- 只从 `outputs/part6/final_manuscript.md`、`outputs/part6/final_abstract.md`、`outputs/part6/final_keywords.json` 与已通过审计的引用材料生成 docx。
- 不得修改 Part 5 / Part 6 markdown 正文内容来适配格式。
- 不得把格式模板残留文字写入最终稿。
- 不得复制封面表格、模板说明或蓝色提示内容。
- 不得把格式规则登记到 `research-wiki/` 或 `raw-library/`。

## 校验要求

`outputs/part6/docx_format_report.json` 至少应记录：

- A4 与页边距检查结果。
- 标题、作者、摘要、关键词、正文标题、正文、参考文献的字体 / 字号 / 加粗 / 行距检查结果。
- 是否已排除封面与模板说明。
- 是否存在占位符、蓝色提示文字或模板残留。
- docx 文本内容与 `final_manuscript.md` 的内容一致性摘要。
- 未满足学校格式要求的 warnings / errors。
