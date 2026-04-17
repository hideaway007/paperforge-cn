# AGENTS.md — Tests Directory

## Scope
- 放置项目运行时脚本的回归测试与 schema 契约测试。
- 测试不得依赖真实 CNKI 网络访问，不得改写 `raw-library/`、`outputs/`、`runtime/state.json` 的真实项目产物。
- 测试样例数据应内联或放在未来的 `tests/fixtures/` 中，避免复用生产数据导致误判。

## Conventions
- 使用 Python 标准库 `unittest` 优先，除非项目明确增加测试依赖。
- 测试文件命名为 `test_*.py`。
- 重点覆盖 canonical artifact schema、gate 校验、状态推进边界。
