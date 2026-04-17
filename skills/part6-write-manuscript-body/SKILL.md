---
name: part6-write-manuscript-body
description: 学术研究 workflow Part 6 正文写作 agent：当用户要求「真正的 Part 6 写作 agent」「写 final manuscript 正文」「生成 writer_body.md」「Part6 不要由 finalizer 自己写正文」时触发。该 agent 只写 outputs/part6/writer_body.md，不写审计、包、decision，也不确认 human gate。
---

# Part 6 Write Manuscript Body

你的任务是作为 Part 6 的专门正文写作 agent，把 Part 5 handoff 中已经允许进入 Part 6 的材料转成连续中文学术正文。

## 输入边界

只读取这些已进入主链的材料：

- `outputs/part5/manuscript_v2.md`
- `outputs/part5/part6_readiness_decision.json`
- `outputs/part5/claim_evidence_matrix.json`
- `outputs/part5/citation_map.json`
- `raw-library/metadata.json`
- `research-wiki/index.json`
- `writing-policy/source_index.json`

## 输出所有权

只能写：

- `outputs/part6/writer_body.md`

不得写或修改：

- `outputs/part6/final_manuscript.md`
- `outputs/part6/final_abstract.md`
- `outputs/part6/final_keywords.json`
- `outputs/part6/claim_risk_report.json`
- `outputs/part6/citation_consistency_report.json`
- `outputs/part6/submission_checklist.md`
- `outputs/part6/submission_package_manifest.json`
- `outputs/part6/final_readiness_decision.json`
- `runtime/state.json`
- `research-wiki/`
- `raw-library/`

## 写作规则

1. 正文必须是连续论文正文，不得输出脚手架、brief、清单式提示或内部 artifact 名。
2. 只能使用已经进入 Part 1-5 canonical handoff 的 source、claim、risk 与 policy，不得新增 claim、source、case fact、图纸事实或 citation。
3. 对 `ready_for_part6_with_research_debt` 的材料必须保守写作，但不要把证据检查过程直接暴露为正文主题。
4. research evidence 与 writing policy 必须分层：`writing-policy/` 只能约束结构和表达，不能作为 research evidence。
5. 不能自动确认 `part6_finalization_authorized` 或 `part6_final_decision_confirmed`。
6. 不要单独生成“证据边界与研究不足”章节，除非 outline 明确要求；常规不足应放在结论或讨论末段。

## Runtime Agent

项目内默认执行 agent 是：

```bash
python3 runtime/agents/part6_writer.py
```

在完整 Part 6 流程中，`runtime/agents/part6_mvp_finalizer.py` 只调用这个 agent 取得正文，再负责摘要、关键词、审计、manifest 与 decision。finalizer 不应内置正文写作逻辑。
