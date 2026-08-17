"""知识库文档 API 契约。"""
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    name: str
    doc_type: str
    size_bytes: int
    status: str
    error_msg: str = ""
    chunk_count: int = 0
    created_at: str


class UploadItemOut(BaseModel):
    id: int
    name: str
    doc_type: str
    status: str


class UploadResponse(BaseModel):
    items: list[UploadItemOut]


class ChunkOut(BaseModel):
    id: int
    chunk_index: int
    text: str


class DocumentDetailOut(BaseModel):
    id: int
    name: str
    doc_type: str
    size_bytes: int
    status: str
    error_msg: str = ""
    chunk_count: int = 0
    chunks: list[ChunkOut]


class KbStats(BaseModel):
    documents: int
    chunks: int
    indexed: int
    processing: int
    failed: int
    vector_store_ready: bool
