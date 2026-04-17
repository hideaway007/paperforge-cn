# Repository Argument Density Baseline

## 统计口径

当前 clean root 中 `raw-library/`、`research-wiki/`、`outputs/` 只有 `.gitkeep` 骨架，没有真实论文全文或历史运行产物。因此本文件只统计仓库内可用的 workflow 样本：

- `writing-policy/reference_cases/case_chinese_architecture_outline.md`
- `writing-policy/rubrics/chapter_argument_alignment.md`
- `skills/part3-argument-generate/SKILL.md`
- `runtime/agents/part3_candidate_generator.py`
- `runtime/agents/part3_argument_seed_map_generator.py`
- `tests/test_part3_runtime_agents.py` 中的 minimal wiki / candidate 测试样例

这些材料只能作为 Part 3 论点密度校准，不代表真实文献库统计。

## 仓库内样本结论

| 样本 | 可见结构 | 观点密度判断 |
|------|----------|--------------|
| 中文建筑学论文参考结构 | 绪论、综述/理论、对象方法、案例类型、转译启示、结论，共 6 个章节位置 | 需要至少 1 个 thesis、3-5 个 main argument、若干章节级 sub-argument |
| Part 4 alignment rubric | 要求 thesis / main_argument 被章节覆盖 | Part 3 至少要提供足够 main_argument，才能支撑 Part 4 |
| 原 Part 3 deterministic generator | 每候选 1 个 thesis、3 个 main_argument、3 个 evidence、可选 1 个 counterargument | 总节点约 7-8；观点节点约 4-5，偏薄 |
| Part 3 seed map generator | candidate_claims 与 evidence_points 随 wiki page 数增长，另有 contradiction/counterclaim/method_path/case_boundary/gap/background | seed map 具备扩展论点池的原料，但旧候选树没有充分展开 |
| Part 3 测试样例 | minimal wiki 只有 3 个页面时也能生成 3 份候选 | 小样本下必须区分 evidence-backed claim 与 hypothesis，不能硬凑结论 |

## 推荐目标区间

每一份候选树：

- 总节点数：12-18
- 观点节点数：9-13
- main_argument：3-5
- sub_argument：6-8
- counterargument：至少 1
- rebuttal：建议 1；若没有，必须在 limitations 说明
- evidence：6-8，用于支撑而不是替代观点

三份候选合计：

- 至少 27 个观点节点
- 至少 12 个不同创新角度标签
- 至少 3 个反方或边界节点
- 每份候选的 thesis 不得只替换策略名，必须呈现不同论证路线

## 创新点安全边界

Part 3 可以生成创新假说，但不能把假说伪装成证据结论：

- 有 `source_ids + wiki_page_ids + seed_item_ids`：可写为 backed claim。
- 只有 evidence gap / contradiction / counterclaim 支撑：写为 innovation hypothesis。
- 完全没有来源支撑：不得进入候选树，只能进入后续检索建议或 open question。
