# 01 Build Target

## 1. Project Name
论文毁灭者

## 2. Project Goal
本项目旨在构建一套面向**全中文学术写作环境**的 research-to-manuscript workflow 系统。系统应能从研究主题出发，完成：

- 研究主题输入与结构化 intake
- 文献检索与优先来源路由
- 文献下载、本地落地与真实性校验
- research wiki 构建与维护
- argument tree 生成、比较与人工选择
- canonical paper outline 生成
- Part 5 写作输入包、正文初稿、结构化 review、保守修订与桌面导出
- Part 6 readiness 判断，但不自动进入 Part 6

本项目不是一次性 prompt，而是一套可重复运行、可校验、可恢复、可审计的多阶段工作流。

## 3. Why This Project Exists
当前 AI 辅助论文写作常见问题包括：

- 资料来源不稳定，检索结果质量波动大
- 引用真实性不足，容易混入伪引文或低可信来源
- 上下文容易丢失，研究信息难以长期积累和复用
- 论证形成过程不可追踪，后续审查和修改成本高
- 不同阶段产物之间缺乏清晰契约，难以复用和回溯
- 中文写作规范、导师偏好和学校要求难以稳定注入流程

论文毁灭者的目标，是把“搜资料 → 建知识层 → 产出论证 → 形成框架 → 写作修订”变成一条长期可迭代的主链，而不是一次性对话式输出。

## 4. MVP Scope
本期 MVP 必须覆盖以下能力：

### 4.1 Part 1: 文献检索与资料库构建
- 从用户提供的研究主题与结构化 intake 出发生成检索计划
- 支持**相关性驱动的检索**
- 支持**中文优先**的来源策略，**CNKI 为默认第一优先来源**
- 支持接入其他中文学术数据库 / 权威来源
- 支持英文补充检索策略，用于补充方法、国际讨论与前沿进展
- 完成文献下载、本地落地、统一元数据记录与真实性校验

### 4.2 Part 2: Research Wiki 构建
- 基于已验真的资料库构建 research wiki
- 将 raw-library 与后续 argument tree / outline 之间建立持久中间层
- 支持 wiki 的更新、维护、校对与健康检查
- 支持将**中文学术论文规范、导师课程 PPT、写作要求**纳入单独的写作规则层，而不与研究证据混淆

### 4.3 Part 3: Argument Tree
- 生成 3 份候选 argument tree
- 提供比较结果
- 保留人工选择与反馈节点
- 产出 canonical `argument_tree.json`

### 4.4 Part 4: Paper Outline
- 基于选中的 argument tree 生成 canonical paper outline
- 在 MVP 阶段支持基于**参考案例 + 写作规范**的框架生成
- 允许使用中文论文样例、导师规范资料、章节结构 rubric 作为约束输入
- 不以模型训练为前提
- Part 4 不再设置 `outline_confirmed` 人工 gate；outline 三件套通过校验后可自动进入 Part 5

### 4.5 Part 5: Draft, Review and Revision
- 基于 Part 4 canonical outline 自动生成章节 brief、案例分析模板、claim-evidence matrix、citation map、figure plan 与 open questions
- 生成保守正文初稿 `outputs/part5/manuscript_v1.md`
- 对初稿执行结构、论证、证据、引用、写作规范与研究债务 review
- 生成面向用户的 `outputs/part5/review_report.md`，并复制到 `~/Desktop/part5_review_report.md`
- 基于 review 生成 `outputs/part5/revision_log.json` 与 canonical final Part 5 draft `outputs/part5/manuscript_v2.md`
- 将最终稿复制到 `~/Desktop/manuscript_v2.md`
- 生成 `outputs/part5/part6_readiness_decision.json`，但只表达 readiness，不自动推进 Part 6

## 5. Out of Scope
本期明确不做：

- 全自动最终投稿
- 自动进入 Part 6 或自动定稿提交
- 过度复杂的多 agent 并发系统
- 一开始就做满所有 hooks、commands、rules
- 一开始就引入训练 / 微调作为核心依赖
- 把预印本、网页摘要或低可信内容默认当作强证据
- 将导师 PPT / 学校规范与研究证据混作同一层知识

## 6. Immutable Constraints
以下规则不可被 AI 擅自改动：

### 6.1 检索与来源
- 不得跳过相关性评估
- 不得绕过预设的数据源优先级策略
- 在全中文学术写作场景下，CNKI 为默认第一优先来源
- 英文来源只能作为补充层，不能无约束替代中文主检索策略

### 6.2 真实性与工件
- 不得跳过真实性校验
- 不得用非 canonical artifacts 推进阶段
- 不得把草稿误当最终稿
- 不得在状态损坏时静默修复

