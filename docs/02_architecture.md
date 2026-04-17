# 02 Architecture

## 1. Architecture Overview
Thesis Destroyer 采用三层结构：Domain Workflow Layer、Research Harness Layer、Provider / Tool Layer。

### 1.1 Domain Workflow Layer
负责论文业务本身：

- 文献检索与资料库构建
- Research wiki
- Argument tree
- Paper outline
- Draft / review / revision
- Final manuscript、audit 与 package decision

对应目录主要是 `raw-library/`、`research-wiki/`、`writing-policy/` 与 `outputs/`。

### 1.2 Research Harness Layer
负责控制面与运行合同：

- Manifest 驱动
- State 管理
- Stage orchestration
- Schema validation
- Gate validation
- Doctor / audit
- Process-memory
- Human-in-the-loop gate

对应目录主要是 `runtime/`、`manifests/`、`schemas/`、`process-memory/` 与 `scripts/`。

### 1.3 Provider / Tool Layer
负责外部来源与工具能力：

- CNKI、万方、维普等中文学术来源
- Crossref、OpenAlex、DOAJ 等英文补充来源
- 下载器、网页归档、文本归一化
- LLM agent roles
- Validator、checker、exporter

Provider 层不得绕过访问控制，不保存账号、Cookie、token 或机构凭据。

## 2. Core Design Principles
- 先契约，后实现
- 中文主检索，英文补充
- 相关性、真实性、可落地性并重
- Canonical artifacts 驱动阶段推进
- Research evidence 与 writing policy 物理分层
- Raw sources 保持稳定，wiki 可持续维护
- Part 1 intake、Part 3 argument tree selection、Part 6 authorization / final decision 是必要人工决策点
- Part 4 / Part 5 不设置人工阻断 gate
- Part 6 是 gated finalization surface，不执行投稿或 submission action
- 开源仓库只保存 harness、规则、schema、测试与本地控制台代码，不保存研究产物

## 3. Stage Boundary
当前主链为：

1. Part 1: Collect Sources
2. Part 2: Build Research Wiki
3. Part 3: Generate Argument Trees
4. Part 4: Generate Outline
5. Part 5: Draft, Review and Revision
6. Part 6: Finalize MVP

Part 6 不会由 Part 5 自动触发。`outputs/part5/part6_readiness_decision.json` 只表达 handoff readiness；进入 Part 6 必须由用户确认 `part6_finalization_authorized`。

## 4. Stage Map

### 4.1 Part 1: Collect Sources
目标：

- 生成 intake request 和 intake template
- 在用户确认 intake 后创建或复用隔离 workspace
- 进行中文优先、英文补充的学术检索
- 完成相关性评分、去重、真实性校验、本地落地与资料库登记

输入：

- `outputs/part1/intake.json`
- `manifests/source-policy.json`
- 相关性策略配置
- 用户合法访问并导出的本地文件或网页 Markdown

输出：

- `outputs/part1/intake_request.md`
- `outputs/part1/intake_template.json`
- `outputs/part1/workspace_manifest.json`
- `outputs/part1/search_plan.json`
- `outputs/part1/supplementary_sources_task.md`
- `outputs/part1/retrieval_log.json`
- `outputs/part1/metadata_records.json`
- `outputs/part1/accepted_sources.json`
- `outputs/part1/excluded_sources_log.json`
- `outputs/part1/source_quota_report.json`
- `outputs/part1/download_manifest.json`
- `outputs/part1/downloaded_papers_table.csv`
- `outputs/part1/downloaded_papers_table.md`
- `outputs/part1/authenticity_report.json`
- `raw-library/metadata.json`
- `raw-library/papers/`
- `raw-library/web-archives/`
- `raw-library/normalized/`
- `raw-library/provenance/`
- `workspaces/ws_NNN/workspace_manifest.json`
- `workspaces/ws_NNN/outputs/part1/intake.json`

Canonical artifacts：

- `raw-library/metadata.json`
- `outputs/part1/authenticity_report.json`

### 4.2 Part 2: Build Research Wiki
目标：

