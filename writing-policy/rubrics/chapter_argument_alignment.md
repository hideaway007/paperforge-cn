# 章节结构与论证路线 Rubric

## 检查项

| 项目 | 要求 |
|------|------|
| thesis 覆盖 | 至少一个一级章节明确承接 thesis |
| main_argument 覆盖 | 每个 main_argument 至少进入一个章节 |
| source 回溯 | 章节的 `support_source_ids` 可回溯到 argument tree 或 raw-library |
| wiki 回溯 | 章节关联节点可回溯到 `research-wiki/index.json` 页面 |
| 写作规范分层 | 写作规则只作为结构/表达约束，不作为研究证据 |
| gate | Part 4 不再设置 `outline_confirmed`；三件套通过 deterministic validation 后即可进入 Part 5 |

## 判定

- 全部满足：可进入 Part 4 gate 校验。
- 任一核心论证节点未覆盖：不能通过 outline gate。
- 存在无法回溯来源：不能确认 outline。
