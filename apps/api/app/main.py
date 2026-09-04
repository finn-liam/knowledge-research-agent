"""FastAPI 应用入口：uvicorn app.main:app --reload --port 8000"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import analytics, documents, research, sources
from app.core.config import get_settings
from app.db.init_db import init_db
from app.llm.gateway import get_llm

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _recover_stale_tasks()
    llm = get_llm()
    print(f"[kra] LLM mode = {llm.mode} | Tavily = {settings.tavily_enabled}")
    asyncio.create_task(_warmup_models())
    yield


async def _warmup_models() -> None:
    """后台预热本地模型：首问不再承担模型加载耗时（CPU 上约 20-40s）。

    模型加载/推理是同步 CPU 密集操作，必须放线程池执行——
    直接在协程里调用会阻塞事件循环（/health 等全部接口无响应）。失败静默（首次真实调用会再尝试）。
    """
    import time

    t0 = time.time()
    try:
        from app.rag.models import encode_hybrid, get_reranker, rerank_scores

        await asyncio.to_thread(encode_hybrid, ["预热"])
        reranker = await asyncio.to_thread(get_reranker)
        if reranker is not None:
            await asyncio.to_thread(rerank_scores, "预热", ["预热"])
        print(f"[kra] 模型预热完成（{time.time() - t0:.0f}s），首问无需冷加载", flush=True)
    except Exception as exc:
        print(f"[kra] 模型预热跳过：{type(exc).__name__}: {exc}", flush=True)


async def _recover_stale_tasks() -> None:
    """服务重启后：把遗留 running 任务标记为 failed（避免历史任务永远'处理中'）。"""
    from sqlalchemy import select, update

    from app.db.session import SessionLocal
    from app.models.research import ResearchTask

    async with SessionLocal() as db:
        stale = (
            await db.execute(select(ResearchTask).where(ResearchTask.status == "running"))
        ).scalars().all()
        for t in stale:
            t.status = "failed"
            t.stats_json = {**(t.stats_json or {}), "interrupted": "服务重启中断"}
        if stale:
            await db.commit()
            print(f"[kra] 已清理 {len(stale)} 个遗留 running 任务")


app = FastAPI(title="Knowledge Research Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(documents.documents_router, prefix="/api/v1")
app.include_router(documents.kb_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "llm_mode": get_llm().mode}