- 将 raw-library 转换为可检索、可维护、可交叉引用的 research wiki
- 建立 research evidence layer 与 writing policy layer 的清晰边界
- 支持 wiki 更新、维护、校对与健康检查

输入：

- `raw-library/metadata.json`
- `outputs/part1/authenticity_report.json`
- `raw-library/normalized/`
- `raw-library/provenance/`
- `writing-policy/` 中的结构与表达约束

输出：

- `research-wiki/index.json`
- `research-wiki/index.md`
- `research-wiki/log.md`
- `research-wiki/update_log.json`
- `research-wiki/contradictions_report.json`
- `research-wiki/pages/source-digest/`
- `research-wiki/pages/evidence-aggregation/`
- `research-wiki/pages/concepts/`
- `research-wiki/pages/topics/`
- `research-wiki/pages/methods/`
- `research-wiki/pages/synthesis/`

Canonical artifact：

- `research-wiki/index.json`

### 4.3 Part 3: Generate Argument Trees
目标：

- 由 deterministic script 从 research wiki 与 raw metadata 提取可回溯 seed map
- 由 LLM `argumentagent` 从 seed map 生成候选论证树
- 比较候选方案
- 保留人工选择与反馈
- 锁定 canonical argument tree

输入：

- `outputs/part3/argument_seed_map.json`
- `research-wiki/index.json`
- `research-wiki/pages/`
- `raw-library/metadata.json`
- `writing-policy/`
- 研究目标与主题范围

输出：

- `outputs/part3/argument_seed_map.json`
- `outputs/part3/argumentagent_candidate_design.json`
- `outputs/part3/argumentagent_provenance.json`
- `outputs/part3/candidate_argument_trees/`
- `outputs/part3/refined_candidate_argument_trees/`
- `outputs/part3/refined_candidate_argument_trees/refinement_summary.json`
- `outputs/part3/candidate_comparison.json`
- `outputs/part3/argument_quality_report.json`
- `outputs/part3/human_selection_feedback.json`
- `outputs/part3/argument_tree.json`

Canonical artifact：

- `outputs/part3/argument_tree.json`

### 4.4 Part 4: Generate Outline
目标：

- 基于选定 argument tree 生成 canonical paper outline
- 生成 rationale 与 reference alignment report
- 为 Part 5 写作输入包做准备

输入：

- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `research-wiki/pages/`
- `writing-policy/`
- 中文论文参考案例
- 章节结构 rubric

输出：

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`

Canonical artifact：

- `outputs/part4/paper_outline.json`

说明：

- Part 4 不再设置人工 outline gate。
- 三份 outline artifacts 通过校验后即可作为 Part 4 completion，并允许自动进入 Part 5。

### 4.5 Part 5: Draft, Review and Revision
目标：

- 基于 canonical outline 自动生成写作输入包
- 生成保守正文初稿
- 执行结构化 review 与 citation precheck
- 生成面向用户的 review report 与修订后的 canonical Part 5 draft
- 只生成 Part 6 readiness 判断，不授权 Part 6

输入：

- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`
- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `research-wiki/pages/`
- `writing-policy/source_index.json`
- `raw-library/metadata.json`

输出：

- `outputs/part5/chapter_briefs/`
- `outputs/part5/case_analysis_templates/`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `outputs/part5/figure_plan.json`
- `outputs/part5/open_questions.json`
- `outputs/part5/manuscript_v1.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/review_summary.md`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`
- `outputs/part5/revision_log.json`
- `outputs/part5/manuscript_v2.md`
- `outputs/part5/part6_readiness_decision.json`

Canonical artifacts：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/review_matrix.json`
- `outputs/part5/review_report.md`
- `outputs/part5/revision_log.json`
- `outputs/part5/part6_readiness_decision.json`

说明：

- Part 5 不再设置人工写作、review 或 revision gate。
- `manuscript_v1.md` 只是中间稿；`manuscript_v2.md` 才是 Part 5 canonical final draft。
- Part 5 默认不写桌面副本；`outputs/part5/` 中的文件就是 canonical artifacts。

### 4.6 Part 6: Finalize MVP
目标：

- 在用户授权后，从 Part 5 handoff 生成最终稿与最终交付包
- 执行最终 claim audit 与 citation audit
- 生成 submission package manifest 与 final readiness decision
- 记录用户最终确认，但不执行 submission action

