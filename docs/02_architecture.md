# 02 Architecture

## 1. Architecture Overview
Thesis Destroyer 采用三层结构：

### 1.1 Domain Workflow Layer
负责论文业务本身，包括：
- 文献检索
- 资料库构建
- research wiki
- argument tree
- paper outline
- 后续写作、评审、修订与导出

### 1.2 Research Harness Layer
负责控制与运行，包括：
- manifest 驱动
- state 管理
- stage orchestration
- schema validation
- doctor / audit
- process-memory
- human-in-the-loop gate
- hooks 与诊断工具

### 1.3 Provider / Tool Layer
负责接入外部来源与能力，包括：
- 中文学术数据库 / 权威来源
- 英文补充学术来源
- 下载器 / 文本归一化
- LLM provider
- validator / checker / exporter

## 2. Core Design Principles
- 先契约，后实现
- 中文主检索，英文补充
- 相关性、真实性、可落地性并重
- canonical artifacts 驱动阶段推进
- research evidence 与 writing policy 分层
- raw sources 保持稳定，wiki 可持续维护
- 必要人工决策点不可跳过：Part 1 intake 与 Part 3 argument tree selection 仍需人工确认
- Part 4 / Part 5 不设置人工阻断 gate，系统承担自动衔接与校验
- Part 6 当前 deferred，不属于主链自动推进范围
- 先跑通主链，再扩展 hooks / commands / agents

## 3. MVP Stage Boundary
本期 MVP 的主链为：

1. Part 1: Collect Sources
2. Part 2: Build Research Wiki
3. Part 3: Generate Argument Trees
4. Part 4: Generate Outline
5. Part 5: Draft, Review and Revision

Part 6（finalize / submission package）当前为 deferred / future design。Part 5 会生成 `part6_readiness_decision.json`，但该文件只表达后续准备度，不授权、不触发、也不自动推进 Part 6。

## 4. Stage Map

### Part 1: Collect Sources
目标：
- 从研究主题出发生成结构化检索计划
- 进行中文优先、英文补充的学术检索
- 完成下载、本地落地、真实性校验与资料库登记

输入：
- 用户研究主题
- 用户结构化 intake
- 来源策略配置
- 相关性策略配置

输出：
- `outputs/part1/intake.json`
- `outputs/part1/search_plan.json`
- `outputs/part1/retrieval_log.json`
- `outputs/part1/metadata_records.json`
- `outputs/part1/accepted_sources.json`
- `outputs/part1/excluded_sources_log.json`
- `outputs/part1/download_manifest.json`
- `outputs/part1/authenticity_report.json`
- `outputs/part1/downloaded_papers_table.csv`
- `outputs/part1/downloaded_papers_table.md`
- `~/Desktop/part1_downloaded_papers_table.csv`
- `~/Desktop/part1_downloaded_papers_table.md`
- `raw-library/metadata.json`
- `raw-library/papers/`
- `raw-library/normalized/`
- `raw-library/provenance/`

### Part 2: Build Research Wiki
目标：
- 将 raw-library 转换为可检索、可维护、可交叉引用的 research wiki
- 建立研究证据层与写作规范层
- 支持 wiki 更新、维护、校对与健康检查

输入：
- Part 1 canonical artifacts
- 已验真原始文献
- 导师 PPT / 课程资料 / 中文学术写作规范
- 写作规则提炼结果

输出：
- `research-wiki/pages/`
- `research-wiki/index.json`
- `research-wiki/contradictions_report.json`
- `research-wiki/update_log.json`
- `writing-policy/rules/`
- `writing-policy/style_guides/`
- `writing-policy/source_index.json`

### Part 3: Generate Argument Trees
目标：
- 基于 research wiki 生成候选论证树
- 比较候选方案
- 保留人工选择与反馈
- 锁定 canonical argument tree

输入：
- `research-wiki/`
- `writing-policy/`
- 研究目标与主题范围
- 论证生成策略

输出：
- `outputs/part3/candidate_argument_trees/`
- `outputs/part3/candidate_comparison.json`
- `outputs/part3/human_selection_feedback.json`
- `outputs/part3/argument_tree.json`

### Part 4: Generate Outline
目标：
- 基于选定的 argument tree 生成 canonical paper outline
- 在 MVP 阶段采用参考案例与写作规范约束生成
- 为后续章节 brief 与正文写作做准备

输入：
- `outputs/part3/argument_tree.json`
- `research-wiki/`
- `writing-policy/`
- 中文论文参考案例
- 章节结构 rubric

