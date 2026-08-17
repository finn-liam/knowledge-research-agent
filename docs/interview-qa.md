# 面试 Q&A 要点（Knowledge Research Agent）

> 基于项目真实决策链整理，覆盖高频面试问题。

## 1. 为什么选 RAG 而不是微调模型？

企业知识：私有、动态更新、回答必须可溯源 → 微调会过期、无法溯源、成本高；RAG 数据不出内网 + 引用可核对 + 成本可控。

## 2. 为什么是 Agentic RAG 而不是普通 RAG？

普通 RAG 是"检索→拼接→生成"的直线流水线，缺陷是**搜到的未必相关**。本项目加入 Agent 决策：检索后 Grader 逐候选打分，低分时用"原因描述"驱动 LLM 改写查询重查（≤2 次）——系统会判断、会反思、会重搜（Self-RAG）。

## 3. 为什么用 LangGraph？Graph API 还是 Function API？

- 用**低层 Graph API（StateGraph）**，不是 create_agent：检索场景是"固定管线+质量判断"，不是 LLM 自由调工具；需要完全控制三路并行扇出、条件路由、改写回边、自定义 SSE 事件
- 用到的 API：add_node / add_edge / add_conditional_edges / ainvoke；状态用 TypedDict + Annotated reducer（解决并行节点并发写冲突）
- LangChain 只用于 LLM 接入（ChatOpenAI），检索栈手写直连（qdrant-client）

## 4. 为什么选 bge-m3 向量模型？

五约束推导：合规（本地）→ 排除云端 API；中英双语 → 排除单语模型；混合检索需 dense+sparse → bge-m3 一次前向双表示（GTE/Qwen3 主打 dense）；CPU 可跑 → 排除 4B/8B 大模型；生态成熟 → BGE 系列中文社区最普及。**选型是约束推导，不是排行榜挑最强的**。

## 5. 混合检索怎么做的？为什么需要？

- dense（1024 维余弦）管语义、sparse（词法权重）管术语精确匹配（"650 token"这类词）——双路 Top-K + RRF(k=60) 排名融合 + reranker 精排
- 为什么：纯向量对术语/编号命中弱；纯关键词不懂同义改写——互补

## 6. 查询增强为什么 dense/sparse 用不同文本？

实测发现：把"改写+关键词"拼接进 dense 查询会稀释余弦分数导致命中掉出阈值 → 改为 **dense 用简洁改写、sparse 用改写+关键词**，各取所长；增强无命中自动回退原问题（不劣化）。

## 7. 怎么防幻觉？（三层）

① REPORT_PROMPT 强制每条论断标 [n] 引用 ② 生成后 Verifier 核查 faithfulness（<0.7 附证据重生成一次）③ 越界引用剔除 + /kb/chunk 端点可核对片段全文。

## 8. 踩过的坑（讲 2~3 个最有价值的）

1. **"不走企业知识库"**：查询增强让 sparse 路产生独有命中 → `retrieve_dense` 的 list/numpy 类型 bug → 异常被 except 静默吞掉 → KB 整路返回空。教训：兜底必须可观测（traceback 日志），"环境故障"和"代码 bug"要区分处理
2. **LLM 输出全是原文**：`asyncio.wait_for` 包 async generator 直接 TypeError → 静默降级成摘录。教训：超时兜底用 `asyncio.timeout()` 上下文管理器；降级必须打印原因
3. **评估分数失真**：一半样本 nan（评分超时）+ 多源口径错配（0.426 假低分）→ 修超时、拆双口径后 KB 口径 0.772 揭示真实水平。教训：先让分数可信，再谈优化

## 9. 评估体系怎么设计的？

RAGAS 四指标 + 40 条 Golden Dataset（三类题型：事实/分析/图表）+ 两阶段执行（检索层进程内全量 + 生成层真实 API 抽样）+ 双口径 + 分项评分 + 参数对比工具。**所有优化用 before/after 数据验证**——例如调检索参数发现 recall 仅 +0.008 而 precision -0.031 → 数据驱动回滚。

## 10. 如果面试官问"给你 GPU 服务器会换模型吗？"

先小规模对比评估（Qwen3-Embedding 等候选），用基线数据说话，而不是直接换——换模型成本已配置化（改 .env + 重建索引 + 评估对比）。

## 11. 架构一句话

LangGraph 编排的 Agentic RAG：`提问 → 查询增强 → 三路并行检索 → 融合精排 → Grader 判断 → (生成 ∥ 改写重查) → 带引用报告`；SSE 全流程实时推送；多轮追问报告版本保留。