输入：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/part6_readiness_decision.json`
- `outputs/part5/claim_risk_report.json`
- `outputs/part5/citation_consistency_precheck.json`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `raw-library/metadata.json`
- `research-wiki/index.json`
- `writing-policy/source_index.json`

输出：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`
- `~/Desktop/{论文题目}.docx`

Canonical artifacts：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

说明：

- Part 6 需要 `part6_finalization_authorized` 与 `part6_final_decision_confirmed` 两个人工 gate。
- Part 6 不执行投稿、上传、提交或任何外部 submission action。
- `final_manuscript.docx` 与 `docx_format_report.json` 是 package required files；桌面 `{论文题目}.docx` 是用户阅读副本，不是 canonical artifact。

## 5. Part 1 Retrieval Architecture

### 5.1 User Intake First
Part 1 不采用“一句话主题直接搜索”的模式，而采用：

**intake request -> 用户填写 intake -> 用户确认 intake -> 隔离 workspace -> 检索计划 -> 多源检索**

建议 intake 字段包括：

- 研究主题
- 核心研究问题
- 学科 / 领域
- 时间范围
- 必须覆盖关键词
- 可选同义词
- 排除项
- 中文 / 英文偏好
- 预期研究类型
- 特殊来源要求

### 5.2 Workspace Isolation
确认 `intake_confirmed` 后，`scripts/new_workspace.py` 必须：

- 计算 intake hash
- 复用相同 hash 的既有 workspace，避免制造多个上下文副本
- 自动编号使用现有最大 `ws_NNN` + 1，不回填已删除编号
- 只复制 harness、规则、脚本与 confirmed intake
- 不复制 root 的 `raw-library/`、`research-wiki/`、`outputs/` 或 `process-memory/` 研究产物

### 5.3 Retrieval Pipeline
Part 1 的执行顺序：

1. intake request
2. workspace bootstrap
3. intake normalization
4. query planning
5. source routing
6. multi-source retrieval
7. relevance scoring
8. deduplication
9. authenticity verification
10. local download or web archive import
11. normalization
12. provenance capture
13. source quota validation
14. library registration

### 5.4 Source Priority
默认来源优先级：

#### Tier 1: Chinese Primary
- CNKI
- 万方
- 维普
- 其他学科匹配的中文权威来源

#### Tier 2: English Supplement
- Crossref
- OpenAlex
- DOAJ
- 学科专用英文来源

#### Tier 3: Other Supplement
- 经策略允许的开放资源
- 经真实性校验的辅助来源

### 5.5 Relevance Strategy
相关性评估至少考虑：

- 主题一致性
- 研究问题匹配度
- Confirmed intake 的对象锚点与场景锚点
- 标题 / 摘要 / 关键词命中
- 方法 / 样本 / 对象匹配度
- 时间范围适配
- 中文写作场景的可用性
- 来源可信度

### 5.6 Authenticity Strategy
进入主资料库前必须通过真实性校验。至少包含：

- 标识证据
- 索引证据
- 来源落地证据
- 本地文件或网页归档落地成功
- 来源记录与 provenance 完整

## 6. Part 2 Wiki Architecture

### 6.1 Why a Research Wiki Exists
Research wiki 是 raw-library 与 argument tree 之间的持久中间层。它的职责不是替代原始文献，而是：

- 将原始资料转成可组织、可检索、可复用的知识层
- 按主题、概念、方法、证据和争议建立交叉链接
- 支撑后续论证树生成、大纲生成和写作审计
- 保留对 raw sources 的可回溯映射

### 6.2 Wiki Page Types
Part 2 至少维护以下页面类型：

- Source digest
- Evidence aggregation
- Concepts
- Topics
- Methods
- Synthesis

### 6.3 Wiki Integrity
每个 wiki 页面必须具备：

- `source_ids`
- `file_path`
- `page_type`
- 来源映射
- 交叉链接
- 变更依据
- `source_mapping_complete=true`

跨来源冲突必须进入 `research-wiki/contradictions_report.json`。

### 6.4 Writing Policy Layer
Writing policy 存放：