输出：
- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`

说明：
- Part 4 不再设置 `outline_confirmed` 人工 gate。
- 三份 outline artifacts 通过校验后即可作为 Part 4 completion，并允许自动进入 Part 5。

### Part 5: Draft, Review and Revision
目标：
- 基于 canonical outline 自动生成写作输入包
- 生成保守正文初稿 `manuscript_v1.md`
- 执行结构化 review 与 citation precheck
- 生成面向用户的 review 汇报和修订后的 canonical Part 5 draft
- 把 review report 与最终稿导出到桌面
- 只生成 Part 6 readiness 判断，不自动进入 Part 6

输入：
- `outputs/part4/paper_outline.json`
- `outputs/part4/outline_rationale.json`
- `outputs/part4/reference_alignment_report.json`
- `outputs/part3/argument_tree.json`
- `research-wiki/index.json`
- `writing-policy/source_index.json`

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
- `~/Desktop/part5_review_report.md`
- `~/Desktop/manuscript_v2.md`

说明：
- Part 5 不再设置 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted` 人工 gate。
- `manuscript_v1.md` 只是中间稿；`manuscript_v2.md` 才是 Part 5 canonical final draft。
- 桌面文件是用户交互层，必须与 `outputs/part5/` 对应 canonical 文件内容一致。

## 5. Part 1 Retrieval Architecture

### 5.1 User Intake First
Part 1 不采用“只给一句话主题就直接搜索”的模式，而采用：

**用户结构化 intake → AI 扩写检索计划 → 执行多源检索**

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

### 5.2 Retrieval Pipeline
Part 1 的执行顺序：

1. intake normalization
2. query planning
3. source routing
4. multi-source retrieval
5. relevance scoring
6. deduplication
7. authenticity verification
8. local download
9. normalization
10. provenance capture

### 5.3 Source Priority
默认来源优先级：

#### Tier 1: 中文主来源
- CNKI（第一优先）
- 万方
- 维普
- 其他学科匹配的中文权威来源

#### Tier 2: 英文补充来源
- Crossref
- OpenAlex
- DOAJ
- 学科专用英文来源

#### Tier 3: 其他补充来源
- 经策略允许的开放资源
- 经真实性校验的辅助来源

### 5.4 Relevance Strategy
相关性评估至少考虑：
- 主题一致性
- 研究问题匹配度
- 标题 / 摘要 / 关键词命中
- 方法 / 样本 / 对象匹配度
- 时间范围适配
- 中文写作场景的可用性
- 来源可信度

### 5.5 Authenticity Strategy
进入主资料库前必须通过真实性校验。至少包含：
- 标识证据
- 索引证据
- 来源落地证据
- 本地文件落地成功
- 来源记录与 provenance 完整

## 6. Part 2 Wiki Architecture

### 6.1 Why a Research Wiki Exists
research wiki 是 raw-library 与 argument tree 之间的持久中间层。  
它的职责不是替代原始文献，而是：

- 将原始资料转成可组织、可检索、可复用的知识层
- 按主题、概念、方法、证据和争议建立交叉链接
- 支撑后续论证树生成与大纲生成
- 保留对 raw sources 的可回溯映射

### 6.2 Wiki Layering
Part 2 至少分为两类知识层：

#### Research Evidence Layer
存放：
- 概念页面
- 主题页面
- 方法页面
- 争议 / 矛盾页面
- 证据聚合页面

#### Writing Policy Layer
存放：
- 中文学术写作规范
- 学校格式要求
- 导师 PPT 提炼出的结构与表达偏好
- 常见错误与禁区
- 示例结构 / 章节约束

### 6.3 Wiki Maintenance
wiki 不是一次性生成物，必须支持：
- update：新资料进入后增量更新
- reconcile：发现冲突或重复时合并 / 纠偏
- lint：检查孤立页面、无来源页面、冲突页面、过时页面
- health check：检查链接、来源映射、结构完整性

## 7. Part 3 Argument Tree Architecture

### 7.1 Candidate Generation
Part 3 默认生成 3 份候选 argument tree，而不是单份直出。

### 7.2 Human Selection
系统必须产出：
- 候选比较
- 各候选优缺点
- 选择建议
- 人工反馈入口

未完成人工选择前，不得推进到 Part 4。

### 7.3 Canonical Locking
一旦人工选定，必须锁定：
- canonical `argument_tree.json`
- 选择依据
- 比较记录
- 反馈快照

## 8. Part 4 Outline Architecture

### 8.1 Outline Generation Strategy
MVP 阶段不依赖训练。  
Part 4 采用：

**argument tree + research wiki + writing policy + reference cases**

共同约束 outline 生成。

### 8.2 Reference Cases
参考案例可包括：
- 高质量中文学术论文框架
- 导师推荐范文
- 目标期刊常见结构
- 学校或学院提供的模板

