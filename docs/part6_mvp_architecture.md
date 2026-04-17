# Part 6 MVP Architecture

> Current status: Part 6 MVP is implemented as an explicit finalization surface. It provides 7 MVP skills, the `part6-finalize` CLI command, one deterministic finalizer script, and one dedicated writer script. It must not auto-confirm Part 6 human gates, must not perform submission, and must not advance Part 7.

## 1. MVP Decision

Part 6 MVP 的目标是把 Part 5 已完成 gate 的 `manuscript_v2.md` handoff 稿收口为一个可审计、可交付、但不自动提交的最终包。

结论：

**Part 6 MVP = Finalize + Final Audit + Submission Manifest + Human Final Decision**

它不是：

- 自动投稿系统
- `.pdf` 格式导出系统
- 自动投稿所需的在线系统上传版本
- 新一轮研究补资料系统
- 把 evidence debt 润色掉的最终美化器

Part 6 MVP 只解决一个核心问题：

> 当前 Part 5 canonical draft 是否已经可以作为正式提交、内部评阅，还是仍被 evidence debt 阻断。

---

## 2. MVP Scope

### 2.1 In Scope

当前 Part 6 MVP 应完成：

1. 校验 Part 6 entry preconditions。
2. 基于 `outputs/part5/manuscript_v2.md` 生成 `outputs/part6/final_manuscript.md`。
3. 继承 Part 5 residual risks，生成最终 `claim_risk_report.json`。
4. 对 `citation_map.json`、`raw-library/metadata.json`、`research-wiki/index.json` 做最终引用一致性检查。
5. 生成 submission package manifest。
6. 生成 final readiness decision。
7. 保留 human final decision，不自动提交。

### 2.2 Out of Scope

MVP 不做：

- 自动生成正式 `.pdf`
- 学校 / 期刊模板精排通用系统
- 自动投稿、自动邮件、自动上传
- 完整图源授权包自动化
- 自动补文献、补案例、补图纸
- 多轮人工改稿工作台
- Part 7 或 submission automation

这些属于 Part 6 后续增强，不进入最小闭环。

---

## 3. Entry Preconditions

进入 Part 6 MVP 前，必须同时满足以下条件。

### 3.1 Stage Preconditions

- Part 1 gate 已通过
- Part 2 gate 已通过
- Part 3 gate 已通过
- Part 4 gate 已通过
- Part 5 gate 已通过

Part 6 不得只看文件存在就推进。它必须从 pipeline state 继承 Part 1-5 的 gate 状态。`status` / `get_next_action()` 可在条件满足时推荐 `part6-authorize`、`part6-finalize` 或 `part6-confirm-final`，但不得替用户确认 gate。

### 3.2 Part 5 Handoff Preconditions

必须存在并通过现有 Part 5 gate 校验：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `outputs/part5/figure_plan.json`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`

Part 6 不再依赖 Part 5 已废弃的 `manuscript_v2_accepted` human gate。Part 6 entry 的硬边界是：

- `part5.status == completed`
- `part5.gate_passed == true`
- Part 5 handoff artifacts 当前存在且仍通过 Part 5 gate 校验
- `part6_readiness_decision.verdict != blocked_by_evidence_debt`
- 用户通过新的 `part6_finalization_authorized` gate 授权进入 Part 6

`part6_finalization_authorized` 应记录当前 Part 5 handoff artifacts 的 fingerprint。若授权后 Part 5 handoff artifacts 变化，Part 6 必须阻断，并要求用户重新授权 Part 6 finalization。

### 3.3 Readiness Verdict Preconditions

`outputs/part5/part6_readiness_decision.json` 的 verdict 决定是否允许进入 Part 6：

| Part 5 verdict | Part 6 action |
|---|---|
| `ready_for_part6` | 可请求进入 Part 6，但不得自动提交 |
| `ready_for_part6_with_research_debt` | 可请求进入 Part 6，但 residual risks 必须延续到 Part 6 reports；不得自动提交 |
| `blocked_by_evidence_debt` | 不得进入 Part 6，只能返回补 evidence debt |

---

## 4. Human Gates

Part 6 MVP 只新增两个 human gates。

| Gate ID | 作用 | 位置 |
|---|---|---|
| `part6_finalization_authorized` | 用户明确授权从 Part 5 completed handoff draft 进入最终定稿阶段 | finalization / package generation 前 |
| `part6_final_decision_confirmed` | 用户确认最终状态：正式提交、内部评阅或 blocked | Part 6 completion 前 |

Part 5 的 `manuscript_v2_accepted` 是 deprecated no-op，不作为 Part 6 entry precondition。Part 6 只依赖 Part 5 completion gate 和新的 `part6_finalization_authorized`。

规则：

- agent 不得自动确认任何 Part 6 human gate。
- 任何后续 finalization CLI 入口不得自动确认 final decision。
- final readiness verdict 不是 submission authorization。
- `formal_submission_ready` 也不等于系统可以自动提交。

---

## 5. Canonical Artifacts

Part 6 MVP 只把以下 5 个文件定义为 completion gate 的 canonical artifacts：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

说明：

- `final_manuscript.md` 单独存在不构成 Part 6 完成。
- 没有 claim risk 与 citation consistency audit 的 final manuscript 只能算 draft export。
- `submission_package_manifest.json` 是最终交付包的合同，不只是文件列表。

### 5.1 Non-Canonical Side Artifacts

以下文件可作为 side artifacts 生成，但不进入 MVP completion gate：

- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/style_consistency_report.json`
- `outputs/part6/figure_source_report.json`
- `outputs/part6/references_final.bib`
- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`

如果后续学校或期刊要求明确，再把其中部分提升为 canonical。

但 MVP 的 `submission_package_manifest.json.required_files` 必须至少包含：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/final_readiness_decision.json`

