# 简历项目描述（Knowledge Research Agent）

> 用于简历"项目经历"栏目的推荐写法。按简历篇幅自行裁剪。

## 一句话定位（项目标题下）

**企业级 Agentic RAG 知识研究助手**：输入问题自动完成多源检索、质量判断与反思重查，生成带引用溯源的研究报告（FastAPI + LangGraph + Qdrant + bge-m3 + React）。

## 推荐 Bullet（挑 3~5 条）

- 基于 **LangGraph 低层 StateGraph** 手写 7 节点 Agent 工作流：三路并行检索（企业知识库∥arXiv 论文∥Tavily 网页）→ 融合精排 → **Retrieval Grader 打分判断** → 低分改写重查（Self-RAG 闭环），配套 Answer Verification 防幻觉
- 实现**混合检索**：bge-m3 一次前向产出 dense(1024)+sparse 双表示，RRF(k=60) 融合 + bge-reranker 精排；查询增强（LLM 改写+关键词扩展）双路分离应用，增强无命中自动回退原问题
- **PDF 智能解析**：类型分流（原生/扫描/图文混排）→ 版面还原（阅读顺序/页眉页脚/标题章节/页码）→ RapidOCR 图片识别 + mimo-v2.5 VLM 图表描述 → Parent-Child 两级切片，全链路页码溯源
- 基于 **RAGAS 四指标评估体系**：40 条 Golden Dataset、双口径（KB/全量）、分项评分（文字/图表）、参数对比工具，量化优化效果——最终基线 **faithfulness 0.855 / 检索 precision 0.748**（10/10 样本出分）
- 全栈落地：SSE 流式交互 + 多轮追问（报告多版本保留）+ 引用双向联动（点击定位原文页码）；31 文档 / 3195 切片真实知识库；7 个自动化测试全通过

## 技术栈关键词（简历技能栏）

`Python · FastAPI · LangGraph · LangChain · Qdrant · bge-m3 · Redis(规划) · React · TypeScript · Tailwind · SSE · RAGAS`

## 亮点数据（面试/简历可用）

| 指标 | 值 |
|---|---|
| 评估基线 | faithfulness 0.855 / 检索 precision 0.748 / recall 0.501 |
| 知识库规模 | 31 文档 / 3195 切片（含 633 页真实 PDF） |
| 自动化测试 | 7 个脚本（冒烟/回归/多轮/渲染/参数对比）全 PASS |
| 模型全本地化 | bge-m3 + reranker 4.4GB（内网合规部署） |