- 中文学术写作规范
- 格式要求
- 结构与表达偏好
- 常见错误与禁区
- 示例结构 / 章节约束

Writing policy 只能约束表达和结构，不得作为 research evidence。

## 7. Part 3 Argument Tree Architecture

### 7.1 Seed Map Ownership
Part 3 的 seed map 属于 deterministic runtime script。它负责从 `research-wiki/` 与 `raw-library/metadata.json` 提取 candidate claims、evidence points、counterclaims、method paths、case boundaries 与 evidence gaps。

`argumentagent` 不得生成、改写或拥有 `outputs/part3/argument_seed_map.json`。

### 7.2 LLM Candidate Generation
正式候选论点与候选 argument tree 必须由 LLM `argumentagent` 生成，而不是由 deterministic script 默认拼接。

运行顺序：

```text
deterministic seed map
-> LLM candidate argument design
-> LLM stress test and comparison
-> LLM refined candidate proposal
-> deterministic density / trace / schema validation
-> human selection
-> deterministic canonical lock
```

本地 Codex adapter：

```bash
export RTM_ARGUMENTAGENT_COMMAND="python3 runtime/agents/argumentagent_codex_cli.py"
```

`argumentagent` 必须使用：

- `part3-argument-generate`
- `part3-argument-divergent-generate`
- `part3-argument-compare`
- `part3-argument-stress-test`
- `part3-argument-refine`
- `part3-human-selection`

### 7.3 Density and Trace Validation
Runtime scripts 负责校验：

- 候选树通常包含 12-18 个总节点、9-13 个观点节点
- 每份候选至少包含 thesis、main_argument、sub_argument、counterargument 与 rebuttal
- 每个节点必须保留 `support_source_ids`、`wiki_page_ids` 与 `seed_item_ids`
- 节点的 source/page 不得超出 referenced seed items 覆盖范围
- 创新点必须标记为 evidence-bounded hypothesis 或带清晰 evidence status

过薄、无来源、seed trace 不成立或 schema 不通过的 LLM 输出不得落入正式候选。

### 7.4 Human Selection
系统必须产出：

- 候选比较
- 各候选优缺点
- 选择建议
- 人工反馈入口

未完成人工选择前，不得推进到 canonical lock。

### 7.5 Canonical Locking
一旦人工选定，必须锁定：

- canonical `argument_tree.json`
- 选择依据
- 比较记录
- 反馈快照

## 8. Part 4 Outline Architecture

### 8.1 Generation Strategy
Part 4 不依赖训练。Outline 生成由以下输入共同约束：

- Canonical argument tree
- Research wiki
- Writing policy
- Reference cases
- Chapter rubric

### 8.2 Reference Cases
参考案例用于：

- 章节顺序参考
- 结构密度参考
- 表达规范参考
- 论证展开方式参考

参考案例不得提供新的 research facts。

### 8.3 Validation
Part 4 completion gate 必须确认：

- `paper_outline.json` 已生成
- Outline 与 argument tree 对齐
- `outline_rationale.json` 可解释章节设计
- `reference_alignment_report.json` 可说明参考案例和 writing policy 的使用边界

## 9. Part 5 Draft / Review / Revision Architecture

### 9.1 Automated Flow
Part 5 不再保留人工阻断节点。Part 4 completion gate 通过后，可自动执行：

```text
prep -> draft -> review -> revise
```

该流程必须生成章节 brief、案例模板、claim-evidence matrix、citation map、figure plan、open questions、`manuscript_v1.md`、review artifacts、`review_report.md`、`revision_log.json`、`manuscript_v2.md` 与 `part6_readiness_decision.json`。

### 9.2 Drafting Policy
Part 5 的正文生成必须保守：

- 只能使用已登记证据
- 不新增不可回溯事实
- 不确定 claim 必须降级、标注或进入 blocker
- `manuscript_v1.md` 只是中间稿

### 9.3 Review Policy
Review 至少覆盖：

- 结构完整性
- 论证连续性
- Claim-evidence 对齐
- Citation consistency
- Writing policy compliance
- Research debt
- Critical blocker