也就是说，abstract、keywords、checklist 不作为独立 stage canonical artifact，但必须作为 submission package 的 required files 被检查。

桌面交付物只面向用户阅读，不作为 canonical package：

- 默认只写 `outputs/part6/`；如显式设置 `PART6_DESKTOP_DIR`，可额外导出 `part6_final_manuscript.md` 到该目录。外部导出不是 canonical package。
- 不向桌面导出 `final_abstract.md`、`final_keywords.json` 或 `writer_body.md` 副本。
- 内部 `outputs/part6/final_abstract.md` 与 `outputs/part6/final_keywords.json` 仍保留，用于 Part 6 package 校验。

---

## 6. Runtime Finalizer Architecture

### 6.1 Runtime Agent Boundary

Part 6 package 生成阶段保留一个用户入口，但正文写作必须由独立 writer agent 承担：

- `runtime/agents/part6_mvp_finalizer.py`
- `runtime/agents/part6_writer.py`

`part6_writer.py` 只写 `outputs/part6/writer_body.md`。`part6_mvp_finalizer.py` 调用 writer agent 获取正文，再负责摘要、关键词、审计、manifest、readiness decision 与 human gate 边界。

支持 steps：

| Step | 职责 | 输出 |
|---|---|---|
| `precheck` | 校验 Part 1-5 gate、Part 5 handoff、readiness verdict、human authorization | 只输出诊断，不写 canonical |
| `finalize` | 调用 `part6_writer.py` 生成正文，再装订 `final_manuscript.md`，只做保守收束 | `writer_body.md`, `final_manuscript.md` |
| `audit-claim` | 生成最终 claim risk report | `claim_risk_report.json` |
| `audit-citation` | 生成最终 citation consistency report | `citation_consistency_report.json` |
| `package-draft` | 生成或刷新 draft package side artifacts 与初始 manifest 信息 | `final_abstract.md`, `final_keywords.json`, `submission_checklist.md` |
| `decide` | 基于 final manuscript 与 audit reports 生成 final readiness decision | `final_readiness_decision.json` |
| `package-final` | 读取 final readiness decision，生成最终 submission package manifest | `submission_package_manifest.json` |
| `all` | 顺序执行 `precheck -> finalize -> audit-claim -> audit-citation -> package-draft -> decide -> package-final` | 完整 Part 6 package |

顺序说明：

- `final_readiness_decision.json` 可以先写入 `manifest_ref: outputs/part6/submission_package_manifest.json`，即声明它将由最后的 `package-final` step 索引。
- `submission_package_manifest.json` 必须最后生成或刷新，并把 `final_readiness_decision.json` 纳入 `required_files` / `included_files`。
- `part6-check` 负责在所有文件生成后验证 manifest 与 readiness decision 的双向引用是否闭合。

