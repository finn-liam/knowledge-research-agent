# Changelog

All notable changes to this project are documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

本文档记录项目所有重要变更，格式遵循 Keep a Changelog，版本号遵循语义化版本。

## [Unreleased] / 未发布

### Planned / 规划中
- Query Router with per-source routing (kb / kb+web / kb+paper / full) · 查询路由按源分发
- DOCX image extraction · DOCX 图片提取
- Table structuring (Docling / PP-Structure) · 表格结构化
- Enterprise capabilities: JWT/SSO, RBAC, audit logs · 企业能力：认证、权限、审计
- Production hardening: PostgreSQL / Redis Pub-Sub / Celery · 生产化部署
- pytest unit-test suite · pytest 单元测试套件

## [0.1.0] - 2026-08-17

### Added / 新增
- Agentic RAG core: multi-source retrieval (KB ∥ arXiv ∥ Tavily) + Self-RAG (grader → rewrite/re-search) + citation tracing with forced `[n]` references · Agentic RAG 核心链路：多源检索 + Self-RAG 反思重查 + 引用溯源
- Hybrid retrieval: bge-m3 dense+sparse dual-path + RRF + bge-reranker · bge-m3 混合检索 + RRF + 精排
- Intelligent PDF parsing: type routing (native/scanned/mixed) + layout restoration + RapidOCR + VLM chart description · PDF 智能解析：类型分流 + 版面还原 + OCR + VLM 图表描述
- Multi-round dialogue with report versioning · 多轮对话与报告多版本
- Streaming UX: SSE events (steps / sources / grader / report tokens) · SSE 流式交互
- RAGAS evaluation suite with golden dataset (40 items) and baseline (faithfulness 0.855, precision 0.748) · RAGAS 评估体系与基线
- Mock mode: full demo without any API key · 无 Key Mock 降级模式
- Sample documents for demo (employee handbook, product whitepaper, meeting minutes) · 演示示例文档

### Docs / 文档
- Bilingual README (English + Chinese) with architecture diagram and 2×2 screenshot grid · 双语 README + 架构图 + 截图
- Home statistics panels tooltip (data source & aggregation scope) · 首页统计口径说明
- Bilingual CONTRIBUTING guide + Issue/PR templates + Code of Conduct · 双语贡献指南 + 模板 + 行为准则

### CI / 持续集成
- GitHub Actions workflow: backend compile check + frontend lint/build · CI：后端编译检查 + 前端 lint/build
- Architecture diagram optimized to 471KB (256-color quantization) · 架构图压缩优化

### Fixed / 修复
- `app/models` ORM package was accidentally excluded by `.gitignore` (`models/` → `/models/`) · 修复 `.gitignore` 误忽略 ORM 包的问题