### 9.4 Revision Policy
Revision 只处理 review 中可安全处理的问题。不能用修订掩盖来源缺失、真实性不足或 claim 证据不足。

### 9.5 Part 6 Handoff
Part 5 只输出 handoff readiness，不授权 Part 6。`part6_readiness_decision.json` 可以建议 `ready_for_part6` 或 `ready_for_part6_with_research_debt`，但进入 Part 6 必须由用户确认 `part6_finalization_authorized`。

## 10. Part 6 Finalization Architecture

### 10.1 Authorization
Part 6 必须先通过 `part6_finalization_authorized`。授权时应记录 Part 5 handoff fingerprint；如果 Part 5 handoff artifacts 漂移，必须重新授权。

### 10.2 Final Package
Part 6 final package 至少包括：

- Final manuscript
- Final abstract
- Final keywords
- Submission checklist
- Formatted docx
- Docx format report
- Claim risk report
- Citation consistency report
- Submission package manifest
- Final readiness decision

### 10.3 Final Decision
Part 6 completion 必须经过 `part6_final_decision_confirmed`。该 gate 只确认最终 readiness verdict 与 package manifest，不执行投稿。

### 10.4 DOCX Export
Part 6 docx export 是确定性格式导出步骤。它只读取已生成的 final manuscript、abstract、keywords、claim audit 与 citation audit，不改写正文，不新增 source、claim、case fact、citation 或 research conclusion。

Docx export 必须产出：

- `outputs/part6/final_manuscript.docx`
- `outputs/part6/docx_format_report.json`
- `~/Desktop/{论文题目}.docx`

`docx_format_report.json` 必须记录 source manuscript、项目内 docx、桌面副本、论文题目、cover/template residue 检查、style checks 与 content checks。缺少桌面副本或 format report blocked 时，Part 6 gate 不得通过。

### 10.5 MVP Runtime Steps
Part 6 MVP 的 `all` flow 为：

```text
precheck
-> finalize
-> audit-claim
-> audit-citation
-> package-draft
-> export-docx
-> decide
-> package-final
```

用户入口保持少量命令：

- `part6-precheck`
- `part6-authorize`
- `part6-finalize --step ...`
- `part6-export-docx`
- `part6-check`
- `part6-confirm-final`

`formal_submission_ready` 只是 readiness verdict，不是投稿授权。系统不得执行投稿、上传、邮件发送或任何 submission action。

## 11. Canonical Artifacts
当前 canonical artifacts 为：

- Part 1: `raw-library/metadata.json`, `outputs/part1/authenticity_report.json`
- Part 2: `research-wiki/index.json`
- Part 3: `outputs/part3/argument_tree.json`
- Part 4: `outputs/part4/paper_outline.json`
- Part 5: `outputs/part5/manuscript_v2.md`, `outputs/part5/review_matrix.json`, `outputs/part5/review_report.md`, `outputs/part5/revision_log.json`, `outputs/part5/part6_readiness_decision.json`
- Part 6: `outputs/part6/final_manuscript.md`, `outputs/part6/claim_risk_report.json`, `outputs/part6/citation_consistency_report.json`, `outputs/part6/submission_package_manifest.json`, `outputs/part6/final_readiness_decision.json`

任何阶段推进均不得绕过 canonical artifacts。

## 12. Stage Gates

### 12.1 Part 1 Gate
必须满足：

- Intake 已由用户确认
- 已确认 intake 的隔离 workspace 已创建或复用
- 检索计划已生成
- CNKI 优先策略已执行
- 相关性评估已完成
- 真实性校验通过
- 本地资料库落地完成
- Accepted sources 满足 40 篇、CNKI 24-28 篇、英文期刊至少 5 篇
- 已下载论文清单与 source quota report 已生成在 `outputs/part1/`

### 12.2 Part 2 Gate
必须满足：

- Research wiki 页面生成完成
- `research-wiki/index.json` 可用
- 来源映射完整
- Contradictions / health check 通过基本门槛
- Writing policy 层已建立且未混入 research evidence

### 12.3 Part 3 Gate
必须满足：

- 3 份候选 argument tree 齐备
- Comparison 齐备
- Human feedback 齐备
- Canonical argument tree 已锁定

