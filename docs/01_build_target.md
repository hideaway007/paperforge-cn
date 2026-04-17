# 01 Build Target

## 1. Project Name
Thesis Destroyer

## 2. Project Goal
本项目是一套面向中文学术论文写作的 research-to-manuscript workflow harness。它不是一次性 prompt，也不是自动代写论文系统，而是把“研究主题 intake -> 文献资料库 -> research wiki -> argument tree -> paper outline -> 正文草稿 / review / revision -> 最终定稿包”拆成可校验、可恢复、可审计的阶段。

系统应能从用户确认的研究主题出发，完成：

- 结构化 intake 与隔离 workspace 创建
- 中文优先、英文补充的文献检索与来源路由
- 文献下载、本地落地、去重、相关性评分与真实性校验
- research wiki 构建、维护、来源映射与冲突记录
- argument tree 候选生成、比较、人工选择与 canonical lock
- canonical paper outline 三件套生成与校验
- Part 5 写作输入包、正文初稿、结构化 review、保守修订与 readiness handoff
- Part 6 finalization：最终稿、claim / citation audit、submission package manifest 与最终 readiness 决策

所有 canonical artifacts 默认保存在项目目录内。外部导出文件只作为用户阅读副本，不作为 canonical package。

## 3. Why This Project Exists
AI 辅助论文写作的主要风险不在“能不能生成文字”，而在以下问题：

- 资料来源不稳定，检索结果质量波动大
- 引用真实性不足，容易混入伪引文或低可信来源
- 上下文容易丢失，研究信息难以长期积累和复用
- 论证形成过程不可追踪，后续审查和修改成本高
- 阶段之间缺乏清晰 artifact 合同，导致草稿、证据和最终稿边界混乱
- 中文写作规范、导师偏好和格式要求容易与研究证据混杂

Thesis Destroyer 的目标，是把论文工作流变成一条长期可迭代的主链：先建立可信证据层，再形成论证结构，最后生成可审计的稿件与交付包。

## 4. MVP Scope
当前开源版主链覆盖 Part 1 到 Part 6。

### 4.1 Part 1: Collect Sources
- 每次启动 Part 1，先生成 `outputs/part1/intake_request.md` 与 `outputs/part1/intake_template.json`
- 用户填写并确认 `outputs/part1/intake.json` 后，系统创建或复用隔离 workspace
- 隔离 workspace 只复制 harness、规则、脚本与 confirmed intake，不复制既有研究产物
- CNKI 是第一优先来源，必须先执行由 confirmed intake 派生的聚焦查询
- `cnki_q1_1` 必须绑定当前 intake 的研究对象与方法 / 教学 / 应用 / 案例锚点，不得复用旧主题模板
- 支持万方、维普、Crossref、OpenAlex、DOAJ 等补充来源
- Part 1 accepted sources 目标为 40 篇：CNKI 24-28 篇，英文期刊至少 5 篇，其余来自非 CNKI 可验真补充来源
- 支持本地 PDF 与开放网页 Markdown 归档，所有来源必须写入 provenance
- 完成去重、相关性评分、真实性校验、本地落地与资料库注册

### 4.2 Part 2: Build Research Wiki
- 基于 Part 1 canonical artifacts 与 `raw-library/metadata.json` 构建 research wiki
- `research-wiki/` 是持久研究证据层，不是 metadata 卡片副本
- 必须维护 `research-wiki/index.json`、`index.md`、`log.md`、`update_log.json` 与 `contradictions_report.json`
- 必须生成 source digest、evidence aggregation、concept、topic、method、synthesis 类页面
- 每个 wiki 页面必须包含 `source_ids`、`file_path`、`page_type`、来源映射、交叉链接、变更依据与 `source_mapping_complete=true`
- `writing-policy/` 只保存结构、表达、格式和参考案例规则，不得混入 research evidence

