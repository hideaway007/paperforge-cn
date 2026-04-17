# Part 6 Architecture

> Current status: Part 6 is in the active `STAGE_ORDER` as a human-gated finalization surface. The current runnable contract is the MVP defined in `docs/part6_mvp_architecture.md`, `manifests/pipeline-stages.json`, `runtime/pipeline.py`, and `runtime/agents/part6_mvp_finalizer.py`. `outputs/part5/part6_readiness_decision.json` is a readiness signal, not authorization.

## 1. Stage Purpose
Part 6 的职责是把 Part 5 的 canonical draft 推进为：

- 最终可交付稿 `final_manuscript.*`
- claim risk 与 citation consistency 均受控的终版
- 可导出的 submission package

因此，Part 6 的推荐定义为：

**Finalize + Export**

它不是简单润色，而是：

1. 最终一致性清理
2. 高风险 claim 收口
3. 引用一致性与格式合规检查
4. 图文与附件组织
5. 最终交付决策

---

## 2. Entry Preconditions
进入 Part 6 前，必须满足：

### 2.1 Part 5 Canonical Draft Ready
至少具备：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`

### 2.2 Readiness Decision Allows Finalization
`part6_readiness_decision.json` 只能表达 readiness。若用户授权进入 Part 6，它必须给出允许进入 Part 6 的结论。允许状态为：

- `ready_for_part6`
- `ready_for_part6_with_research_debt`

若为 `blocked_by_evidence_debt`，则不得推进。无论 verdict 如何，系统都不得自动确认 Part 6 human gates。

### 2.3 Policy Inputs Ready
至少具备：

- `writing-policy/source_index.json`
- 目标学校 / 导师 / 期刊格式要求
- 中文学术写作规范
- 图表、注释、参考文献格式规则

---

## 3. Stage Scope
Part 6 的范围分为五个子阶段。

### 3.1 Final Polishing
对 `manuscript_v2.md` 做最终层面的：

- 语言收束
- 章节衔接优化
- 术语统一
- 标题层级统一
- 摘要 / 关键词 / 结论一致性检查

### 3.2 Claim Risk Final Audit
对全部关键 claims 做最终核查：

- 是否都有来源或明确标记为综合解释
- 是否存在证据不足却语气过强的段落
- 是否仍包含不应被写成硬事实的案例表述

### 3.3 Citation Consistency Final Audit
对引用层做最终核查：

- 正文 claim 与参考文献是否对应
- 引文格式是否统一
- 是否存在 accepted sources 之外的漂移引用
- 图表 / 图片 /案例材料来源是否可追踪

### 3.4 Export Preparation
整理最终交付所需文件：

- 最终稿
- 摘要
- 关键词
- 图表清单
- 参考文献清单
- submission checklist
- submission manifest

### 3.5 Final Decision
给出最终状态：

- 可正式提交
- 仅适合内部评阅
- 仍需补资料后再提交

---

## 4. Core Inputs

### 4.1 Canonical Draft Inputs
- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/revision_log.json`

### 4.2 Evidence and Citation Inputs
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `raw-library/metadata.json`
- `outputs/part1/accepted_sources.json`
- `outputs/part1/authenticity_report.json`

### 4.3 Policy Inputs
- `writing-policy/source_index.json`
- 中文学术规范
- 学校 / 导师 / 期刊格式要求

### 4.4 Figure / Asset Inputs
- `outputs/part5/figure_plan.json`
- `raw-library/images/`
- `raw-library/case-notes/`
- 图纸、照片、截图与授权说明（如有）

### 4.5 Debt Register Inputs
- research debt register
- case verification notes
- `mvp_acceptance_report.md`
- unresolved blocker notes

---

## 5. Stage Outputs

### 5.1 Finalization Outputs
建议至少生成：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/final_section_outline.json`

### 5.2 Audit Outputs
建议至少生成：

- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/style_consistency_report.json`
- `outputs/part6/figure_source_report.json`

### 5.3 Export Outputs
建议至少生成：

- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/references_final.bib` 或等价导出
- `outputs/part6/final_readiness_decision.json`

### 5.4 Optional Export Variants
如项目需要，可选生成：

- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `outputs/part6/final_manuscript.pdf`
- 期刊或学校要求的特定模板版本

特定学校或期刊模板导出属于后续扩展，必须显式配置格式策略，并且不得改变 Part 6 已审计正文、claim、citation 或 source set。

---

## 6. Canonical Artifacts
Part 6 的 canonical artifacts 建议定义为：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

说明：

- 最终稿不仅是正文文件本身，还必须附带风险与一致性审计结果
- 若没有审计报告，`final_manuscript.md` 不应视为真正 canonical final

---

## 7. Finalization Strategy

### 7.1 Do Not Over-Polish Unsupported Claims
Part 6 不允许把证据不足的段落“润色得更像真理”。

如果某个判断仍有证据不足，应采取以下策略之一：

- 降低断言强度
- 改为概念性解释
- 加入限定条件
- 明确为进一步研究或待核验项

### 7.2 Distinguish Submission Classes
Part 6 应区分三种最终状态：

- **Formal submission ready**：可正式提交
- **Internal review ready**：可内部评阅，但不建议正式提交
- **Blocked by evidence debt**：证据债务仍阻断提交

### 7.3 Preserve Transparency
所有 research debt 若未完全消解，必须继续保留：

- 在 `claim_risk_report.json` 中留痕
- 在 `final_readiness_decision.json` 中显式说明
- 不得因追求“最终稿好看”而删除风险标记

---

## 8. Claim Risk Architecture
Claim risk final audit 建议至少区分以下等级：

- `low_risk`
- `medium_risk`
- `high_risk`
- `blocked`

并按以下类型分类：

- factual risk
- interpretation risk
- citation risk
- source sufficiency risk
- case verification risk

对于 high_risk 或 blocked 项，必须明确处理动作：

- revise wording
- add source
- downgrade claim
- remove paragraph
- defer to future research

---

## 9. Citation Consistency Architecture
最终引用一致性检查至少覆盖：

- 参考文献条目是否存在
- 条目与正文 claim 是否对应
- 中英文参考文献格式是否统一
- 图像 / 图纸 / 项目资料是否带来源
- 是否存在 accepted sources 之外的无来源漂移引用
- 是否存在同一来源在不同章节被错误复述

---

## 10. Human-in-the-Loop
当前 Part 6 必须保留以下人工节点：

- `part6_finalization_authorized`：用户授权从 Part 5 handoff 进入 Part 6 finalization，且记录 Part 5 handoff fingerprints。
- `part6_final_decision_confirmed`：用户确认 final readiness decision 与 submission package manifest。

业务上仍需用户判断：

- 是否接受最终稿论证强度
- 是否接受未完全消解的 research debt
- 是否接受某些案例仅作为概念参照保留
- 是否进入正式导出
- 是否标记为可正式提交

`formal_submission_ready` 不是自动提交授权。系统不得执行 submission action。

---

## 11. Stage Gates

### 11.1 Final Draft Gate
通过条件：

- `final_manuscript.md` 已生成
- 摘要、关键词、正文、结论结构完整
- 标题层级与术语统一
- 语言与格式完成最终整理

### 11.2 Claim Risk Gate
通过条件：

- `claim_risk_report.json` 已生成
- 不存在未登记的 blocked claims
- 所有 high_risk claims 已处理、降级或显式保留原因

### 11.3 Citation Consistency Gate
通过条件：

- `citation_consistency_report.json` 已生成
- 不存在虚构引用
- 不存在关键 claim 的无来源状态
- 图文来源可追踪

### 11.4 Export Gate
通过条件：

- `submission_package_manifest.json` 已生成
- `submission_checklist.md` 已生成
- 所需导出文件齐备
- 最终 readiness decision 已给出

### 11.5 Part 6 Completion Gate
通过条件：

- `final_manuscript.md` 已锁定
- `claim_risk_report.json` 齐备
- `citation_consistency_report.json` 齐备
- `submission_package_manifest.json` 齐备
- `final_readiness_decision.json` 已生成
- 人工已确认最终状态

---

## 12. Final Readiness Decision
建议给出以下三类 verdict：

- `formal_submission_ready`
- `internal_review_only`
- `blocked_by_evidence_debt`

推荐规则：

- 若中文核心文献债务已显著缓解、关键案例成立、claim risk 可控，可标为 `formal_submission_ready`
- 若主文稿已完整，但仍有部分资料债务未解决，可标为 `internal_review_only`
- 若关键证据不足、案例事实不稳或引用链不完整，应标为 `blocked_by_evidence_debt`

---

## 13. State and Diagnostics
运行时至少应记录：

- finalization 当前子阶段
- 最终稿版本
- 当前 readiness verdict
- 未解决 claim risks
- export 完成情况
- human approval snapshot

诊断工具至少应支持：

- final draft completeness check
- claim risk aggregation
- citation consistency validation
- export package completeness check
- readiness verdict validation

---

## 14. ECC Reference Boundary
Part 6 继续参考 ECC 的工程思想：

- staged gates
- audit / doctor
- canonical artifacts
- diagnostics
- process-memory

但 Part 6 的核心业务不是代码交付，而是：

- 最终学术文稿定稿
- 风险与引用一致性受控
- 面向正式提交的导出与留痕

---

## 15. End-State Deliverable Set
Part 6 完成后，最小交付包建议包括：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

如需对外提交，再在此基础上导出 `.docx` / `.pdf` 版本。

## 16. DOCX / PDF Export Extension

DOCX / PDF export 是 Part 6 的格式导出子流程，而不是新的写作或研究阶段。

设计边界：

- 输入只来自 Part 6 final manuscript 与显式配置的 writing policy 格式规则。
- 输出应留在 `outputs/part6/` 或用户显式指定的导出目录。
- 导出不得新增 claim、source、case fact、citation 或 research conclusion。
- 若启用该导出，用户应在导出文件与格式报告生成后再确认 `part6_final_decision_confirmed`。
