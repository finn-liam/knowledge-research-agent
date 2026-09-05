"""LangGraph 节点：kb_search → report_write（纯企业知识库 RAG）。

- 学术检索 / 网页检索 / 知识图谱构建已按需求暂停（不入图）
- 知识库无命中时明确告知，不编造
- 无 LLM Key 时报告改为真实片段关键句摘录（带 [n] 标签，零编造）
"""
import asyncio
import re
import time
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.agents import mock_data
from app.agents.events import EVENT_BUS
from app.agents.prompts import (
    CHART_REPORT_PROMPT,
    CHAT_PROMPT,
    GRADE_PROMPT,
    QUERY_PROCESS_PROMPT,
    REPORT_PROMPT,
    REWRITE_PROMPT,
    ROUTER_PROMPT,
    VERIFY_PROMPT,
)
from app.agents.state import ResearchState
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.arxiv_client import search_papers
from app.integrations.web_search import search_web
from app.llm.gateway import get_llm
from app.models.research import (
    STEP_DEFS,
    Citation,
    Document,
    DocumentChunk,
    Report,
    ResearchStep,
    ResearchTask,
    Source,
)

MAX_KB_SOURCES = 12  # KB 候选上限（= merger 窗口；兄弟扩展后仍能整体进入精排）
MAX_GRADE_SOURCES = 12  # merger 输出给 grader 评估的候选上限
SIBLING_BASE = 6      # 兄弟扩展：参与扩展的核心命中数
SIBLING_MAX_ADD = 6   # 兄弟扩展：最多补充的邻居切片数（核心+邻居 ≤ MAX_KB_SOURCES）
_step_lock = asyncio.Lock()

settings = get_settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _step(task_id: str, step_key: str, label: str, status: str, meta: dict | None = None) -> None:
    meta = meta or {}
    async with _step_lock:
        async with SessionLocal() as db:
            row = (
                await db.execute(
                    select(ResearchStep).where(
                        ResearchStep.task_id == task_id, ResearchStep.step_key == step_key
                    )
                )
            ).scalar_one_or_none()
            if row:
                row.status = status
                if status == "running":
                    row.started_at = _now()
                if status in ("done", "failed", "skipped"):
                    row.finished_at = _now()
                row.meta_json = {**(row.meta_json or {}), **meta}
                await db.commit()
    if status == "running":
        EVENT_BUS.emit(task_id, "step_started", {"step": step_key, "label": label})
    elif status == "done":
        EVENT_BUS.emit(task_id, "step_completed", {"step": step_key, "label": label, **meta})
    elif status == "failed":
        EVENT_BUS.emit(task_id, "step_failed", {"step": step_key, "label": label, **meta})
    elif status == "skipped":
        EVENT_BUS.emit(task_id, "step_skipped", {"step": step_key, "label": label})


def _emit_sources(task_id: str, sources: list[dict]) -> None:
    for s in sources:
        EVENT_BUS.emit(
            task_id,
            "source_found",
            {
                "type": s["type"],
                "title": s["title"],
                "url": s.get("url", ""),
                "snippet": s.get("snippet", ""),
                "relevance": s.get("relevance", 0.0),
                "source_label": s.get("source_label", ""),
            },
        )


# ---------------- 意图路由（chat / knowledge） ----------------

async def fanout_node(state: ResearchState) -> dict:
    """扇出占位节点：multi 模式三路并行 / KB 无命中升级补查（fanout_external）时经由它分发。"""
    return {}


async def fanout_external_node(state: ResearchState) -> dict:
    """KB 无命中升级：解除 paper/web 的规划跳过（本轮补查外部源）。"""
    return {"plan": ["kb", "paper", "web"], "external_run": True}


async def router_node(state: ResearchState) -> dict:
    """检索规划器（Planner）：chat 直接回复；knowledge 逐源规划 kb/paper/web。

    plan = 规划的来源子集；search_mode 由 plan 派生（多源=multi，仅KB=kb_only 渐进式）。
    兼容旧输出格式 {"sources": "kb_only"/"multi"}（LLM 偶发老格式时降级解析）。
    """
    task_id = state["task_id"]
    query = state.get("original_query") or state["query"]
    llm = get_llm()
    payload = await llm.extract_json(
        ROUTER_PROMPT.format(query=query), mock_data.mock_route(query)
    )
    payload = payload if isinstance(payload, dict) else {}
    qtype = payload.get("type") or "knowledge"
    if qtype not in ("chat", "knowledge"):
        qtype = "knowledge"

    if qtype == "chat":
        plan: list[str] = []
    elif "kb" in payload or "paper" in payload or "web" in payload:
        plan = [s for s in ("kb", "paper", "web") if payload.get(s) is True]
        if not plan:
            plan = ["kb"]
    else:  # 旧格式兼容
        plan = ["kb", "paper", "web"] if payload.get("sources") == "multi" else ["kb"]

    search_mode = "kb_only" if plan == ["kb"] else "multi"

    paused_steps = ["kb_search", "paper_search", "web_search", "graph_build"]
    if qtype == "chat":
        # 闲聊路径：检索相关步骤标记为已暂停（DB 状态；前端由 router_result 事件同步）
        for key, label in STEP_DEFS:
            if key in paused_steps:
                await _step(task_id, key, label, "paused")
    EVENT_BUS.emit(
        task_id, "router_result",
        {"type": qtype, "query": query[:40], "paused_steps": paused_steps,
         "sources": "multi" if len(plan) > 1 else "kb_only", "plan": plan},
    )
    return {"query_type": qtype, "search_mode": search_mode, "plan": plan, "escalation": False}


