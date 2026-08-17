"""向量补写：对已切片但 Qdrant 未入库的文档，从 SQLite 读取文本 → 重新嵌入 → 分块 upsert → 状态修复。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.research import Document, DocumentChunk  # noqa: E402
from app.rag.chunker import chunk_page_nos  # noqa: E402
from app.rag.models import encode_hybrid, get_embedder  # noqa: E402
from app.rag.vector_store import get_vector_store  # noqa: E402


async def main() -> int:
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 36
    store = get_vector_store()
    await store.ensure_collection()

    async with SessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc is None:
            print(f"[backfill] 文档 {doc_id} 不存在", flush=True)
            return 1
        chunks = (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc_id)
                .order_by(DocumentChunk.chunk_index)
            )
        ).scalars().all()

    texts = [c.text for c in chunks]
    print(f"[backfill] {doc.name}: {len(texts)} 切片，开始嵌入", flush=True)
    dense_vecs, sparse_vecs = await asyncio.to_thread(encode_hybrid, texts)
    if dense_vecs is None:
        embedder = get_embedder()
        dense_vecs = await asyncio.to_thread(
            lambda: embedder.encode(texts, batch_size=8, normalize_embeddings=True).tolist()
        )
        sparse_vecs = None
    print("[backfill] 嵌入完成，写入 Qdrant（分块 200）", flush=True)

    points = [
        {
            "id": c.id,
            "dense_vector": dense_vecs[i],
            "sparse_vector": (sparse_vecs[i] if sparse_vecs else None),
            "document_id": doc_id,
            "chunk_index": i,
            "document_name": doc.name,
            "text": texts[i],
            "parent_text": c.parent_text,
            "page_nos": chunk_page_nos(texts[i]),
        }
        for i, c in enumerate(chunks)
    ]
    await store.upsert_chunks(points)

    async with SessionLocal() as db:
        d = await db.get(Document, doc_id)
        if d:
            d.status = "indexed"
            d.error_msg = ""
            await db.commit()
    print(f"[backfill] 完成：{len(points)} 点写入，状态 indexed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
