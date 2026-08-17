"""研究任务生命周期：创建 → 后台运行 LangGraph → 追问重跑。"""
import asyncio
import time
import uuid

from sqlalchemy import delete, select

from app.agents import mock_data, nodes
from app.agents.events import EVENT_BUS
from app.agents.graph import get_research_graph
from app.db.session import SessionLocal
from app.models.research import STEP_DEFS, Message, ResearchStep, ResearchTask, Source


async def create_task(query: str, lang: str = "zh") -> str:
    topic = mock_data.extract_topic(query)
    task_id = str(uuid.uuid4())
    async with SessionLocal() as db:
        db.add(
            ResearchTask(
                id=task_id,
                title=mock_data.task_title(topic),
                query=query,
                mode="deep",
                status="running",
            )
        )
        for idx, (key, label) in enumerate(STEP_DEFS):
            # 学术/网页检索已恢复；知识图谱构建保持暂停
            status = "paused" if key == "graph_build" else "pending"
            db.add(
                ResearchStep(
                    task_id=task_id, step_key=key, label=label,
                    order_index=idx, status=status,
                )
            )
        db.add(Message(task_id=task_id, role="user", content=query))
        await db.commit()
    return task_id


async def _run(task_id: str, query: str, lang: str = "zh") -> None:
    EVENT_BUS.open(task_id)
    t0 = time.time()
    try:
        graph = get_research_graph()
        await graph.ainvoke(
            {
                "task_id": task_id,
                "query": query,
                "original_query": query,
                "lang": lang,
                "metrics": {"t0": t0},
                "errors": [],
            }
        )
    except Exception as exc:  # 任何节点异常都不中断 SSE，转为 error 事件
        await nodes.on_error(task_id, f"{type(exc).__name__}: {exc}")
    finally:
        EVENT_BUS.emit(task_id, "stream_end", {})


def launch(task_id: str, query: str, lang: str = "zh") -> None:
    asyncio.create_task(_run(task_id, query, lang))


async def followup(task_id: str, query: str, lang: str = "zh") -> bool:
    """追问：追加用户消息，重置步骤/来源，按新问题重跑流水线。"""
    async with SessionLocal() as db:
        task = await db.get(ResearchTask, task_id)
        if task is None:
            return False
        task.status = "running"
        task.query = query
        db.add(Message(task_id=task_id, role="user", content=query))
        steps = (
            await db.execute(select(ResearchStep).where(ResearchStep.task_id == task_id))
        ).scalars().all()
        for s in steps:
            # 追问重置时保持图谱步骤 paused
            s.status = "paused" if s.step_key == "graph_build" else "pending"
            s.started_at = None
            s.finished_at = None
            s.meta_json = {}
        await db.execute(delete(Source).where(Source.task_id == task_id))
        await db.commit()
    EVENT_BUS.reset(task_id)
    asyncio.create_task(_run(task_id, query, lang))
    return True