# ---------------- 知识库检索（混合检索：bge-m3 dense+sparse 双路 RRF） ----------------

async def _fuse_hybrid(
    store, dense_hits: list[dict], sparse_hits: list[dict], query_dense: list[float],
    min_score: float | None = None, relax_min_score: float | None = None,
) -> list[dict]:
    """双路合并 → 阈值过滤 → RRF 排序。

    阈值策略：
      主过滤   : dense cosine ≥ KB_MIN_SCORE
      宽松兜底 : sparse 独有命中（sparse Top-5 内）本地补算 dense ≥ 0.35
    relevance 统一用 dense 分展示（0~1）。
    """
    from app.rag.vector_store import RRF_K

    merged: dict[int, dict] = {}
    for rank, h in enumerate(dense_hits, start=1):
        merged[h["id"]] = {**h, "dense_rank": rank, "sparse_rank": None}
    for rank, h in enumerate(sparse_hits, start=1):
        if h["id"] in merged:
            merged[h["id"]]["sparse_rank"] = rank
        else:
            merged[h["id"]] = {**h, "dense_rank": None, "sparse_rank": rank}

    # sparse 独有候选（sparse Top-5 内）：取回 dense 向量本地余弦补算
    missing = [
        h
        for h in merged.values()
        if h["dense_rank"] is None and h["sparse_rank"] is not None and h["sparse_rank"] <= 5
    ]
    if missing:
        vecs = await store.retrieve_dense([h["id"] for h in missing])
        for h in missing:
            v = vecs.get(h["id"])
            h["dense_score_extra"] = (
                round(max(0.0, min(1.0, sum(a * b for a, b in zip(query_dense, v)))), 3)
                if v is not None else 0.0
            )

    cands: list[dict] = []
    ms = settings.kb_min_score if min_score is None else min_score
    rms = settings.kb_relax_min_score if relax_min_score is None else relax_min_score
    for h in merged.values():
        dense_score = h["score"] if h["dense_rank"] is not None else h.get("dense_score_extra", 0.0)
        h["relevance"] = dense_score
        if h["dense_rank"] is not None and h["score"] >= ms:
            cands.append(h)
        elif (
            h["dense_rank"] is None
            and h["sparse_rank"] is not None
            and h["sparse_rank"] <= 5
            and h.get("dense_score_extra", 0.0) >= rms
        ):
            cands.append(h)

    for h in cands:
        rrf = 0.0
        if h["dense_rank"] is not None:
            rrf += 1.0 / (RRF_K + h["dense_rank"])
        if h["sparse_rank"] is not None:
            rrf += 1.0 / (RRF_K + h["sparse_rank"])
        h["rrf"] = rrf
    cands.sort(key=lambda x: x["rrf"], reverse=True)
    return cands


def _build_enhanced_queries(processed: dict, original: str) -> tuple[str, str]:
    """返回 (dense_query, sparse_query)。

    dense 用简洁改写（避免长文本稀释余弦分数）；
    sparse 用改写+关键词（词法权重覆盖更广，精确词命中增强）。
    无增强时两者均为原问题。
    """
    rq = (processed.get("rewritten_query") or original).strip() or original
    kws = [
        k for k in (processed.get("keywords") or [])
        if isinstance(k, str) and k.strip()
    ]
    sparse_query = rq if not kws else f"{rq}\n关键词：{'；'.join(kws)}"
    return rq, sparse_query


def _apply_rerank(query: str, cands: list[dict]) -> list[dict]:
    """bge-reranker-v2-m3 模型精排：按模型相关度分降序，relevance 更新为模型分。

    模型不可用/异常时返回原列表（保持 RRF 排序，链路不中断）。
    """
    from app.rag.models import rerank_scores

    snippets = [c.get("text") or c.get("snippet") or "" for c in cands]
    scores = rerank_scores(query, snippets)
    if scores is None:
        return cands
    for cand, score in zip(cands, scores):
        cand["relevance"] = round(score, 3)
    cands.sort(key=lambda x: x["relevance"], reverse=True)
    return cands


