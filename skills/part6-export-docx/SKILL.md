---
name: part6-export-docx
description: 学术研究 workflow Part 6 最终 DOCX 格式导出：当用户要求生成 Word/docx、按华南理工课程论文模板排版、导出桌面论文文件、或运行 part6-export-docx 时触发。只调用确定性脚本，不让 LLM 直接生成或改写 docx。
---

# Part 6 Export DOCX

本 skill 只负责触发 Part 6 docx 格式导出。docx 由确定性脚本生成，不由 LLM agent 直接生成。

## 输入边界

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `writing-policy/rules/scut_course_paper_format.md`

## 输出

- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `~/Desktop/{论文题目}.docx`

桌面文件名必须来自论文题目。不得改用 `final_manuscript.docx`、`part6_final_manuscript.docx` 等通用名。

## 正常执行

优先使用 CLI：

```bash
python3 cli.py part6-export-docx
```

也可作为 Part 6 finalizer step 执行：

```bash
python3 cli.py part6-finalize --step export-docx
```

## 禁止事项

- 不得让 LLM 直接生成 `.docx`。
- 不得在导出阶段改写论文正文。
- 不得新增 claim、source、case fact、citation 或 research conclusion。
- 不得复制封面、教师评语、成绩评定或模板蓝色提示文字。
- 不得确认 `part6_final_decision_confirmed`。
- 不得执行 submission、上传、邮件发送或 Part 7 推进。

## 失败处理

- 缺少 Part 6 finalization authorization：提示先运行 `part6-authorize`。
- 缺少论文题目：停止并要求补齐 intake 或 final manuscript 标题。
- 桌面副本无法写入：视为 blocked，不静默降级。
- `docx_format_report.json.status=blocked`：停止，不确认 final decision。
