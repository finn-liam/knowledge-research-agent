"""查询增强对比测试：口语化/术语提问，原问题 vs 增强文本的双路检索 Top-5 对比。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.mock_data import mock_query_process  # noqa: E402
from app.agents.nodes import _build_enhanced_queries, _hybrid_search  # noqa: E402
from app.agents.prompts import QUERY_PROCESS_PROMPT  # noqa: E402
from app.llm.gateway import get_llm  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

QUERIES = [
    "切片是咋搞的 650 那个",
    "向量化用的什么模型",
    "RAG 怎么实现检索",
]


async def retrieve(store, dense_text: str, sparse_text: str | None):
    fused = await _hybrid_search(store, dense_text, sparse_text)
    return [
        f"{h['document_name'][:16]}·片{h['chunk_index']+1}(d{h.get('relevance', 0):.2f})"
        for h in fused[:5]
    ]


async def main() -> int:
    store = get_vector_store()
    await store.ensure_collection()
    llm = get_llm()
    print(f"[query_process] chunks = {await store.count()}", flush=True)

    for q in QUERIES:
        processed = await llm.extract_json(
            QUERY_PROCESS_PROMPT.format(query=q), mock_query_process(q)
        )
        dq, sq = _build_enhanced_queries(processed, q)
        print(f"\n=== 提问: {q} ===", flush=True)
        print(f"  dense 文本: {dq[:60]}", flush=True)
        kws = processed.get("keywords") or []
        print(f"  扩展词    : {kws[:8]}", flush=True)
        print(f"  原问题 Top5 : {await retrieve(store, q, None)}", flush=True)
        print(f"  增强   Top5 : {await retrieve(store, dq, sq)}", flush=True)
        # 模拟节点回退：增强为空时用原问题
        if not await _hybrid_search(store, dq, sq):
            fb = await retrieve(store, q, None)
            print(f"  [回退] 增强为空 → 原问题: {fb}", flush=True)

    print("\nQUERY_PROCESS_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
