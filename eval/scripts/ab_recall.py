"""P2 召回优化 A/B：拆解生产路径三要素（多查询/单文档配额/精排）对 ID 级召回的贡献。

ID 级口径：命中 = (document_id, chunk_index) ∈ 标注 relevant_chunks；窗口 K ∈ {8, 12}。
LLM 增强结果缓存到 eval/results/enh_cache.json（已缓存 100 条，重跑零 API 成本）。

用法：python eval/scripts/ab_recall.py [--variants raw,multi,orig_multi]（默认全部）
变体：
  raw           原问题单路 hybrid（基线）
  orig_multi    ★ 原问题当主查询 + sub_queries 变体 + 精排（B1 假设：改写当主路有害的修正方案）
  multi         改写当主查询 + 变体（当前生产组合）
  其余变体见 search_variant()
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from app.agents.mock_data import mock_query_process  # noqa: E402
from app.agents.nodes import (  # noqa: E402
    _apply_rerank,
    _build_enhanced_queries,
    _expand_with_siblings,
    _hybrid_search,
    _multi_query_search,
)
from app.agents.prompts import QUERY_PROCESS_PROMPT  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.llm.gateway import get_llm  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

CACHE_PATH = PROJECT_ROOT / "eval" / "results" / "enh_cache.json"
PER_DOC_CAP = 3
MAX_SUBQ = 2


async def enhance_cached(llm, items) -> dict[str, dict]:
    """批量缓存查询增强结果（rewritten/keywords/sub_queries/hyde）。

    条目缺 hyde 字段（旧版缓存）时回填——HyDE 变体依赖该字段。
    """
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    todo = [
        it["question"] for it in items
        if it["question"] not in cache or "hyde" not in cache[it["question"]]
    ]
    if todo:
        print(f"[ab] 查询增强 {len(todo)} 条（缓存 {len(cache)} 条）...", flush=True)
    for i, q in enumerate(todo):
        processed = await llm.extract_json(
            QUERY_PROCESS_PROMPT.format(query=q), mock_query_process(q)
        )
        cache[q] = {
            "rewritten_query": processed.get("rewritten_query") or q,
            "keywords": processed.get("keywords") or [],
            "sub_queries": processed.get("sub_queries") or [],
            "hyde": str(processed.get("hyde") or ""),
        }
        if (i + 1) % 20 == 0:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[ab] 增强 {i+1}/{len(todo)}", flush=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return cache


async def search_variant(store, it, cache, settings, variant: str) -> list[dict]:
    q = it["question"]
    if variant == "raw":
        return await _hybrid_search(store, q, None, top_k=20)

    p = cache.get(q) or mock_query_process(q)
    sub_qs = [
        s.strip() for s in (p.get("sub_queries") or [])
        if isinstance(s, str) and s.strip() and s.strip() != q
    ][:MAX_SUBQ]
    hyde = str(p.get("hyde") or "").strip()

    # 二批变体：原话主查询 + 子查询 +（HyDE）+（兄弟扩展）+ 精排 —— 与生产结构一致
    if variant in ("sibling", "hyde", "sibling_hyde"):
        pairs = [(q, None)] + [(s, None) for s in sub_qs]
        if "hyde" in variant and hyde and hyde != q:
            pairs.append((hyde, None))
        fused = await _multi_query_search(store, pairs, top_k=20)
        if not fused and (sub_qs or hyde):
            fused = await _hybrid_search(store, q, None, top_k=20)
        if "sibling" in variant and settings.sibling_expand:
            fused = await _expand_with_siblings(fused)
        return _apply_rerank(q, fused)

    if variant == "orig_multi":
        # B1 假设：主查询用用户原话（A/B 实测改写当主路有害），变体承担语义扩展
        pairs = [(q, None)] + [(s, None) for s in sub_qs]
        fused = await _multi_query_search(store, pairs, top_k=20)
        if not fused and sub_qs:
            fused = await _hybrid_search(store, q, None, top_k=20)
        return _apply_rerank(q, fused)

    # legacy 变体（改写当主路系列，保留供对照）
    dense_q, sparse_q = _build_enhanced_queries(p, q)
    if variant == "multi_main":  # 仅主查询增强（无 sub_queries）
        fused = await _hybrid_search(store, dense_q, sparse_q if dense_q != q else None, top_k=20)
    else:
        pairs = [(dense_q, sparse_q if dense_q != q else None)] + [(s, None) for s in sub_qs]
        fused = await _multi_query_search(store, pairs, top_k=20)
    if not fused and (dense_q != q or sub_qs):
        fused = await _hybrid_search(store, q, None, top_k=20)
    if "cap" in variant:  # multi_cap / multi_cap_rerank
        per_doc, capped = {}, []
        for h in fused:
            d = h["document_id"]
            if per_doc.get(d, 0) >= PER_DOC_CAP:
                continue
            per_doc[d] = per_doc.get(d, 0) + 1
            capped.append(h)
        fused = capped
    if variant.endswith("rerank"):
        fused = _apply_rerank(q, fused)
    return fused


def id_pr(hits, rel_ids, k: int) -> tuple[float, float]:
    ids = [(h["document_id"], h["chunk_index"]) for h in hits[:k]]
    overlap = len(set(ids) & rel_ids)
    return (overlap / len(ids) if ids else 0.0, overlap / len(rel_ids) if rel_ids else 0.0)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variants",
        default="raw,orig_multi,sibling,hyde,sibling_hyde",
        help="逗号分隔变体列表（默认 raw,orig_multi,multi,multi_rerank）",
    )
    args = parser.parse_args()

    items = json.loads((PROJECT_ROOT / "eval" / "dataset.json").read_text(encoding="utf-8"))
    store = get_vector_store()
    await store.ensure_collection()
    settings = get_settings()
    llm = get_llm() if settings.query_processing else None

    cache = await enhance_cached(llm, items) if llm else {}
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    # 无 LLM 时多查询变体退化为 raw，只跑 raw 类
    if not llm:
        variants = [v for v in variants if v.startswith("raw")] or ["raw"]

    print(f"[ab] 变体 {variants} | 数据集 {len(items)} 条", flush=True)
    agg = {v: {8: {"p": [], "r": []}, 12: {"p": [], "r": []}} for v in variants}
    for idx, it in enumerate(items):
        rel_ids = set()
        for r in it["relevant_chunks"]:
            d, i = r.split("#")
            rel_ids.add((int(d), int(i)))
        for v in variants:
            hits = await search_variant(store, it, cache, settings, v)
            for k in (8, 12):
                p, r = id_pr(hits, rel_ids, k)
                agg[v][k]["p"].append(p)
                agg[v][k]["r"].append(r)
        if (idx + 1) % 25 == 0:
            print(f"[ab] 进度 {idx+1}/{len(items)}", flush=True)

    def mean(x):
        return sum(x) / len(x) if x else 0.0

    for k in (8, 12):
        print(f"\n===== 窗口 K={k}（ID 级）=====", flush=True)
        print(f"{'变体':<18} {'precision':<10} {'recall':<10}")
        for v in variants:
            print(f"{v:<18} {mean(agg[v][k]['p']):<10.3f} {mean(agg[v][k]['r']):<10.3f}")

    # 保存（合并历史变体结果，只覆盖本次跑的）
    out_path = PROJECT_ROOT / "eval" / "results" / "ab_recall.json"
    out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    for v in variants:
        out[v] = {f"k{k}": {"precision": mean(agg[v][k]["p"]), "recall": mean(agg[v][k]["r"])}
                  for k in (8, 12)}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ab] 已写入 {out_path}", flush=True)
    print("AB_DONE", flush=True)
    return 0


if __name__ == "__main__":
    t0 = time.time()
    code = asyncio.run(main())
    print(f"[ab] 总耗时 {time.time()-t0:.0f}s", flush=True)
    sys.exit(code)