async def _hybrid_search(
    store, dense_text: str, sparse_text: str | None, top_k: int = 20,
    min_score: float | None = None, relax_min_score: float | None = None,
) -> list[dict]:
    """双路混合检索：dense 用简洁文本，sparse 用关键词文本；返回 RRF 融合候选。

    dense_text == sparse_text 时仅编码一次（两路取自同一编码）。
    """
    from app.rag.models import encode_hybrid, get_embedder

    dense_vec = None
    sparse_vec = None
    if dense_text == sparse_text:
        # 同一文本：一次编码取两路
        dense_res = await asyncio.to_thread(encode_hybrid, [dense_text])
        if dense_res[0] is not None:
            dense_vec = dense_res[0][0]
            if settings.hybrid_search and dense_res[1]:
                sparse_vec = dense_res[1][0]
    else:
        dense_res = await asyncio.to_thread(encode_hybrid, [dense_text])
        if dense_res[0] is not None:
            dense_vec = dense_res[0][0]
            if settings.hybrid_search and sparse_text:
                sparse_res = await asyncio.to_thread(encode_hybrid, [sparse_text])
                sparse_vec = sparse_res[1][0] if sparse_res[1] else None
    if dense_vec is None:
        # bge3 不可用 → 降级纯 dense
        embedder = get_embedder()
        if embedder is not None:
            dense_vec = (
                await asyncio.to_thread(
                    lambda: embedder.encode(
                        [dense_text], normalize_embeddings=True
                    ).tolist()
                )
            )[0]
    if dense_vec is None:
        return []
    dense_hits = await store.search_dense(dense_vec, top_k=top_k)
    sparse_hits = (
        await store.search_sparse(sparse_vec, top_k=top_k)
        if settings.hybrid_search and sparse_vec is not None
        else []
    )
    fused = await _fuse_hybrid(
        store, dense_hits, sparse_hits, dense_vec,
        min_score=min_score, relax_min_score=relax_min_score,
    )
    # 注：精排统一在 merger 节点对三路候选执行（避免 KB 内重复计算）
    return fused


async def _multi_query_search(
    store, query_pairs: list[tuple[str, str | None]], top_k: int = 20,
    min_score: float | None = None, relax_min_score: float | None = None,
) -> list[dict]:
    """多查询检索：每路各自 hybrid 检索，再跨查询 RRF 合并（等权、按 chunk id 去重）。

    动机：单条查询的 dense 向量存在语义盲区（诊断显示 37.5% 标注 chunk 不在 dense top-50），
    换措辞的多路查询能覆盖不同语义角度；显示分 relevance 取各路中的最高 dense 分。
    """
    from app.rag.vector_store import RRF_K

    result_lists: list[list[dict]] = []
    for dense_text, sparse_text in query_pairs:
        if not dense_text:
            continue
        res = await _hybrid_search(
            store, dense_text, sparse_text, top_k=top_k,
            min_score=min_score, relax_min_score=relax_min_score,
        )
        if res:
            result_lists.append(res)

    if not result_lists:
        return []
    if len(result_lists) == 1:
        return result_lists[0]

    rrf_scores: dict[int, float] = {}
    best: dict[int, dict] = {}
    for lst in result_lists:
        for rank, h in enumerate(lst, start=1):
            rrf_scores[h["id"]] = rrf_scores.get(h["id"], 0.0) + 1.0 / (RRF_K + rank)
            cur = best.get(h["id"])
            if cur is None or (h.get("relevance") or 0.0) > (cur.get("relevance") or 0.0):
                best[h["id"]] = h

    merged = []
    for cid, score in rrf_scores.items():
        h = dict(best[cid])
        h["rrf_multi"] = round(score, 6)
        merged.append(h)
    merged.sort(key=lambda x: x["rrf_multi"], reverse=True)
    return merged