### 4.3 Part 3: Generate Argument Trees
- 先由 deterministic script 基于 research wiki 与 `raw-library/metadata.json` 生成 `outputs/part3/argument_seed_map.json`
- 正式候选论点与候选 argument tree 必须由 LLM `argumentagent` 基于 seed map 生成，不得默认由脚本代写
- `argumentagent` 必须结合 `part3-argument-generate` 与 `part3-argument-divergent-generate`，先形成论点池，再组织 3 份候选路线
- 候选树必须通过论点密度、来源追溯、seed item 覆盖与 schema validation；过薄候选应被拒绝
- 生成候选比较、质量评估与选择建议
- 必须由用户选择 canonical candidate
- 人工选择后锁定 `outputs/part3/argument_tree.json`

### 4.4 Part 4: Generate Outline
- 基于 canonical argument tree、research wiki 与 writing policy 生成 paper outline
- 同时产出 `paper_outline.json`、`outline_rationale.json` 与 `reference_alignment_report.json`
- 支持中文论文参考案例与章节 rubric 作为结构约束
- 不以模型训练或微调为前提
- 不再设置人工 outline gate；三件套通过 deterministic validation 后即可进入 Part 5

### 4.5 Part 5: Draft, Review and Revision
- 自动生成 chapter briefs、case analysis templates、claim-evidence matrix、citation map、figure plan 与 open questions
- 生成保守正文初稿 `outputs/part5/manuscript_v1.md`
- 执行结构、论证、证据、引用、写作规范与研究债务 review
- 生成 `outputs/part5/review_matrix.json` 与面向用户的 `outputs/part5/review_report.md`
- 生成 `outputs/part5/revision_log.json` 与 canonical final Part 5 draft `outputs/part5/manuscript_v2.md`
- 生成 `outputs/part5/part6_readiness_decision.json`，只表达 handoff readiness，不授权 Part 6

### 4.6 Part 6: Finalize MVP
- Part 6 是当前主链的一部分，但必须由用户显式授权
- `part6_finalization_authorized` 之前不得生成 final package
- 基于 Part 5 handoff 生成最终稿、最终摘要、关键词、submission checklist、claim audit、citation audit、package manifest 与 final readiness decision
- 生成格式化 Word 文件 `outputs/part6/final_manuscript.docx` 与 `outputs/part6/docx_format_report.json`
- 生成桌面阅读副本 `~/Desktop/{论文题目}.docx`，文件名必须来自论文题目
- `part6_final_decision_confirmed` 之前不得标记 Part 6 complete
- Part 6 不执行投稿、提交、上传或任何外部 submission action
- 桌面副本只是用户交互层，不是 canonical artifact，也不是 research evidence

## 5. Out of Scope
当前版本明确不做：

- 自动投稿、自动提交或自动上传最终论文
- 自动确认任何 human gate
- 绕过 CNKI、万方、维普或其他平台访问控制
- 内置账号、Cookie、token、密钥或机构凭据
- 把预印本、网页摘要、二手转述或低可信内容默认当作强证据
- 将 writing policy、格式模板、导师意见或作者风格材料混入 research evidence
- 一开始就引入训练 / 微调作为核心依赖
- 把运行时产物、论文 PDF、个人 intake、草稿或浏览器缓存提交到开源仓库

## 6. Immutable Constraints
以下规则不可被 agent 或脚本擅自改动。

### 6.1 Source Policy
- CNKI 为第一优先来源，任何阶段不可绕过
- Part 1 必须先执行聚焦查询，再执行宽泛扩展
- 聚焦查询必须从 confirmed intake 动态生成，不得保留旧题目模板
- 英文来源只能作为补充层，不能替代中文主检索策略
- 所有来源进入主链前必须经过去重、相关性评分、真实性校验与 provenance 记录
- 来源策略以 `manifests/source-policy.json` 为准，不得在运行时被动态覆盖

### 6.2 Authenticity and Artifacts
- 不得跳过真实性校验
- 校验失败必须记录至 `outputs/part1/excluded_sources_log.json`
- 不得用非 canonical artifacts 推进阶段
- 不得把 `manuscript_v1.md` 当作最终稿
- 状态损坏时必须显式报告，不得静默修复或重置

