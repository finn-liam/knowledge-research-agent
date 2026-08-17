"""建表初始化（Sources 统计为真实聚合，无种子数据）。"""
from app.db.session import Base, engine
from app.models import research as _models  # noqa: F401  确保全部模型注册


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