async def _expand_with_siblings(fused: list[dict]) -> list[dict]:
    """兄弟切片扩展（auto-merging retrieval）：核心命中的 ±1 邻居就近插入候选。

    治"答案横跨相邻切片"的召回摊薄——命中 46 号后 45/47 大概率同样相关，
    ID 级标注往往覆盖整个邻域。邻居按核心命中顺序就近插入（不追加尾部），
    保证能进入 merger 的 top-12 精排窗口；去重、总量受 SIBLING_MAX_ADD 约束。
    """
    if not fused:
        return fused
    core = fused[:SIBLING_BASE]
    existing = {(h["document_id"], h["chunk_index"]) for h in fused}

    # 批量取邻居文本与文档名（SQLite 两次小查询）
    need: dict[int, set[int]] = {}
    for h in core:
        d, i = h["document_id"], h["chunk_index"]
        need.setdefault(d, set()).update((i - 1, i + 1))
    nb_map: dict[tuple[int, int], dict] = {}
    async with SessionLocal() as db:
        for d, idxs in need.items():
            rows = (
                await db.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.document_id == d,
                        DocumentChunk.chunk_index.in_([i for i in idxs if i >= 0]),
                    )
                )
            ).scalars().all()
            for r in rows:
                nb_map[(r.document_id, r.chunk_index)] = {
                    "text": r.text or "", "parent_text": r.parent_text or ""
                }
        doc_ids = list(need.keys())
        names = {
            r[0]: r[1]
            for r in (
                await db.execute(
                    select(Document.id, Document.name).where(Document.id.in_(doc_ids))
                )
            ).all()
        }

    expanded: list[dict] = []
    added = 0
    for h in core:
        expanded.append(h)
        if added >= SIBLING_MAX_ADD:
            continue
        d, i = h["document_id"], h["chunk_index"]
        for ni in (i - 1, i + 1):
            if added >= SIBLING_MAX_ADD:
                break
            key = (d, ni)
            if key in existing or key not in nb_map:
                continue
            existing.add(key)
            nb = nb_map[key]
            expanded.append({
                "id": f"sib-{d}-{ni}",
                "document_id": d,
                "chunk_index": ni,
                "document_name": names.get(d, ""),
                "text": nb["text"],
                "parent_text": nb["parent_text"],
                "relevance": h.get("relevance", 0.0),
                "page_nos": [],
                "sibling": True,
            })
            added += 1
    return expanded