### 6.3 人工节点
- 不得跳过 argument tree 的人工选择
- Part 4 大纲确认不再是人工阻断点；不得把缺少 `outline_confirmed` 视为失败
- Part 5 写作、review 与 revision 不再设置人工阻断点；不得要求 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted`
- 不得自动进入 Part 6；Part 6 必须保持 deferred，除非用户另行明确授权恢复

### 6.4 知识分层
- 研究证据层与写作规范层必须分离
- raw sources 不得被随意改写
- research wiki 允许更新，但必须保留来源映射与变更依据

## 7. Success Criteria
本期 MVP 视为成功，至少满足以下条件：

### 7.1 Part 1 Success
- 系统能够从研究主题出发，稳定生成结构化检索计划
- 能完成中文优先、英文补充的文献检索
- 能从优先来源中产出足量且高相关的候选文献
- 最终进入资料库的文献已完成真实性校验并成功本地落地

### 7.2 Part 2 Success
- 能生成可检索的 research wiki
- research wiki 能作为 raw-library 与 argument tree 之间的稳定中间层
- wiki 具备更新、维护、校对或健康检查能力
- 导师 PPT / 中文学术规范资料能作为独立写作规则层接入

### 7.3 Part 3 Success
- 能生成 3 份候选 argument tree
- 能提供候选比较结果
- 能完成人工选择并锁定 canonical `argument_tree.json`

### 7.4 Part 4 Success
- 能生成可进入正文写作的 canonical `paper_outline.json`
- 生成的大纲能够回溯到 argument tree 与 research wiki
- 大纲生成能参考中文论文案例与写作规范，而不依赖训练
- 大纲通过校验后可直接支撑 Part 5，不需要人工确认 gate

### 7.5 Part 5 Success
- 能生成完整写作输入包、`manuscript_v1.md`、结构化 review artifacts、`review_report.md`、`revision_log.json` 与 `manuscript_v2.md`
- `review_report.md` 已复制到 `~/Desktop/part5_review_report.md`
- `manuscript_v2.md` 已复制到 `~/Desktop/manuscript_v2.md`
- 所有 critical blocker 已登记；不确定 claims 被降级、标注或进入 blocker
- `part6_readiness_decision.json` 只表达 readiness，不触发 Part 6

## 8. Failure Conditions
即使系统能跑，只要出现以下情况，也视为失败：

- 文献真实性不足但仍继续推进
- 相关性明显不足但仍计入主资料库
- 阶段之间交接产物不清晰、不可复用或无法校验
- research wiki 不能支撑 argument tree 的回溯
- argument tree 与 paper outline 不能回溯到资料依据
- Part 5 review report 或 final draft 未按固定文件名导出到桌面
- Part 5 把未核验事实写成确定结论，或吞掉 critical blocker
- 系统自动推进 Part 6 或把 readiness decision 当作 Part 6 授权
- 写作规范层与研究证据层混淆
- 系统一旦中断就无法恢复、无法审计或无法解释推进依据

## 9. Human Decisions Required
以下节点必须人工拍板，不能自动跳过：

- 研究主题与范围边界确认
- 结构化 intake 的关键参数确认（如时间范围、学科范围、排除项）
- 候选 argument tree 的最终选择
- 改变 Part 6 deferred 状态或授权进入 Part 6
- 改变 MVP 边界、不可变约束或 canonical artifact 合同

## 10. Preferred Source Strategy
### 10.1 Chinese Priority Sources
默认优先来源为：

1. CNKI（第一优先）
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

### 10.3 Source Policy
- 中文来源用于构建中文写作主证据层
- 英文来源用于补充方法、国际背景、前沿趋势与术语映射
- 所有来源进入主链前都必须经过统一去重、真实性校验与来源标注

## 11. Relevance Policy
Part 1 的检索不得只按关键词粗暴抓取。检索结果必须综合考虑：

- 研究主题与研究问题匹配度
- 标题 / 摘要 / 关键词命中
- 方法、任务、对象的一致性
- 时间范围与研究阶段适配度
- 中文主写作场景下的可引用性
- 来源可信度与可落地性

## 12. Phase 1 Output
Phase 1 的正式产出包括：

- `docs/01_build_target.md`
- `docs/02_architecture.md`

后续 `manifests/`、`schemas/`、`runtime/`、`AGENTS.md`、`CLAUDE.md` 均需服从本文件定义的目标、边界、约束与成功标准。

当前生效主链为 Part 1 到 Part 5。`docs/02_architecture.md`、`docs/part5_architecture.md`、`manifests/pipeline-stages.json` 与 `runtime/pipeline.py` 共同定义当前可运行合同；Part 6 文档只作为 deferred / future design 参考。
