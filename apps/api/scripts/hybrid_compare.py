"""混合检索对比测试：术语型提问，纯 dense vs 双路 RRF 融合的命中对比。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.nodes import _fuse_hybrid  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.rag.models import encode_hybrid  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402

settings = get_settings()
QUERIES = ["650 token 切片", "bge-m3 向量模型", "切片策略", "LangGraph 编排"]


async def main() -> int:
    store = get_vector_store()
    await store.ensure_collection()
    print(f"[hybrid] 集合 chunks = {await store.count()}", flush=True)

    for q in QUERIES:
        dense_vecs, sparse_vecs = await asyncio.to_thread(encode_hybrid, [q])
        qd = dense_vecs[0]
        dense_hits = await store.search_dense(qd, top_k=20)
        sparse_hits = (
            await store.search_sparse(sparse_vecs[0], top_k=20)
            if sparse_vecs else []
        )
        fused = await _fuse_hybrid(store, dense_hits, sparse_hits, qd)

        def _fmt(hits, n=5):
            return [
                f"{h['document_name'][:18]}·片{h['chunk_index']+1}(d{h.get('score', 0):.2f})"
                for h in hits[:n]
            ]

        print(f"\n=== 提问: {q} ===", flush=True)
        print(f"  纯dense Top5 : {_fmt(dense_hits)}", flush=True)
        print(f"  sparse Top5  : {_fmt(sparse_hits)}", flush=True)
        print(f"  混合RRF Top5 : {_fmt(fused)}", flush=True)

    print("\nHYBRID_COMPARE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