async def kb_retriever_node(state: ResearchState) -> dict:
    task_id, query = state["task_id"], state["query"]
    topic = mock_data.extract_topic(query)
    started = time.time()

    # Planner 逐源规划：KB 不在规划内 → 跳过（步骤标记 skipped，前端可见）
    plan = state.get("plan") or ["kb"]
    if "kb" not in plan:
        await _step(task_id, "kb_search", "查询企业知识库", "skipped")
        return {"kb_results": []}

    await _step(task_id, "kb_search", "查询企业知识库", "running")

    # 反思重查最终轮（escalation）：加大检索量 + 放宽阈值
    esc = bool(state.get("escalation"))
    top_k = 30 if esc else 20
    min_score = (settings.kb_min_score - 0.05) if esc else None

    # 查询增强：LLM 改写 + 关键词扩展 + 多查询变体 + HyDE（一次调用；Mock/失败 → 原问题）
    dense_query, sparse_query = query, query
    sub_queries: list[str] = []
    hyde_text = ""
    enhanced = False
    if settings.query_processing:
        llm = get_llm()
        processed = await llm.extract_json(
            QUERY_PROCESS_PROMPT.format(query=query),
            mock_data.mock_query_process(query),
        )
        dense_query, sparse_query = _build_enhanced_queries(processed, query)
        enhanced = dense_query != query or sparse_query != query
        if settings.multi_query:
            sub_queries = [
                s.strip()
                for s in (processed.get("sub_queries") or [])
                if isinstance(s, str) and s.strip() and s.strip() != query
            ][:2]
        if settings.hyde_enabled and settings.multi_query:
            hyde_text = str(processed.get("hyde") or "").strip()

    results: list[dict] = []
    kb_status = "empty"  # empty / no_hits / unreachable / ok
    from app.rag.vector_store import get_vector_store

    store = get_vector_store()
    try:
        await store.ensure_collection()
        if await store.count() > 0:
            # 主查询用用户原话（A/B: orig_multi K12 recall 0.523 vs 改写主路 0.520，K8 持平；
            # 且不依赖改写质量）——LLM 改写的价值在 sub_queries 变体，文本见 ab_recall.json
            query_pairs: list[tuple[str, str | None]] = [(query, None)]
            query_pairs += [(s, None) for s in sub_queries]
            if hyde_text and hyde_text != query:
                query_pairs.append((hyde_text, None))  # HyDE 变体：假设答案贴近文档表述
            fused = await _multi_query_search(
                store, query_pairs, top_k=top_k, min_score=min_score
            )
            if not fused and (enhanced or sub_queries or hyde_text):
                # 增强未命中 → 回退原问题直接检索（兜底不劣化）
                fused = await _hybrid_search(store, query, None, top_k=top_k, min_score=min_score)
            if not fused:
                kb_status = "no_hits"
            else:
                kb_status = "ok"
                # 兄弟切片扩展：命中切片的 ±1 邻居就近插入（治标注邻域摊薄，零 LLM 成本）
                if settings.sibling_expand:
                    fused = await _expand_with_siblings(fused)
                # 注：不做单文档配额——A/B 实测配额在精排前挤掉同文档的标注相关片段
                # （multi_cap_rerank 0.410 vs multi_rerank 0.497）；多样性由 merger 统一精排+标题去重保证
                for h in fused:
                    doc_id = h["document_id"]
                    results.append(
                        {
                            "title": f"{h['document_name']} · 片段 {h['chunk_index'] + 1}",
                            "url": f"kb://doc/{doc_id}#c{h['chunk_index']}",
                            "snippet": (h.get("text") or "")[:300],
                            "type": "enterprise",
                            "source_label": "企业知识库",
                            "relevance": round(h.get("relevance", 0.0), 3),
                            "meta": {
                                "document_id": doc_id,
                                "parent_text": h.get("parent_text") or "",
                                "page_nos": h.get("page_nos") or [],
                            },
                            "page_nos": h.get("page_nos") or [],
                        }
                    )
                    if len(results) >= MAX_KB_SOURCES:
                        break
    except Exception as exc:
        # 兜底可观测：环境故障与代码 bug 都打印 traceback（此前静默吞错导致 KB 空无日志）
        import traceback

        traceback.print_exc()
        print(f"[kra][kb] 检索异常: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        kb_status = "unreachable"

    for i, s in enumerate(results, start=1):
        s["ref_no"] = i
    unique_docs = len({s.get("meta", {}).get("document_id") for s in results if s.get("meta")})

    # 落库来源（先清旧，支持追问重跑）
    async with SessionLocal() as db:
        await db.execute(delete(Source).where(Source.task_id == task_id))
        for s in results:
            db.add(
                Source(
                    task_id=task_id,
                    ref_no=s["ref_no"],
                    type=s["type"],
                    title=s["title"],
                    url=s.get("url", ""),
                    snippet=s.get("snippet", ""),
                    relevance=s.get("relevance", 0.0),
                    source_label=s.get("source_label", ""),
                    meta_json=s.get("meta", {}),
                )
            )
        await db.commit()

    if results:
        _emit_sources(task_id, results)
        EVENT_BUS.emit(task_id, "sources_final", {"sources": results})
    else:
        EVENT_BUS.emit(task_id, "kb_status", {"status": kb_status})

    kb_hit = bool(results)
    if kb_hit and state.get("search_mode", "kb_only") == "kb_only":
        # 渐进式检索：KB 已命中且用户未要求外部源 → 跳过论文/网页（省下游精排/打分/上下文成本）
        await _step(task_id, "paper_search", "检索学术论文", "skipped")
        await _step(task_id, "web_search", "搜索网页信息", "skipped")

    await _step(
        task_id, "kb_search", "查询企业知识库", "done",
        {"hits": len(results), "kb_status": kb_status,
         "enhanced": enhanced,
         "duration_ms": int((time.time() - started) * 1000)},
    )
    out: dict = {
        "topic": topic,
        "kb_results": results,
        "metrics": {
            **state.get("metrics", {}),
            "kb_docs": unique_docs,  # 命中的唯一文档数（真实计数）
        },
    }
    if kb_hit and state.get("search_mode", "kb_only") == "kb_only":
        # 清空外部源旧结果（改写重查命中 KB 时，不让上一轮论文/网页残留参与融合）
        out["paper_results"] = []
        out["web_results"] = []
    return out


# ---------------- 学术论文检索（arXiv） ----------------

async def paper_retriever_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    active_query = state.get("query") or state.get("original_query", "")
    started = time.time()

    # Planner 逐源规划：论文不在规划内（且非 KB 未命中升级补查）→ 跳过
    plan = state.get("plan") or ["kb", "paper", "web"]
    if "paper" not in plan and not state.get("external_run"):
        await _step(task_id, "paper_search", "检索学术论文", "skipped")
        return {"paper_results": []}

    await _step(task_id, "paper_search", "检索学术论文", "running")

    raw = await search_papers(active_query, max_results=5)
    results = [
        {
            "title": r["title"],
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "type": "paper",
            "source_label": "学术论文",
            "relevance": round(max(0.0, 0.90 - i * 0.02), 3),  # 启发式（merger 统一精排修正）
            "meta": r.get("meta", {}),
        }
        for i, r in enumerate(raw)
    ]
    if len(results) < 2:
        results = mock_data.mock_paper_sources(mock_data.extract_topic(active_query))

    _emit_sources(task_id, results)
    await _step(
        task_id, "paper_search", "检索学术论文", "done",
        {"hits": len(results), "duration_ms": int((time.time() - started) * 1000)},
    )
    return {"paper_results": results}


# ---------------- 网页信息搜索（Tavily） ----------------

async def web_retriever_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    active_query = state.get("query") or state.get("original_query", "")
    started = time.time()

    # Planner 逐源规划：网页不在规划内（且非 KB 未命中升级补查）→ 跳过
    plan = state.get("plan") or ["kb", "paper", "web"]
    if "web" not in plan and not state.get("external_run"):
        await _step(task_id, "web_search", "搜索网页信息", "skipped")
        return {"web_results": []}

    await _step(task_id, "web_search", "搜索网页信息", "running")

    raw = await search_web(f"{active_query} 最新进展", max_results=5)
    results = [
        {
            "title": r["title"],
            "url": r.get("url", ""),
            "snippet": r.get("snippet", ""),
            "type": "web",
            "source_label": "网页",
            "relevance": round(max(0.0, 0.85 - i * 0.02), 3),
            "meta": r.get("meta", {}),
        }
        for i, r in enumerate(raw)
    ]
    if len(results) < 2:
        results = mock_data.mock_web_sources(mock_data.extract_topic(active_query))

    _emit_sources(task_id, results)
    await _step(
        task_id, "web_search", "搜索网页信息", "done",
        {"hits": len(results), "duration_ms": int((time.time() - started) * 1000)},
    )
    return {"web_results": results}


# ---------------- 三路融合 ----------------

async def merger_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    cands = (
        state.get("kb_results", [])
        + state.get("paper_results", [])
        + state.get("web_results", [])
    )
    if not cands:
        EVENT_BUS.emit(task_id, "sources_final", {"sources": []})
        return {"merged_sources": []}

    # 标题指纹去重
    seen: set[str] = set()
    deduped: list[dict] = []
    for s in cands:
        key = re.sub(r"\s+", "", s["title"])[:40]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)

    # 统一精排：全部候选经 bge-reranker 模型打分（可开关；失败保持原分）
    if settings.rerank_enabled:
        deduped = _apply_rerank(state.get("query") or "", deduped)
    deduped.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)

    final = deduped[:MAX_GRADE_SOURCES]
    for i, s in enumerate(final, start=1):
        s["ref_no"] = i

    # 落库（先清旧，支持重检索/追问重跑）
    async with SessionLocal() as db:
        await db.execute(delete(Source).where(Source.task_id == task_id))
        for s in final:
            db.add(
                Source(
                    task_id=task_id,
                    ref_no=s["ref_no"],
                    type=s["type"],
                    title=s["title"],
                    url=s.get("url", ""),
                    snippet=s.get("snippet", ""),
                    relevance=s.get("relevance", 0.0),
                    source_label=s.get("source_label", ""),
                    meta_json=s.get("meta", {}),
                )
            )
        await db.commit()

    EVENT_BUS.emit(
        task_id,
        "sources_final",
        {
            "sources": [
                {
                    "ref_no": s["ref_no"],
                    "type": s["type"],
                    "title": s["title"],
                    "url": s.get("url", ""),
                    "snippet": s.get("snippet", ""),
                    "relevance": s.get("relevance", 0.0),
                    "source_label": s.get("source_label", ""),
                    "page_nos": s.get("page_nos") or [],
                }
                for s in final
            ]
        },
    )
    return {"merged_sources": final}


