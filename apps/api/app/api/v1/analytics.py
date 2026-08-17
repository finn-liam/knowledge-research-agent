"""Research Statistics 聚合（首页 + 全局统计）。"""
from fastapi import APIRouter
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.research import ResearchTask, Source

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary():
    async with SessionLocal() as db:
        total_research = (
            await db.execute(select(func.count(ResearchTask.id)))
        ).scalar() or 0
        # Knowledge Sources：累计真实检索到的来源总数
        knowledge_sources = (
            await db.execute(select(func.count(Source.id)))
        ).scalar() or 0
        done_tasks = (
            await db.execute(
                select(ResearchTask).where(ResearchTask.status == "done")
            )
        ).scalars().all()

    docs_processed = sum(int((t.stats_json or {}).get("docs_processed", 0)) for t in done_tasks)
    relevance_vals = [
        int((t.stats_json or {}).get("relevance_avg", 0))
        for t in done_tasks
        if (t.stats_json or {}).get("relevance_avg")
    ]
    accuracy_rate = round(sum(relevance_vals) / len(relevance_vals)) if relevance_vals else 0

    return {
        "total_research": total_research,
        "knowledge_sources": knowledge_sources,
        "documents_processed": docs_processed,
        "accuracy_rate": accuracy_rate,
    }
