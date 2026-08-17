"""研究任务路由：创建 / 列表 / 详情 / SSE 流 / 追问 / 导出。"""
import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select

from app.agents.events import EVENT_BUS
from app.core.timeutil import fmt_dt
from app.db.session import SessionLocal
from app.models.research import Message, Report, ResearchStep, ResearchTask, Source
from app.schemas.research import (
    CreateResearchRequest,
    CreateResearchResponse,
    FollowupRequest,
    TaskDetailOut,
    TaskSummaryOut,
)
from app.services import research_service

router = APIRouter(prefix="/research", tags=["research"])


def _sse(payload: dict) -> str:
    return f"event: {payload['event']}\ndata: {json.dumps(payload['data'], ensure_ascii=False)}\n\n"


@router.post("", response_model=CreateResearchResponse)
async def create_research(body: CreateResearchRequest):
    task_id = await research_service.create_task(body.query.strip(), body.lang)
    research_service.launch(task_id, body.query.strip(), body.lang)
    async with SessionLocal() as db:
        task = await db.get(ResearchTask, task_id)
        title = task.title if task else ""
    return CreateResearchResponse(task_id=task_id, title=title)


@router.get("", response_model=list[TaskSummaryOut])
async def list_research(limit: int = 20):
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(ResearchTask).order_by(ResearchTask.created_at.desc()).limit(limit)
            )
        ).scalars().all()
    return [
        TaskSummaryOut(
            id=t.id, title=t.title, query=t.query, status=t.status,
            created_at=fmt_dt(t.created_at),
        )
        for t in rows
    ]


@router.get("/{task_id}", response_model=TaskDetailOut)
async def get_research(task_id: str):
    async with SessionLocal() as db:
        task = await db.get(ResearchTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        steps = (
            await db.execute(
                select(ResearchStep)
                .where(ResearchStep.task_id == task_id)
                .order_by(ResearchStep.order_index)
            )
        ).scalars().all()
        sources = (
            await db.execute(
                select(Source).where(Source.task_id == task_id).order_by(Source.ref_no)
            )
        ).scalars().all()
        report = (
            await db.execute(
                select(Report).where(Report.task_id == task_id).order_by(Report.version.desc())
            )
        ).scalars().first()
        all_reports = (
            await db.execute(
                select(Report).where(Report.task_id == task_id).order_by(Report.version.asc())
            )
        ).scalars().all()
        messages = (
            await db.execute(
                select(Message).where(Message.task_id == task_id).order_by(Message.created_at)
            )
        ).scalars().all()

    return TaskDetailOut(
        id=task.id,
        title=task.title,
        query=task.query,
        status=task.status,
        steps=[
            {"step_key": s.step_key, "label": s.label, "order_index": s.order_index,
             "status": s.status, "meta": s.meta_json or {}}
            for s in steps
        ],
        sources=[
            {"ref_no": s.ref_no, "type": s.type, "title": s.title, "url": s.url,
             "snippet": s.snippet, "relevance": s.relevance, "source_label": s.source_label,
             "page_nos": (s.meta_json or {}).get("page_nos", [])}
            for s in sources
        ],
        report=(
            {"id": report.id, "title": report.title, "summary": report.summary,
             "markdown": report.markdown, "version": report.version}
            if report else None
        ),
        reports=[
            {"id": r.id, "title": r.title, "summary": r.summary,
             "markdown": r.markdown, "version": r.version}
            for r in all_reports
        ],
        graph=task.graph_json or {"nodes": [], "edges": []},
        stats=task.stats_json or {},
        messages=[{"role": m.role, "content": m.content} for m in messages],
    )


@router.get("/{task_id}/stream")
async def stream_research(task_id: str):
    async def event_gen():
        queue = EVENT_BUS.subscribe(task_id)
        # 重连重放：过滤 report_token（报告全文由前端 onopen 时拉取详情，避免重复/拼接错乱）
        history = [p for p in EVENT_BUS.history(task_id) if p["event"] != "report_token"]
        seen = {id(p) for p in history}  # 同一 payload 对象引用去重，防重放竞态
        for payload in history:
            yield _sse(payload)
            if payload["event"] == "stream_end":
                return
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
                continue
            if id(payload) in seen:
                continue
            yield _sse(payload)
            if payload["event"] == "stream_end":
                return

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.post("/{task_id}/followup")
async def followup_research(task_id: str, body: FollowupRequest):
    ok = await research_service.followup(task_id, body.query.strip(), body.lang)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found")
    return {"ok": True}


@router.get("/{task_id}/export", response_class=PlainTextResponse)
async def export_research(task_id: str):
    async with SessionLocal() as db:
        report = (
            await db.execute(
                select(Report).where(Report.task_id == task_id).order_by(Report.version.desc())
            )
        ).scalars().first()
    if report is None:
        raise HTTPException(status_code=404, detail="report not ready")
    headers = {"Content-Disposition": f'attachment; filename="report-{task_id[:8]}.md"'}
    return PlainTextResponse(content=report.markdown, headers=headers)