# ---------------- Retrieval Grader（相关性评估 + 路由） ----------------

async def grade_documents_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    sources = state.get("merged_sources", [])
    if not sources:
        return {"grade_results": [], "route": "done"}

    llm = get_llm()
    items_block = "\n".join(
        f"[{s['ref_no']}] ({s['source_label']}) {s['title']}\n{s.get('snippet', '')[:150]}"
        for s in sources
    )
    mock_grades = [
        {"ref_no": s["ref_no"], "score": s.get("relevance", 0.0), "reason": "启发式相关度"}
        for s in sources
    ]
    grades = await llm.extract_json(
        GRADE_PROMPT.format(
            query=state.get("original_query", ""), count=len(sources),
            items_block=items_block,
        ),
        mock_grades,
    )
    if not isinstance(grades, list):
        grades = mock_grades

    EVENT_BUS.emit(task_id, "grade_result", {"grades": grades, "query": state.get("query", "")})

    high = [g for g in grades if isinstance(g.get("score"), (int, float)) and g["score"] >= 0.6]
    low = [g for g in grades if isinstance(g.get("score"), (int, float)) and g["score"] < 0.4]
    retry_count = state.get("retry_count", 0)
    if high:
        route = "report"
    elif low and retry_count < 2:
        route = "rewrite"
    else:
        route = "done"
    return {"grade_results": grades, "route": route, "retry_count": retry_count}


