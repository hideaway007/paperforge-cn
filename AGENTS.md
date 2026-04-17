# AGENTS.md — 论文毁灭者

## Project Identity
- **Project**: 论文毁灭者
- **Domain**: 全中文学术写作 research-to-manuscript workflow
- **Historical Baseline Docs**: `docs/01_build_target.md`, `docs/02_architecture.md` 是不可改的原始设计文档 / 历史基线，不再作为无条件当前 workflow truth source
- **Current Effective Workflow Sources**: 当前生效 workflow 以 `AGENTS.md`、`manifests/pipeline-stages.json`、`docs/part5_architecture.md`、`docs/part6_mvp_architecture.md`、`docs/part6_docx_format_export_architecture.md` 与 runtime gate 校验为准
- **2026-04-16 User-Approved Override**: 用户已批准 Part 4 / Part 5 自动化取消人工 gate；该 override 覆盖 `docs/01_build_target.md` 与 `docs/02_architecture.md` 中旧的 HITL / MVP 范围表述，但不修改这两个历史基线文档本身
- **MVP Scope**: Part 1（文献收集）→ Part 2（Research Wiki）→ Part 3（Argument Tree）→ Part 4（Paper Outline）→ Part 5 MVP（Draft + Review + Revision）→ Part 6 gated finalization（Final Manuscript + Audit + Package Decision）

---

## Architecture Layers

| Layer | 职责 | 目录 |
|-------|------|------|
| Domain Workflow Layer | 业务逻辑（检索、wiki、论证、大纲） | `raw-library/`, `research-wiki/`, `outputs/` |
| Research Harness Layer | 控制面（manifest、state、gate、audit、HITL） | `runtime/`, `process-memory/`, `manifests/` |
| Provider / Tool Layer | 外部资源接入（CNKI、万方、Crossref 等） | 由 `manifests/source-policy.json` 配置 |

---

## Immutable Constraints

### Source Policy
- CNKI 为**第一优先来源**，任何阶段不可绕过
- Part 1 最终 accepted sources 目标为 40 篇；CNKI 来源必须不低于 60% 且不高于 70%（即 24-28 篇），英文期刊来源必须至少 5 篇，其余来源必须来自非 CNKI 的可验真补充来源
- Part 1 检索计划必须先执行聚焦查询，再执行宽泛扩展；聚焦查询必须由已确认 intake 的研究对象、方法、教学、应用或案例锚点生成
- 为保留现有合同兼容性，`cnki_q1_1` 必须继续存在，但它必须绑定当前 confirmed intake 的聚焦主检索，不得被写成大 OR 式泛化查询，也不得复用旧题目的固定检索词
- `cnki_q1_1` 的检索表达必须从当前 confirmed intake 的研究对象与方法 / 教学 / 应用 / 案例锚点动态生成，不得保留或注入任何旧论文主题模板
- 宽泛扩展只能在聚焦查询完成、记录检索结果与召回不足后补充使用，不得覆盖或替代 CNKI 聚焦主检索链
- 英文来源只能作为补充层，不能无约束替代中文主检索策略
- 所有来源进入主链前必须经过去重、真实性校验与来源标注
- 来源策略配置在 `manifests/source-policy.json`，不得在运行时被动态覆盖

### Part 1 Relevance Policy
- Part 1 的最前提是系统先发出 intake request：每次启动 `part1`，必须生成或刷新 `outputs/part1/intake_request.md` 与 `outputs/part1/intake_template.json`，提示用户填写 `outputs/part1/intake.json`
- 用户填写并确认 `intake_confirmed` 后，系统必须自动创建或复用一个隔离 workspace（`workspaces/ws_NNN/`），把已确认 intake 复制到该 workspace，在 workspace 内记录 `intake_confirmed`，并自动启动该 workspace 的 Part 1 runner；只有显式使用 `--no-auto-run-part1` 时才允许只创建 workspace 不运行
- 隔离 workspace 只复制 harness、规则、脚本与已确认 intake；不得复制 root 项目的 raw-library、research-wiki、outputs、process-memory 等研究产物，避免新论文运行污染 root 上下文
- 隔离 workspace 应复制已有 baseline `writing-policy/` 规则层；该层只作为结构与表达约束，不属于 research evidence，不会污染研究证据层
- 未填写并确认 `intake_confirmed`、且未生成隔离 workspace 前，Part 1 不得执行检索计划、下载、相关性评分、真实性校验或资料库注册
- 相关性评分的 `tier_A` 锚点必须从 confirmed intake 派生，并同时覆盖研究对象与研究问题场景；不得仅凭单一地域词、文化词或泛传统文化词进入主证据链
- `tier_A` 必须同时命中当前 intake 的研究对象锚点与研究问题场景锚点；例如某一研究主题应同时命中其对象锚点与其场景、方法、应用或案例锚点，不能复用任何旧论文题目的固定锚点组合
- 相关性评分必须显式记录命中的 confirmed intake 锚点与降级原因，避免旧题目规则污染新论文运行