### 12.4 Part 4 Gate
必须满足：

- Canonical outline 已生成
- Outline 与 argument tree 对齐
- Rationale 与 reference alignment report 可用
- 无需人工 outline gate

### 12.5 Part 5 Gate
必须满足：

- 写作输入包齐备
- `manuscript_v1.md` 已生成
- `review_matrix.json`、`review_report.md`、`revision_log.json`、`part6_readiness_decision.json` 齐备
- `manuscript_v2.md` 已生成且非空
- 不存在未登记的 critical blocker
- Part 6 readiness decision 只作为 readiness verdict，不授权 Part 6

### 12.6 Part 6 Gate
必须满足：

- Part 1-5 gates completed
- `part6_finalization_authorized` 已记录
- Part 5 readiness verdict 不是 blocked
- Part 5 handoff fingerprint 未漂移
- Citation 与 evidence allowlist 通过
- Final manuscript、claim audit、citation audit、submission package manifest 与 final readiness decision 齐备
- `final_manuscript.docx` 与 `docx_format_report.json` 齐备
- `docx_format_report.desktop_docx_ref` 指向存在的桌面 `{论文题目}.docx`
- `part6_final_decision_confirmed` 已记录
- 未执行 submission action

## 13. State Management
运行时至少包含以下状态能力：

- 当前阶段记录
- 阶段开始 / 完成时间
- 当前 canonical artifact 状态
- 最近一次失败位置
- Repair 记录
- Human decision 记录

State rules：

- 状态损坏不可静默重置
- Repair 必须留备份
- 未通过 gate 不得推进
- 回滚必须有显式记录

## 14. Memory Architecture

### 14.1 raw-library
保存原始资料、网页归档、规范化文本、元数据与 provenance。

### 14.2 research-wiki
保存结构化研究知识、交叉链接、更新记录和冲突报告。

### 14.3 writing-policy
保存规范、模板、格式规则、参考案例与表达限制。

### 14.4 process-memory
保存 gate 结果、评审结论、选择理由、失败、修复与人工决策记录。

### 14.5 workspaces
保存从 confirmed intake 派生的隔离运行空间。Workspace 是运行时上下文，不应作为开源模板内容提交。

## 15. Validation and Diagnostics
当前架构至少包含：

- JSON schema validation
- Artifact presence check
- Stage gate validation
- Wiki health check
- State diagnostics
- Audit / doctor 入口
- Script-level path safety checks
- Source quota validation

## 16. LLM Agent Boundary
LLM agent roles 负责判断、综合、批判和写作建议；runtime scripts 负责文件落盘、schema 校验、state/gate 写入和 canonical lock。

当前启用角色包括：

- `researchagent`
- `wikisynthesisagent`
- `argumentagent`
- `outlineagent`
- `writeagent` / `writeragent`
- `claimauditor`
- `citationauditor`

LLM agent 不得确认 human gate，不得写 `runtime/state.json`，不得绕过 deterministic validation，不得新增不可回溯的 source、citation、case fact、data 或 research conclusion。

其中，`argumentagent` 拥有正式 Part 3 候选论点和候选论证树的生成判断；deterministic runtime 只拥有 seed map、密度/溯源/schema validation、候选文件落盘、human selection 与 canonical lock。

## 17. Open Source Boundary
开源仓库只保存：

- Workflow harness
- Runtime scripts
- Schemas
- Manifests
- Skills
- Writing-policy baseline rules
- Tests
- Docs

以下内容不得提交：

- 论文 PDF
- 原始研究材料
- 个人 intake
- Manuscript 草稿
- 生成的 docx 或桌面副本
- 浏览器缓存
- 账号、Cookie、token、密钥
- 运行时 workspace 内容
- `outputs/`、`raw-library/`、`research-wiki/`、`process-memory/` 中的生成产物

## 18. Contract Files
当前架构由以下文件共同定义：

- `AGENTS.md`
- `README.md`
- `docs/01_build_target.md`
- `docs/02_architecture.md`
- `manifests/pipeline-stages.json`
- `manifests/source-policy.json`
- `schemas/`
- `runtime/pipeline.py`