### 6.3 Human-in-the-Loop Gates
以下 gate 必须由用户决策，不能由 agent 或脚本自动确认：

- `intake_confirmed`
- `argument_tree_selected`
- `part6_finalization_authorized`
- `part6_final_decision_confirmed`

Part 4 与 Part 5 不再设置人工阻断 gate。旧流程中的 Part 4 / Part 5 人工确认节点不应被视为当前流程的必需条件。

### 6.4 Knowledge Layering
- `research-wiki/` 与 `writing-policy/` 必须物理分离
- `raw-library/` 中的原始资料不得被改写；规范化文本放入 `raw-library/normalized/`
- Research evidence 必须可回溯到 `raw-library/metadata.json` 与 provenance
- Writing policy 只能约束结构、表达和格式，不得作为研究证据来源

### 6.5 Open Source Hygiene
- 开源仓库只提交 workflow harness、规则、schema、测试和本地控制台代码
- `outputs/`、`raw-library/`、`research-wiki/`、`process-memory/`、`workspaces/` 默认只保留 `.gitkeep`
- 密钥、账号、token、Cookie、论文 PDF、个人 intake、manuscript 草稿和浏览器缓存不得进入 Git

## 7. Success Criteria
当前版本视为成功，至少满足以下条件。

### 7.1 Part 1 Success
- 系统能生成 intake request 与 intake template
- 用户确认 intake 后能创建或复用隔离 workspace，并自动启动 workspace 内 Part 1 runner
- 能生成中文优先、英文补充的检索计划
- CNKI 聚焦查询先于宽泛扩展执行
- accepted sources 满足 40 篇、CNKI 24-28 篇、英文期刊至少 5 篇的配额
- 进入资料库的来源完成真实性校验、本地落地与 provenance 记录
- 已下载论文清单与 `source_quota_report.json` 生成在 `outputs/part1/`

### 7.2 Part 2 Success
- `research-wiki/index.json` 可用
- wiki 页面覆盖 source digest、evidence aggregation、concept、topic、method、synthesis 类页面
- 每个页面具备来源映射、交叉链接和变更依据
- 冲突进入 `research-wiki/contradictions_report.json`
- Writing policy 层独立存在，不污染 evidence layer

### 7.3 Part 3 Success
- `argument_seed_map.json` 由 deterministic script 生成并可回溯到 Part 2 / raw-library
- 3 份候选 argument tree 由 LLM `argumentagent` 生成，且具备足够论点密度、反方处理与创新假说边界
- 候选树通过 source/wiki/seed trace validation 与 schema validation
- comparison、quality report 与 human selection feedback 齐备
- 用户完成选择后 canonical `argument_tree.json` 被锁定

### 7.4 Part 4 Success
- `paper_outline.json`、`outline_rationale.json` 与 `reference_alignment_report.json` 齐备
- Outline 能回溯到 argument tree 与 research wiki
- Reference alignment 能说明 writing policy 和参考案例的使用边界
- 通过校验后能自动支撑 Part 5，不需要人工 outline gate

### 7.5 Part 5 Success
- 写作输入包、`manuscript_v1.md`、review artifacts、`review_report.md`、`revision_log.json` 与 `manuscript_v2.md` 齐备
- `manuscript_v2.md` 只使用已登记证据，不能新增不可回溯事实
- Critical blocker 被登记，不确定 claims 被降级、标注或进入 blocker
- `part6_readiness_decision.json` 只表达 handoff readiness，不授权 Part 6

### 7.6 Part 6 Success
- 用户已授权 `part6_finalization_authorized`
- Part 5 handoff fingerprint 未漂移
- `final_manuscript.md`、claim audit、citation audit、submission package manifest 与 final readiness decision 齐备
- `final_manuscript.docx`、`docx_format_report.json` 与桌面 `{论文题目}.docx` 齐备
- 用户已确认 `part6_final_decision_confirmed`
- Part 6 complete 不代表投稿完成，也不授权 submission action

## 8. Failure Conditions
出现以下情况即视为失败：

