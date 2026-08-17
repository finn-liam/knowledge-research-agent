"""时间序列化助手。

SQLite 不保存时区信息，SQLAlchemy 读回的 naive datetime 实际值为 UTC。
isoformat() 对 naive 输出不带时区标记，前端 JS 会按本地时区误解析（产生时区偏移量偏差）。
统一在此补 UTC 标记：输出 "+00:00" 后缀。
"""
from datetime import datetime, timezone


def fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
