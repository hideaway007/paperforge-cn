---
name: part6-finalize-manuscript
description: 学术研究 workflow Part 6 定稿收束：只从 outputs/part5/manuscript_v2.md 保守生成 outputs/part6/final_manuscript.md、final_abstract.md、final_keywords.json。当用户说「Part 6 定稿」「生成 final manuscript」「finalize manuscript」「part6-finalize-manuscript」时触发。不得新增 claim、source 或 case fact。
---

# Part 6 Finalize Manuscript

你的任务是把 Part 5 最终稿保守收束为 Part 6 final manuscript 三件套。只做表达、结构与摘要关键词收束，不扩展研究内容。

## 输入

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/review_matrix.json`
- `outputs/part5/part6_readiness_decision.json`
- 已 canonical 的 research wiki 与 raw metadata，只能用于核对，不得用于新增内容。

## 输出所有权

本 skill 只能写：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`

## 收束规则

1. 以 `manuscript_v2.md` 为唯一正文基线。
2. 保留已确认结构、论点、案例与来源边界。
3. 允许修正明显的语言、标题层级、重复表述、摘要压缩和关键词规范化。
4. 不得新增 claim、source_id、案例事实、图纸、引文或研究结论。
5. 不得删除高风险 claim 的风险标记，除非已有 Part 5 revision 依据支持。
6. 无法保守处理的问题，保留在正文或交给 audit/report，不得私自补造。
7. 正文不要写成审计报告：不要反复暴露“已核验资料”“可回溯”“证据链”等系统语言。
8. 不要单独生成“证据边界与研究不足”章节，除非 outline 明确要求；常规不足放入结论或讨论末段。

## 禁止事项

- 不得写 `claim_risk_report.json`。
- 不得写 `citation_consistency_report.json`。
- 不得写 `submission_package_manifest.json`。
- 不得写 `final_readiness_decision.json`。
- 不得修改 Part 5 artifacts、manifest、runtime state 或 research wiki。