### 6.2 Internal Helpers

MVP 阶段不把内部 helpers 暴露给用户。后续可拆：

- `part6_claim_risk_auditor.py`
- `part6_citation_consistency_auditor.py`
- `part6_manifest_builder.py`
- `part6_final_readiness_builder.py`

但 MVP 先保持一个入口，避免用户面对过多命令。

---

## 7. CLI Surface

当前命令：

| Command | 行为 |
|---|---|
| `part6-precheck` | 只读检查，不生成 Part 6 canonical artifacts |
| `part6-authorize` | 记录 `part6_finalization_authorized`，并保存当前 Part 5 handoff fingerprints |
| `part6-finalize --step precheck/finalize/audit-claim/audit-citation/package-draft/decide/package-final/all` | 调用 `runtime/agents/part6_mvp_finalizer.py` 执行指定 step；默认 `all`；可透传 `--project-root`；不自动确认任何 human gate |
| `part6-check` | 调用 `validate part6` 或等价 gate check |
| `part6-confirm-final` | 记录 `part6_final_decision_confirmed`，只记录人工最终状态，不执行提交 |

不建议 MVP 阶段暴露 `part6-audit`、`part6-package`、`part6-decide` 等细粒度命令。它们可以作为 script step 存在，但用户入口保持简单。

---

## 8. Schema Contracts

MVP 只为 4 个 canonical JSON 建 schema。

### 8.1 `schemas/part6_claim_risk_report.schema.json`

最小字段：

- `schema_version`
- `generated_at`
- `manuscript_ref`
- `source_manuscript_ref`
- `claim_evidence_matrix_ref`
- `part5_claim_risk_report_ref`
- `risk_items`
- `summary`

`risk_items[]` 最小字段：

- `risk_id`
- `claim_id`
- `risk_level`: `low_risk | medium_risk | high_risk | blocked`
- `risk_type`: `factual | interpretation | citation | source_sufficiency | case_verification`
- `finding`
- `source_ids`
- `wiki_page_ids`
- `recommended_action`: `revise_wording | add_source | downgrade_claim | remove_paragraph | defer_to_future_research | no_action_needed`
- `applied_action`: `revise_wording | downgrade_claim | remove_paragraph | defer_to_future_research | no_action_needed`
- `status`: `resolved | mitigated | downgraded | deferred | blocked`
- `residual_debt`

说明：`add_source` 在 MVP 中只能作为 `recommended_action`，不能作为 `applied_action`。若最终定稿仍需要新增来源，Part 6 应标记为 `blocked` 或 `deferred`，返回前序阶段补 evidence，而不是自动补文献。

### 8.2 `schemas/part6_citation_consistency_report.schema.json`

最小字段：

- `schema_version`
- `generated_at`
- `manuscript_ref`
- `citation_map_ref`
- `raw_metadata_ref`
- `wiki_index_ref`
- `accepted_sources_ref`
- `authenticity_report_ref`
- `status`: `pass | pass_with_warnings | blocked`
- `checked_claim_ids`
- `checked_source_ids`
- `citation_items`
- `warnings`
- `errors`

`citation_items[]` 最小字段：

- `source_id`
- `claim_ids`
- `citation_status`
- `raw_metadata_present`
- `wiki_mapped`
- `authenticity_status`
- `reference_entry_status`: `present | missing | malformed`
- `drift_detected`
- `issues`
- `action`: `keep | fix_format | remove_citation | downgrade_claim | block_submission`

### 8.3 `schemas/part6_submission_package_manifest.schema.json`

最小字段：

- `schema_version`
- `generated_at`
- `package_id`
- `status`: `complete | incomplete | blocked`
- `submission_class`: `formal_submission_ready | internal_review_only | blocked_by_evidence_debt`
- `included_files`
- `required_files`
- `missing_files`
- `audit_refs`
- `policy_refs`
- `evidence_refs`
- `human_decision_required`

### 8.4 `schemas/part6_final_readiness_decision.schema.json`

最小字段：

- `schema_version`
- `generated_at`
- `verdict`: `formal_submission_ready | internal_review_only | blocked_by_evidence_debt`
- `manifest_ref`
- `claim_risk_report_ref`
- `citation_consistency_report_ref`
- `blocking_issues`
- `residual_risks`
- `residual_research_debts`
- `required_human_decisions`
- `does_not_advance_part7`

