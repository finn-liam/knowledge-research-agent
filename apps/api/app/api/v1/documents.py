"""知识库文档管理：上传 / 列表 / 详情(含 chunk 预览) / 删除 / KB 统计。"""
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.timeutil import fmt_dt
from app.db.session import SessionLocal
from app.models.research import Document, DocumentChunk
from app.rag.vector_store import get_vector_store
from app.schemas.documents import (
    ChunkOut,
    DocumentDetailOut,
    DocumentOut,
    KbStats,
    UploadResponse,
)
from app.services.ingestion_service import (
    MAX_FILE_BYTES,
    UPLOAD_DIR,
    ingest_document,
    save_upload,
)

documents_router = APIRouter(prefix="/documents", tags=["documents"])
kb_router = APIRouter(prefix="/kb", tags=["kb"])

settings = get_settings()
MAX_FILES_PER_BATCH = 5


@documents_router.post("", response_model=UploadResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(status_code=422, detail=f"单次最多上传 {MAX_FILES_PER_BATCH} 个文件")
    items = []
    async with SessionLocal() as db:
        for f in files:
            content = await f.read()
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=422, detail=f"{f.filename} 超过 {settings.max_upload_mb}MB 限制")
            try:
                doc_type, relative = save_upload(f.filename or "unnamed", content)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            doc = Document(
                name=f.filename or "unnamed",
                doc_type=doc_type,
                size_bytes=len(content),
                file_path=relative,
                status="pending",
            )
            db.add(doc)
            await db.flush()
            doc_id = doc.id
            items.append({"id": doc_id, "name": doc.name, "doc_type": doc.doc_type, "status": "pending"})
        await db.commit()

    for item in items:
        background_tasks.add_task(ingest_document, item["id"])
    return UploadResponse(items=items)


@documents_router.get("", response_model=list[DocumentOut])
async def list_documents():
    async with SessionLocal() as db:
        rows = (
            await db.execute(select(Document).order_by(Document.created_at.desc()))
        ).scalars().all()
    return [
        DocumentOut(
            id=d.id,
            name=d.name,
            doc_type=d.doc_type,
            size_bytes=d.size_bytes,
            status=d.status,
            error_msg=d.error_msg,
            chunk_count=d.chunk_count,
            created_at=fmt_dt(d.created_at),
        )
        for d in rows
    ]


@documents_router.get("/{doc_id}", response_model=DocumentDetailOut)
async def get_document(doc_id: int):
    async with SessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        chunks = (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc_id)
                .order_by(DocumentChunk.chunk_index)
                .limit(50)
            )
        ).scalars().all()
    return DocumentDetailOut(
        id=doc.id,
        name=doc.name,
        doc_type=doc.doc_type,
        size_bytes=doc.size_bytes,
        status=doc.status,
        error_msg=doc.error_msg,
        chunk_count=doc.chunk_count,
        chunks=[ChunkOut(id=c.id, chunk_index=c.chunk_index, text=c.text) for c in chunks],
    )


@documents_router.delete("/{doc_id}")
async def delete_document(doc_id: int):
    async with SessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        file_path = doc.file_path
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
        await db.execute(delete(Document).where(Document.id == doc_id))
        await db.commit()
    # 联动删除 Qdrant 向量（失败不阻塞，下次检索按 document_id 无命中）
    try:
        await get_vector_store().delete_by_document(doc_id)
    except Exception:
        pass
    if file_path:
        try:
            (UPLOAD_DIR / file_path).unlink(missing_ok=True)
        except OSError:
            pass
    return {"ok": True}


@kb_router.get("/chunk")
async def kb_chunk(document_id: int, chunk_index: int):
    """按 document_id + chunk_index 返回完整片段全文（来源溯源查看）。"""
    async with SessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="document not found")
        chunk = (
            await db.execute(
                select(DocumentChunk).where(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.chunk_index == chunk_index,
                )
            )
        ).scalar_one_or_none()
        if chunk is None:
            raise HTTPException(status_code=404, detail="chunk not found")
        return {
            "document_id": document_id,
            "document_name": doc.name,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
        }


@kb_router.get("/stats", response_model=KbStats)
async def kb_stats():
    store = get_vector_store()
    try:
        await store.ensure_collection()
        ready = True
    except Exception:
        ready = False
    async with SessionLocal() as db:
        documents = (await db.execute(select(func.count(Document.id)))).scalar() or 0
        chunks = (await db.execute(select(func.count(DocumentChunk.id)))).scalar() or 0
        indexed = (
            await db.execute(
                select(func.count(Document.id)).where(Document.status == "indexed")
            )
        ).scalar() or 0
        processing = (
            await db.execute(
                select(func.count(Document.id)).where(Document.status.in_(["pending", "parsing", "embedding"]))
            )
        ).scalar() or 0
        failed = (
            await db.execute(
                select(func.count(Document.id)).where(Document.status == "failed")
            )
        ).scalar() or 0
    return KbStats(
        documents=documents,
        chunks=chunks,
        indexed=indexed,
        processing=processing,
        failed=failed,
        vector_store_ready=ready,
    )