### Authenticity
- 不得跳过真实性校验；校验失败必须记录至 `outputs/part1/excluded_sources_log.json`
- 不得用非 canonical artifacts 推进阶段
- 不得在状态损坏时静默修复，必须显式报告

### Human-in-the-Loop Gates
以下节点仍为必须人工决策的阻断 gate，**不得被任何 agent 或脚本自动跳过**：

| Gate ID | 描述 | 阶段位置 |
|---------|------|----------|
| `intake_confirmed` | 研究主题与结构化 intake 关键参数已由用户确认 | Part 1 检索执行前 |
| `argument_tree_selected` | 候选 argument tree 已由用户选定 | Part 3 canonical lock 前 |
| `part6_finalization_authorized` | 用户已授权从 Part 5 handoff 进入 Part 6 finalization | Part 6 final package 生成前 |
| `part6_final_decision_confirmed` | 最终 readiness verdict 与 submission package manifest 已由用户确认 | Part 6 completion 前 |

Part 4 与 Part 5 不再设置人工阻断 gate。Part 4 生成 canonical outline 三件套并通过校验后，可自动进入 Part 5。Part 5 按 prep → draft → review → revise 自动运行，所有产物保存在 `outputs/part5/`，不得自动进入 Part 6。
Part 6 必须由用户显式授权后才可运行 finalization，并且 final decision 仍需用户最终确认；Part 6 不执行投稿或提交动作。
Part 6 docx 格式导出不新增 human gate；若用户要求最终 docx，应在 `part6_final_decision_confirmed` 前生成项目内 docx 与桌面副本，并让 submission package manifest 记录这些导出文件。

### Knowledge Layering
- Research evidence layer（`research-wiki/`）与 writing policy layer（`writing-policy/`）**必须物理分离**
- `raw-library/` 中的原始资料**不得被改写**；规范化文本放 `raw-library/normalized/`
- `research-wiki/` 是持久、累积的研究层，不是 `raw-library/metadata.json` 的卡片化副本
- 除 canonical `research-wiki/index.json` 外，Part 2 必须维护 `research-wiki/index.md`、`research-wiki/log.md`、`research-wiki/update_log.json` 与 `research-wiki/contradictions_report.json`
- Part 2 必须生成 source digest / evidence aggregation / concept / topic / method / synthesis 类页面，用于承载来源消化、证据聚合、概念解释、专题梳理、方法抽取与综合判断
- 每个 `research-wiki/` 页面必须包含来源映射、交叉链接与变更依据；跨来源冲突必须进入 `research-wiki/contradictions_report.json`
- `research-wiki/` 更新必须保留来源映射与变更依据，记录至 `research-wiki/update_log.json`

---

## Canonical Artifacts

