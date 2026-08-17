"""Sources 分类统计（首页面板）：3 类真实聚合计数（学术/网页检索已恢复）。"""
from fastapi import APIRouter
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.research import Source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/stats")
async def source_stats():
    async with SessionLocal() as db:
        rows = (
            await db.execute(select(Source.type, func.count(Source.id)).group_by(Source.type))
        ).all()
    counts = {t: n for t, n in rows}
    return {
        "items": [
            {"category": "enterprise", "label": "企业内部文档", "count": counts.get("enterprise", 0)},
            {"category": "paper", "label": "学术论文", "count": counts.get("paper", 0)},
            {"category": "web", "label": "网页资源", "count": counts.get("web", 0)},
        ]
    }
