# 论文毁灭者

面向中文学术论文写作的 research-to-manuscript workflow。它不是一次性让 AI 写论文，而是把“选题 intake -> 文献资料库 -> research wiki -> argument tree -> paper outline -> 正文草稿 / review / revision -> 最终定稿包”拆成可校验、可恢复、可审计的阶段。

当前主链已经包含 **Part 1 到 Part 6**。Part 6 是显式授权后的 finalization surface：系统可以生成最终稿、最终审计与 submission package manifest，但不会自动确认人工 gate，也不会执行投稿 / 提交动作。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 cli.py init
python3 cli.py doctor
```

如果需要使用浏览器自动化下载器，请安装 Playwright 浏览器：

```bash
python3 -m playwright install chromium
```

## 开源边界

仓库只提交 workflow harness、规则、schema、测试和本地控制台代码。以下目录用于运行时产物，默认只保留 `.gitkeep`：

- `outputs/`
- `raw-library/`
- `research-wiki/`
- `process-memory/`
- `workspaces/`

不要把论文 PDF、原始文献、导师意见、个人 intake、manuscript 草稿、浏览器缓存或任何账号凭据提交到仓库。

CNKI、万方、维普等来源访问必须遵守各平台条款与所在机构授权。本项目不内置账号、Cookie、token 或绕过访问控制的机制。

CNKI CDP 下载器默认尝试读取本机 Chrome remote debugging endpoint。跨平台或自定义浏览器场景可设置 `CNKI_CDP_ENDPOINT`；如需校验页面上的机构登录文本，可设置 `CNKI_INSTITUTION_PATTERN`。

## License

MIT

## 当前主链

| Part | 目标 | 是否人工确认 | 关键输出 |
|---|---|---:|---|
| Part 1 | 文献检索、下载、本地资料库、真实性校验 | 需要确认 intake | `raw-library/metadata.json`, `outputs/part1/authenticity_report.json` |
| Part 2 | 构建 research wiki 与 writing policy | 不需要 | `research-wiki/index.json` |
| Part 3 | 生成 3 份 argument tree，比较并锁定 canonical tree | 需要选择候选 | `outputs/part3/argument_tree.json` |
| Part 4 | 生成论文大纲三件套 | 不需要 | `outputs/part4/paper_outline.json`, `outline_rationale.json`, `reference_alignment_report.json` |
| Part 5 | 写作输入包、正文初稿、结构化 review 与修订稿 | 不需要 | `outputs/part5/manuscript_v2.md`, `review_report.md`, `revision_log.json` |
| Part 6 | 最终定稿、claim / citation audit、submission package manifest 与最终 readiness 决策 | 需要最终授权和确认 | `outputs/part6/final_manuscript.md`, `claim_risk_report.json`, `citation_consistency_report.json`, `submission_package_manifest.json`, `final_readiness_decision.json` |

当前保留的人工节点只有：

- `intake_confirmed`：确认研究主题和 Part 1 intake 参数。
- `argument_tree_selected`：从 3 份候选 argument tree 中选定 canonical tree。
- `part6_finalization_authorized`：授权从 Part 5 completed handoff 进入 Part 6 finalization。
- `part6_final_decision_confirmed`：确认最终 readiness verdict 与 submission package manifest。

已移除的人工阻断节点：

- Part 4：`outline_confirmed`
- Part 5：`writing_phase_authorized`, `part5_prep_confirmed`, `part5_review_completed`, `manuscript_v2_accepted`

这些旧命令在 CLI 里只作为兼容入口保留，不再阻断流程。

## 用户可见输出

Part 1 已下载论文清单保存在对应阶段目录：

- `outputs/part1/downloaded_papers_table.csv`
- `outputs/part1/downloaded_papers_table.md`
- `outputs/part1/source_quota_report.json`

Part 1 当前资料库配额为 40 篇 accepted sources：CNKI 24-28 篇，英文期刊至少 5 篇，其余来自非 CNKI 补充来源。网页详情页或开放网页全文可用本地 Chrome 的 Obsidian/Web Clipper 插件生成 Markdown，再导入到 `raw-library/web-archives/`。

Part 5 的 review 汇报和最终 Part 5 稿保存在对应阶段目录：

- `outputs/part5/review_report.md`
- `outputs/part5/manuscript_v2.md`

`outputs/` 中的文件就是当前 canonical artifacts，不再额外生成外部副本。

Part 6 的最终稿和交付包保存在对应阶段目录：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`

Part 6 默认只写入 `outputs/part6/`。如需额外导出给用户阅读，可显式设置 `PART6_DESKTOP_DIR`，系统会在该目录写入 `part6_final_manuscript.md`；外部导出文件不是 canonical package。

## 目录说明

| 路径 | 作用 |
|---|---|
| `AGENTS.md` | 项目最高优先级规则、工作流边界和 agent 行为约束 |
| `docs/` | 架构、目标、Part 5 / Part 6 设计说明 |
| `manifests/` | pipeline stage 与 source policy 配置 |
| `runtime/` | pipeline 状态、gate 校验、stage 推进逻辑 |
| `runtime/agents/` | 各 Part 的业务脚本 |
| `schemas/` | canonical JSON artifacts 的 schema |
| `raw-library/` | 原始文献、规范化文本、来源 provenance |
| `research-wiki/` | 研究证据 wiki |
| `writing-policy/` | 写作规范、导师要求、格式规则 |
| `outputs/` | 各阶段产物 |
| `process-memory/` | gate、失败、推进、人工决策等过程记录 |
| `skills/` | agent 可调用的阶段工作说明 |
| `workspaces/` | 隔离 workspace，用于从 intake 派生独立运行空间 |

