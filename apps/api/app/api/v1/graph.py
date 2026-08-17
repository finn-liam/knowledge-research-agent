"""知识图谱子图查询。"""
from fastapi import APIRouter, HTTPException

from app.db.session import SessionLocal
from app.models.research import ResearchTask

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/subgraph")
async def subgraph(task_id: str):
    async with SessionLocal() as db:
        task = await db.get(ResearchTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task.graph_json or {"nodes": [], "edges": []}