| Part | Canonical Artifacts | Gate 校验条件 |
|------|---------------------|--------------|
| Part 1 | `raw-library/metadata.json`<br>`outputs/part1/authenticity_report.json` | 真实性校验通过，本地落地完成 |
| Part 2 | `research-wiki/index.json` | index 可用，来源映射完整，health check 通过 |
| Part 3 | `outputs/part3/argument_tree.json` | human selection 完成且锁定，comparison 齐备 |
| Part 4 | `outputs/part4/paper_outline.json` | outline 与 argument tree 对齐，rationale 与 reference alignment report 可用，可自动进入 Part 5 |
| Part 5 | `outputs/part5/manuscript_v2.md`<br>`outputs/part5/review_matrix.json`<br>`outputs/part5/review_report.md`<br>`outputs/part5/revision_log.json`<br>`outputs/part5/part6_readiness_decision.json` | review + revision 齐备，critical blocker 已登记，review report 与 final manuscript 保存在 `outputs/part5/`，Part 6 readiness 仅表达判断不推进 |
| Part 6 | `outputs/part6/final_manuscript.md`<br>`outputs/part6/claim_risk_report.json`<br>`outputs/part6/citation_consistency_report.json`<br>`outputs/part6/submission_package_manifest.json`<br>`outputs/part6/final_readiness_decision.json` | 已授权 finalization，最终稿 / claim audit / citation audit / package manifest 齐备，final decision 已由用户确认，且不执行 submission |

任何阶段推进均**不得绕过 canonical artifacts**。

---

## Stage Gate Rules
- 未通过当前阶段 gate，不得推进至下一阶段
- gate 校验结果必须记录至 `process-memory/`
- 状态损坏时必须显式报告，不得静默重置
- 回滚必须有显式记录，不得覆盖原始状态文件

---

## What AI Can Do

| 允许的 AI 行为 |
|----------------|
| 生成检索计划草稿 |
| 生成 Part 1 intake request，并提示用户填写 intake |
| 在 intake 确认后创建隔离 workspace，把该 intake 带入 workspace，并自动启动 workspace 内 Part 1 runner |
| 执行多源检索并进行相关性评分 |
| 在 Part 1 下载完成后导出已下载论文清单到 `outputs/part1/` |
| 生成 wiki 页面草稿 |
| 生成 3 份候选 argument tree |
| 提供候选比较与选择建议 |
| 生成并校验 canonical paper outline 三件套 |
| 自动运行 Part 5 写作输入包、保守正文 scaffold、结构化 review、revision、用户汇报与最终稿本地输出，以及 Part 6 readiness decision |
| 在用户授权后运行 Part 6 finalization、claim / citation audit、submission package manifest 与 final readiness decision 生成；不得自动确认 final decision |

## What Requires Human Decision

| 必须人工介入的节点 |
|-------------------|
| 确认研究主题与 intake 关键参数 |
| 选定并锁定 canonical argument tree |
| 改变 MVP 边界或不可变约束 |
| 授权进入 Part 6 finalization |
| 确认 Part 6 final readiness verdict 与 submission package manifest |

---

## State Rules
- 当前阶段 + 开始/完成时间必须记录在 `runtime/state.json`
- 最近一次失败位置必须记录
- repair 必须留备份，不得覆盖原始状态文件
- 回滚必须有显式记录在 `process-memory/`

---

## Naming & Directory Conventions

