# Knowledge Research Agent

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-orange.svg)](https://www.langchain.com/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.18-ff3f59.svg)](https://qdrant.tech/)

**An enterprise-grade Agentic RAG assistant** — ask one question and the system autonomously performs multi-source retrieval, quality judgment and reflective re-search, then produces a citation-traced research report.

[中文文档](README.zh-CN.md)

</div>

---

## 📐 Architecture

<div align="center">
  <img src="docs/Diagram.png" width="55%" alt="Architecture" />
</div>

```
User Question → Query Router (chat | knowledge)
    → Parallel Retrieval (Knowledge Base ∥ arXiv Papers ∥ Tavily Web)
    → Merge + RRF + bge-reranker
    → Retrieval Grader ── low quality → Rewrite & Re-search (≤2 rounds)
    → LLM Generation (DeepSeek streaming, forced [n] citations)
    → Answer Verification → Citation-Traced Report
```

## ✨ Key Features

| Capability | Description |
|---|---|
| **Agentic RAG (Self-RAG)** | 7-node LangGraph StateGraph: parallel retrieval + grader judgment + rewrite/re-search loop |
| **Hybrid Retrieval** | bge-m3 dense (1024-dim) + sparse lexical weights in one forward pass → dual-path recall + RRF(k=60) + bge-reranker |
| **Query Enhancement** | LLM rewrite + keyword expansion with dual-path encoding (dense=concise rewrite, sparse=rewrite+keywords); auto fallback to the original query |
| **Multi-source Retrieval** | Enterprise knowledge base (Qdrant) ∥ arXiv papers ∥ Tavily web search |
| **Intelligent PDF Parsing** | Page-level routing (native / scanned OCR / mixed) → layout restoration (reading order, header/footer removal, headings, page markers) → RapidOCR + VLM chart description (OpenAI-compatible, e.g. mimo-v2.5) |
| **Parent-Child Chunking** | child (650 tokens) for precise retrieval + parent (chapter-level, 2000 tokens) for complete context |
| **Citation Tracing** | Every claim forced to carry [n] citations; page-number locating and full-text verification via `/kb/chunk` |
| **Multi-round Dialogue** | Follow-up questions re-run the pipeline; report versioning preserved |
| **Streaming UX** | SSE-driven: step status, incremental sources, grader scores and report tokens in real time; auto-reconnect + completion calibration |
| **Evaluation Suite** | RAGAS metrics + 40-item Golden Dataset + dual-scope scoring + parameter A/B comparison tool |
| **Graceful Degradation** | Runs without any API key (Mock mode); tiered fallbacks keep the pipeline alive |

## 🖼 Screenshots

<div align="center">
  <img src="docs/screenshots/1-home.png" width="45%" alt="Home page" />
  &nbsp;&nbsp;
  <img src="docs/screenshots/2-research.png" width="45%" alt="Research in progress" />
  <br /><br />
  <img src="docs/screenshots/3-citation.png" width="45%" alt="Citation tracing" />
  &nbsp;&nbsp;
  <img src="docs/screenshots/4-kb.png" width="45%" alt="Knowledge base" />
</div>

*Home · Agent workflow in progress · Citation-to-source tracing · Knowledge base ingestion*

## 🚀 Quick Start

### Prerequisites

- Python 3.11
- Node.js 18+
- Docker (optional — Qdrant vector database; a running Qdrant also works via `QDRANT_URL`)

### 1. Start Qdrant

```bash
docker compose -f infra/docker-compose.yml up -d qdrant
```

### 2. Download local models (~4.4GB, stored in the project `models/`)

```bash
cd apps/api
python scripts/download_models.py   # bge-m3 + bge-reranker-v2-m3 (via hf-mirror)
```

### 3. Configure

```bash
cp apps/api/.env.example apps/api/.env
```

```ini
DEEPSEEK_API_KEY=        # LLM (leave empty → excerpt fallback, Mock mode)
TAVILY_API_KEY=          # Web search (leave empty → simulated web sources)
VLM_API_KEY=             # Chart description (leave empty → skip VLM)
# All three can be empty — the full demo still works (Mock mode).
```

### 4. Start the backend

```bash
cd apps/api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

### 5. Start the frontend

```bash
cd apps/web
npm install
npm run dev
```

Open **http://localhost:5173/** and ask a question.

### 6. (Optional) Upload enterprise documents

Use the **Knowledge Base** page to upload PDF/DOCX/MD/TXT files (≤100MB each, configurable). They are parsed, chunked and vectorized automatically.

## 📊 Statistics & Data Scope

The numbers on the home page are **live aggregations of real data** (not display samples):

| Panel | Scope |
|---|---|
| **Sources** | Source fragments actually retrieved across all historical research, grouped by type (enterprise documents / academic papers / web pages); grows after every research |
| **Research Statistics** | Cumulative metrics: Total Research = research count; Knowledge Sources = total retrieved sources; Documents Hit = cumulative documents matched; Accuracy Rate = historical average relevance |

## 📈 Evaluation

```bash
cd apps/api
python -m pip install -r requirements-eval.txt

# 1. Generate the evaluation dataset from knowledge-base chunks (40 items by default)
python eval/scripts/eval_dataset_gen.py 40

# 2. Run evaluation (retrieval layer on all items + generation layer via the real API on 10 sampled items)
python eval/scripts/eval_run.py --gen 10 --save-baseline

# 3. Read the report at eval/report.md (metric summary + baseline diff + low-score cases)
# 4. A/B test retrieval parameters: python eval/scripts/param_compare.py
```

**Baseline example** (40-item dataset): faithfulness 0.855 · retrieval precision 0.748 · KB-scope precision 0.772 · recall 0.501 (multi-annotation scope).

## 🗂 Project Structure

```
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── agents/         # LangGraph: graph / nodes / state / prompts / events + mock
│   │   │   ├── rag/            # chunker / parsers / models (embedding) / vector_store / ocr / vlm
│   │   │   ├── integrations/   # arXiv / Tavily
│   │   │   ├── llm/            # LLM gateway (DeepSeek + Mock)
│   │   │   ├── services/       # task lifecycle / ingestion pipeline
│   │   │   ├── api/v1/         # REST + SSE routes
│   │   │   └── models/         # 9 ORM tables
│   │   ├── scripts/            # model download / tests / utilities
│   │   └── requirements*.txt
│   └── web/                    # React frontend
│       └── src/
│           ├── components/     # ui / layout / research / sources / graph / stats / kb
│           ├── features/       # researchStore + SSE hook + userStore
│           └── pages/          # home / research / knowledge-base / library
├── eval/                       # evaluation suite (dataset / scripts / report / baseline)
├── infra/                      # docker-compose (PG/Qdrant/Redis/MinIO + api/web)
├── docs/                       # architecture / screenshots / resume & interview notes
└── sample-data/                # sample documents for demo
```

## 🔌 API Overview

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/research` | Create a research task |
| GET | `/api/v1/research/{id}/stream` | SSE event stream (steps / sources / grader / report tokens) |
| GET | `/api/v1/research/{id}` | Task detail (multi-version reports / sources / stats) |
| POST | `/api/v1/research/{id}/followup` | Follow-up question |
| POST/GET/DELETE | `/api/v1/documents` | Knowledge-base document management |
| GET | `/api/v1/kb/chunk` | Full chunk text for citation tracing |
| GET | `/api/v1/kb/stats` · `/api/v1/sources/stats` | Statistics |
| GET | `/docs` | Auto-generated API docs |

## 🐳 Deployment

- **Single-node Docker**: `infra/docker-compose.yml` (PostgreSQL/Qdrant/Redis/MinIO + api + web), models mounted as a volume
- Production hardening (PostgreSQL / Redis Pub-Sub / Celery) and multi-node plans are documented in the project roadmap

## 📄 License

- Code: **MIT** (see LICENSE)
- Models: bge-m3 / bge-reranker-v2-m3 (MIT, BAAI); RapidOCR models (Apache 2.0)
- Third-party services: DeepSeek / Tavily / mimo require your own API keys

## 🗺 Roadmap

- [x] Agentic RAG core (multi-source + Self-RAG + citation tracing)
- [x] Intelligent PDF parsing (OCR + VLM chart description)
- [x] RAGAS evaluation suite + stable baseline
- [ ] Query Router with per-source routing (kb / kb+web / kb+paper / full)
- [ ] DOCX image extraction (reuse OCR/VLM pipeline)
- [ ] Table structuring (Docling / PP-Structure evaluation)
- [ ] Enterprise capabilities: auth (JWT/SSO), RBAC, audit logs
- [ ] Production hardening: PostgreSQL / Redis Pub-Sub / Celery
- [ ] CI/CD (pytest + GitHub Actions)