`does_not_advance_part7` 必须为 `true`。

---

## 9. Finalization Rules

Part 6 finalization 必须遵守：

1. 不得新增 `claim_evidence_matrix.json` 之外的硬 claim。
2. 不得新增 `citation_map.json` 之外的新引用。
3. 不得把 evidence debt 从最终报告中删除。
4. 不得把 case verification risk 写成已证实事实。
5. `ready_for_part6_with_research_debt` 的 residual risks 必须进入 Part 6 `claim_risk_report.json` 和 `final_readiness_decision.json`。
6. `blocked_by_evidence_debt` 不得进入 `finalize`。
7. `final_manuscript.md` 的修改只能是语言收束、术语统一、结构清理和风险降级表达。

---

## 10. Citation and Evidence Rules

Part 6 的 evidence allowlist 只能来自：

- `raw-library/metadata.json`
- `research-wiki/index.json`
- `outputs/part1/accepted_sources.json`
- `outputs/part1/authenticity_report.json`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`

`writing-policy/source_index.json` 只能进入 `policy_refs`，不能进入：

- `source_ids`
- `evidence_refs`
- `citation_items[].source_id`
- final manuscript 的 citation source list

引用一致性必须至少检查：

1. `source_id` 存在于 `raw-library/metadata.json`
2. `source_id` 存在于 `research-wiki/index.json.pages[].source_ids`
3. `source_id` 在 `outputs/part5/citation_map.json` 中为 accepted source
4. authenticity 状态通过
5. final manuscript 没有 citation map 之外的新 source id

任一关键引用漂移必须进入 `citation_consistency_report.json`，不得静默修复。

---

## 11. Final Readiness Rules

`final_readiness_decision.json.verdict` 只能是：

- `formal_submission_ready`
- `internal_review_only`
- `blocked_by_evidence_debt`

推荐判定：

| 条件 | Verdict |
|---|---|
| 无 blocked / high unresolved risk，citation report pass，manifest complete | `formal_submission_ready` |
| final manuscript 完整，但仍有 residual research debt 或 citation warnings | `internal_review_only` |
| blocked claim、citation drift、关键 evidence debt 未处理 | `blocked_by_evidence_debt` |

`formal_submission_ready` 仍然只是 readiness，不是自动提交授权。

### 11.1 Final Manuscript Completeness

`final_manuscript.md` 不能只是 `manuscript_v2.md` 的无检查复制。MVP 至少要检查：

- 摘要存在
- 关键词存在
- 正文章节存在
- 结论存在
- 风险降级说明或 residual risk 说明存在
- 与 `final_abstract.md`、`final_keywords.json` 一致

未通过 completeness check 时，`final_readiness_decision.verdict` 不得为 `formal_submission_ready`。

---

## 12. Skill Surface

Part 6 MVP 暴露 7 个 workflow skills：

- `part6-finalize-package`
- `part6-write-manuscript-body`
- `part6-finalize-manuscript`
- `part6-audit-claim-risk`
- `part6-audit-citation-consistency`
- `part6-build-submission-package`
- `part6-decide-readiness`

manifest automation flow 使用 snake_case step 名：

- `part6_finalize`
- `part6_audit_claim`
- `part6_audit_citation`
- `part6_package_draft`
- `part6_decide`
- `part6_package_final`

触发语义：

- “开始 Part 6”
- “生成最终稿”
- “做最终审计”
- “生成 submission package”
- “part6-finalize-package”

职责：

1. 运行 Part 6 precheck。
2. 缺少 human gate 时停止，并报告需要用户确认的 gate。
3. 授权后运行 finalization。
4. 生成 Part 6 canonical artifacts。
5. 运行 Part 6 validation。
6. 输出用户可读的最终状态摘要。
7. 停在 final decision，不自动提交。

禁止：

- 不自动确认 `part6_finalization_authorized`
- 不自动确认 `part6_final_decision_confirmed`
- 不自动提交
- 不把 `.docx` / `.pdf` 当作 MVP 必需产物
- 不把 writing policy 当 research evidence

---

## 13. Implementation Plan

### Phase 1: Contracts and Gates

- Status: implemented contract。
- Part 6 canonical artifact、schema、human gate 与 CLI check 设计已进入当前 MVP 合同。
- 进入 Part 6 时必须确认：
  - Part 1-5 completed + gate passed
  - Part 5 handoff artifacts 当前有效
  - Part 5 readiness verdict 非 blocked
  - `part6_finalization_authorized` fingerprint 与当前 Part 5 handoff artifacts 一致

### Phase 2: Finalizer MVP

- Status: implemented runtime surface。
- 使用 `runtime/agents/part6_mvp_finalizer.py`
- 实现 `precheck`
- 实现 `finalize`
- 实现 `audit-claim`
- 实现 `audit-citation`
- 实现 `package-draft`
- 实现 `decide`
- 实现 `package-final`

### Phase 3: CLI and Skill

- Status: implemented explicit surface。
- CLI:
  - `part6-precheck`
  - `part6-authorize`
  - `part6-finalize`
  - `part6-check`
  - `part6-confirm-final`
- Skills:
  - `part6-finalize-package`
  - `part6-finalize-manuscript`
  - `part6-audit-claim-risk`
  - `part6-audit-citation-consistency`
  - `part6-build-submission-package`
  - `part6-decide-readiness`
- Manifest automation flow:
  - `part6_finalize`
  - `part6_audit_claim`
  - `part6_audit_citation`
  - `part6_package_draft`
  - `part6_decide`
  - `part6_package_final`

### Phase 4: Tests

- Status: active MVP test plan。
- schema contract tests
- Part 6 pipeline gate tests
- Part 6 finalizer tests
- CLI passthrough tests
- writing-policy separation regression tests
- citation drift blocking tests

---

## 14. Test Plan

MVP 必须先覆盖以下测试。

### 14.1 Schema Tests

- 4 个 Part 6 schema 的最小有效样例通过。
- 缺 required field 时失败。
- `does_not_advance_part7` 不是 `true` 时失败。

### 14.2 Entry Gate Tests

- 缺 Part 5 gate 时 `part6-precheck` 失败。
- 缺 `manuscript_v2.md` 时失败。
- 缺 `part6_finalization_authorized` 或 Part 5 handoff fingerprint 失效时失败。
- Part 5 readiness 为 `blocked_by_evidence_debt` 时失败。
- `ready_for_part6_with_research_debt` 可进入，但 residual risks 必须进入 Part 6 reports。

### 14.3 Citation Tests

- citation map 之外的新 source id 必须 blocked。
- raw metadata 不存在的 source id 必须 blocked。
- research-wiki 未映射的 source id 必须 blocked。
- writing-policy 路径不得进入 citation items。

### 14.4 Claim Risk Tests

- blocked claim 未处理时 final verdict 必须 blocked。
- high risk 没有 `recommended_action` / `applied_action` / `status` 时 gate 失败。
- residual research debt 不得丢失。

### 14.5 CLI Tests

- `part6-precheck` 只读，不写 `outputs/part6/*`。
- `part6-authorize` 只记录 Part 6 authorization 和 Part 5 handoff fingerprints，不生成 final artifacts。
- `part6-finalize` 在缺少 `part6_finalization_authorized` 时失败。
- `part6-finalize` 的 `all` 顺序必须是 `precheck -> finalize -> audit-claim -> audit-citation -> package-draft -> decide -> package-final`。
- `submission_package_manifest.json` 必须最后生成或刷新，并包含 `final_readiness_decision.json`。
- `part6-confirm-final` 只记录 human decision，不执行 submission。

---

## 15. Acceptance Criteria

Part 6 MVP 完成必须同时满足：

- `outputs/part6/final_manuscript.md` 已生成且非空。
- `outputs/part6/final_manuscript.md` 通过摘要、关键词、正文、结论 completeness check。
- `submission_package_manifest.json.required_files` 包含 `final_abstract.md`、`final_keywords.json` 与 `submission_checklist.md`。
- `outputs/part6/claim_risk_report.json` schema valid。
- `outputs/part6/citation_consistency_report.json` schema valid。
- `outputs/part6/submission_package_manifest.json` schema valid。
- `outputs/part6/final_readiness_decision.json` schema valid。
- final verdict 符合 claim/citation/manifest 状态。
- process-memory 中有 Part 6 gate 校验与 human decision 记录。
- 系统没有执行任何 submission action。
- `.docx` / `.pdf` 不是 completion gate 的必要条件。