```
raw-library/papers/{source_id}.pdf
raw-library/web-archives/{source_id}.md
raw-library/normalized/{source_id}.txt
raw-library/provenance/{source_id}.json

research-wiki/index.json
research-wiki/index.md
research-wiki/log.md
research-wiki/update_log.json
research-wiki/contradictions_report.json
research-wiki/pages/source-digest/{source_id}.md
research-wiki/pages/evidence-aggregation/{topic_id}.md
research-wiki/pages/concepts/{concept_id}.md
research-wiki/pages/topics/{topic_id}.md
research-wiki/pages/methods/{method_id}.md
research-wiki/pages/synthesis/{synthesis_id}.md

writing-policy/rules/{rule_id}.md
writing-policy/style_guides/{guide_id}.md
writing-policy/reference_cases/{case_id}.md
writing-policy/rubrics/{rubric_id}.md

outputs/part1/{artifact_name}.json
outputs/part1/intake_request.md
outputs/part1/intake_template.json
outputs/part1/workspace_manifest.json
outputs/part1/supplementary_sources_task.md
outputs/part1/source_quota_report.json
outputs/part1/downloaded_papers_table.csv
outputs/part1/downloaded_papers_table.md
outputs/part3/candidate_argument_trees/{candidate_id}.json
outputs/part3/argument_tree.json           ← canonical
outputs/part4/paper_outline.json           ← canonical
outputs/part4/outline_rationale.json
outputs/part4/reference_alignment_report.json

outputs/part5/chapter_briefs/{section_id}.md
outputs/part5/case_analysis_templates/{template_id}.md
outputs/part5/claim_evidence_matrix.json
outputs/part5/citation_map.json
outputs/part5/figure_plan.json
outputs/part5/open_questions.json
outputs/part5/manuscript_v1.md             ← intermediate
outputs/part5/review_matrix.json           ← canonical
outputs/part5/review_report.md             ← canonical user-facing report
outputs/part5/review_summary.md
outputs/part5/claim_risk_report.json
outputs/part5/citation_consistency_precheck.json
outputs/part5/revision_log.json            ← canonical
outputs/part5/manuscript_v2.md             ← canonical final Part 5 draft
outputs/part5/part6_readiness_decision.json ← canonical readiness verdict only; does not advance Part 6
outputs/part6/final_manuscript.md          ← canonical finalization draft
outputs/part6/claim_risk_report.json       ← canonical final claim audit
outputs/part6/citation_consistency_report.json ← canonical final citation audit
outputs/part6/submission_package_manifest.json ← canonical package manifest; not submission authorization
outputs/part6/final_readiness_decision.json ← canonical final readiness verdict
outputs/part6/final_manuscript.docx        ← Part 6 formatted package export, non-evidence
outputs/part6/docx_format_report.json      ← Part 6 docx format validation report
~/Desktop/{论文题目}.docx                  ← user-facing desktop copy, not canonical

process-memory/{YYYYMMDD}_{event_type}.json
workspaces/ws_NNN/workspace_manifest.json
workspaces/ws_NNN/outputs/part1/intake.json

skills/{skill-name}/SKILL.md
skills/{skill-name}/agents/openai.yaml

runtime/agents/part2_{business_step}.py
runtime/agents/part3_{business_step}.py
runtime/agents/part4_{business_step}.py
runtime/agents/part5_{business_step}.py
runtime/agents/part6_{business_step}.py
```

