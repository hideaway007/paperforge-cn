---
name: part1-search-result-triage
description: 学术研究 workflow Part 1 下载前搜索结果 triage skill：用于 researchagent 审查 outputs/part1/search_results_candidates.json，给出 download/maybe/skip 与 semantic_relevance 建议。只输出 sidecar，不得写 canonical artifacts、不得确认 gate、不得新增 source_id/citation/fact。
---

# Part 1 Search Result Triage

## 目标

在下载前审查 `outputs/part1/search_results_candidates.json`，提高下载命中率。你的输出只作为 `runtime/agents/part1_download_queue_builder.py` 的 advisory sidecar；最终下载队列、相关性评分、真实性校验和资料库注册仍由 deterministic runtime 负责。

## 输入

- `outputs/part1/intake.json`
- `outputs/part1/search_plan.json`
- `outputs/part1/search_results_candidates.json`
- `manifests/source-policy.json`

缺少 `intake.json`、`search_plan.json` 或候选结果时停止并报告，不要补造。

## 输出

只输出 sidecar JSON，例如：

- `outputs/part1/researchagent_search_result_triage.json`

建议 JSON 结构：

```json
{
  "payload": {
    "verdict": "usable | needs_more_candidates | blocked",
    "triage_items": [
      {
        "candidate_id": "cnki_q1_1_rank_001",
        "recommendation": "download | maybe | skip",
        "semantic_relevance": 0.0,
        "matched_intake_anchors": ["岭南建筑", "现代性"],
        "risk_flags": ["wrong_region", "generic_style_description"],
        "reason": "简要说明为什么建议下载或跳过"
      }
    ],
    "cnki_priority_checked": true,
    "does_not_modify_canonical_artifacts": true,
    "does_not_confirm_human_gate": true
  }
}
```

## 判断规则

1. 优先判断是否同时命中研究对象锚点与研究问题场景锚点；单独命中“现代性”“地域性”等泛词不足以建议下载。
2. CNKI 候选优先，但不能因 CNKI 来源而跳过主题相关性判断。
3. 英文期刊候选只作为补充层，优先保留与 `keywords_required` 和 `research_question` 明确相关的建筑理论、地域现代性、建筑创作研究。
4. 对错地域、纯结构技术、纯工程建造、泛城市规划、泛风格描述候选给出 `skip` 或低分 `maybe`。
5. 对疑似核心论文、代表建筑师创作思想、岭南现代建筑学派、两观三性、地域适应、传统与现代融合等候选给出较高 `semantic_relevance`。
6. 只能评价候选是否值得下载；不能判断它已经可以进入 `raw-library/metadata.json`。

## 禁止行为

- 不得改写 `outputs/part1/intake.json`、`outputs/part1/search_plan.json` 或 `outputs/part1/search_results_candidates.json`。
- 不得写入 `outputs/part1/download_queue.json`；该文件只能由 deterministic queue builder 生成。
- 不得写入 `raw-library/metadata.json`、`outputs/part1/authenticity_report.json`、`outputs/part1/accepted_sources.json`。
- 不得确认、跳过或伪造 `intake_confirmed` gate。
- 不得新增 `source_id`、citation、案例事实、研究结论或不可回溯的数据。