- 未确认 intake 就执行检索、下载、评分或资料库注册
- 绕过 CNKI 优先策略或把 CNKI 聚焦查询退化为泛化大 OR 查询
- 文献真实性不足但仍进入主资料库
- 相关性明显不足但仍计入 accepted sources
- 资料库配额不满足却推进 Part 1 canonical artifacts
- Research wiki 页面缺少来源映射或把 writing policy 当作 research evidence
- Part 3 在未配置 LLM `argumentagent` 时默默用 deterministic fallback 代写正式论点
- Argument tree 或 outline 不能回溯到资料依据
- Part 4 / Part 5 重新引入旧人工 gate 作为阻断条件
- Part 5 把未核验事实写成确定结论，或吞掉 critical blocker
- 未获用户授权就运行 Part 6 finalization，或把 Part 5 readiness 当作 Part 6 授权
- Part 6 docx format report blocked、缺少项目内 docx，或缺少桌面 `{论文题目}.docx` 副本
- Part 6 执行投稿、提交、上传或任何外部 submission action
- 运行时产物、个人资料、论文 PDF、密钥或浏览器缓存进入 Git
- 系统一旦中断就无法恢复、无法审计或无法解释推进依据

## 9. Human Decisions Required
以下节点必须人工拍板：

- 研究主题、范围边界与结构化 intake 关键参数确认
- 候选 argument tree 的最终选择
- 授权从 Part 5 handoff 进入 Part 6 finalization
- 确认 Part 6 final readiness verdict 与 submission package manifest
- 改变 MVP 边界、不可变约束或 canonical artifact 合同

## 10. Preferred Source Strategy
### 10.1 Chinese Priority Sources
默认优先来源为：

1. CNKI
2. 万方
3. 维普
4. 其他与学科匹配的中文权威来源

### 10.2 English Supplement Sources
英文补充来源可包括：

- Crossref
- OpenAlex
- DOAJ
- 学科专用英文来源
- 经真实性校验的开放论文来源

### 10.3 Web Archives
网页详情页或开放网页全文可以作为补充落地 artifact，但必须：

- 由用户合法访问并导出为 Markdown
- 导入 `raw-library/web-archives/`
- 写入 provenance
- 通过真实性校验

## 11. Relevance Policy
Part 1 不得只按关键词粗暴抓取。相关性评分必须综合考虑：

- 研究主题与研究问题匹配度
- Confirmed intake 的对象锚点与场景锚点
- 标题、摘要、关键词命中
- 方法、任务、对象的一致性
- 时间范围与研究阶段适配度
- 中文主写作场景下的可引用性
- 来源可信度与可落地性

## 12. Canonical Artifact Contract
当前 canonical artifacts 以 `AGENTS.md`、`manifests/pipeline-stages.json`、`schemas/` 与 runtime gate 为准。核心路径包括：

- Part 1: `raw-library/metadata.json`, `outputs/part1/authenticity_report.json`
- Part 2: `research-wiki/index.json`
- Part 3: `outputs/part3/argument_tree.json`
- Part 4: `outputs/part4/paper_outline.json`
- Part 5: `outputs/part5/manuscript_v2.md`, `review_matrix.json`, `review_report.md`, `revision_log.json`, `part6_readiness_decision.json`
- Part 6: `outputs/part6/final_manuscript.md`, `claim_risk_report.json`, `citation_consistency_report.json`, `submission_package_manifest.json`, `final_readiness_decision.json`

Part 6 package 还要求 `outputs/part6/final_abstract.md`、`final_keywords.json`、`submission_checklist.md`、`final_manuscript.docx` 与 `docx_format_report.json`。这些 package files 支撑最终交付检查，但其中 docx 与桌面副本不属于 research evidence。

## 13. Project Contract Files
当前目标、架构、运行合同与项目规则由以下文件共同定义：

- `AGENTS.md`
- `README.md`
- `docs/01_build_target.md`
- `docs/02_architecture.md`
- `manifests/pipeline-stages.json`
- `manifests/source-policy.json`
- `schemas/`
- `runtime/pipeline.py`
