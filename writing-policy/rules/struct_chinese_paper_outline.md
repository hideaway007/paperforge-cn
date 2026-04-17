---
rule_id: struct_chinese_paper_outline
rule_type: structure
title: 中文建筑学论文基础章节结构
source: baseline_chinese_academic_policy
priority: medium
applies_to:
  - paper_outline
  - chapter_brief
---

# 中文建筑学论文基础章节结构

## 规则内容

MVP 阶段的大纲应至少覆盖以下功能性章节：

1. 绪论：研究背景、研究问题、研究对象、研究方法与论文结构。
2. 文献综述与理论基础：研究现状、核心概念、方法基础与研究缺口。
3. 核心论证章节：按照 canonical argument tree 展开 thesis、main_argument 与必要的 sub_argument。
4. 结论：回收主论题，说明研究贡献、局限与后续写作准备。

## 使用边界

该规则只约束论文结构，不提供研究证据。研究判断必须回溯到 `research-wiki/` 与 `raw-library/`。

## 违反后果

若章节结构无法覆盖 argument tree 的核心节点，Part 4 不应进入 `outline_confirmed`。