# ---------------- 重检索（reason 驱动改写） ----------------

async def rewrite_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    llm = get_llm()
    reasons = [
        f"[{g.get('ref_no')}] {g.get('reason', '')}"
        for g in state.get("grade_results", [])
        if isinstance(g.get("score"), (int, float)) and g["score"] < 0.5
    ]
    feedback = "\n".join(reasons[:8]) or "检索结果整体不相关"
    payload = await llm.extract_json(
        REWRITE_PROMPT.format(query=state.get("original_query", ""), feedback=feedback),
        {"rewritten_query": state.get("original_query", "")},
    )
    new_query = (payload.get("rewritten_query") or state.get("original_query", "")).strip()
    EVENT_BUS.emit(task_id, "rewrite", {"query": new_query})
    next_retry = state.get("retry_count", 0) + 1
    # Research Loop 升级：最终轮（retry 将达上限 2）自动扩大火力——
    # 强制三路全开 + 放宽阈值 + 加大检索量（kb_retriever 读 escalation）
    escalation = next_retry >= 2
    if escalation:
        EVENT_BUS.emit(task_id, "rewrite", {"query": new_query, "escalation": True})
    return {
        "query": new_query,
        "retry_count": next_retry,
        "escalation": escalation,
        "plan": ["kb", "paper", "web"] if escalation else state.get("plan"),
        "search_mode": "multi" if escalation else state.get("search_mode"),
    }


# ---------------- 报告生成（问答式） ----------------

def _first_sentence(text: str) -> str:
    for seg in re.split(r"(?<=[。！？；!?])", text):
        seg = seg.strip()
        if seg:
            return seg[:160]
    return text[:160]


def _excerpt_report(sources: list[dict], lang: str) -> str:
    """无 LLM Key 时：基于真实检索片段的关键句摘录（带标签，不编造）。"""
    if lang == "en":
        lines = ["Answers grounded in enterprise knowledge base:", ""]
        for s in sources:
            lines.append(f"- {_first_sentence(s['snippet'])} [{s['ref_no']}]")
    else:
        lines = ["基于企业知识库的要点：", ""]
        for s in sources:
            lines.append(f"- {_first_sentence(s['snippet'])} [{s['ref_no']}]")
        lines.append("")
        lines.append("（以上内容均摘自知识库片段原文，未添加额外信息。）")
    return "\n".join(lines)


def _verify_citations(report: str, sources: list[dict]) -> tuple[str, list[int]]:
    total = len(sources)
    used = sorted({int(n) for n in re.findall(r"\[(\d+)\]", report) if 1 <= int(n) <= total})

    def _repl(match: re.Match) -> str:
        return match.group(0) if 1 <= int(match.group(1)) <= total else ""

    cleaned = re.sub(r"\[(\d+)\]", _repl, report)
    return cleaned, used


