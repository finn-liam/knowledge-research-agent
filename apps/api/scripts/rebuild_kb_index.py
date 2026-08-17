"""重建知识库向量索引（Parent-Child 迁移）：
从 uploads 原始文件重新解析 → hierarchical 切片（parent+child）→
重写 document_chunks（含 parent_text）→ 双向量重嵌 Qdrant。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.research import Document, DocumentChunk
from app.rag.chunker import chunk_page_nos, chunk_text_hierarchical
from app.rag.models import encode_hybrid, get_embedder
from app.rag.parsers import parse_file
from app.rag.vector_store import get_vector_store
from app.services.ingestion_service import UPLOAD_DIR


async def main() -> int:
    store = get_vector_store()
    await store.drop()
    await store.ensure_collection()
    print("[rebuild] 集合已重建（dense+sparse 双向量）", flush=True)

    async with SessionLocal() as db:
        docs = (
            await db.execute(select(Document).where(Document.status == "indexed"))
        ).scalars().all()

    total = 0
    for doc in docs:
        try:
            text = parse_file(UPLOAD_DIR / doc.file_path, doc.doc_type)
        except Exception as exc:
            print(f"[rebuild] {doc.name} 解析失败: {exc}", flush=True)
            continue
        units = chunk_text_hierarchical(text)
        if not units:
            print(f"[rebuild] {doc.name} 无有效文本", flush=True)
            continue
        child_texts = [u["child"] for u in units]
        parent_texts = [u["parent"] for u in units]

        dense_vecs, sparse_vecs = await asyncio.to_thread(encode_hybrid, child_texts)
        if dense_vecs is None:
            embedder = get_embedder()
            dense_vecs = await asyncio.to_thread(
                lambda: embedder.encode(
                    child_texts, batch_size=8, normalize_embeddings=True
                ).tolist()
            )
            sparse_vecs = None

        async with SessionLocal() as db:
            await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            new_chunks = [
                DocumentChunk(
                    document_id=doc.id, chunk_index=i,
                    text=child_texts[i], parent_text=parent_texts[i],
                )
                for i in range(len(child_texts))
            ]
            db.add_all(new_chunks)
            await db.commit()
            ids = [c.id for c in new_chunks]

        points = [
            {
                "id": chunk_id,
                "dense_vector": dense_vecs[i],
                "sparse_vector": (sparse_vecs[i] if sparse_vecs else None),
                "document_id": doc.id,
                "chunk_index": i,
                "document_name": doc.name,
                "text": child_texts[i],
                "parent_text": parent_texts[i],
                "page_nos": chunk_page_nos(child_texts[i]),
            }
            for i, chunk_id in enumerate(ids)
        ]
        await store.upsert_chunks(points)
        total += len(points)
        print(
            f"[rebuild] {doc.name}: {len(points)} chunks（sparse={'有' if sparse_vecs else '无'}）",
            flush=True,
        )

    print(f"REBUILD_DONE total={total}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
