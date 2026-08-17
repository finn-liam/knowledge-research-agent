"""清理冒烟测试产生的失败任务，保持演示数据干净。"""
import asyncio

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.research import (
    Citation,
    Message,
    Report,
    ResearchStep,
    ResearchTask,
    Source,
)


async def main() -> None:
    async with SessionLocal() as db:
        failed = (
            await db.execute(select(ResearchTask).where(ResearchTask.status == "failed"))
        ).scalars().all()
        for t in failed:
            report_ids = (
                await db.execute(select(Report.id).where(Report.task_id == t.id))
            ).scalars().all()
            if report_ids:
                await db.execute(delete(Citation).where(Citation.report_id.in_(report_ids)))
            await db.execute(delete(Report).where(Report.task_id == t.id))
            await db.execute(delete(Source).where(Source.task_id == t.id))
            await db.execute(delete(Message).where(Message.task_id == t.id))
            await db.execute(delete(ResearchStep).where(ResearchStep.task_id == t.id))
            await db.execute(delete(ResearchTask).where(ResearchTask.id == t.id))
            print(f"deleted failed task {t.id}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