async def report_writer_node(state: ResearchState) -> dict:
    task_id = state["task_id"]
    original_query = state.get("original_query") or state["query"]
    topic = state.get("topic") or mock_data.extract_topic(original_query)
    sources = state.get("merged_sources", [])
    started = time.time()
    await _step(task_id, "report_write", "生成分析报告", "running")

    llm = get_llm()
    lang = state.get("lang", "zh")

    def _build_context_block(srcs: list[dict]) -> str:
        """上下文块：KB 来源优先用章节级 parent 文本（上下文完整），外部来源用 snippet。"""
        lines = []
        for s in srcs:
            parent = (s.get("meta") or {}).get("parent_text")
            content = parent or s.get("snippet", "")
            lines.append(f"[{s['ref_no']}] ({s['title']})\n{content}")
        return "\n".join(lines)

    if not sources:
        if state.get("query_type") == "chat":
            # 闲聊路径：LLM 简短回复（Mock 模式固定回复），流式输出
            chat_prompt = CHAT_PROMPT.format(query=original_query)
            mock_reply = (
                "Hello! I'm your enterprise knowledge assistant. How can I help you?"
                if lang == "en"
                else "你好！我是企业知识库助手，有什么可以帮您？"
            )
            parts: list[str] = []
            async for piece in llm.stream_report(chat_prompt, mock_reply):
                parts.append(piece)
                EVENT_BUS.emit(task_id, "report_token", {"delta": piece})
            report = "".join(parts).strip() or mock_reply
        elif lang == "en":
            report = ("No sufficiently relevant content was found in the knowledge base "
                      "and other sources for this question. Please upload related documents "
                      "or try a different question.")
        else:
            report = ("知识库中未找到足够相关的信息。\n\n"
                      "建议：1) 在 Knowledge Base 页面上传相关企业文档；2) 换一个角度重新提问。")
    else:
        context_block = _build_context_block(sources)
        lang_note = (
            "\nNote: answer entirely in English."
            if lang == "en"
            else ""
        )
        mock_text = _excerpt_report(sources, lang)

        # 第一轮生成
        is_chart_context = "图描述" in context_block or "[图]" in context_block
        prompt_template = CHART_REPORT_PROMPT if is_chart_context else REPORT_PROMPT
        prompt = (
            prompt_template.format(
                query=original_query, context_block=context_block, count=len(sources)
            )
            + lang_note
        )
        parts: list[str] = []
        async for piece in llm.stream_report(prompt, mock_text):
            parts.append(piece)
            EVENT_BUS.emit(task_id, "report_token", {"delta": piece})
        report = "".join(parts).strip()
        if len(report) < 20:
            report = mock_text

        # --- Answer Verification（真实 LLM 模式）---
        if llm.mode == "deepseek" and sources:
            verify_payload = await llm.extract_json(
                VERIFY_PROMPT.format(
                    query=original_query, answer=report, context_block=_build_context_block(sources)
                ),
                {"faithfulness": 1.0, "unsupported_claims": [], "pass": True},
            )
            if isinstance(verify_payload, dict) and not verify_payload.get("pass"):
                # 附核查反馈重生成一次
                claims = verify_payload.get("unsupported_claims") or []
                fix_note = (
                    "\n【修正要求】上一版回答中以下论断缺少知识库依据，请删除或改写为有依据的表述：\n"
                    + "\n".join(f"- {c}" for c in claims[:5])
                )
                prompt2 = (
                    REPORT_PROMPT.format(
                        query=original_query, context_block=context_block, count=len(sources)
                    )
                    + lang_note
                    + fix_note
                )
                parts2: list[str] = []
                async for piece in llm.stream_report(prompt2, mock_text):
                    parts2.append(piece)
                    EVENT_BUS.emit(task_id, "report_token", {"delta": piece})
                report2 = "".join(parts2).strip()
                if len(report2) < 20:
                    report2 = mock_text
                report = report2

    report, used_refs = _verify_citations(report, sources)

    title = mock_data.task_title(topic)
    summary = report[:160].replace("\n", " ")

    async with SessionLocal() as db:
        # 保留历史报告（多轮对话展示），version 递增
        prev_versions = (
            await db.execute(
                select(Report.version).where(Report.task_id == task_id)
            )
        ).scalars().all()
        next_version = (max(prev_versions) if prev_versions else 0) + 1
        db_report = Report(
            task_id=task_id, title=title, summary=summary,
            markdown=report, version=next_version,
        )
        db.add(db_report)
        await db.flush()
        src_rows = (
            await db.execute(select(Source).where(Source.task_id == task_id))
        ).scalars().all()
        ref_to_src = {s.ref_no: s.id for s in src_rows}
        for ref in used_refs:
            if ref in ref_to_src:
                db.add(
                    Citation(
                        report_id=db_report.id,
                        ref_no=ref,
                        source_id=ref_to_src[ref],
                        claim_text="",
                    )
                )
        metrics = state.get("metrics", {})
        # docs_processed：真实命中的唯一文档数（KB-only 口径）
        docs_processed = int(metrics.get("kb_docs", len(sources) if sources else 0))
        duration = round(time.time() - float(metrics.get("t0", started)), 1)
        relevance_avg = (
            round(sum(s.get("relevance", 0.0) for s in sources) / len(sources) * 100)
            if sources else 0
        )
        stats = {
            "duration_sec": duration,
            "sources_count": len(sources),
            "docs_processed": docs_processed,
            "relevance_avg": relevance_avg,
            "citations_count": len(used_refs),
        }
        task = await db.get(ResearchTask, task_id)
        if task:
            task.status = "done"
            task.duration_sec = duration
            task.stats_json = stats
            task.completed_at = _now()
        await db.commit()
        report_id = db_report.id

    await _step(
        task_id, "report_write", "生成分析报告", "done",
        {"hits": len(used_refs), "duration_ms": int((time.time() - started) * 1000)},
    )
    EVENT_BUS.emit(
        task_id,
        "report_completed",
        {"report_id": report_id, "title": title, "stats": stats, "citations": used_refs},
    )
    return {"report_md": report, "report_title": title, "metrics": {**metrics, **stats}}


async def on_error(task_id: str, message: str) -> None:
    async with SessionLocal() as db:
        task = await db.get(ResearchTask, task_id)
        if task:
            task.status = "failed"
            task.completed_at = _now()
            await db.commit()
    EVENT_BUS.emit(task_id, "error", {"message": message})