参考案例用于：
- 章节顺序参考
- 结构密度参考
- 表达规范参考
- 论证展开方式参考

### 8.3 Training Policy
训练 / 微调不是 MVP 前提。  
只有当系统积累了足够多的高质量：
- outline
- chapter brief
- review / revision records

之后，才考虑作为升级项。

## 9. Canonical Artifacts
MVP 主链中的 canonical artifacts 为：

- Part 1: `raw-library/metadata.json`, `outputs/part1/authenticity_report.json`
- Part 2: `research-wiki/index.json`
- Part 3: `outputs/part3/argument_tree.json`
- Part 4: `outputs/part4/paper_outline.json`, `outputs/part4/outline_rationale.json`, `outputs/part4/reference_alignment_report.json`
- Part 5: `outputs/part5/manuscript_v2.md`, `outputs/part5/review_matrix.json`, `outputs/part5/review_report.md`, `outputs/part5/revision_log.json`, `outputs/part5/part6_readiness_decision.json`

任何阶段推进均不得绕过 canonical artifacts。

## 10. Stage Gates

### Part 1 Gate
必须满足：
- 检索计划已生成
- 优先来源策略已执行
- 相关性评估已完成
- 真实性校验通过
- 本地资料库落地完成
- 已下载论文清单已生成，并复制到桌面

### Part 2 Gate
必须满足：
- research wiki 页面生成完成
- index 可用
- 来源映射完整
- contradictions / health check 通过基本门槛
- writing policy 层已建立

### Part 3 Gate
必须满足：
- 3 份候选 argument tree 齐备
- comparison 齐备
- human feedback 齐备
- canonical argument tree 已锁定

### Part 4 Gate
必须满足：
- canonical outline 已生成
- outline 与 argument tree 对齐
- reference alignment report 可用
- 无需 `outline_confirmed`；可以自动进入 Part 5

### Part 5 Gate
必须满足：
- `manuscript_v2.md` 已生成且非空
- `review_matrix.json`、`review_report.md`、`revision_log.json`、`part6_readiness_decision.json` 齐备并通过 schema / contract 校验
- Part 5 step artifacts 齐备：chapter briefs、case templates、claim-evidence matrix、citation map、figure plan、open questions、manuscript_v1、review summary、claim risk report、citation precheck
- `~/Desktop/part5_review_report.md` 存在，并与 `outputs/part5/review_report.md` 内容一致
- `~/Desktop/manuscript_v2.md` 存在，并与 `outputs/part5/manuscript_v2.md` 内容一致
- 不存在未登记的 critical blocker
- `part6_readiness_decision.json` 只作为 readiness verdict，不推进 Part 6

## 11. State Management
运行时至少包含以下状态能力：

- 当前阶段记录
- 阶段开始 / 完成时间
- 当前 canonical artifact 状态
- 最近一次失败位置
- repair 记录
- human decision 记录

### State Rules
- 状态损坏不可静默重置
- repair 必须留备份
- 未通过 gate 不得推进
- 回滚必须有显式记录

## 12. Memory Architecture

### 12.1 raw-library
保存原始资料、规范化文本、元数据与 provenance。

### 12.2 research-wiki
保存结构化研究知识与交叉链接。

### 12.3 writing-policy
保存规范、模板、导师资料与表达限制。

### 12.4 process-memory
保存过程决策、评审结论、选择理由、失败与修复记录。

## 13. Validation and Diagnostics
MVP 至少包含：

- schema validation
- artifact presence check
- stage gate validation
- wiki health check
- state diagnostics
- audit / doctor 入口

## 14. ECC Reference Boundary
本项目参考 ECC 的部分包括：
- manifests
- runtime orchestration
- state / audit / doctor
- hooks / diagnostics 的工程思想
- rules / contract first 的方法

本项目**不直接照搬** ECC 的部分包括：
- 软件开发默认 workflow
- coding-oriented agent 角色设计
- TDD / code review 作为核心业务逻辑
- 面向代码库的默认命名与目录假设

换言之，本项目借鉴的是 **ECC 式 harness 思想**，而不是把 ECC 当作论文业务架构本身。

## 15. Next Phase Outputs
本文件之后，应继续派生：

- `manifests/pipeline-stages.json`
- `manifests/source-policy.json`
- `schemas/part1_source_bundle.schema.json`
- `schemas/part2_wiki_bundle.schema.json`
- `schemas/part3_argument_tree.schema.json`
- `schemas/part4_outline.schema.json`
- `schemas/part5_review_matrix.schema.json`
- `schemas/part5_revision_log.schema.json`
- `schemas/part5_readiness_decision.schema.json`
- `AGENTS.md`
- `CLAUDE.md`
