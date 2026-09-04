"""B4 BM25 对比实验：经典 BM25（jieba 分词）vs 当前生产混合检索的 ID 级召回对比。

动机：面试高频问题"为什么不用 BM25"。与其争论，用同一数据集跑出数字。
口径：ID 级（命中 = (document_id, chunk_index) ∈ 标注），窗口 K ∈ {8, 12}，与 ab_recall 完全一致。
成本：零 API——BM25 是纯内存计算，语料从 SQLite 读切片文本。

用法：python eval/scripts/bm25_compare.py
"""
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from rank_bm25 import BM25Okapi  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.agents.nodes import _apply_rerank, _hybrid_search  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.research import DocumentChunk  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402


def tokenize(text: str) -> list[str]:
    """jieba 分词 + 小写化（BM25 语料与查询用同一分词器）。"""
    import jieba

    return [t.lower() for t in jieba.lcut(text) if t.strip()]


async def load_corpus() -> list[tuple[int, int, str]]:
    """全部知识库切片：(document_id, chunk_index, child_text)。"""
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    DocumentChunk.document_id, DocumentChunk.chunk_index, DocumentChunk.text
                )
            )
        ).all()
    return [(r[0], r[1], r[2] or "") for r in rows]


async def main() -> int:
    items = json.loads((PROJECT_ROOT / "eval" / "dataset.json").read_text(encoding="utf-8"))

    corpus = await load_corpus()
    print(f"[bm25] 语料 {len(corpus)} 切片 | 数据集 {len(items)} 条", flush=True)

    # BM25 索引（纯内存，秒级）
    tokenized = [tokenize(text) for _, _, text in corpus]
    bm25 = BM25Okapi(tokenized)
    id_map = [(d, i) for d, i, _ in corpus]

    # 生产混合检索（对照）
    store = get_vector_store()
    await store.ensure_collection()
    settings = get_settings()

    agg = {"bm25": {8: {"p": [], "r": []}, 12: {"p": [], "r": []}},
           "bm25_rerank": {8: {"p": [], "r": []}, 12: {"p": [], "r": []}},
           "hybrid_prod": {8: {"p": [], "r": []}, 12: {"p": [], "r": []}}}

    for idx, it in enumerate(items):
        q = it["question"]
        rel_ids = set()
        for r in it["relevant_chunks"]:
            d, i = r.split("#")
            rel_ids.add((int(d), int(i)))

        # BM25 检索（top 20，与 hybrid 的 top_k 对齐）
        scores = bm25.get_scores(tokenize(q))
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:20]
        bm25_hits = [
            {"document_id": id_map[i][0], "chunk_index": id_map[i][1],
             "text": corpus[i][2], "relevance": float(scores[i])}
            for i in top if scores[i] > 0
        ]
        bm25_rr = _apply_rerank(q, bm25_hits)  # BM25 + 精排（公平对照：生产也有精排）

        # 生产混合检索（原问题单路 + 精排，即 raw_rerank 口径）
        hybrid = await _hybrid_search(store, q, None, top_k=20)
        hybrid_rr = _apply_rerank(q, hybrid) if settings.rerank_enabled else hybrid

        for k in (8, 12):
            for name, hits in (("bm25", bm25_hits), ("bm25_rerank", bm25_rr),
                               ("hybrid_prod", hybrid_rr)):
                ids = [(h["document_id"], h["chunk_index"]) for h in hits[:k]]
                overlap = len(set(ids) & rel_ids)
                agg[name][k]["p"].append(overlap / len(ids) if ids else 0.0)
                agg[name][k]["r"].append(overlap / len(rel_ids) if rel_ids else 0.0)

        if (idx + 1) % 25 == 0:
            print(f"[bm25] 进度 {idx+1}/{len(items)}", flush=True)

    def mean(x):
        return sum(x) / len(x) if x else 0.0

    out = {}
    for k in (8, 12):
        print(f"\n===== 窗口 K={k}（ID 级）=====", flush=True)
        print(f"{'方案':<16} {'precision':<10} {'recall':<10}")
        for name, label in (("bm25", "BM25"), ("bm25_rerank", "BM25+精排"),
                            ("hybrid_prod", "混合+精排(生产)")):
            p, r = mean(agg[name][k]["p"]), mean(agg[name][k]["r"])
            print(f"{label:<16} {p:<10.3f} {r:<10.3f}")
            out[f"{name}_k{k}"] = {"precision": round(p, 4), "recall": round(r, 4)}

    out_path = PROJECT_ROOT / "eval" / "results" / "bm25_compare.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[bm25] 已写入 {out_path}", flush=True)
    print("BM25_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