### Workflow Extension Conventions
- `skills/` 保存项目内可迁移的 workflow skills；新增 skill 必须用 `skill-creator` 初始化，目录名使用小写 hyphen-case。
- `skills/` 只放面向论文 workflow 的业务技能，不放 ECC 的 coding-oriented agent 角色。
- `runtime/agents/part1_intake.py` 负责生成 Part 1 intake request；它不得自动确认 `intake_confirmed`，也不得覆盖已填写的 `outputs/part1/intake.json`。
- `scripts/new_workspace.py --intake outputs/part1/intake.json --confirm-intake` 负责从已确认 intake 创建隔离 workspace；重复执行同一 intake hash 时必须复用既有 workspace，不得无意义制造多个上下文副本。自动命名必须使用现有最大 `ws_NNN` 编号 + 1，不得回填已删除或缺失的旧编号。`python3 cli.py confirm-gate intake_confirmed ...` 在 bootstrap 后必须自动进入该 workspace 启动 `runtime/agents/part1_runner.py`，除非显式传入 `--no-auto-run-part1`。
- `outputs/part1/workspace_manifest.json` 记录 root intake 与隔离 workspace 的映射；workspace 自身必须有 `workspace_manifest.json` 说明来源、intake hash 与 isolation rule。
- `runtime/agents/part1_library_table_exporter.py` 负责导出 Part 1 已下载论文清单；表格从 `raw-library/provenance/` 与 `raw-library/metadata.json` 读取，不得替代 canonical `raw-library/metadata.json`。
- Part 1 检索计划必须先生成并执行 CNKI 聚焦查询；`cnki_q1_1` 必须绑定当前 confirmed intake 的研究对象与方法 / 教学 / 应用 / 案例锚点，不得退化为泛化大 OR 查询，也不得复用旧题目的固定检索词。
- Part 1 相关性评分必须从当前 confirmed intake 派生 `tier_A` 锚点；任何旧题目锚点都不得作为当前论文的必要条件。
- `runtime/agents/part1_download_queue_builder.py` 负责从 `outputs/part1/search_results_candidates.json` 与可选 `outputs/part1/researchagent_search_result_triage.json` 生成 `outputs/part1/download_queue.json`；下载前 triage 只提高候选排序与下载命中率，不替代后续相关性评分、真实性校验或资料库注册 gate。
- `part1-search-result-triage` 是 `researchagent` 的下载前候选审查 skill；它只能输出 sidecar recommendation，不得写 `download_queue.json`、不得新增 `source_id` / citation / case fact / research conclusion、不得确认 human gate。
- Part 1 下载 manifest 校验通过后，必须生成 `outputs/part1/downloaded_papers_table.csv` / `.md`；资料库注册完成后应刷新该表格以补充 relevance、authenticity 与 accepted 状态。
- Part 1 资料库注册必须生成 `outputs/part1/source_quota_report.json`；未满足 40 篇总量、CNKI 24-28 篇、英文期刊不少于 5 篇时，不得写入或推进 canonical `raw-library/metadata.json`。
- 网页详情页或开放网页全文可作为本地落地 artifact 进入 `raw-library/web-archives/{source_id}.md`；优先由本地 Google Chrome 的 Obsidian/Web Clipper 插件生成 Markdown，再由 `runtime/agents/web_markdown_archiver.py` 导入仓库并写 provenance。Chrome 插件调用本身不作为 deterministic gate；deterministic 边界是 Markdown 文件导入、路径校验、provenance 与真实性校验。
- Codex LLM agent role 与 `runtime/agents/*.py` 不是同一层：LLM agent 负责判断、综合、批判和写作建议；runtime script 负责文件落盘、schema 校验、state/gate 写入和 canonical lock。
- 当前启用的论文 workflow LLM roles 为 `researchagent`、`wikisynthesisagent`、`argumentagent`、`outlineagent`、`writeagent` / `writeragent`、`claimauditor`、`citationauditor`；角色说明见 `docs/llm_agent_architecture.md`。
- 所有 LLM agent 均不得确认 human gate、不得写 `runtime/state.json`、不得绕过 deterministic validation、不得把 writing-policy 或作者风格材料当作 research evidence、不得新增不可回溯的 source_id / citation / case fact / data / research conclusion。
- `researchagent` 只负责 Part 1/2 的检索策略、相关性判断、source triage 与研究缺口建议；不得绕过 CNKI 优先策略、真实性校验、去重、provenance 或 intake/workspace gate。
- `runtime/agents/part2_*.py` 保存 Part 2 Research Wiki 业务 agent 脚本；命名必须表达 wiki 生成、来源映射、health check、validate 或 advance 等论文流程步骤。
- Part 2 自动化只能从 Part 1 canonical artifacts 与 `raw-library/metadata.json` 读取 research evidence，不得从 `writing-policy/`、临时草稿或未 canonical 的中间产物补充证据。
- Part 2 自动化不得把 `writing-policy/` 内容混入 `research-wiki/`；writing policy 只能作为写作规则层，不能作为 research evidence 层来源。
- Part 2 自动化不得引用未进入 `raw-library/metadata.json` 的 `source_id`；发现缺失来源时必须记录为校验失败，不得静默补造或跳过。
- Part 2 自动化必须把 `research-wiki/` 作为持久累积研究层维护；不得只生成 metadata 卡片或一次性摘要。
- Part 2 自动化除生成 canonical `research-wiki/index.json` 外，还必须维护 `research-wiki/index.md`、`research-wiki/log.md`、`research-wiki/update_log.json` 与 `research-wiki/contradictions_report.json`。
- Part 2 自动化必须生成 source digest、evidence aggregation、concept、topic、method、synthesis 类页面；页面必须包含 `source_ids`、`file_path`、`page_type`、来源映射、交叉链接、变更依据，且 `source_mapping_complete=true`。
- 自动生成 `research-wiki/index.json` 前，必须保证每个 wiki 页面具备 `source_ids`、`file_path`、`page_type`、来源映射、交叉链接、变更依据，且 `source_mapping_complete=true`。
- Part 2 自动化不得自动推进 Part 3；必须通过 part2-health/validate/advance 的 gate 流程，且 gate 结果记录至 `process-memory/` 后才能进入 Part 3。
- `wikisynthesisagent` 只负责 Part 2 的 research wiki 综合判断与页面草案建议；canonical `research-wiki/index.json`、source mapping、health check 与 update log integrity 仍由 deterministic Part 2 自动化负责。
- `runtime/agents/part3_*.py` 保存 Part 3 业务 agent 脚本；命名必须表达论文流程步骤，如 candidate generation、comparison、human selection。
- Part 3 允许使用 LLM `argumentagent` 提升候选论证树质量；`argumentagent` 只负责候选论证设计、比较、压力测试和 refined candidate proposal，不拥有 canonical artifact。
- Part 3 deterministic scripts 继续负责 seed map、schema 校验、source/wiki 回溯、候选文件落盘和 human selection 后的 canonical lock。
- `argumentagent` 必须使用 `part3-argument-generate`、`part3-argument-compare`、`part3-argument-stress-test`、`part3-argument-refine` 与 `part3-human-selection` 的边界；不得绕过这些 skill 直接写 canonical。
- 新增 Part 3 自动化不得直接写入 canonical `outputs/part3/argument_tree.json`，除非用户已经通过 human selection 接口明确选择候选树。
- `runtime/agents/part4_*.py` 保存 Part 4 业务 agent 脚本；新增 outline 生成必须同时产出 `paper_outline.json`、`outline_rationale.json` 与 `reference_alignment_report.json`。
- `outlineagent` 只负责 Part 4 的章节论证路线、衔接逻辑和 alignment risk 判断；不得修改 Part 3 canonical argument tree，不得绕过 Part 4 validation，不得手动标记 Part 4 complete。
- `writing-policy/reference_cases/` 保存中文论文参考案例，`writing-policy/rubrics/` 保存章节结构 rubric；两者只约束结构与表达，不得作为 research evidence 混入 `research-wiki/`。
- Part 4 不再设置 `outline_confirmed` 人工 gate；三份 outline artifacts 通过校验后即可作为 Part 4 canonical completion，并允许自动进入 Part 5。
- `part4-outline-confirm` 仅作为旧流程兼容 skill 保留，不属于正常 workflow surface。
- `runtime/agents/part5_*.py` 保存 Part 5 业务 agent 脚本；MVP 允许一个脚本支持多个 step，正常流程应自动执行 prep → draft → review → revise，并把产物保存在 `outputs/part5/`。
- `writeagent` / `writeragent` 是 Codex LLM 写作角色，不等同于 `runtime/agents/part5_*.py` 或 `runtime/agents/part6_*.py`；它只负责学术写作、保守修订、作者风格约束和语体收束，不得新增研究事实或直接写 review/audit/decision/state 产物。
- `claimauditor` 与 `citationauditor` 是 Part 5/6 风险审计 LLM roles；它们只能输出审计判断或由对应 skill 允许的 report/fragments，不得直接改稿、不得新增来源、不得写 readiness decision、不得自动确认 Part 6 human gates。
- Part 5 不再设置 `writing_phase_authorized`、`part5_prep_confirmed`、`part5_review_completed` 或 `manuscript_v2_accepted` 人工 gate；review/revision artifacts 仍必须完整生成并校验。
- `manuscript_v1.md` 只能作为中间稿，不得作为 Part 5 canonical artifact 或 Part 6 handoff。
- `part6_readiness_decision.json` 只能表达 readiness verdict，不得自动授权或推进 Part 6。

---

## Prohibited at All Times
- 跳过相关性评估
- 绕过来源优先级策略
- 跳过真实性校验
- 用非 canonical artifacts 推进阶段
- 将 writing policy 材料混入 research evidence 层
- 将格式模板或 docx 导出产物混入 research evidence 层
- 在没有 human confirmation 的情况下推进 Part 1 intake 或 Part 3 argument tree selection
- 自动进入 Part 6，或把 `part6_readiness_decision.json` 当作 Part 6 授权
- 静默修复状态损坏
- 修改 `docs/01_build_target.md` 或 `docs/02_architecture.md` 的内容

---

## What NOT to Change Without Explicit User Approval
- `docs/01_build_target.md` 与 `docs/02_architecture.md` 的任何内容
- Immutable Constraints 列表
- Stage gate 定义
- Human-in-the-loop 节点列表
- Canonical artifact 路径与 schema
