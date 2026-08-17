# RAG 评估报告

> 数据集 40 条 | 生成层抽样 10 条 | 时间 2026-08-07 12:48

## 指标汇总

| 层 | 指标 | 分数 | 有效样本 |
|---|---|---|---|
| 检索层 | context_precision | 0.748 | 40/40 |
| 检索层 | context_recall | 0.501 | 40/40 |
| 生成层 | faithfulness | 0.855 | 10/10 |
| 生成层 | context_precision | 0.593 | 10/10 |
| 生成层 | context_recall | 0.499 | 10/10 |
| 生成层·KB口径 | context_precision | 0.772 | - |
| 生成层·KB口径 | context_recall | 0.506 | - |
| 生成层·chart题 | faithfulness | 0.800 | - |
| 生成层·text题 | faithfulness | 0.779 | - |

## 与基线对比

| 指标 | 基线 | 本次 | 变化 |
|---|---|---|---|
| context_precision | 0.321 | 0.748 | +0.427 ✅ |
| context_recall | 0.473 | 0.501 | +0.028 ✅ |
| faithfulness | 0.837 | 0.855 | +0.018 ✅ |
| context_precision | 0.336 | 0.593 | +0.257 ✅ |
| context_recall | 0.431 | 0.499 | +0.068 ✅ |

## 生成层明细（faithfulness 低分 <0.6 高亮）

- 根据图中描述，在Reality capture中创建正射投影的先决条件是什么？工具在什么情况下被激活 | faithfulness=0.800
- 在代码中，如何将文件名（不含扩展名）赋值给文档元数据的 dish_name 字段？ | faithfulness=1.000
- LangChain 中的“文本到 Cypher”技术是如何将自然语言问题转换为图数据库查询的？ | faithfulness=0.917
- 如何加载本地保存的FAISS向量库？ | faithfulness=0.714
- 结合表格及说明，分析RAGAS、LlamaIndex和Phoenix三种RAG评估工具在核心机制、独 | faithfulness=0.800
- 在代码中，如何获取并记录图查询的查询类型？ | faithfulness=0.900
- 根据该片段，RAG（检索增强生成）技术的核心是什么？ | faithfulness=0.909
- 该竞赛旨在培养学生哪些方面的能力？ | faithfulness=0.700
- 结合章节内容，分析为什么用户原始问题需要经过查询重构与分发？其中查询翻译和查询路由各起什么作用？ | faithfulness=1.000
- 根据文档片段，进行基础配置包括哪些步骤？ | faithfulness=0.812