## 常用命令

初始化与状态：

```bash
python3 cli.py init
python3 cli.py status
python3 cli.py doctor
python3 cli.py audit
```

Part 1：

```bash
python3 cli.py part1-intake
python3 cli.py confirm-gate intake_confirmed --notes "主题与 intake 参数已确认"
python3 cli.py part1-export-table
python3 cli.py part1-archive-web --source-id crossref_2026_001 --url "https://doi.org/..." --from-obsidian page.md
python3 cli.py validate part1
python3 cli.py advance part1
```

`confirm-gate intake_confirmed` 会创建或复用隔离 workspace，并自动在该 workspace 中启动 `runtime/agents/part1_runner.py`。如果只想确认 intake 和创建 workspace，不立即运行 Part 1，可加 `--no-auto-run-part1`。

Part 2：

```bash
python3 cli.py part2-generate
python3 cli.py part2-health
python3 cli.py validate part2
python3 cli.py advance part2
```

Part 3：

```bash
python3 cli.py part3-seed-map
python3 cli.py part3-generate
python3 cli.py part3-compare
python3 cli.py part3-refine
python3 cli.py part3-review
python3 cli.py part3-select --candidate-id candidate_problem_solution --notes "选择理由"
python3 cli.py validate part3
python3 cli.py advance part3
```

Part 4：

```bash
python3 cli.py part4-generate
python3 cli.py part4-check
python3 cli.py validate part4
python3 cli.py advance part4
```

Part 5：

```bash
python3 cli.py part5-prep
python3 cli.py part5-draft
python3 cli.py part5-review
python3 cli.py part5-revise
python3 cli.py part5-check
python3 cli.py validate part5
python3 cli.py advance part5
```

Part 6：

```bash
python3 cli.py part6-precheck
python3 cli.py part6-authorize --notes "授权进入 Part 6 finalization"
python3 cli.py part6-finalize --step all
python3 cli.py part6-check
python3 cli.py part6-confirm-final --notes "最终状态：内部评阅"
python3 cli.py validate part6
python3 cli.py advance part6
```

验证：

```bash
python3 -m pytest -q
python3 cli.py validate part5
python3 cli.py validate part6
```

workspace 验证：

```bash
cd workspaces/ws_NNN
python3 -m pytest -q
```

## Part 6 状态

Part 6 当前在 active `STAGE_ORDER` 中，但它不是自动投稿系统：

- `status` / `get_next_action()` 可以在 Part 5 gate 通过后推荐 `part6-authorize`。
- `outputs/part5/part6_readiness_decision.json` 只表达 Part 5 handoff readiness，不等于授权。
- `part6-authorize` 会记录当前 Part 5 handoff fingerprints；授权后如果 Part 5 handoff artifacts 变化，必须重新授权。
- `part6-finalize --step all` 生成最终稿、审计报告、manifest 与 final readiness decision。
- `part6-confirm-final` 只记录人工最终决策，不执行 submission。
- `formal_submission_ready` 也只是 readiness verdict，不是自动提交授权。

## 当前文档入口

- [docs/01_build_target.md](docs/01_build_target.md)：历史基线目标文档，不作为当前唯一 workflow truth source。
- [docs/02_architecture.md](docs/02_architecture.md)：历史基线架构文档，Part 6 等当前状态以 manifest / runtime / Part6 MVP 文档为准。
- [docs/part5_architecture.md](docs/part5_architecture.md)：Part 5 写作、review、revision 与本地产物合同。
- [docs/part6_mvp_architecture.md](docs/part6_mvp_architecture.md)：当前 Part 6 MVP finalization surface、gate、artifact 与 CLI 合同。
- [docs/part6_architecture.md](docs/part6_architecture.md)：Part 6 总体架构说明，当前实现以 MVP 文档和 runtime gate 为准。
- [docs/llm_agent_architecture.md](docs/llm_agent_architecture.md)：LLM agent 角色与 deterministic runtime script 的职责分层。
- [docs/part3_argumentagent_architecture.md](docs/part3_argumentagent_architecture.md)：Part 3 argumentagent 边界。

## 核心原则

- CNKI 是中文主检索第一优先来源，英文来源只能作为补充层。
- Part 1 accepted sources 必须满足 40 篇总量、CNKI 60%-70% 与英文期刊至少 5 篇。
- 所有进入主链的来源必须完成真实性校验和来源标注。
- 不得用非 canonical artifacts 推进阶段。
- research evidence 与 writing policy 必须物理分离。
- Part 5 可以自动写作、review 和 revision，但不能虚构证据、吞掉 blocker 或把 readiness decision 当作 Part 6 授权。
- Part 6 可以生成最终交付包，但必须保留人工 finalization authorization 与 final decision，不得自动投稿。
